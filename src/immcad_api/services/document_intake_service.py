from __future__ import annotations

from datetime import date
import re
import uuid

from immcad_api.schemas import DocumentIntakeResult
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


class DocumentIntakeService:
    def __init__(
        self,
        *,
        min_text_char_count_for_processed: int = 25,
        low_confidence_char_count: int = 80,
    ) -> None:
        self.min_text_char_count_for_processed = min_text_char_count_for_processed
        self.low_confidence_char_count = low_confidence_char_count

    @staticmethod
    def _classify_document(extracted_text: str) -> str:
        normalized_text = extracted_text.strip().lower()
        if not normalized_text:
            return "unclassified"

        for classification, phrases in _CLASSIFICATION_RULES:
            if any(phrase in normalized_text for phrase in phrases):
                return classification
        return "unclassified"

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

    def process_file(
        self,
        *,
        original_filename: str,
        payload_bytes: bytes,
    ) -> DocumentIntakeResult:
        file_id = uuid.uuid4().hex[:10]

        try:
            extraction = extract_text_and_page_signals(payload_bytes)
        except ValueError:
            return DocumentIntakeResult(
                file_id=file_id,
                original_filename=original_filename,
                normalized_filename=self._build_normalized_filename(
                    classification="unclassified",
                    original_filename=original_filename,
                    file_id=file_id,
                ),
                classification="unclassified",
                quality_status="failed",
                issues=["file_unreadable"],
            )

        classification = self._classify_document(extraction.extracted_text)
        issues: list[str] = []

        total_chars = extraction.total_extracted_char_count
        if total_chars < self.min_text_char_count_for_processed:
            issues.append("ocr_required")
            quality_status = "needs_review"
        else:
            quality_status = "processed"
            if total_chars < self.low_confidence_char_count:
                issues.append("ocr_low_confidence")

        return DocumentIntakeResult(
            file_id=file_id,
            original_filename=original_filename,
            normalized_filename=self._build_normalized_filename(
                classification=classification,
                original_filename=original_filename,
                file_id=file_id,
            ),
            classification=classification,
            quality_status=quality_status,
            issues=issues,
        )


__all__ = ["DocumentIntakeService"]
