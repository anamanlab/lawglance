from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, model_validator


SourceType = Literal["statute", "regulation", "policy", "case_law"]
UpdateCadence = Literal["daily", "weekly", "scheduled_incremental"]

DEFAULT_REGISTRY_RELATIVE_PATH = Path("data/sources/canada-immigration/registry.json")
DEFAULT_REGISTRY_REPO_PATH = Path(__file__).resolve().parents[3] / DEFAULT_REGISTRY_RELATIVE_PATH


class SourceRegistryEntry(BaseModel):
    source_id: str = Field(min_length=3, max_length=128)
    source_type: SourceType
    instrument: str = Field(min_length=3, max_length=256)
    url: HttpUrl
    update_cadence: UpdateCadence


class SourceRegistry(BaseModel):
    version: str = Field(min_length=3, max_length=64)
    jurisdiction: str = Field(pattern=r"^[A-Za-z]{2}$")
    sources: list[SourceRegistryEntry]

    @model_validator(mode="after")
    def _validate_unique_source_ids(self) -> "SourceRegistry":
        source_ids = [entry.source_id for entry in self.sources]
        duplicates = {source_id for source_id in source_ids if source_ids.count(source_id) > 1}
        if duplicates:
            duplicate_list = ", ".join(sorted(duplicates))
            raise ValueError(f"Duplicate source_id values in registry: {duplicate_list}")
        return self

    def get_source(self, source_id: str) -> SourceRegistryEntry | None:
        for source in self.sources:
            if source.source_id == source_id:
                return source
        return None


def _candidate_paths(path: str | Path | None) -> list[Path]:
    if path is not None:
        return [Path(path)]
    return [DEFAULT_REGISTRY_RELATIVE_PATH, DEFAULT_REGISTRY_REPO_PATH]


def load_source_registry(path: str | Path | None = None) -> SourceRegistry:
    candidates = _candidate_paths(path)
    for candidate in candidates:
        if candidate.exists():
            with candidate.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            return SourceRegistry.model_validate(payload)

    candidate_paths = ", ".join(str(item) for item in candidates)
    raise FileNotFoundError(f"Source registry not found. Checked: {candidate_paths}")
