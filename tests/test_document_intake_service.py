from __future__ import annotations

import fitz
import pytest

from immcad_api.services.document_intake_service import DocumentIntakeService


def _build_pdf_bytes(*, text: str | None = None) -> bytes:
    document = fitz.open()
    page = document.new_page()
    if text:
        page.insert_text((72, 72), text)
    payload = document.tobytes()
    document.close()
    return payload


def _build_png_bytes() -> bytes:
    document = fitz.open()
    page = document.new_page(width=200, height=200)
    payload = page.get_pixmap(matrix=fitz.Matrix(2, 2)).tobytes("png")
    document.close()
    return payload


def _classification_candidates(result: object) -> list[object]:
    for field_name in ("classification_candidates", "candidates"):
        value = getattr(result, field_name, None)
        if value is not None:
            assert isinstance(value, list)
            return value
    raise AssertionError("expected classification candidates field on intake result")


def _classification_confidence_bucket(result: object) -> str:
    for field_name in (
        "classification_confidence_bucket",
        "confidence_bucket",
        "classification_confidence",
    ):
        value = getattr(result, field_name, None)
        if isinstance(value, str) and value.strip():
            return value
    raise AssertionError("expected classification confidence bucket field on intake result")


def _candidate_label(candidate: object) -> str:
    if isinstance(candidate, str) and candidate.strip():
        return candidate.strip().lower()
    for key in ("classification", "document_type", "type", "label"):
        value = candidate.get(key) if isinstance(candidate, dict) else getattr(candidate, key, None)
        if isinstance(value, str) and value.strip():
            return value.strip().lower()
    raise AssertionError(f"unsupported candidate payload shape: {candidate!r}")


def _candidate_score(candidate: object) -> float | None:
    for key in ("score", "confidence", "weight"):
        value = candidate.get(key) if isinstance(candidate, dict) else getattr(candidate, key, None)
        if isinstance(value, int | float):
            return float(value)
    return None


def _issue_detail_by_code(result: object, code: str) -> object:
    for detail in getattr(result, "issue_details", []):
        detail_code = getattr(detail, "code", None)
        if detail_code == code:
            return detail
    raise AssertionError(f"expected issue detail for {code}")


def test_pipeline_flags_image_only_pdf_for_ocr_review() -> None:
    service = DocumentIntakeService()
    payload = _build_pdf_bytes()

    result = service.process_file(
        original_filename="scan.pdf",
        payload_bytes=payload,
    )

    assert result.quality_status == "needs_review"
    assert "ocr_required" in result.issues
    assert result.classification == "unclassified"
    assert _classification_confidence_bucket(result) in {"low", "medium", "high"}


def test_pipeline_flags_image_upload_for_ocr_review() -> None:
    service = DocumentIntakeService()
    payload = _build_png_bytes()

    result = service.process_file(
        original_filename="scan.png",
        payload_bytes=payload,
    )

    assert result.quality_status == "needs_review"
    assert "ocr_required" in result.issues


def test_pipeline_assigns_normalized_filename_from_classification() -> None:
    service = DocumentIntakeService()
    payload = _build_pdf_bytes(text="AFFIDAVIT of John Smith sworn today.")

    result = service.process_file(
        original_filename="document 1.PDF",
        payload_bytes=payload,
    )

    assert result.classification == "affidavit"
    assert result.normalized_filename.endswith(".pdf")
    assert "affidavit" in result.normalized_filename
    assert result.quality_status == "processed"
    candidates = _classification_candidates(result)
    candidate_labels = [_candidate_label(candidate) for candidate in candidates]
    assert candidate_labels
    assert candidate_labels[0] == "affidavit"
    candidate_scores = [
        score for candidate in candidates if (score := _candidate_score(candidate)) is not None
    ]
    if len(candidate_scores) >= 2:
        assert candidate_scores == sorted(candidate_scores, reverse=True)
    assert _classification_confidence_bucket(result) in {"low", "medium", "high"}


