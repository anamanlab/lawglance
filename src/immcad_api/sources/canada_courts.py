from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from email.utils import parsedate_to_datetime
import html
import json
import logging
import re
from typing import Any, Literal
from urllib.parse import urljoin
import xml.etree.ElementTree as ET

LOGGER = logging.getLogger(__name__)


CourtCode = Literal["SCC", "FC", "FCA"]

_COURT_CITATION_PATTERNS: dict[CourtCode, re.Pattern[str]] = {
    "SCC": re.compile(r"\b(19|20)\d{2}\s+SCC\s+\d+\b", re.IGNORECASE),
    "FC": re.compile(r"\b(19|20)\d{2}\s+FC\s+\d+\b", re.IGNORECASE),
    "FCA": re.compile(r"\b(19|20)\d{2}\s+(FCA|CAF)\s+\d+\b", re.IGNORECASE),
}
_SCC_REPORT_CITATION_PATTERN = re.compile(
    r"\[\d{4}\]\s+\d+\s+SCR\s+\d+",
    re.IGNORECASE,
)

_SOURCE_TO_COURT: dict[str, CourtCode] = {
    "SCC_DECISIONS": "SCC",
    "FC_DECISIONS": "FC",
    "FCA_DECISIONS": "FCA",
}


@dataclass(frozen=True)
class CourtDecisionRecord:
    source_id: str
    court_code: CourtCode
    case_id: str
    title: str
    citation: str
    decision_date: date | None
    decision_url: str
    pdf_url: str | None


@dataclass(frozen=True)
class CourtPayloadValidation:
    source_id: str
    records_total: int
    records_valid: int
    records_invalid: int
    errors: list[str]


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    normalized = text.split("T", 1)[0]
    try:
        return date.fromisoformat(normalized)
    except ValueError:
        pass
    try:
        return parsedate_to_datetime(text).date()
    except (ValueError, TypeError):
        return None


def _extract_case_id(value: str | None) -> str:
    if not value:
        return ""
    patterns = (
        r"/item/(\d+)/index\.do",
        r"/en/(\d+)/1/document\.do",
        r"/(\d+)/index\.do",
    )
    for pattern in patterns:
        match = re.search(pattern, value)
        if match:
            return match.group(1)
    return ""


def _derive_pdf_url(decision_url: str) -> str | None:
    if not decision_url:
        return None
    candidate = re.sub(r"/item/(\d+)/index\.do$", r"/\1/1/document.do", decision_url)
    if candidate == decision_url:
        return None
    return candidate


def _extract_citation(text: str, *, court_code: CourtCode) -> str:
    pattern = _COURT_CITATION_PATTERNS[court_code]
    match = pattern.search(text or "")
    if not match:
        return ""
    return re.sub(r"\s+", " ", match.group(0)).strip()


