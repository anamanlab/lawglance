#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any

import httpx

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


FC_SOURCE_ID = "FC_DECISIONS"
FCA_SOURCE_ID = "FCA_DECISIONS"
SCC_SOURCE_ID = "SCC_DECISIONS"
FEDERAL_LAWS_SOURCE_ID = "FEDERAL_LAWS_BULK_XML"

SCC_INTERVAL_HOURS = 6
FEDERAL_LAWS_DAILY_HOUR_UTC = 3
FEDERAL_LAWS_FULL_SYNC_HOUR_UTC = 4
FEDERAL_LAWS_FULL_SYNC_WEEKDAYS_UTC = frozenset({1, 4})  # Tuesday + Friday


def _normalize_env_value(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return normalized


def resolve_default_runtime_environment() -> str:
    explicit_environment = _normalize_env_value(os.getenv("ENVIRONMENT"))
    compatibility_environment = _normalize_env_value(os.getenv("IMMCAD_ENVIRONMENT"))
    if (
        explicit_environment
        and compatibility_environment
        and explicit_environment.lower() != compatibility_environment.lower()
    ):
        raise ValueError("ENVIRONMENT and IMMCAD_ENVIRONMENT must match when both are set")
    return explicit_environment or compatibility_environment or "development"


def _parse_utc_timestamp(raw_value: str) -> datetime:
    normalized = raw_value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ValueError("utc timestamp must include timezone offset (for example 2026-02-27T04:00:00Z)")
    return parsed.astimezone(timezone.utc)


def build_hourly_schedule(run_at_utc: datetime) -> dict[str, Any]:
    if run_at_utc.tzinfo is None:
        raise ValueError("run_at_utc must be timezone-aware")

    source_ids = [FC_SOURCE_ID, FCA_SOURCE_ID]
    scc_due = run_at_utc.hour % SCC_INTERVAL_HOURS == 0
    laws_due = run_at_utc.hour == FEDERAL_LAWS_DAILY_HOUR_UTC
    laws_full_sync_due = (
        run_at_utc.hour == FEDERAL_LAWS_FULL_SYNC_HOUR_UTC
        and run_at_utc.weekday() in FEDERAL_LAWS_FULL_SYNC_WEEKDAYS_UTC
    )

    if scc_due:
        source_ids.append(SCC_SOURCE_ID)
    if laws_due or laws_full_sync_due:
        source_ids.append(FEDERAL_LAWS_SOURCE_ID)

    return {
        "source_ids": source_ids,
        "scc_due": scc_due,
        "laws_due": laws_due,
        "laws_full_sync_due": laws_full_sync_due,
    }


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=True))
            handle.write("\n")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def _utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _checkpoint_key_for_source(source_id: str) -> str:
    normalized = source_id.strip()
    return "".join(
        character if character.isalnum() or character in {"_", "-"} else "_"
        for character in normalized
    )


def _federal_laws_cache_file(cache_dir: Path, source_id: str) -> Path:
    return cache_dir / f"{_checkpoint_key_for_source(source_id)}.jsonl"


def _load_federal_laws_materialization_checkpoints(
    checkpoint_path: Path | None,
) -> dict[str, dict[str, str]]:
    if checkpoint_path is None or not checkpoint_path.exists():
        return {}

    payload = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    acts_payload = payload.get("acts", {})
    if not isinstance(acts_payload, dict):
        return {}

    checkpoints: dict[str, dict[str, str]] = {}
    for source_id, raw_entry in acts_payload.items():
        if not isinstance(raw_entry, dict):
            continue
        revision = raw_entry.get("revision")
        official_number = raw_entry.get("official_number")
        if not isinstance(revision, str) or not revision:
            continue
        if not isinstance(official_number, str) or not official_number:
            continue
        entry: dict[str, str] = {
            "revision": revision,
            "official_number": official_number,
        }
        last_materialized_at = raw_entry.get("last_materialized_at")
        if isinstance(last_materialized_at, str) and last_materialized_at:
            entry["last_materialized_at"] = last_materialized_at
        checkpoints[source_id] = entry
    return checkpoints


def _save_federal_laws_materialization_checkpoints(
    checkpoint_path: Path | None,
    checkpoints: dict[str, dict[str, str]],
) -> None:
    if checkpoint_path is None:
        return

    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "updated_at": _utc_now_iso(),
        "acts": checkpoints,
    }
    checkpoint_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _index_entry_revision(index_entry: Any) -> str:
    current_to_date = (
        index_entry.current_to_date.isoformat()
        if getattr(index_entry, "current_to_date", None)
        else ""
    )
    revision_basis = "|".join(
        [
            str(getattr(index_entry, "unique_id", "")),
            str(getattr(index_entry, "official_number", "")),
            str(getattr(index_entry, "language", "")),
            str(getattr(index_entry, "link_to_xml", "")),
            str(getattr(index_entry, "title", "")),
            current_to_date,
        ]
    )
    return hashlib.sha256(revision_basis.encode("utf-8")).hexdigest()


