from __future__ import annotations

from dataclasses import dataclass
import io
import logging
import os
import shutil

import fitz

try:
    from PIL import Image
except Exception:  # pragma: no cover - optional OCR dependency
    Image = None  # type: ignore[assignment]

try:
    import pytesseract
except Exception:  # pragma: no cover - optional OCR dependency
    pytesseract = None  # type: ignore[assignment]

LOGGER = logging.getLogger(__name__)


def _normalize_signature(payload_bytes: bytes) -> bytes:
    normalized = payload_bytes.lstrip(b"\x00\t\r\n\f ")
    if normalized.startswith(b"\xef\xbb\xbf"):
        return normalized[3:]
    return normalized


def _detect_supported_filetype(payload_bytes: bytes) -> str | None:
    normalized = _normalize_signature(payload_bytes)
    if normalized.startswith(b"%PDF-") or b"%PDF-" in normalized[:16]:
        return "pdf"
    if normalized.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if normalized.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if normalized.startswith(b"II*\x00") or normalized.startswith(b"MM\x00*"):
        return "tiff"
    return None


@dataclass(frozen=True)
class PageSignal:
    page_number: int
    extracted_char_count: int


@dataclass(frozen=True)
class DocumentExtractionResult:
    extracted_text: str
    total_pages: int
    total_extracted_char_count: int
    page_signals: tuple[PageSignal, ...]
    used_ocr: bool
    ocr_pages: int
    ocr_char_count: int
    ocr_limit_hit: bool
    ocr_capability: str = "unavailable"
    ocr_confidence: str = "not_applicable"


def _is_tesseract_ocr_enabled() -> bool:
    raw_value = os.environ.get("IMMCAD_ENABLE_TESSERACT_OCR", "1").strip().lower()
    return raw_value not in {"0", "false", "no", "off"}


def _can_run_tesseract_ocr() -> bool:
    return (
        _is_tesseract_ocr_enabled()
        and pytesseract is not None
        and Image is not None
        and shutil.which("tesseract") is not None
    )


def _ocr_capability() -> str:
    return "available" if _can_run_tesseract_ocr() else "unavailable"


def _ocr_confidence_class(*, used_ocr: bool, ocr_char_count: int, ocr_limit_hit: bool) -> str:
    if not used_ocr:
        return "not_applicable"
    if ocr_limit_hit:
        return "low"
    if ocr_char_count >= 64:
        return "high"
    if ocr_char_count >= 24:
        return "medium"
    return "low"


def _ocr_text_from_page(page: fitz.Page) -> str:
    if not _can_run_tesseract_ocr():
        return ""

    try:
        # Render at 2x to improve OCR quality on scanned uploads.
        image_bytes = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False).tobytes("png")
        with Image.open(io.BytesIO(image_bytes)) as image:
            return str(pytesseract.image_to_string(image) or "")
    except Exception:
        return ""


def _open_document_for_extraction(payload_bytes: bytes) -> fitz.Document:
    detected_filetype = _detect_supported_filetype(payload_bytes)
    if detected_filetype is None:
        raise ValueError("unreadable_document_payload")
    try:
        return fitz.open(stream=payload_bytes, filetype=detected_filetype)
    except Exception as exc:
        raise ValueError("unreadable_document_payload") from exc


def _positive_int_env(var_name: str, default: int) -> int:
    raw_value = os.environ.get(var_name)
    if raw_value is None:
        return default
    try:
        parsed = int(raw_value)
    except ValueError:
        LOGGER.warning(
            "Invalid integer value for %s=%r; using default %s",
            var_name,
            raw_value,
            default,
        )
        return default
    if parsed <= 0:
        LOGGER.warning(
            "Non-positive value for %s=%r; using default %s",
            var_name,
            raw_value,
            default,
        )
        return default
    return parsed


def _ocr_page_limit() -> int:
    return _positive_int_env("IMMCAD_OCR_PAGE_LIMIT", 16)


def _ocr_char_limit() -> int:
    return _positive_int_env("IMMCAD_OCR_CHAR_LIMIT", 4000)


def extract_text_and_page_signals(payload_bytes: bytes) -> DocumentExtractionResult:
    if not payload_bytes:
        raise ValueError("empty payload")

    document = _open_document_for_extraction(payload_bytes)

    page_signals: list[PageSignal] = []
    text_fragments: list[str] = []
    ocr_pages = 0
    ocr_char_count = 0
    used_ocr = False
    ocr_limit_hit = False
    ocr_capability = _ocr_capability()
    page_limit = _ocr_page_limit()
    char_limit = _ocr_char_limit()

    try:
        for page_index in range(document.page_count):
            try:
                page = document.load_page(page_index)
                page_text = page.get_text("text") or ""
                if not page_text.strip():
                    should_ocr = (
                        _can_run_tesseract_ocr()
                        and ocr_pages < page_limit
                        and ocr_char_count < char_limit
                    )
                    if should_ocr:
                        ocr_result = _ocr_text_from_page(page)
                        trimmed = ocr_result.strip()
                        if trimmed:
                            page_text = trimmed
                            ocr_pages += 1
                            ocr_char_count += len(trimmed)
                            used_ocr = True
                        if ocr_pages >= page_limit or ocr_char_count >= char_limit:
                            ocr_limit_hit = True
                    else:
                        if _can_run_tesseract_ocr():
                            ocr_limit_hit = True
            except Exception as exc:
                raise ValueError("unreadable_document_payload") from exc

            extracted_char_count = len(page_text.strip())
            page_signals.append(
                PageSignal(
                    page_number=page_index + 1,
                    extracted_char_count=extracted_char_count,
                )
            )
            if page_text:
                text_fragments.append(page_text)
    finally:
        document.close()

    extracted_text = "\n".join(fragment for fragment in text_fragments if fragment)
    total_extracted_char_count = sum(signal.extracted_char_count for signal in page_signals)
    ocr_confidence = _ocr_confidence_class(
        used_ocr=used_ocr,
        ocr_char_count=ocr_char_count,
        ocr_limit_hit=ocr_limit_hit,
    )

    return DocumentExtractionResult(
        extracted_text=extracted_text,
        total_pages=len(page_signals),
        total_extracted_char_count=total_extracted_char_count,
        page_signals=tuple(page_signals),
        used_ocr=used_ocr,
        ocr_pages=ocr_pages,
        ocr_char_count=ocr_char_count,
        ocr_limit_hit=ocr_limit_hit,
        ocr_capability=ocr_capability,
        ocr_confidence=ocr_confidence,
    )


__all__ = [
    "PageSignal",
    "DocumentExtractionResult",
    "extract_text_and_page_signals",
]