def _dict_text(value: object) -> str | None:
    if isinstance(value, str):
        normalized = value.strip()
        return normalized or None
    if isinstance(value, dict):
        for key in ("#text", "text", "value", "en"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
        for candidate in value.values():
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _iter_json_item_dicts(node: object) -> list[dict[str, Any]]:
    if isinstance(node, list):
        results: list[dict[str, Any]] = []
        for item in node:
            results.extend(_iter_json_item_dicts(item))
        return results
    if isinstance(node, dict):
        results: list[dict[str, Any]] = []
        has_link = any(key in node for key in ("link", "url"))
        has_item_metadata = any(
            key in node
            for key in (
                "title",
                "id",
                "pubDate",
                "date",
                "decisionDate",
                "date_published",
                "date_modified",
            )
        )
        if has_link and has_item_metadata:
            results.append(node)
            return results
        for value in node.values():
            results.extend(_iter_json_item_dicts(value))
        return results
    return []


def parse_scc_json_feed(payload: bytes) -> list[CourtDecisionRecord]:
    raw = json.loads(payload.decode("utf-8"))
    items = _iter_json_item_dicts(raw)

    records: list[CourtDecisionRecord] = []
    for item in items:
        title = _dict_text(item.get("title")) or "Untitled"
        link = _dict_text(item.get("link")) or _dict_text(item.get("url")) or ""
        decision_date = _parse_date(
            _dict_text(item.get("decisionDate"))
            or _dict_text(item.get("publishedDate"))
            or _dict_text(item.get("pubDate"))
            or _dict_text(item.get("date"))
            or _dict_text(item.get("date_published"))
            or _dict_text(item.get("date_modified"))
        )
        citation = (
            _dict_text(item.get("_neutral_citation"))
            or _dict_text(item.get("neutralCitation"))
            or _dict_text(item.get("_report_citation"))
            or _dict_text(item.get("reportCitation"))
            or _extract_citation(
                f"{title} {_dict_text(item.get('description')) or ''}",
                court_code="SCC",
            )
        )
        case_id = (
            _dict_text(item.get("id"))
            or _dict_text(item.get("itemId"))
            or _dict_text(item.get("caseId"))
            or _extract_case_id(link)
        )
        decision_url = link
        pdf_url = _dict_text(item.get("pdf")) or _dict_text(item.get("documentUrl")) or _derive_pdf_url(link)

        if not decision_url:
            continue
        records.append(
            CourtDecisionRecord(
                source_id="SCC_DECISIONS",
                court_code="SCC",
                case_id=(case_id or "").strip(),
                title=title,
                citation=citation,
                decision_date=decision_date,
                decision_url=decision_url,
                pdf_url=pdf_url,
            )
        )
    return records


def parse_fca_decisions_html_feed(payload: bytes) -> list[CourtDecisionRecord]:
    text = payload.decode("utf-8")
    item_pattern = re.compile(
        r'<li class="[^"]*list-item-expanded[^"]*">.*?'
        r'<a[^>]+href="(?P<link>/fca-caf/decisions/en/item/(?P<case_id>\d+)/index\.do)"[^>]*>'
        r"(?P<title>.*?)</a>.*?"
        r'<span class="citation">(?P<citation>[^<]+)</span>.*?'
        r'<span class="publicationDate">(?P<publication_date>\d{4}-\d{2}-\d{2})</span>.*?'
        r'(?:href="(?P<pdf>/fca-caf/decisions/en/\d+/1/document\.do)".*?)?'
        r"</li>",
        re.IGNORECASE | re.DOTALL,
    )

    records: list[CourtDecisionRecord] = []
    for match in item_pattern.finditer(text):
        title = html.unescape(re.sub(r"<[^>]+>", "", match.group("title"))).strip()
        citation = html.unescape(match.group("citation")).strip()
        decision_date = _parse_date(match.group("publication_date"))
        link = urljoin("https://decisions.fca-caf.gc.ca", match.group("link"))
        pdf_relative = match.group("pdf")
        pdf_url = urljoin("https://decisions.fca-caf.gc.ca", pdf_relative) if pdf_relative else _derive_pdf_url(link)

        records.append(
            CourtDecisionRecord(
                source_id="FCA_DECISIONS",
                court_code="FCA",
                case_id=match.group("case_id"),
                title=title or "Untitled",
                citation=citation,
                decision_date=decision_date,
                decision_url=link,
                pdf_url=pdf_url,
            )
        )

    return records


def _xml_text(item: ET.Element, tag_name: str) -> str | None:
    element = item.find(tag_name)
    if element is not None and element.text and element.text.strip():
        return element.text.strip()
    return None


def parse_decisia_rss_feed(payload: bytes, *, source_id: str, court_code: CourtCode) -> list[CourtDecisionRecord]:
    root = ET.fromstring(payload.decode("utf-8"))
    items = root.findall(".//item")

    records: list[CourtDecisionRecord] = []
    for item in items:
        title = _xml_text(item, "title") or "Untitled"
        link = _xml_text(item, "link") or ""
        description = _xml_text(item, "description") or ""
        pub_date = _xml_text(item, "pubDate")
        decision_date = _parse_date(pub_date)
        citation = _extract_citation(f"{title} {description}", court_code=court_code)
        case_id = _extract_case_id(link)
        pdf_url = _derive_pdf_url(link)

        if not link:
            continue
        records.append(
            CourtDecisionRecord(
                source_id=source_id,
                court_code=court_code,
                case_id=case_id,
                title=title,
                citation=citation,
                decision_date=decision_date,
                decision_url=link,
                pdf_url=pdf_url,
            )
        )
    return records


def validate_decision_record(
    record: CourtDecisionRecord,
    *,
    expected_court_code: CourtCode,
    expected_year: int | None = None,
) -> list[str]:
    errors: list[str] = []
    if record.court_code != expected_court_code:
        errors.append("unexpected_court_code")
    if not record.case_id:
        errors.append("missing_case_id")
    if not record.decision_url.startswith("https://"):
        errors.append("invalid_decision_url")
    if not record.citation:
        errors.append("missing_citation")
    else:
        pattern = _COURT_CITATION_PATTERNS[expected_court_code]
        if expected_court_code == "SCC":
            has_valid_scc_citation = bool(
                pattern.search(record.citation)
                or _SCC_REPORT_CITATION_PATTERN.search(record.citation)
            )
            if not has_valid_scc_citation:
                errors.append("invalid_citation_pattern")
        elif not pattern.search(record.citation):
            errors.append("invalid_citation_pattern")
    if expected_year is not None:
        if record.decision_date is None:
            errors.append("missing_decision_date")
        elif record.decision_date.year != expected_year:
            errors.append("decision_year_mismatch")
    return errors


def validate_court_source_payload(
    source_id: str,
    payload: bytes,
    *,
    expected_year: int | None = None,
) -> CourtPayloadValidation | None:
    expected_court_code = _SOURCE_TO_COURT.get(source_id)
    if expected_court_code is None:
        return None

    try:
        if source_id == "SCC_DECISIONS":
            records = parse_scc_json_feed(payload)
        elif source_id == "FC_DECISIONS":
            records = parse_decisia_rss_feed(payload, source_id=source_id, court_code="FC")
        elif source_id == "FCA_DECISIONS":
            try:
                records = parse_decisia_rss_feed(
                    payload,
                    source_id=source_id,
                    court_code="FCA",
                )
            except ET.ParseError:
                records = parse_fca_decisions_html_feed(payload)
            if not records:
                # Decisia can return an HTML listing page instead of RSS for FCA.
                records = parse_fca_decisions_html_feed(payload)
        else:  # pragma: no cover
            return None
    except (json.JSONDecodeError, ET.ParseError, UnicodeDecodeError) as exc:
        LOGGER.warning("Court payload parse failed for %s", source_id, exc_info=exc)
        return CourtPayloadValidation(
            source_id=source_id,
            records_total=0,
            records_valid=0,
            records_invalid=0,
            errors=[f"payload_parse_error: {exc}"],
        )

    errors: list[str] = []
    valid_count = 0
    invalid_count = 0
    for record in records:
        record_errors = validate_decision_record(
            record,
            expected_court_code=expected_court_code,
            expected_year=expected_year,
        )
        if not record_errors:
            valid_count += 1
            continue
        invalid_count += 1
        record_id = record.case_id or "unknown_case_id"
        errors.append(f"{record_id}: {', '.join(record_errors)}")

    return CourtPayloadValidation(
        source_id=source_id,
        records_total=len(records),
        records_valid=valid_count,
        records_invalid=invalid_count,
        errors=errors,
    )
