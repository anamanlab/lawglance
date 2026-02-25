from __future__ import annotations

from immcad_api.services.case_document_resolver import (
    resolve_pdf_status,
    resolve_pdf_status_with_reason,
)


def test_resolve_pdf_status_marks_unavailable_when_document_url_missing() -> None:
    status = resolve_pdf_status(
        document_url=None,
        source_url="https://decisions.fct-cf.gc.ca",
    )
    assert status == "unavailable"


def test_resolve_pdf_status_marks_unavailable_when_document_url_host_untrusted() -> None:
    status, reason = resolve_pdf_status_with_reason(
        document_url="https://example.com/cases/123.pdf",
        source_url="https://decisions.fct-cf.gc.ca/fc-cf/decisions/en",
    )
    assert status == "unavailable"
    assert reason == "document_url_host_untrusted"


def test_resolve_pdf_status_marks_available_for_trusted_source_host() -> None:
    status, reason = resolve_pdf_status_with_reason(
        document_url="https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/item/123456/index.do",
        source_url="https://decisions.fct-cf.gc.ca/fc-cf/decisions/en",
    )
    assert status == "available"
    assert reason == "document_url_trusted"
