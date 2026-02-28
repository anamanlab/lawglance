from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from immcad_api.policy.document_types import require_canonical_document_type


CompilationForum = Literal[
    "federal_court_jr",
    "rpd",
    "rad",
    "id",
    "iad",
    "ircc_application",
]
RuleSeverity = Literal["warning", "blocking"]

DEFAULT_COMPILATION_RULES_RELATIVE_PATH = Path("data/policy/document_compilation_rules.ca.json")
DEFAULT_COMPILATION_RULES_PACKAGE_PATH = (
    Path(__file__).resolve().with_name("document_compilation_rules.ca.json")
)
DEFAULT_COMPILATION_RULES_REPO_PATH = (
    Path(__file__).resolve().parents[3] / DEFAULT_COMPILATION_RULES_RELATIVE_PATH
)

_ALLOWED_FORUMS: tuple[str, ...] = (
    "federal_court_jr",
    "rpd",
    "rad",
    "id",
    "iad",
    "ircc_application",
)


@dataclass(frozen=True)
class RequiredDocumentRule:
    rule_id: str
    document_type: str
    severity: RuleSeverity
    source_url: str
    remediation: str


@dataclass(frozen=True)
class ConditionalDocumentRule:
    rule_id: str
    when_document_type: str
    requires_document_type: str
    severity: RuleSeverity
    source_url: str
    remediation: str


@dataclass(frozen=True)
class OrderRequirements:
    rule_id: str
    document_types: tuple[str, ...]
    source_url: str
    remediation: str


@dataclass(frozen=True)
class PaginationRequirements:
    rule_id: str
    require_continuous_package_pagination: bool
    require_index_document: bool
    index_document_type: str
    source_url: str
    remediation: str


@dataclass(frozen=True)
class DocumentCompilationProfile:
    profile_id: str
    forum: CompilationForum
    title: str
    required_documents: tuple[RequiredDocumentRule, ...]
    conditional_rules: tuple[ConditionalDocumentRule, ...]
    order_requirements: OrderRequirements
    pagination_requirements: PaginationRequirements

    def all_rule_ids(self) -> tuple[str, ...]:
        rule_ids: list[str] = []
        rule_ids.extend(rule.rule_id for rule in self.required_documents)
        rule_ids.extend(rule.rule_id for rule in self.conditional_rules)
        rule_ids.append(self.order_requirements.rule_id)
        rule_ids.append(self.pagination_requirements.rule_id)
        return tuple(rule_ids)


@dataclass(frozen=True)
class DocumentCompilationCatalog:
    version: str
    jurisdiction: str
    profiles: tuple[DocumentCompilationProfile, ...]

    def require_profile(self, profile_id: str) -> DocumentCompilationProfile:
        normalized_profile_id = _normalize_token(profile_id)
        for profile in self.profiles:
            if profile.profile_id == normalized_profile_id:
                return profile
        raise KeyError(f"Unknown document compilation profile: {profile_id}")


def _normalize_token(value: object) -> str:
    return str(value).strip().lower()


def _normalize_severity(value: object, *, rule_id: str) -> RuleSeverity:
    severity = _normalize_token(value)
    if severity not in {"warning", "blocking"}:
        raise ValueError(f"Invalid severity '{severity}' for rule_id='{rule_id}'")
    return severity  # type: ignore[return-value]


def _require_string(
    payload: dict[str, object],
    key: str,
    *,
    context: str,
    normalize: bool = False,
) -> str:
    raw_value = payload.get(key, "")
    value = str(raw_value).strip()
    if not value:
        raise ValueError(f"Missing {key} for {context}")
    if normalize:
        return value.lower()
    return value


def _require_source_url(payload: dict[str, object], *, rule_id: str) -> str:
    source_url = _require_string(payload, "source_url", context=f"rule_id='{rule_id}'")
    parsed = urlparse(source_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"Invalid source_url '{source_url}' for rule_id='{rule_id}'")
    return source_url


def _parse_required_documents(raw_rules: object, *, profile_id: str) -> tuple[RequiredDocumentRule, ...]:
    if not isinstance(raw_rules, list) or not raw_rules:
        raise ValueError(f"required_documents must be a non-empty list for profile_id='{profile_id}'")

    parsed: list[RequiredDocumentRule] = []
    for item in raw_rules:
        if not isinstance(item, dict):
            raise ValueError(f"Invalid required_document entry for profile_id='{profile_id}'")
        rule_id = _require_string(item, "rule_id", context=f"profile_id='{profile_id}'", normalize=True)
        parsed.append(
            RequiredDocumentRule(
                rule_id=rule_id,
                document_type=require_canonical_document_type(
                    _require_string(
                        item,
                        "document_type",
                        context=f"rule_id='{rule_id}'",
                        normalize=True,
                    ),
                    context=f"rule_id='{rule_id}'",
                ),
                severity=_normalize_severity(item.get("severity", "blocking"), rule_id=rule_id),
                source_url=_require_source_url(item, rule_id=rule_id),
                remediation=_require_string(item, "remediation", context=f"rule_id='{rule_id}'"),
            )
        )
    return tuple(parsed)


