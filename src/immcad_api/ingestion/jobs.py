from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
from pathlib import Path
from typing import Callable

import httpx

from immcad_api.ingestion.planner import build_ingestion_plan_from_registry
from immcad_api.sources import SourceRegistryEntry, load_source_registry
from immcad_api.sources.source_registry import UpdateCadence

FetchResult = tuple[bytes, int]
Fetcher = Callable[[SourceRegistryEntry], FetchResult]


@dataclass(frozen=True)
class IngestionSourceResult:
    source_id: str
    source_type: str
    update_cadence: str
    url: str
    status: str
    http_status: int | None
    checksum_sha256: str | None
    bytes_fetched: int | None
    error: str | None
    fetched_at: str


@dataclass(frozen=True)
class IngestionExecutionReport:
    jurisdiction: str
    version: str
    cadence: str
    started_at: str
    completed_at: str
    total: int
    succeeded: int
    failed: int
    results: list[IngestionSourceResult]

    def to_dict(self) -> dict:
        return asdict(self)


def _utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _select_sources(
    registry_path: str | Path | None,
    cadence: UpdateCadence | None,
) -> tuple[str, str, list[SourceRegistryEntry]]:
    registry = load_source_registry(registry_path)
    plan = build_ingestion_plan_from_registry(registry)

    if cadence is None:
        return plan.jurisdiction, plan.version, list(registry.sources)

    source_ids = set(plan.cadence_to_sources.get(cadence, []))
    selected = [source for source in registry.sources if source.source_id in source_ids]
    return plan.jurisdiction, plan.version, selected


def _execute_jobs(
    *,
    jurisdiction: str,
    version: str,
    cadence_label: str,
    sources: list[SourceRegistryEntry],
    fetcher: Fetcher,
) -> IngestionExecutionReport:
    started_at = _utc_now_iso()
    results: list[IngestionSourceResult] = []

    for source in sources:
        fetched_at = _utc_now_iso()
        try:
            payload, http_status = fetcher(source)
            checksum = hashlib.sha256(payload).hexdigest()
            results.append(
                IngestionSourceResult(
                    source_id=source.source_id,
                    source_type=source.source_type,
                    update_cadence=source.update_cadence,
                    url=str(source.url),
                    status="success",
                    http_status=http_status,
                    checksum_sha256=checksum,
                    bytes_fetched=len(payload),
                    error=None,
                    fetched_at=fetched_at,
                )
            )
        except Exception as exc:  # pragma: no cover - tested through injected fetcher
            results.append(
                IngestionSourceResult(
                    source_id=source.source_id,
                    source_type=source.source_type,
                    update_cadence=source.update_cadence,
                    url=str(source.url),
                    status="error",
                    http_status=None,
                    checksum_sha256=None,
                    bytes_fetched=None,
                    error=str(exc),
                    fetched_at=fetched_at,
                )
            )

    succeeded = sum(1 for item in results if item.status == "success")
    failed = sum(1 for item in results if item.status == "error")

    return IngestionExecutionReport(
        jurisdiction=jurisdiction,
        version=version,
        cadence=cadence_label,
        started_at=started_at,
        completed_at=_utc_now_iso(),
        total=len(results),
        succeeded=succeeded,
        failed=failed,
        results=results,
    )


def run_ingestion_jobs(
    *,
    cadence: UpdateCadence | None = None,
    registry_path: str | Path | None = None,
    timeout_seconds: float = 30.0,
    fetcher: Fetcher | None = None,
) -> IngestionExecutionReport:
    jurisdiction, version, sources = _select_sources(registry_path, cadence)
    cadence_label = cadence or "all"

    if fetcher is not None:
        return _execute_jobs(
            jurisdiction=jurisdiction,
            version=version,
            cadence_label=cadence_label,
            sources=sources,
            fetcher=fetcher,
        )

    with httpx.Client(timeout=timeout_seconds, follow_redirects=True) as client:

        def _fetch(source: SourceRegistryEntry) -> FetchResult:
            response = client.get(str(source.url))
            response.raise_for_status()
            return response.content, response.status_code

        return _execute_jobs(
            jurisdiction=jurisdiction,
            version=version,
            cadence_label=cadence_label,
            sources=sources,
            fetcher=_fetch,
        )
