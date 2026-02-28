from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
from typing import Callable

import httpx

from immcad_api.ingestion.planner import build_ingestion_plan_from_registry
from immcad_api.ingestion.source_fetch_policy import (
    FetchPolicyRule,
    SourceFetchPolicy,
    load_fetch_policy,
)
from immcad_api.policy.source_policy import (
    SourcePolicy,
    is_source_ingest_allowed,
    load_source_policy,
)
from immcad_api.sources import (
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

_HEAD_PROBE_SOURCE_IDS = frozenset({"FEDERAL_LAWS_BULK_XML"})


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
    policy_reason: str | None
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
    blocked: int
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
    source_ids: list[str] | tuple[str, ...] | None = None,
) -> tuple[str, str, list[SourceRegistryEntry]]:
    registry = load_source_registry(registry_path)
    plan = build_ingestion_plan_from_registry(registry)

    if cadence is None:
        selected = list(registry.sources)
    else:
        cadence_source_ids = set(plan.cadence_to_sources.get(cadence, []))
        selected = [
            source for source in registry.sources if source.source_id in cadence_source_ids
        ]

    if source_ids:
        requested_source_ids: list[str] = []
        seen_requested: set[str] = set()
        for raw_source_id in source_ids:
            normalized_source_id = raw_source_id.strip()
            if not normalized_source_id:
                continue
            dedupe_key = normalized_source_id.upper()
            if dedupe_key in seen_requested:
                continue
            seen_requested.add(dedupe_key)
            requested_source_ids.append(normalized_source_id)

        known_source_ids = {source.source_id for source in registry.sources}
        unknown_source_ids = [
            source_id for source_id in requested_source_ids if source_id not in known_source_ids
        ]
        if unknown_source_ids:
            raise ValueError(
                "Unknown source_id values requested: "
                + ", ".join(sorted(unknown_source_ids))
            )

        requested_source_id_set = set(requested_source_ids)
        selected = [
            source for source in selected if source.source_id in requested_source_id_set
        ]

    return plan.jurisdiction, plan.version, selected


def _fetch_with_retry_budget(
    *,
    fetcher: Fetcher,
    source: SourceRegistryEntry,
    context: FetchContext,
    fetch_policy: SourceFetchPolicy,
) -> FetchResult:
    source_fetch_policy = fetch_policy.for_source(source.source_id)
    attempts = source_fetch_policy.max_retries + 1
    last_error: Exception | None = None

    for attempt_index in range(attempts):
        try:
            return fetcher(source, context)
        except Exception as exc:
            last_error = exc
            if attempt_index + 1 >= attempts:
                break
            backoff_seconds = source_fetch_policy.retry_backoff_seconds * (
                attempt_index + 1
            )
            if backoff_seconds > 0:
                time.sleep(backoff_seconds)

    if last_error is not None:
        raise RuntimeError(
            f"fetch failed after {attempts} attempts: {last_error}"
        ) from last_error

    raise RuntimeError(f"fetch failed after {attempts} attempts")


def _execute_jobs(
    *,
    jurisdiction: str,
    version: str,
    cadence_label: str,
    sources: list[SourceRegistryEntry],
    fetcher: Fetcher,
    checkpoints: dict[str, SourceCheckpoint],
    source_policy: SourcePolicy,
    fetch_policy: SourceFetchPolicy,
    environment: str,
) -> tuple[IngestionExecutionReport, dict[str, SourceCheckpoint]]:
    started_at = _utc_now_iso()
    results: list[IngestionSourceResult] = []
    updated_checkpoints = dict(checkpoints)

    for source in sources:
        fetched_at = _utc_now_iso()
        checkpoint = updated_checkpoints.get(source.source_id)
        ingest_allowed, policy_reason = is_source_ingest_allowed(
            source.source_id,
            source_policy=source_policy,
            environment=environment,
        )
        if not ingest_allowed:
            results.append(
                IngestionSourceResult(
                    source_id=source.source_id,
                    source_type=source.source_type,
                    update_cadence=source.update_cadence,
                    url=str(source.url),
                    status="blocked_policy",
                    http_status=None,
                    checksum_sha256=checkpoint.checksum_sha256 if checkpoint else None,
                    bytes_fetched=0,
                    error=None,
                    policy_reason=policy_reason,
                    fetched_at=fetched_at,
                )
            )
            continue

        context = FetchContext(
            etag=checkpoint.etag if checkpoint else None,
            last_modified=checkpoint.last_modified if checkpoint else None,
        )
        try:
            fetch_result = _fetch_with_retry_budget(
                fetcher=fetcher,
                source=source,
                context=context,
                fetch_policy=fetch_policy,
            )

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
                        policy_reason=policy_reason,
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

            checksum = hashlib.sha256(fetch_result.payload).hexdigest()
            if (
                checkpoint is not None
                and checkpoint.checksum_sha256 is not None
                and checkpoint.checksum_sha256 == checksum
            ):
                results.append(
                    IngestionSourceResult(
                        source_id=source.source_id,
                        source_type=source.source_type,
                        update_cadence=source.update_cadence,
                        url=str(source.url),
                        status="not_modified",
                        http_status=fetch_result.http_status,
                        checksum_sha256=checksum,
                        bytes_fetched=0,
                        error=None,
                        policy_reason=policy_reason,
                        fetched_at=fetched_at,
                    )
                )
                updated_checkpoints[source.source_id] = SourceCheckpoint(
                    source_id=source.source_id,
                    etag=fetch_result.etag or checkpoint.etag,
                    last_modified=fetch_result.last_modified or checkpoint.last_modified,
                    checksum_sha256=checksum,
                    last_http_status=fetch_result.http_status,
                    last_success_at=fetched_at,
                )
                continue

            court_validation = validate_court_source_payload(source.source_id, fetch_result.payload)
            validation_warning: str | None = None
            if court_validation is not None:
                if court_validation.records_total == 0:
                    raise ValueError(
                        f"{source.source_id} payload did not include any decision records"
                    )
                if court_validation.records_invalid > 0:
                    if court_validation.records_valid == 0:
                        first_errors = "; ".join(court_validation.errors[:3])
                        raise ValueError(
                            f"{source.source_id} validation failed: "
                            f"{court_validation.records_invalid}/{court_validation.records_total} "
                            f"invalid records ({first_errors})"
                        )
                    first_errors = "; ".join(court_validation.errors[:3])
                    validation_warning = (
                        f"{source.source_id} validation warning: "
                        f"{court_validation.records_invalid}/{court_validation.records_total} "
                        f"invalid records ({first_errors})"
                    )

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
                    error=validation_warning,
                    policy_reason=policy_reason,
                    records_total=court_validation.records_total if court_validation else None,
                    records_valid=court_validation.records_valid if court_validation else None,
                    records_invalid=court_validation.records_invalid if court_validation else None,
                    fetched_at=fetched_at,
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
                    policy_reason=policy_reason,
                    fetched_at=fetched_at,
                )
            )

    succeeded = sum(1 for item in results if item.status == "success")
    not_modified = sum(1 for item in results if item.status == "not_modified")
    blocked = sum(1 for item in results if item.status == "blocked_policy")
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
        blocked=blocked,
        failed=failed,
        results=results,
    )
    return report, updated_checkpoints


