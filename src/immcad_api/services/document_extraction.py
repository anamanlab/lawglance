from __future__ import annotations

from dataclasses import dataclass

import fitz


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


def extract_text_and_page_signals(payload_bytes: bytes) -> DocumentExtractionResult:
    if not payload_bytes:
        raise ValueError("empty payload")

    try:
        document = fitz.open(stream=payload_bytes, filetype="pdf")
    except Exception as exc:
        raise ValueError("unreadable_pdf_payload") from exc

    page_signals: list[PageSignal] = []
    text_fragments: list[str] = []

    for page_index in range(document.page_count):
        page = document.load_page(page_index)
        page_text = page.get_text("text") or ""
        extracted_char_count = len(page_text.strip())
        page_signals.append(
            PageSignal(
                page_number=page_index + 1,
                extracted_char_count=extracted_char_count,
            )
        )
        if page_text:
            text_fragments.append(page_text)

    document.close()

    extracted_text = "\n".join(fragment for fragment in text_fragments if fragment)
    total_extracted_char_count = sum(signal.extracted_char_count for signal in page_signals)

    return DocumentExtractionResult(
        extracted_text=extracted_text,
        total_pages=len(page_signals),
        total_extracted_char_count=total_extracted_char_count,
        page_signals=tuple(page_signals),
    )


__all__ = [
    "PageSignal",
    "DocumentExtractionResult",
    "extract_text_and_page_signals",
]
