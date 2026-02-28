from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Literal

from pydantic import BaseModel, Field, model_validator
import yaml
from immcad_api.policy.source_policy_embedded import SOURCE_POLICY_PAYLOAD_JSON


SourceClass = Literal["official", "unofficial", "commercial"]
RuntimeEnvironment = Literal["internal", "production"]

DEFAULT_SOURCE_POLICY_RELATIVE_PATH = Path("config/source_policy.yaml")
DEFAULT_SOURCE_POLICY_PACKAGE_PATH = (
    Path(__file__).resolve().parents[2] / DEFAULT_SOURCE_POLICY_RELATIVE_PATH
)
DEFAULT_SOURCE_POLICY_REPO_PATH = (
    Path(__file__).resolve().parents[3] / DEFAULT_SOURCE_POLICY_RELATIVE_PATH
)
_HARDENED_ENVIRONMENT_PATTERN = re.compile(r"^(production|prod|ci)(?:[-_].+)?$")


class SourcePolicyEntry(BaseModel):
    source_id: str = Field(min_length=3, max_length=128)
    source_class: SourceClass
    internal_ingest_allowed: bool
    production_ingest_allowed: bool
    answer_citation_allowed: bool
    export_fulltext_allowed: bool
    license_notes: str = Field(min_length=3, max_length=1024)
    review_owner: str = Field(min_length=2, max_length=128)
    review_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")


class SourcePolicy(BaseModel):
    version: str = Field(min_length=3, max_length=64)
    jurisdiction: str = Field(pattern=r"^[A-Za-z]{2}$")
    sources: list[SourcePolicyEntry]

    @model_validator(mode="after")
    def _validate_unique_source_ids(self) -> "SourcePolicy":
        source_ids = [entry.source_id for entry in self.sources]
        duplicates = {source_id for source_id in source_ids if source_ids.count(source_id) > 1}
        if duplicates:
            duplicate_list = ", ".join(sorted(duplicates))
            raise ValueError(f"Duplicate source_id values in source policy: {duplicate_list}")
        return self

    def get_source(self, source_id: str) -> SourcePolicyEntry | None:
        for source in self.sources:
            if source.source_id == source_id:
                return source
        return None


def _candidate_paths(path: str | Path | None) -> list[Path]:
    if path is not None:
        return [Path(path)]
    return [
        DEFAULT_SOURCE_POLICY_RELATIVE_PATH,
        DEFAULT_SOURCE_POLICY_PACKAGE_PATH,
        DEFAULT_SOURCE_POLICY_REPO_PATH,
    ]


def _load_policy_payload(path: Path) -> dict[str, object]:
    raw = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    try:
        if suffix == ".json":
            payload = json.loads(raw)
        elif suffix in {".yaml", ".yml"}:
            payload = yaml.safe_load(raw)
        else:
            raise ValueError(f"Unsupported source policy format for {path} (expected .json/.yaml/.yml)")
    except (json.JSONDecodeError, yaml.YAMLError) as exc:
        raise ValueError(f"Source policy parse failed for {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Source policy root payload must be an object: {path}")
    return payload


def load_source_policy(path: str | Path | None = None) -> SourcePolicy:
    candidates = _candidate_paths(path)
    for candidate in candidates:
        if candidate.exists():
            payload = _load_policy_payload(candidate)
            return SourcePolicy.model_validate(payload)
    if path is None:
        payload = json.loads(SOURCE_POLICY_PAYLOAD_JSON)
        return SourcePolicy.model_validate(payload)

    candidate_paths = ", ".join(str(item) for item in candidates)
    raise FileNotFoundError(f"Source policy not found. Checked: {candidate_paths}")


def normalize_runtime_environment(environment: str | None) -> RuntimeEnvironment:
    normalized = (environment or "development").strip().lower()
    if _HARDENED_ENVIRONMENT_PATTERN.fullmatch(normalized):
        return "production"
    return "internal"


def is_source_ingest_allowed(
    source_id: str,
    *,
    source_policy: SourcePolicy,
    environment: str | None,
) -> tuple[bool, str]:
    runtime_environment = normalize_runtime_environment(environment)
    entry = source_policy.get_source(source_id)

    if entry is None:
        if runtime_environment == "production":
            return False, "source_not_in_policy_for_production"
        return True, "source_not_in_policy_allowed_internal"

    if runtime_environment == "production":
        if entry.production_ingest_allowed:
            return True, "production_ingest_allowed"
        return False, "production_ingest_blocked_by_policy"

    if entry.internal_ingest_allowed:
        return True, "internal_ingest_allowed"
    return False, "internal_ingest_blocked_by_policy"


def is_source_export_allowed(
    source_id: str,
    *,
    source_policy: SourcePolicy,
) -> tuple[bool, str]:
    entry = source_policy.get_source(source_id)
    if entry is None:
        return False, "source_not_in_policy_for_export"
    if entry.export_fulltext_allowed:
        return True, "source_export_allowed"
    return False, "source_export_blocked_by_policy"
