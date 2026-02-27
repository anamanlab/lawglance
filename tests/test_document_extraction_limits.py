from __future__ import annotations

import fitz

from immcad_api.services.document_extraction import extract_text_and_page_signals


def _build_pdf_bytes(*, pages: int = 1) -> bytes:
    document = fitz.open()
    for _ in range(pages):
        document.new_page()
    payload = document.tobytes()
    document.close()
    return payload


def test_extract_reports_ocr_capability_unavailable_when_engine_cannot_run(
    monkeypatch,
) -> None:
    payload = _build_pdf_bytes()
    monkeypatch.setattr(
        "immcad_api.services.document_extraction._can_run_tesseract_ocr",
        lambda: False,
    )

    result = extract_text_and_page_signals(payload)

    assert result.ocr_capability == "unavailable"
    assert result.ocr_confidence == "not_applicable"


def test_extract_reports_high_ocr_confidence_for_sufficient_ocr_text(monkeypatch) -> None:
    payload = _build_pdf_bytes()
    monkeypatch.setattr(
        "immcad_api.services.document_extraction._can_run_tesseract_ocr",
        lambda: True,
    )
    monkeypatch.setattr(
        "immcad_api.services.document_extraction._ocr_text_from_page",
        lambda _page: (
            "OCR extracted content with enough readable characters to classify as high confidence"
        ),
    )

    result = extract_text_and_page_signals(payload)

    assert result.ocr_capability == "available"
    assert result.used_ocr is True
    assert result.ocr_confidence == "high"


def test_extract_honors_page_limit_and_reports_low_confidence_when_budget_hit(
    monkeypatch,
) -> None:
    payload = _build_pdf_bytes(pages=2)
    monkeypatch.setenv("IMMCAD_OCR_PAGE_LIMIT", "1")
    monkeypatch.setenv("IMMCAD_OCR_CHAR_LIMIT", "200")
    monkeypatch.setattr(
        "immcad_api.services.document_extraction._can_run_tesseract_ocr",
        lambda: True,
    )
    monkeypatch.setattr(
        "immcad_api.services.document_extraction._ocr_text_from_page",
        lambda _page: "short ocr text",
    )

    result = extract_text_and_page_signals(payload)

    assert result.total_pages == 2
    assert result.ocr_pages == 1
    assert result.ocr_limit_hit is True
    assert result.ocr_confidence == "low"