def _parse_conditional_rules(raw_rules: object, *, profile_id: str) -> tuple[ConditionalDocumentRule, ...]:
    if not isinstance(raw_rules, list) or not raw_rules:
        raise ValueError(f"conditional_rules must be a non-empty list for profile_id='{profile_id}'")

    parsed: list[ConditionalDocumentRule] = []
    for item in raw_rules:
        if not isinstance(item, dict):
            raise ValueError(f"Invalid conditional_rule entry for profile_id='{profile_id}'")
        rule_id = _require_string(item, "rule_id", context=f"profile_id='{profile_id}'", normalize=True)
        parsed.append(
            ConditionalDocumentRule(
                rule_id=rule_id,
                when_document_type=require_canonical_document_type(
                    _require_string(
                        item,
                        "when_document_type",
                        context=f"rule_id='{rule_id}'",
                        normalize=True,
                    ),
                    context=f"rule_id='{rule_id}'",
                ),
                requires_document_type=require_canonical_document_type(
                    _require_string(
                        item,
                        "requires_document_type",
                        context=f"rule_id='{rule_id}'",
                        normalize=True,
                    ),
                    context=f"rule_id='{rule_id}'",
                ),
                severity=_normalize_severity(item.get("severity", "blocking"), rule_id=rule_id),
                source_url=_require_source_url(item, rule_id=rule_id),
                remediation=_require_string(item, "remediation", context=f"rule_id='{rule_id}'"),
            )
        )
    return tuple(parsed)


def _parse_order_requirements(raw_order: object, *, profile_id: str) -> OrderRequirements:
    if not isinstance(raw_order, dict):
        raise ValueError(f"Missing order_requirements for profile_id='{profile_id}'")

    rule_id = _require_string(
        raw_order,
        "rule_id",
        context=f"profile_id='{profile_id}' order_requirements",
        normalize=True,
    )
    raw_document_types = raw_order.get("document_types")
    if not isinstance(raw_document_types, list) or not raw_document_types:
        raise ValueError(f"document_types must be non-empty for rule_id='{rule_id}'")

    normalized_doc_types = tuple(
        require_canonical_document_type(document_type, context=f"rule_id='{rule_id}'")
        for document_type in raw_document_types
        if str(document_type).strip()
    )
    if not normalized_doc_types:
        raise ValueError(f"document_types must be non-empty for rule_id='{rule_id}'")

    return OrderRequirements(
        rule_id=rule_id,
        document_types=normalized_doc_types,
        source_url=_require_source_url(raw_order, rule_id=rule_id),
        remediation=_require_string(raw_order, "remediation", context=f"rule_id='{rule_id}'"),
    )


def _parse_pagination_requirements(raw_pagination: object, *, profile_id: str) -> PaginationRequirements:
    if not isinstance(raw_pagination, dict):
        raise ValueError(f"Missing pagination_requirements for profile_id='{profile_id}'")

    rule_id = _require_string(
        raw_pagination,
        "rule_id",
        context=f"profile_id='{profile_id}' pagination_requirements",
        normalize=True,
    )

    return PaginationRequirements(
        rule_id=rule_id,
        require_continuous_package_pagination=bool(
            raw_pagination.get("require_continuous_package_pagination", True)
        ),
        require_index_document=bool(raw_pagination.get("require_index_document", True)),
        index_document_type=require_canonical_document_type(
            _require_string(
                raw_pagination,
                "index_document_type",
                context=f"rule_id='{rule_id}'",
                normalize=True,
            ),
            context=f"rule_id='{rule_id}'",
        ),
        source_url=_require_source_url(raw_pagination, rule_id=rule_id),
        remediation=_require_string(raw_pagination, "remediation", context=f"rule_id='{rule_id}'"),
    )


