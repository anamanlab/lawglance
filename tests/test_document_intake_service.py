from __future__ import annotations

import fitz

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


def test_pipeline_flags_image_only_pdf_for_ocr_review() -> None:
    service = DocumentIntakeService()
    payload = _build_pdf_bytes()

    result = service.process_file(
        original_filename="scan.pdf",
        payload_bytes=payload,
    )

    assert result.quality_status == "needs_review"
    assert "ocr_required" in result.issues


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
