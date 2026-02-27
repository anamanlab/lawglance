from __future__ import annotations

from immcad_api.policy.document_requirements import FilingForum
from immcad_api.schemas import DocumentIntakeResult
from immcad_api.services.document_extraction import DocumentExtractionResult, PageSignal
from immcad_api.services.document_intake_service import DocumentIntakeService
from immcad_api.services.document_matter_store import InMemoryDocumentMatterStore


def test_intake_service_populates_compilation_metadata(monkeypatch) -> None:
    def _stub_extract(payload_bytes: bytes) -> DocumentExtractionResult:
        del payload_bytes
        return DocumentExtractionResult(
            extracted_text="Notice of application\nExample text",
            total_pages=2,
            total_extracted_char_count=48,
            page_signals=(
                PageSignal(page_number=1, extracted_char_count=30),
                PageSignal(page_number=2, extracted_char_count=18),
            ),
            used_ocr=True,
            ocr_pages=1,
            ocr_char_count=18,
            ocr_limit_hit=False,
        )

    monkeypatch.setattr(
        "immcad_api.services.document_intake_service.extract_text_and_page_signals",
        _stub_extract,
    )

    service = DocumentIntakeService(min_text_char_count_for_processed=1)
    result = service.process_file(original_filename="notice.pdf", payload_bytes=b"%PDF")

    assert result.total_pages == 2
    assert result.page_char_counts[0].page_number == 1
    assert result.page_char_counts[1].extracted_char_count == 18
    assert result.file_hash
    assert result.ocr_confidence_class in {"high", "medium", "low"}
    assert result.ocr_capability


def test_in_memory_store_preserves_compilation_state_metadata() -> None:
    store = InMemoryDocumentMatterStore()
    stored_result = DocumentIntakeResult(
        file_id="file-state-1",
        original_filename="notice.pdf",
        normalized_filename="notice.pdf",
        classification="notice_of_application",
        quality_status="processed",
        issues=[],
        total_pages=3,
        page_char_counts=[
            {"page_number": 1, "extracted_char_count": 90},
            {"page_number": 2, "extracted_char_count": 75},
            {"page_number": 3, "extracted_char_count": 60},
        ],
        file_hash="abc12345",
        ocr_confidence_class="high",
        ocr_capability="tesseract_available",
    )

    store.put(
        client_id="198.51.100.70",
        matter_id="matter-state",
        forum=FilingForum.FEDERAL_COURT_JR,
        results=[stored_result],
    )
    loaded = store.get(client_id="198.51.100.70", matter_id="matter-state")

    assert loaded is not None
    assert loaded.results[0].total_pages == 3
    assert loaded.results[0].page_char_counts[2].page_number == 3
    assert loaded.results[0].file_hash == "abc12345"
