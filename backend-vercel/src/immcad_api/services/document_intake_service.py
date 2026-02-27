from __future__ import annotations

from datetime import date
import hashlib
import re
import uuid

from immcad_api.policy.document_types import require_canonical_document_type
from immcad_api.schemas import DocumentIntakeResult, DocumentIssue
from immcad_api.services.document_extraction import extract_text_and_page_signals


_CLASSIFICATION_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("notice_of_application", ("notice of application",)),
    ("decision_under_review", ("decision under review", "decision", "order")),
    ("affidavit", ("affidavit", "sworn before", "commissioner for taking affidavits")),
    ("memorandum", ("memorandum", "memorandum of argument", "written representations")),
    ("translation", ("translation", "translated by")),
    ("translator_declaration", ("translator declaration", "certified translation")),
    ("witness_list", ("witness list", "list of witnesses")),
    ("disclosure_package", ("disclosure", "document disclosure")),
    ("appeal_record", ("appeal record",)),
)
_FAILED_ISSUE_TEMPLATES: dict[str, tuple[str, str | None]] = {
    "file_unreadable": (
        "Unable to read the uploaded file.",
        (
            "Open the file and re-save it as a clean PDF or image "
            "(PNG/JPEG/TIFF), then upload again."
        ),
    ),
    "unsupported_file_type": (
        "Unsupported file type.",
        "Convert the file to PDF, PNG, JPEG, or TIFF and upload it again.",
    ),
    "upload_size_exceeded": (
        "File exceeds the upload size limit.",
        "Upload a smaller file by compressing it or splitting it into smaller parts.",
    ),
    "submission_channel_size_exceeded": (
        "File exceeds the size limit for the selected submission channel.",
        (
            "Compress or split the file, then retry. If needed, choose a "
            "submission channel with a higher file-size allowance."
        ),
    ),
}


