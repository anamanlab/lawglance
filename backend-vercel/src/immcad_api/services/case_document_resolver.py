from __future__ import annotations

from typing import Literal
from urllib.parse import urlparse


PdfStatus = Literal["available", "unavailable"]


def allowed_hosts_for_source(source_url: str) -> set[str]:
    source_host = (urlparse(source_url).hostname or "").strip().lower()
    if not source_host:
        return set()
    return {source_host}


def is_url_allowed_for_source(document_url: str, allowed_hosts: set[str]) -> bool:
    document_host = (urlparse(document_url).hostname or "").strip().lower()
    if not document_host or not allowed_hosts:
        return False
    for allowed_host in allowed_hosts:
        if document_host == allowed_host:
            return True
        if document_host.endswith(f".{allowed_host}"):
            return True
    return False


def resolve_pdf_status_with_reason(
    *,
    document_url: str | None,
    source_url: str,
) -> tuple[PdfStatus, str]:
    if not document_url:
        return "unavailable", "document_url_missing"

    allowed_hosts = allowed_hosts_for_source(source_url)
    if not allowed_hosts:
        return "unavailable", "source_url_invalid"

    if not is_url_allowed_for_source(document_url, allowed_hosts):
        return "unavailable", "document_url_host_untrusted"

    return "available", "document_url_trusted"


def resolve_pdf_status(
    *,
    document_url: str | None,
    source_url: str,
) -> PdfStatus:
    status, _ = resolve_pdf_status_with_reason(
        document_url=document_url,
        source_url=source_url,
    )
    return status
