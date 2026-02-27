from __future__ import annotations

import fitz
import pytest

from immcad_api.services import document_extraction
from immcad_api.services.document_extraction import extract_text_and_page_signals


def _build_pdf_bytes(*, text: str | None = None) -> bytes:
    document = fitz.open()
    page = document.new_page()
    if text:
        page.insert_text((72, 72), text)
    payload = document.tobytes()
    document.close()
    return payload


def _build_jpeg_bytes() -> bytes:
    document = fitz.open()
    page = document.new_page(width=200, height=200)
    payload = page.get_pixmap(matrix=fitz.Matrix(2, 2)).tobytes("jpeg")
    document.close()
    return payload


def test_extract_rejects_unsupported_payload_signature() -> None:
    with pytest.raises(ValueError):
        extract_text_and_page_signals(b"plain-text-payload")


def test_extract_accepts_jpeg_payload_signature() -> None:
    payload = _build_jpeg_bytes()
    result = extract_text_and_page_signals(payload)
    assert result.total_pages == 1


def test_extract_uses_ocr_fallback_for_textless_page(monkeypatch) -> None:
    payload = _build_pdf_bytes()
    monkeypatch.setattr(
        "immcad_api.services.document_extraction._ocr_text_from_page",
        lambda _page: "OCR extracted procedural narrative",
    )

    result = extract_text_and_page_signals(payload)

    assert "OCR extracted procedural narrative" in result.extracted_text
    assert result.total_extracted_char_count > 0


def test_extract_skips_ocr_fallback_when_text_layer_present(monkeypatch) -> None:
    payload = _build_pdf_bytes(text="Native text layer content")

    def _raise_if_called(_page):
        raise AssertionError("OCR fallback should not run for text-layer pages")

    monkeypatch.setattr(
        "immcad_api.services.document_extraction._ocr_text_from_page",
        _raise_if_called,
    )

    result = extract_text_and_page_signals(payload)

    assert "Native text layer content" in result.extracted_text
    assert result.total_extracted_char_count > 0


def test_extract_records_ocr_budget_hit(monkeypatch) -> None:
    payload = _build_pdf_bytes()
    monkeypatch.setenv("IMMCAD_OCR_PAGE_LIMIT", "1")
    monkeypatch.setenv("IMMCAD_OCR_CHAR_LIMIT", "1")
    monkeypatch.setattr(
        "immcad_api.services.document_extraction._can_run_tesseract_ocr",
        lambda: True,
    )
    monkeypatch.setattr(
        "immcad_api.services.document_extraction._ocr_text_from_page",
        lambda _page: "Too Much Text",
    )

    result = extract_text_and_page_signals(payload)

    assert result.used_ocr
    assert result.ocr_limit_hit
    assert "Too Much Text" in result.extracted_text


def test_extract_uses_default_ocr_limits_when_env_values_invalid(monkeypatch) -> None:
    payload = _build_pdf_bytes()
    monkeypatch.setenv("IMMCAD_OCR_PAGE_LIMIT", "not-a-number")
    monkeypatch.setenv("IMMCAD_OCR_CHAR_LIMIT", "also-invalid")
    result = extract_text_and_page_signals(payload)
    assert result.total_pages == 1


def test_extract_returns_value_error_when_fitz_runtime_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(document_extraction, "fitz", None)

    with pytest.raises(ValueError, match="unreadable_document_payload"):
        extract_text_and_page_signals(b"%PDF-1.4\n%fallback\n")