def test_pipeline_uses_ocr_fallback_for_textless_pages(monkeypatch) -> None:
    service = DocumentIntakeService()
    payload = _build_pdf_bytes()

    monkeypatch.setattr(
        "immcad_api.services.document_extraction._ocr_text_from_page",
        lambda _page: "Notice of Application with supporting procedural background and relief sought.",
    )

    result = service.process_file(
        original_filename="scan.pdf",
        payload_bytes=payload,
    )

    assert result.classification == "notice_of_application"
    assert result.quality_status == "processed"
    assert "ocr_required" not in result.issues


def test_pipeline_reports_ocr_budget_reached(monkeypatch) -> None:
    service = DocumentIntakeService()
    payload = _build_pdf_bytes()
    monkeypatch.setenv("IMMCAD_OCR_PAGE_LIMIT", "1")
    monkeypatch.setenv("IMMCAD_OCR_CHAR_LIMIT", "1")
    monkeypatch.setattr(
        "immcad_api.services.document_extraction._can_run_tesseract_ocr",
        lambda: True,
    )
    monkeypatch.setattr(
        "immcad_api.services.document_extraction._ocr_text_from_page",
        lambda _page: "Noticed text for OCR",
    )

    result = service.process_file(
        original_filename="scan-budget.pdf",
        payload_bytes=payload,
    )

    assert result.used_ocr
    assert "ocr_budget_reached" in result.issues


def test_pipeline_flags_low_classification_confidence_for_review() -> None:
    service = DocumentIntakeService()
    payload = _build_pdf_bytes(
        text=(
            "This filing references the decision and memorandum repeatedly while lacking "
            "strong anchors for either category. The decision and memorandum references are "
            "intentionally ambiguous to force low confidence classification."
        )
    )

    result = service.process_file(
        original_filename="ambiguous.pdf",
        payload_bytes=payload,
    )

    assert result.quality_status == "needs_review"
    assert "classification_low_confidence" in result.issues
    assert _classification_confidence_bucket(result) == "low"


def test_pipeline_accepts_medium_confidence_when_threshold_is_low() -> None:
    service = DocumentIntakeService(
        minimum_classification_confidence_for_auto_processing="low"
    )
    payload = _build_pdf_bytes(
        text=(
            "This filing references the decision and memorandum repeatedly while lacking "
            "strong anchors for either category. The decision and memorandum references are "
            "intentionally ambiguous to force low confidence classification."
        )
    )

    result = service.process_file(
        original_filename="ambiguous-low-threshold.pdf",
        payload_bytes=payload,
    )

    assert result.quality_status == "processed"
    assert "classification_low_confidence" not in result.issues


def test_pipeline_rejects_invalid_classification_threshold() -> None:
    with pytest.raises(
        ValueError,
        match="minimum_classification_confidence_for_auto_processing",
    ):
        DocumentIntakeService(
            minimum_classification_confidence_for_auto_processing="invalid-threshold"
        )


def test_failed_result_for_unreadable_file_includes_actionable_remediation() -> None:
    service = DocumentIntakeService()

    result = service.build_failed_result(
        original_filename="scan.pdf",
        issue="file_unreadable",
    )

    detail = _issue_detail_by_code(result, "file_unreadable")
    assert detail.code == "file_unreadable"
    assert detail.severity == "error"
    assert detail.message
    assert detail.remediation
    assert "upload" in detail.remediation.lower()


@pytest.mark.parametrize(
    ("issue_code", "expected_keyword"),
    [
        ("unsupported_file_type", "pdf"),
        ("upload_size_exceeded", "smaller"),
    ],
)
def test_failed_result_adds_actionable_remediation_for_deterministic_upload_failures(
    issue_code: str,
    expected_keyword: str,
) -> None:
    service = DocumentIntakeService()

    result = service.build_failed_result(
        original_filename="upload.bin",
        issue=issue_code,
    )

    detail = _issue_detail_by_code(result, issue_code)
    assert detail.severity == "error"
    assert detail.message
    assert detail.remediation
    assert expected_keyword in detail.remediation.lower()
