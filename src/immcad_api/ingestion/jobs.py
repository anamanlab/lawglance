from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Callable

import httpx

from immcad_api.ingestion.planner import build_ingestion_plan_from_registry
from immcad_api.sources import (
    CourtPayloadValidation,
    CourtPayloadValidationConfig,
    SourceRegistryEntry,
    load_source_registry,
    validate_court_source_payload,
)
from immcad_api.sources.source_registry import UpdateCadence


@dataclass(frozen=True)
class FetchContext:
    etag: str | None
    last_modified: str | None


@dataclass(frozen=True)
class FetchResult:
    payload: bytes | None
    http_status: int
    etag: str | None = None
    last_modified: str | None = None


Fetcher = Callable[[SourceRegistryEntry, FetchContext], FetchResult]


@dataclass(frozen=True)
class SourceCheckpoint:
    source_id: str
    etag: str | None
    last_modified: str | None
    checksum_sha256: str | None
    last_http_status: int | None
    last_success_at: str | None


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
    records_total: int | None = None
    records_valid: int | None = None
    records_invalid: int | None = None


@dataclass(frozen=True)
class IngestionExecutionReport:
    jurisdiction: str
    version: str
    cadence: str
    started_at: str
    completed_at: str
    total: int
    succeeded: int
    not_modified: int
    failed: int
    results: list[IngestionSourceResult]

    def to_dict(self) -> dict:
        return asdict(self)


def _utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _load_checkpoints(state_path: str | Path | None) -> dict[str, SourceCheckpoint]:
    if state_path is None:
        return {}

    path = Path(state_path)
    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    checkpoints_raw = payload.get("checkpoints", {})
    checkpoints: dict[str, SourceCheckpoint] = {}
    for source_id, item in checkpoints_raw.items():
        checkpoints[source_id] = SourceCheckpoint(
            source_id=source_id,
            etag=item.get("etag"),
            last_modified=item.get("last_modified"),
            checksum_sha256=item.get("checksum_sha256"),
            last_http_status=item.get("last_http_status"),
            last_success_at=item.get("last_success_at"),
        )

    return checkpoints


def _save_checkpoints(state_path: str | Path | None, checkpoints: dict[str, SourceCheckpoint]) -> None:
    if state_path is None:
        return

    target = Path(state_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "updated_at": _utc_now_iso(),
        "checkpoints": {source_id: asdict(checkpoint) for source_id, checkpoint in checkpoints.items()},
    }
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")


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
    checkpoints: dict[str, SourceCheckpoint],
    court_validation_config: CourtPayloadValidationConfig,
) -> tuple[IngestionExecutionReport, dict[str, SourceCheckpoint]]:
    started_at = _utc_now_iso()
    results: list[IngestionSourceResult] = []
    updated_checkpoints = dict(checkpoints)

    for source in sources:
        fetched_at = _utc_now_iso()
        checkpoint = updated_checkpoints.get(source.source_id)
        context = FetchContext(
            etag=checkpoint.etag if checkpoint else None,
            last_modified=checkpoint.last_modified if checkpoint else None,
        )
        try:
            court_validation: CourtPayloadValidation | None = None
            fetch_result = fetcher(source, context)

            if fetch_result.http_status == 304:
                results.append(
                    IngestionSourceResult(
                        source_id=source.source_id,
                        source_type=source.source_type,
                        update_cadence=source.update_cadence,
                        url=str(source.url),
                        status="not_modified",
                        http_status=fetch_result.http_status,
                        checksum_sha256=checkpoint.checksum_sha256 if checkpoint else None,
                        bytes_fetched=0,
                        error=None,
                        fetched_at=fetched_at,
                    )
                )
                updated_checkpoints[source.source_id] = SourceCheckpoint(
                    source_id=source.source_id,
                    etag=fetch_result.etag or (checkpoint.etag if checkpoint else None),
                    last_modified=fetch_result.last_modified
                    or (checkpoint.last_modified if checkpoint else None),
                    checksum_sha256=checkpoint.checksum_sha256 if checkpoint else None,
                    last_http_status=fetch_result.http_status,
                    last_success_at=fetched_at,
                )
                continue

            if fetch_result.payload is None:
                raise ValueError(
                    f"Provider fetch returned empty payload for status={fetch_result.http_status}"
                )

            court_validation = validate_court_source_payload(
                source.source_id,
                fetch_result.payload,
                validation_config=court_validation_config,
            )
            if court_validation is not None:
                if court_validation.records_total == 0:
                    raise ValueError(f"{source.source_id} payload did not include any decision records")
                if court_validation.records_valid < court_validation_config.min_valid_records:
                    raise ValueError(
                        f"{source.source_id} validation failed: "
                        f"valid records {court_validation.records_valid} below minimum "
                        f"{court_validation_config.min_valid_records}"
                    )
                if court_validation.invalid_ratio > court_validation_config.max_invalid_ratio:
                    first_errors = "; ".join(court_validation.errors[:3])
                    raise ValueError(
                        f"{source.source_id} validation failed: invalid ratio "
                        f"{court_validation.records_invalid}/{court_validation.records_total} "
                        f"({court_validation.invalid_ratio:.2f}) exceeds "
                        f"{court_validation_config.max_invalid_ratio:.2f}"
                        + (f" ({first_errors})" if first_errors else "")
                    )

            checksum = hashlib.sha256(fetch_result.payload).hexdigest()
            results.append(
                IngestionSourceResult(
                    source_id=source.source_id,
                    source_type=source.source_type,
                    update_cadence=source.update_cadence,
                    url=str(source.url),
                    status="success",
                    http_status=fetch_result.http_status,
                    checksum_sha256=checksum,
                    bytes_fetched=len(fetch_result.payload),
                    error=None,
                    fetched_at=fetched_at,
                    records_total=court_validation.records_total if court_validation else None,
                    records_valid=court_validation.records_valid if court_validation else None,
                    records_invalid=court_validation.records_invalid if court_validation else None,
                )
            )
            updated_checkpoints[source.source_id] = SourceCheckpoint(
                source_id=source.source_id,
                etag=fetch_result.etag,
                last_modified=fetch_result.last_modified,
                checksum_sha256=checksum,
                last_http_status=fetch_result.http_status,
                last_success_at=fetched_at,
            )
        except Exception as exc:  # pragma: no cover - exercised through injected fetchers
            results.append(
                IngestionSourceResult(
                    source_id=source.source_id,
                    source_type=source.source_type,
                    update_cadence=source.update_cadence,
                    url=str(source.url),
                    status="error",
                    http_status=None,
                    checksum_sha256=checkpoint.checksum_sha256 if checkpoint else None,
                    bytes_fetched=None,
                    error=str(exc),
                    fetched_at=fetched_at,
                )
            )

    succeeded = sum(1 for item in results if item.status == "success")
    not_modified = sum(1 for item in results if item.status == "not_modified")
    failed = sum(1 for item in results if item.status == "error")

    report = IngestionExecutionReport(
        jurisdiction=jurisdiction,
        version=version,
        cadence=cadence_label,
        started_at=started_at,
        completed_at=_utc_now_iso(),
        total=len(results),
        succeeded=succeeded,
        not_modified=not_modified,
        failed=failed,
        results=results,
    )
    return report, updated_checkpoints