def _apply_timeout_override(
    fetch_policy: SourceFetchPolicy,
    timeout_seconds: float,
) -> SourceFetchPolicy:
    normalized_timeout = max(timeout_seconds, 1.0)
    default_rule = FetchPolicyRule(
        timeout_seconds=normalized_timeout,
        max_retries=fetch_policy.default.max_retries,
        retry_backoff_seconds=fetch_policy.default.retry_backoff_seconds,
    )
    source_rules = {
        source_id: FetchPolicyRule(
            timeout_seconds=normalized_timeout,
            max_retries=rule.max_retries,
            retry_backoff_seconds=rule.retry_backoff_seconds,
        )
        for source_id, rule in fetch_policy.by_source.items()
    }
    return SourceFetchPolicy(default=default_rule, by_source=source_rules)


def _is_head_probe_source(source_id: str) -> bool:
    return source_id in _HEAD_PROBE_SOURCE_IDS


def run_ingestion_jobs(
    *,
    cadence: UpdateCadence | None = None,
    registry_path: str | Path | None = None,
    source_ids: list[str] | tuple[str, ...] | None = None,
    source_policy_path: str | Path | None = None,
    fetch_policy_path: str | Path | None = None,
    environment: str = "development",
    timeout_seconds: float | None = None,
    state_path: str | Path | None = None,
    fetcher: Fetcher | None = None,
) -> IngestionExecutionReport:
    jurisdiction, version, sources = _select_sources(
        registry_path,
        cadence,
        source_ids=source_ids,
    )
    cadence_label = cadence or "all"
    checkpoints = _load_checkpoints(state_path)
    source_policy = load_source_policy(source_policy_path)
    fetch_policy = load_fetch_policy(
        fetch_policy_path,
        default_timeout_seconds=30.0 if timeout_seconds is None else timeout_seconds,
    )
    if timeout_seconds is not None:
        fetch_policy = _apply_timeout_override(fetch_policy, timeout_seconds)

    if fetcher is not None:
        report, updated_checkpoints = _execute_jobs(
            jurisdiction=jurisdiction,
            version=version,
            cadence_label=cadence_label,
            sources=sources,
            fetcher=fetcher,
            checkpoints=checkpoints,
            source_policy=source_policy,
            fetch_policy=fetch_policy,
            environment=environment,
        )
        _save_checkpoints(state_path, updated_checkpoints)
        return report

    with httpx.Client(follow_redirects=True) as client:

        def _fetch(source: SourceRegistryEntry, context: FetchContext) -> FetchResult:
            headers: dict[str, str] = {}
            if context.etag:
                headers["If-None-Match"] = context.etag
            if context.last_modified:
                headers["If-Modified-Since"] = context.last_modified

            source_fetch_policy = fetch_policy.for_source(source.source_id)
            if _is_head_probe_source(source.source_id):
                try:
                    head_response = client.head(
                        str(source.url),
                        headers=headers or None,
                        timeout=source_fetch_policy.timeout_seconds,
                    )
                    head_etag = head_response.headers.get("ETag")
                    head_last_modified = head_response.headers.get("Last-Modified")
                    if head_response.status_code == 304:
                        return FetchResult(
                            payload=None,
                            http_status=head_response.status_code,
                            etag=head_etag,
                            last_modified=head_last_modified,
                        )
                    if 200 <= head_response.status_code < 300:
                        unchanged = bool(
                            (context.etag and head_etag and context.etag == head_etag)
                            or (
                                context.last_modified
                                and head_last_modified
                                and context.last_modified == head_last_modified
                            )
                        )
                        if unchanged:
                            return FetchResult(
                                payload=None,
                                http_status=304,
                                etag=head_etag or context.etag,
                                last_modified=head_last_modified or context.last_modified,
                            )
                    elif head_response.status_code not in {403, 405, 501}:
                        head_response.raise_for_status()
                except httpx.HTTPError:
                    # Some providers do not support HEAD consistently; fallback to GET.
                    pass

            response = client.get(
                str(source.url),
                headers=headers or None,
                timeout=source_fetch_policy.timeout_seconds,
            )
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
            source_policy=source_policy,
            fetch_policy=fetch_policy,
            environment=environment,
        )

    _save_checkpoints(state_path, updated_checkpoints)
    return report