class DocumentIntakeService:
    def __init__(
        self,
        *,
        min_text_char_count_for_processed: int = 25,
        low_confidence_char_count: int = 80,
        minimum_classification_confidence_for_auto_processing: str = "medium",
    ) -> None:
        self.min_text_char_count_for_processed = min_text_char_count_for_processed
        self.low_confidence_char_count = low_confidence_char_count
        normalized_threshold = (
            str(minimum_classification_confidence_for_auto_processing).strip().lower()
        )
        if normalized_threshold not in {"low", "medium", "high"}:
            raise ValueError(
                "minimum_classification_confidence_for_auto_processing must be low, medium, or high"
            )
        self.minimum_classification_confidence_for_auto_processing = normalized_threshold

    @staticmethod
    def _confidence_rank(value: str | None) -> int:
        rank = {"low": 0, "medium": 1, "high": 2}
        if value is None:
            return 0
        return rank.get(str(value).strip().lower(), 0)

    @staticmethod
    def _normalize_phrase_specificity(phrase: str) -> float:
        return min(len(phrase) / 40.0, 1.0)

    @classmethod
    def _score_classification(
        cls,
        *,
        normalized_text: str,
        phrases: tuple[str, ...],
    ) -> float:
        matched_phrases = [phrase for phrase in phrases if phrase in normalized_text]
        if not matched_phrases:
            return 0.0

        coverage_ratio = len(matched_phrases) / len(phrases)
        best_phrase_specificity = max(
            cls._normalize_phrase_specificity(phrase) for phrase in matched_phrases
        )
        score = 0.45 + (0.4 * coverage_ratio) + (0.15 * best_phrase_specificity)
        return round(min(score, 1.0), 4)

    @staticmethod
    def _resolve_classification_confidence(*, top_score: float, second_score: float) -> str:
        score_gap = max(0.0, top_score - second_score)
        if top_score >= 0.82 and score_gap >= 0.18:
            return "high"
        if top_score >= 0.6 and score_gap >= 0.08:
            return "medium"
        return "low"

    @classmethod
    def _classify_document(
        cls,
        extracted_text: str,
    ) -> tuple[str, list[dict[str, str | float]], str | None]:
        normalized_text = extracted_text.strip().lower()
        if not normalized_text:
            return (
                "unclassified",
                [{"classification": "unclassified", "score": 1.0}],
                "low",
            )

        ranked_candidates: list[tuple[str, float, int]] = []
        for index, (classification, phrases) in enumerate(_CLASSIFICATION_RULES):
            score = cls._score_classification(
                normalized_text=normalized_text,
                phrases=phrases,
            )
            if score <= 0:
                continue
            ranked_candidates.append((classification, score, index))

        if not ranked_candidates:
            return (
                "unclassified",
                [{"classification": "unclassified", "score": 1.0}],
                "low",
            )

        ranked_candidates.sort(key=lambda candidate: (-candidate[1], candidate[2]))
        top_classification, top_score, _ = ranked_candidates[0]
        second_score = ranked_candidates[1][1] if len(ranked_candidates) > 1 else 0.0
        classification_confidence = cls._resolve_classification_confidence(
            top_score=top_score,
            second_score=second_score,
        )
        classification_candidates = [
            {"classification": classification, "score": score}
            for classification, score, _ in ranked_candidates[:3]
        ]
        return top_classification, classification_candidates, classification_confidence

    @staticmethod
    def _slugify_stem(filename: str) -> str:
        stem = filename.rsplit(".", 1)[0].strip().lower()
        stem = re.sub(r"[^a-z0-9]+", "-", stem)
        return stem.strip("-") or "document"

    @classmethod
    def _build_normalized_filename(
        cls,
        *,
        classification: str,
        original_filename: str,
        file_id: str,
    ) -> str:
        stem = cls._slugify_stem(original_filename)
        return f"{classification}-{stem}-{date.today().isoformat()}-{file_id}.pdf"

    def _resolve_ocr_confidence_class(self, *, total_chars: int) -> str:
        if total_chars < self.min_text_char_count_for_processed:
            return "low"
        if total_chars < self.low_confidence_char_count:
            return "medium"
        return "high"

    @staticmethod
    def _resolve_ocr_capability(*, used_ocr: bool, ocr_limit_hit: bool) -> str:
        if used_ocr:
            return "tesseract_used"
        if ocr_limit_hit:
            return "tesseract_limited"
        return "native_text_extraction"

    def _classification_requires_review(self, *, classification_confidence: str | None) -> bool:
        threshold_rank = self._confidence_rank(
            self.minimum_classification_confidence_for_auto_processing
        )
        observed_rank = self._confidence_rank(classification_confidence)
        return observed_rank < threshold_rank

    def process_file(
        self,
        *,
        original_filename: str,
        payload_bytes: bytes,
    ) -> DocumentIntakeResult:
        file_id = uuid.uuid4().hex[:10]
        file_hash = hashlib.sha256(payload_bytes).hexdigest()

        try:
            extraction = extract_text_and_page_signals(payload_bytes)
        except ValueError:
            return self.build_failed_result(
                original_filename=original_filename,
                issue="file_unreadable",
                file_id=file_id,
            )

        (
            classification,
            classification_candidates,
            classification_confidence,
        ) = self._classify_document(extraction.extracted_text)
        issues: list[str] = []

        total_chars = extraction.total_extracted_char_count
        if total_chars < self.min_text_char_count_for_processed:
            issues.append("ocr_required")
            quality_status = "needs_review"
        else:
            quality_status = "processed"
            if total_chars < self.low_confidence_char_count:
                issues.append("ocr_low_confidence")
            if self._classification_requires_review(
                classification_confidence=classification_confidence
            ):
                issues.append("classification_low_confidence")
                quality_status = "needs_review"
        if extraction.ocr_limit_hit:
            issues.append("ocr_budget_reached")

        normalized_classification = require_canonical_document_type(
            classification,
            context=f"intake classification for filename='{original_filename}'",
        )
        return DocumentIntakeResult(
            file_id=file_id,
            original_filename=original_filename,
            normalized_filename=self._build_normalized_filename(
                classification=normalized_classification,
                original_filename=original_filename,
                file_id=file_id,
            ),
            classification=normalized_classification,
            classification_confidence=classification_confidence,
            classification_candidates=classification_candidates,
            quality_status=quality_status,
            issues=issues,
            used_ocr=extraction.used_ocr,
            total_pages=extraction.total_pages,
            page_char_counts=[
                {
                    "page_number": signal.page_number,
                    "extracted_char_count": signal.extracted_char_count,
                }
                for signal in extraction.page_signals
            ],
            file_hash=file_hash,
            ocr_confidence_class=self._resolve_ocr_confidence_class(total_chars=total_chars),
            ocr_capability=self._resolve_ocr_capability(
                used_ocr=extraction.used_ocr,
                ocr_limit_hit=extraction.ocr_limit_hit,
            ),
        )

    def build_failed_result(
        self,
        *,
        original_filename: str,
        issue: str,
        classification: str = "unclassified",
        file_id: str | None = None,
    ) -> DocumentIntakeResult:
        resolved_file_id = file_id or uuid.uuid4().hex[:10]
        return DocumentIntakeResult(
            file_id=resolved_file_id,
            original_filename=original_filename,
            normalized_filename=self._build_normalized_filename(
                classification=classification,
                original_filename=original_filename,
                file_id=resolved_file_id,
            ),
            classification=classification,
            quality_status="failed",
            issues=[issue],
            issue_details=[self.issue_detail_for_failed_result(issue=issue)],
        )

    @staticmethod
    def issue_detail_for_failed_result(*, issue: str) -> DocumentIssue:
        normalized_issue = str(issue).strip().lower() or "document_processing_failed"
        message, remediation = _FAILED_ISSUE_TEMPLATES.get(
            normalized_issue,
            (
                "Document intake failed while processing this file.",
                (
                    "Try uploading the file again. If the issue continues, "
                    "replace the file with a clean export."
                ),
            ),
        )
        return DocumentIssue(
            code=normalized_issue,
            message=message,
            severity="error",
            remediation=remediation,
        )


__all__ = ["DocumentIntakeService"]