def run_ingestion_jobs(
    *,
    cadence: UpdateCadence | None = None,
    registry_path: str | Path | None = None,
    court_validation_max_invalid_ratio: float = 0.0,
    court_validation_min_valid_records: int = 1,
    court_validation_expected_year: int | None = None,
    court_validation_year_window: int = 0,
    timeout_seconds: float = 30.0,
    state_path: str | Path | None = None,
    fetcher: Fetcher | None = None,
) -> IngestionExecutionReport:
    jurisdiction, version, sources = _select_sources(registry_path, cadence)
    cadence_label = cadence or "all"
    checkpoints = _load_checkpoints(state_path)
    court_validation_config = CourtPayloadValidationConfig(
        max_invalid_ratio=court_validation_max_invalid_ratio,
        min_valid_records=court_validation_min_valid_records,
        expected_year=court_validation_expected_year,
        year_window=court_validation_year_window,
    )

    if fetcher is not None:
        report, updated_checkpoints = _execute_jobs(
            jurisdiction=jurisdiction,
            version=version,
            cadence_label=cadence_label,
            sources=sources,
            fetcher=fetcher,
            checkpoints=checkpoints,
            court_validation_config=court_validation_config,
        )
        _save_checkpoints(state_path, updated_checkpoints)
        return report

    with httpx.Client(timeout=timeout_seconds, follow_redirects=True) as client:

        def _fetch(source: SourceRegistryEntry, context: FetchContext) -> FetchResult:
            headers: dict[str, str] = {}
            if context.etag:
                headers["If-None-Match"] = context.etag
            if context.last_modified:
                headers["If-Modified-Since"] = context.last_modified

            response = client.get(str(source.url), headers=headers or None)
            etag = response.headers.get("ETag")
            last_modified = response.headers.get("Last-Modified")

            if response.status_code == 304:
                return FetchResult(
                    payload=None,
                    http_status=response.status_code,
                    etag=etag,
                    last_modified=last_modified,
                )

            response.raise_for_status()
            return FetchResult(
                payload=response.content,
                http_status=response.status_code,
                etag=etag,
                last_modified=last_modified,
            )

        report, updated_checkpoints = _execute_jobs(
            jurisdiction=jurisdiction,
            version=version,
            cadence_label=cadence_label,
            sources=sources,
            fetcher=_fetch,
            checkpoints=checkpoints,
            court_validation_config=court_validation_config,
        )

    _save_checkpoints(state_path, updated_checkpoints)
    return report
