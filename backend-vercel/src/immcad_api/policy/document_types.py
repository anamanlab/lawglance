from __future__ import annotations

import re

_CANONICAL_DOCUMENT_TYPES = frozenset(
    {
        "affidavit",
        "appeal_record",
        "decision_under_review",
        "disclosure_package",
        "index",
        "memorandum",
        "notice_of_application",
        "supporting_evidence",
        "translation",
        "translator_declaration",
        "unclassified",
        "witness_list",
    }
)

_DOCUMENT_TYPE_ALIASES = {
    "notice of application": "notice_of_application",
    "decision under review": "decision_under_review",
    "disclosure package": "disclosure_package",
    "appeal record": "appeal_record",
    "witness list": "witness_list",
    "translator declaration": "translator_declaration",
    "supporting evidence": "supporting_evidence",
}


def canonical_document_types() -> frozenset[str]:
    return _CANONICAL_DOCUMENT_TYPES


def normalize_document_type(value: object) -> str:
    raw = str(value).strip().lower()
    if not raw:
        return ""
    normalized = re.sub(r"[^a-z0-9]+", "_", raw).strip("_")
    if normalized in _CANONICAL_DOCUMENT_TYPES:
        return normalized
    alias_key = raw.replace("-", " ")
    return _DOCUMENT_TYPE_ALIASES.get(alias_key, normalized)


def is_canonical_document_type(value: object) -> bool:
    return normalize_document_type(value) in _CANONICAL_DOCUMENT_TYPES


def require_canonical_document_type(value: object, *, context: str) -> str:
    normalized = normalize_document_type(value)
    if normalized not in _CANONICAL_DOCUMENT_TYPES:
        raise ValueError(f"Unknown document_type '{value}' for {context}")
    return normalized


__all__ = [
    "canonical_document_types",
    "is_canonical_document_type",
    "normalize_document_type",
    "require_canonical_document_type",
]
