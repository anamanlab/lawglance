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


def test_pipeline_flags_image_only_pdf_for_ocr_review() -> None:
    service = DocumentIntakeService()
    payload = _build_pdf_bytes()

    result = service.process_file(
        original_filename="scan.pdf",
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
