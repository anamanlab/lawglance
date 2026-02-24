from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from immcad_api.sources import SourceRegistry, load_source_registry


@dataclass(frozen=True)
class IngestionPlan:
    jurisdiction: str
    version: str
    cadence_to_sources: dict[str, list[str]]


def build_ingestion_plan_from_registry(registry: SourceRegistry) -> IngestionPlan:
    cadence_map: dict[str, list[str]] = defaultdict(list)
    for source in registry.sources:
        cadence_map[source.update_cadence].append(source.source_id)

    normalized_map = {cadence: sorted(source_ids) for cadence, source_ids in cadence_map.items()}
    return IngestionPlan(
        jurisdiction=registry.jurisdiction.lower(),
        version=registry.version,
        cadence_to_sources=normalized_map,
    )


def build_ingestion_plan(path: str | Path | None = None) -> IngestionPlan:
    registry = load_source_registry(path)
    return build_ingestion_plan_from_registry(registry)