def materialize_federal_laws_sections(
    *,
    registry_path: str | None,
    output_path: Path,
    timeout_seconds: float | None,
    checkpoint_path: Path | None = None,
    cache_dir: Path | None = None,
    force_full_sync: bool = False,
) -> dict[str, Any]:
    from immcad_api.sources import load_source_registry
    from immcad_api.sources.federal_laws_bulk_xml import (
        parse_federal_law_section_chunks,
        parse_federal_laws_index,
        select_index_entry,
        target_federal_law_source_ids,
    )

    registry = load_source_registry(registry_path)
    targets = target_federal_law_source_ids(registry)
    if not targets:
        return {
            "status": "skipped_no_targets",
            "target_source_count": 0,
            "target_source_ids": [],
            "chunks_written": 0,
        }

    federal_laws_source = registry.get_source(FEDERAL_LAWS_SOURCE_ID)
    if federal_laws_source is None:
        return {
            "status": "error",
            "error": "FEDERAL_LAWS_BULK_XML source not found in registry",
            "target_source_count": len(targets),
            "target_source_ids": sorted(targets),
            "chunks_written": 0,
        }

    effective_timeout = 30.0 if timeout_seconds is None else max(timeout_seconds, 1.0)
    checkpoint_by_source = _load_federal_laws_materialization_checkpoints(checkpoint_path)
    updated_checkpoint_by_source = dict(checkpoint_by_source)
    materialization_timestamp = _utc_now_iso()
    if cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)

    with httpx.Client(follow_redirects=True, timeout=effective_timeout) as client:
        legis_response = client.get(str(federal_laws_source.url))
        legis_response.raise_for_status()
        index_entries = parse_federal_laws_index(legis_response.content)

        chunk_records: list[dict[str, Any]] = []
        acts_processed = 0
        acts_skipped_checkpoint = 0
        acts_missing_from_index: list[str] = []

        for source_id, official_number in sorted(targets.items()):
            source_cache_file = (
                _federal_laws_cache_file(cache_dir, source_id)
                if cache_dir is not None
                else None
            )
            index_entry = select_index_entry(index_entries, identifier=official_number)
            if index_entry is None:
                acts_missing_from_index.append(source_id)
                updated_checkpoint_by_source.pop(source_id, None)
                if source_cache_file is not None and source_cache_file.exists():
                    source_cache_file.unlink()
                continue

            checkpoint = checkpoint_by_source.get(source_id)
            revision = _index_entry_revision(index_entry)
            checkpoint_matches = (
                checkpoint is not None
                and checkpoint.get("revision") == revision
                and checkpoint.get("official_number") == official_number
            )
            if (
                not force_full_sync
                and checkpoint_matches
                and source_cache_file is not None
                and source_cache_file.exists()
            ):
                cached_chunks = _read_jsonl(source_cache_file)
                if cached_chunks:
                    acts_skipped_checkpoint += 1
                    chunk_records.extend(cached_chunks)
                    updated_checkpoint_by_source[source_id] = {
                        "revision": revision,
                        "official_number": official_number,
                        "last_materialized_at": materialization_timestamp,
                    }
                    continue

            act_response = client.get(index_entry.link_to_xml)
            act_response.raise_for_status()
            chunks = parse_federal_law_section_chunks(
                act_response.content,
                source_id=source_id,
                index_entry=index_entry,
            )
            acts_processed += 1
            act_chunk_records = [chunk.to_dict() for chunk in chunks]
            chunk_records.extend(act_chunk_records)
            if source_cache_file is not None:
                _write_jsonl(source_cache_file, act_chunk_records)
            updated_checkpoint_by_source[source_id] = {
                "revision": revision,
                "official_number": official_number,
                "last_materialized_at": materialization_timestamp,
            }

    _write_jsonl(output_path, chunk_records)
    _save_federal_laws_materialization_checkpoints(
        checkpoint_path,
        updated_checkpoint_by_source,
    )
    return {
        "status": "ok",
        "target_source_count": len(targets),
        "target_source_ids": sorted(targets),
        "acts_processed": acts_processed,
        "acts_skipped_checkpoint": acts_skipped_checkpoint,
        "acts_missing_from_index": acts_missing_from_index,
        "full_sync_forced": force_full_sync,
        "chunks_written": len(chunk_records),
        "output_path": str(output_path),
        "checkpoint_path": str(checkpoint_path) if checkpoint_path is not None else None,
        "cache_dir": str(cache_dir) if cache_dir is not None else None,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run hourly Cloudflare-safe ingestion schedule "
            "(FC hourly, SCC every 6h, federal laws daily + Tue/Fri full-sync window)."
        )
    )
    parser.add_argument(
        "--utc-timestamp",
        default=None,
        help="Optional UTC timestamp override (ISO-8601, for example 2026-02-27T04:00:00Z).",
    )
    parser.add_argument(
        "--registry",
        default=None,
        help="Optional path to source registry JSON (defaults to canonical registry).",
    )
    parser.add_argument(
        "--source-policy",
        default=os.getenv("SOURCE_POLICY_PATH") or "config/source_policy.yaml",
        help="Optional path to source policy JSON/YAML (defaults to config/source_policy.yaml).",
    )
    parser.add_argument(
        "--fetch-policy",
        default=os.getenv("FETCH_POLICY_PATH") or "config/fetch_policy.yaml",
        help="Optional path to source fetch policy YAML (defaults to config/fetch_policy.yaml).",
    )
    parser.add_argument(
        "--environment",
        default=resolve_default_runtime_environment(),
        help=(
            "Runtime environment for policy gates "
            "(development/staging/production/prod/ci, including hardened aliases)."
        ),
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=None,
        help=(
            "Optional HTTP timeout override applied to all source fetches "
            "(when omitted, fetch policy defaults are used)."
        ),
    )
    parser.add_argument(
        "--state-path",
        default=".cache/immcad/ingestion-checkpoints.json",
        help="Checkpoint state path used for conditional requests (ETag/Last-Modified).",
    )
    parser.add_argument(
        "--output",
        default="artifacts/ingestion/ingestion-cloudflare-hourly.json",
        help="JSON output path for scheduler + ingestion report.",
    )
    parser.add_argument(
        "--federal-laws-output",
        default="artifacts/ingestion/federal-laws-sections.jsonl",
        help="JSONL output path for materialized federal laws section chunks.",
    )
    parser.add_argument(
        "--federal-laws-checkpoint-path",
        default=".cache/immcad/federal-laws-materialization-checkpoints.json",
        help="Checkpoint path for per-act federal laws materialization revisions.",
    )
    parser.add_argument(
        "--federal-laws-cache-dir",
        default=".cache/immcad/federal-laws-sections",
        help="Cache directory for per-act federal laws section chunks.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute schedule and write report without running ingestion jobs.",
    )
    parser.add_argument(
        "--fail-on-error",
        action="store_true",
        help="Exit non-zero when any selected source ingestion fails.",
    )
    return parser.parse_args()