def _parse_profile(raw_profile: object) -> DocumentCompilationProfile:
    if not isinstance(raw_profile, dict):
        raise ValueError("Each profile must be an object")

    profile_id = _require_string(raw_profile, "profile_id", context="profile", normalize=True)
    forum = _require_string(raw_profile, "forum", context=f"profile_id='{profile_id}'", normalize=True)
    if forum not in _ALLOWED_FORUMS:
        raise ValueError(f"Unknown forum '{forum}' for profile_id='{profile_id}'")

    return DocumentCompilationProfile(
        profile_id=profile_id,
        forum=forum,  # type: ignore[arg-type]
        title=_require_string(raw_profile, "title", context=f"profile_id='{profile_id}'"),
        required_documents=_parse_required_documents(
            raw_profile.get("required_documents"),
            profile_id=profile_id,
        ),
        conditional_rules=_parse_conditional_rules(
            raw_profile.get("conditional_rules"),
            profile_id=profile_id,
        ),
        order_requirements=_parse_order_requirements(
            raw_profile.get("order_requirements"),
            profile_id=profile_id,
        ),
        pagination_requirements=_parse_pagination_requirements(
            raw_profile.get("pagination_requirements"),
            profile_id=profile_id,
        ),
    )


def _validate_uniqueness(profiles: tuple[DocumentCompilationProfile, ...]) -> None:
    profile_ids = [profile.profile_id for profile in profiles]
    duplicate_profile_ids = {
        profile_id for profile_id in profile_ids if profile_ids.count(profile_id) > 1
    }
    if duplicate_profile_ids:
        duplicate_list = ", ".join(sorted(duplicate_profile_ids))
        raise ValueError(f"Duplicate profile_id values: {duplicate_list}")

    rule_ids: list[str] = []
    for profile in profiles:
        rule_ids.extend(profile.all_rule_ids())

    duplicate_rule_ids = {rule_id for rule_id in rule_ids if rule_ids.count(rule_id) > 1}
    if duplicate_rule_ids:
        duplicate_list = ", ".join(sorted(duplicate_rule_ids))
        raise ValueError(f"Duplicate rule_id values: {duplicate_list}")


def _candidate_paths(path: str | Path | None) -> tuple[Path, ...]:
    if path is not None:
        return (Path(path),)
    return (
        DEFAULT_COMPILATION_RULES_PACKAGE_PATH,
        DEFAULT_COMPILATION_RULES_RELATIVE_PATH,
        DEFAULT_COMPILATION_RULES_REPO_PATH,
    )


def _load_payload(path: str | Path | None) -> dict[str, object]:
    candidates = _candidate_paths(path)
    for candidate in candidates:
        if candidate.exists():
            with candidate.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            if not isinstance(payload, dict):
                raise ValueError("Document compilation rules catalog must be an object")
            return payload

    # Cloudflare Python Workers package only Python modules by default.
    # Keep a Python-embedded fallback so runtime startup is not blocked when
    # JSON artifact paths are unavailable in the deployed bundle.
    embedded_error: Exception | None = None
    if path is None:
        try:
            from immcad_api.policy.document_compilation_rules_embedded import (
                CATALOG_PAYLOAD_JSON,
            )
        except ImportError as exc:
            embedded_error = exc
        else:
            try:
                payload = json.loads(CATALOG_PAYLOAD_JSON)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    "Embedded document compilation rules catalog is not valid JSON"
                ) from exc
            if not isinstance(payload, dict):
                raise ValueError(
                    "Embedded document compilation rules catalog must be an object"
                )
            return payload

    checked = ", ".join(str(item) for item in candidates)
    if embedded_error is not None:
        raise FileNotFoundError(
            "Document compilation rules catalog not found and embedded fallback "
            f"failed. Checked: {checked}"
        ) from embedded_error
    raise FileNotFoundError(f"Document compilation rules catalog not found. Checked: {checked}")


def load_document_compilation_rules(path: str | Path | None = None) -> DocumentCompilationCatalog:
    payload = _load_payload(path)

    version = _require_string(payload, "version", context="catalog")
    jurisdiction = _require_string(payload, "jurisdiction", context="catalog", normalize=True)

    raw_profiles = payload.get("profiles")
    if not isinstance(raw_profiles, list) or not raw_profiles:
        raise ValueError("profiles must be a non-empty list")

    profiles = tuple(_parse_profile(profile) for profile in raw_profiles)
    _validate_uniqueness(profiles)

    return DocumentCompilationCatalog(
        version=version,
        jurisdiction=jurisdiction,
        profiles=profiles,
    )


__all__ = [
    "CompilationForum",
    "ConditionalDocumentRule",
    "DEFAULT_COMPILATION_RULES_PACKAGE_PATH",
    "DEFAULT_COMPILATION_RULES_RELATIVE_PATH",
    "DocumentCompilationCatalog",
    "DocumentCompilationProfile",
    "OrderRequirements",
    "PaginationRequirements",
    "RequiredDocumentRule",
    "RuleSeverity",
    "load_document_compilation_rules",
]
