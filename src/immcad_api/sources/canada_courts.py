from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from email.utils import parsedate_to_datetime
import json
import re
from typing import Any, Literal
import xml.etree.ElementTree as ET


CourtCode = Literal["SCC", "FC", "FCA"]

_COURT_CITATION_PATTERNS: dict[CourtCode, re.Pattern[str]] = {
    "SCC": re.compile(r"\b(19|20)\d{2}\s+SCC\s+\d+\b", re.IGNORECASE),
    "FC": re.compile(r"\b(19|20)\d{2}\s+FC\s+\d+\b", re.IGNORECASE),
    "FCA": re.compile(r"\b(19|20)\d{2}\s+(FCA|CAF)\s+\d+\b", re.IGNORECASE),
}

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
class CourtPayloadValidationConfig:
    max_invalid_ratio: float = 0.0
    min_valid_records: int = 1
    expected_year: int | None = None
    year_window: int = 0

    def __post_init__(self) -> None:
        if not 0.0 <= self.max_invalid_ratio <= 1.0:
            raise ValueError("max_invalid_ratio must be between 0.0 and 1.0")
        if self.min_valid_records < 0:
            raise ValueError("min_valid_records must be >= 0")
        if self.year_window < 0:
            raise ValueError("year_window must be >= 0")


@dataclass(frozen=True)
class CourtPayloadValidation:
    source_id: str
    records_total: int
    records_valid: int
    records_invalid: int
    errors: list[str]

    @property
    def invalid_ratio(self) -> float:
        if self.records_total <= 0:
            return 1.0
        return self.records_invalid / self.records_total


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
    return None


def _iter_json_item_dicts(node: object) -> list[dict[str, Any]]:
    if isinstance(node, list):
        results: list[dict[str, Any]] = []
        for item in node:
            results.extend(_iter_json_item_dicts(item))
        return results
    if isinstance(node, dict):
        results: list[dict[str, Any]] = []
        if any(key in node for key in ("title", "link", "url", "pubDate", "date", "decisionDate")):
            results.append(node)
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
        )
        citation = _extract_citation(
            f"{title} {_dict_text(item.get('description')) or ''}",
            court_code="SCC",
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
    year_window: int = 0,
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
        if not pattern.search(record.citation):
            errors.append("invalid_citation_pattern")
    if expected_year is not None:
        if record.decision_date is None:
            errors.append("missing_decision_date")
        else:
            min_year = expected_year - year_window
            max_year = expected_year + year_window
            if not (min_year <= record.decision_date.year <= max_year):
                if year_window > 0:
                    errors.append("decision_year_out_of_window")
                else:
                    errors.append("decision_year_mismatch")
    return errors


def validate_court_source_payload(
    source_id: str,
    payload: bytes,
    *,
    validation_config: CourtPayloadValidationConfig | None = None,
) -> CourtPayloadValidation | None:
    expected_court_code = _SOURCE_TO_COURT.get(source_id)
    if expected_court_code is None:
        return None

    config = validation_config or CourtPayloadValidationConfig()

    if source_id == "SCC_DECISIONS":
        records = parse_scc_json_feed(payload)
    elif source_id == "FC_DECISIONS":
        records = parse_decisia_rss_feed(payload, source_id=source_id, court_code="FC")
    elif source_id == "FCA_DECISIONS":
        records = parse_decisia_rss_feed(payload, source_id=source_id, court_code="FCA")
    else:  # pragma: no cover
        return None

    errors: list[str] = []
    valid_count = 0
    invalid_count = 0
    for record in records:
        record_errors = validate_decision_record(
            record,
            expected_court_code=expected_court_code,
            expected_year=config.expected_year,
            year_window=config.year_window,
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

