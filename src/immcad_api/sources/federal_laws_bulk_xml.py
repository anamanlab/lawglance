from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
import hashlib
import re
from typing import Iterable
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

from immcad_api.sources.source_registry import SourceRegistry

_OFFICIAL_NUMBER_PATTERN = re.compile(
    r"/eng/(?:acts|regulations)/([^/]+)/",
    re.IGNORECASE,
)
_FEDERAL_LAWS_SOURCE_ID = "FEDERAL_LAWS_BULK_XML"
_FEDERAL_LAWS_HOSTS = frozenset({"laws-lois.justice.gc.ca", "laws.justice.gc.ca"})


@dataclass(frozen=True)
class FederalLawIndexEntry:
    unique_id: str
    official_number: str
    language: str
    link_to_xml: str
    link_to_html_toc: str | None
    title: str
    current_to_date: date | None


@dataclass(frozen=True)
class FederalLawSectionChunk:
    source_id: str
    official_number: str
    act_title: str
    current_to_date: date | None
    heading_label: str | None
    heading_title: str | None
    section_label: str
    section_title: str | None
    section_url: str | None
    text: str
    content_hash_sha256: str

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["current_to_date"] = (
            self.current_to_date.isoformat() if self.current_to_date else None
        )
        return payload


def _normalize_space(value: str | None) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def _normalize_url(value: str | None) -> str:
    normalized = _normalize_space(value)
    if not normalized:
        return ""
    if normalized.startswith("http://"):
        return "https://" + normalized[len("http://") :]
    return normalized


def _parse_date(value: str | None) -> date | None:
    normalized = _normalize_space(value)
    if not normalized:
        return None
    try:
        return date.fromisoformat(normalized)
    except ValueError:
        return None


def infer_official_number_from_registry_url(url: str) -> str | None:
    match = _OFFICIAL_NUMBER_PATTERN.search(url)
    if not match:
        return None
    return match.group(1)


def target_federal_law_source_ids(registry: SourceRegistry) -> dict[str, str]:
    targets: dict[str, str] = {}
    for source in registry.sources:
        if source.source_id == _FEDERAL_LAWS_SOURCE_ID:
            continue
        if source.source_type not in {"statute", "regulation"}:
            continue
        parsed = urlparse(str(source.url))
        if parsed.hostname is None:
            continue
        if parsed.hostname.lower() not in _FEDERAL_LAWS_HOSTS:
            continue
        official_number = infer_official_number_from_registry_url(parsed.path + "/")
        if not official_number:
            continue
        targets[source.source_id] = official_number
    return targets


def parse_federal_laws_index(payload: bytes) -> list[FederalLawIndexEntry]:
    root = ET.fromstring(payload.decode("utf-8"))
    entries: list[FederalLawIndexEntry] = []
    for tag in ("Acts", "Regulations"):
        container = root.find(tag)
        if container is None:
            continue
        for node in container:
            unique_id = _normalize_space(node.findtext("UniqueId"))
            official_number = _normalize_space(node.findtext("OfficialNumber")) or unique_id
            link_to_xml = _normalize_url(node.findtext("LinkToXML"))
            if not official_number or not link_to_xml:
                continue
            entry = FederalLawIndexEntry(
                unique_id=unique_id,
                official_number=official_number,
                language=_normalize_space(node.findtext("Language")) or "eng",
                link_to_xml=link_to_xml,
                link_to_html_toc=_normalize_url(node.findtext("LinkToHTMLToC")) or None,
                title=_normalize_space(node.findtext("Title")) or "Untitled",
                current_to_date=_parse_date(node.findtext("CurrentToDate")),
            )
            entries.append(entry)
    return entries


def select_index_entry(
    entries: Iterable[FederalLawIndexEntry],
    *,
    identifier: str,
    language: str = "eng",
) -> FederalLawIndexEntry | None:
    normalized_identifier = identifier.lower()
    normalized_language = language.lower()
    fallback: FederalLawIndexEntry | None = None
    for entry in entries:
        if (
            entry.unique_id.lower() != normalized_identifier
            and entry.official_number.lower() != normalized_identifier
        ):
            continue
        if fallback is None:
            fallback = entry
        if entry.language.lower() == normalized_language:
            return entry
    return fallback


def _section_url_from_toc(
    link_to_html_toc: str | None,
    *,
    section_label: str,
) -> str | None:
    if not link_to_html_toc:
        return None
    if "/" not in link_to_html_toc:
        return None
    base = link_to_html_toc.rsplit("/", 1)[0]
    section_slug = re.sub(r"[^0-9A-Za-z_.-]+", "-", section_label).strip("-").lower()
    if not section_slug:
        return None
    return f"{base}/section-{section_slug}.html"


def _section_text(section: ET.Element) -> str:
    fragments: list[str] = []
    for node in section.iter():
        if node.tag in {"Label", "MarginalNote", "TitleText"}:
            continue
        if node.tag != "Text":
            continue
        text_value = _normalize_space(node.text)
        if text_value:
            fragments.append(text_value)
    return _normalize_space(" ".join(fragments))


def parse_federal_law_section_chunks(
    payload: bytes,
    *,
    source_id: str,
    index_entry: FederalLawIndexEntry,
) -> list[FederalLawSectionChunk]:
    root = ET.fromstring(payload.decode("utf-8"))
    body = root.find("Body")
    if body is None:
        return []

    chunks: list[FederalLawSectionChunk] = []
    heading_label: str | None = None
    heading_title: str | None = None

    for node in body:
        if node.tag in {"Heading", "GroupHeading"}:
            label_value = _normalize_space(node.findtext("Label"))
            title_value = _normalize_space(node.findtext("TitleText"))
            heading_label = label_value or None
            heading_title = title_value or None
            continue
        if node.tag != "Section":
            continue

        section_label = _normalize_space(node.findtext("Label"))
        if not section_label:
            continue
        section_title = _normalize_space(node.findtext("MarginalNote")) or None
        text = _section_text(node)
        if not text:
            continue
        section_url = _section_url_from_toc(
            index_entry.link_to_html_toc,
            section_label=section_label,
        )
        content_hash = hashlib.sha256(
            (
                f"{source_id}|{index_entry.official_number}|{section_label}|"
                f"{index_entry.current_to_date.isoformat() if index_entry.current_to_date else ''}|"
                f"{text}"
            ).encode("utf-8")
        ).hexdigest()
        chunks.append(
            FederalLawSectionChunk(
                source_id=source_id,
                official_number=index_entry.unique_id or index_entry.official_number,
                act_title=index_entry.title,
                current_to_date=index_entry.current_to_date,
                heading_label=heading_label,
                heading_title=heading_title,
                section_label=section_label,
                section_title=section_title,
                section_url=section_url,
                text=text,
                content_hash_sha256=content_hash,
            )
        )
    return chunks