def main() -> int:
    from immcad_api.ingestion import run_ingestion_jobs

    try:
        args = parse_args()
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    run_at_utc = (
        _parse_utc_timestamp(args.utc_timestamp)
        if args.utc_timestamp
        else datetime.now(tz=timezone.utc)
    )
    schedule = build_hourly_schedule(run_at_utc)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    payload: dict[str, Any] = {
        "timestamp_utc": run_at_utc.isoformat().replace("+00:00", "Z"),
        "schedule": schedule,
    }

    if args.dry_run:
        payload["status"] = "dry_run"
        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(
            "Cloudflare hourly schedule dry-run "
            f"(sources={schedule['source_ids']}, output={output_path})"
        )
        return 0

    report = run_ingestion_jobs(
        cadence=None,
        registry_path=args.registry,
        source_ids=schedule["source_ids"],
        source_policy_path=args.source_policy,
        fetch_policy_path=args.fetch_policy,
        environment=args.environment,
        timeout_seconds=args.timeout_seconds,
        state_path=args.state_path,
    )
    payload["status"] = "ok"
    payload["ingestion_report"] = report.to_dict()

    if FEDERAL_LAWS_SOURCE_ID in schedule["source_ids"]:
        laws_result = next(
            (
                item
                for item in report.results
                if item.source_id == FEDERAL_LAWS_SOURCE_ID
            ),
            None,
        )
        if laws_result and laws_result.status == "success":
            payload["federal_laws_materialization"] = materialize_federal_laws_sections(
                registry_path=args.registry,
                output_path=Path(args.federal_laws_output),
                timeout_seconds=args.timeout_seconds,
                checkpoint_path=Path(args.federal_laws_checkpoint_path),
                cache_dir=Path(args.federal_laws_cache_dir),
                force_full_sync=schedule["laws_full_sync_due"],
            )
        else:
            payload["federal_laws_materialization"] = {
                "status": "skipped_not_modified_or_unavailable",
                "chunks_written": 0,
            }

    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(
        "Cloudflare hourly ingestion report generated "
        f"(sources={schedule['source_ids']}, total={report.total}, "
        f"succeeded={report.succeeded}, not_modified={report.not_modified}, "
        f"failed={report.failed})"
    )
    print(f"Report path: {output_path}")

    if args.fail_on_error and report.failed > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
