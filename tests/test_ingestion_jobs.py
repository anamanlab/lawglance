from __future__ import annotations

import json
from pathlib import Path

from immcad_api.ingestion import FetchContext, FetchResult, run_ingestion_jobs
from immcad_api.sources import SourceRegistryEntry


def _write_registry(path: Path) -> Path:
    payload = {
        "version": "2026-02-23",
        "jurisdiction": "ca",
        "sources": [
            {
                "source_id": "SRC_DAILY",
                "source_type": "policy",
                "instrument": "Daily Source",
                "url": "https://example.com/daily",
                "update_cadence": "daily",
            },
            {
                "source_id": "SRC_WEEKLY",
                "source_type": "statute",
                "instrument": "Weekly Source",
                "url": "https://example.com/weekly",
                "update_cadence": "weekly",
            },
            {
                "source_id": "SRC_INCREMENTAL",
                "source_type": "case_law",
                "instrument": "Scheduled Incremental Source",
                "url": "https://example.com/incremental",
                "update_cadence": "scheduled_incremental",
            },
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_run_ingestion_jobs_filters_by_cadence(tmp_path: Path) -> None:
    registry_path = _write_registry(tmp_path / "registry.json")

    def fetcher(source: SourceRegistryEntry, context: FetchContext) -> FetchResult:
        assert context.etag is None
        assert context.last_modified is None
        return FetchResult(payload=source.source_id.encode("utf-8"), http_status=200)

    report = run_ingestion_jobs(
        cadence="daily",
        registry_path=registry_path,
        fetcher=fetcher,
    )

    assert report.cadence == "daily"
    assert report.total == 1
    assert report.failed == 0
    assert report.not_modified == 0
    assert report.succeeded == 1
    assert report.results[0].source_id == "SRC_DAILY"
    assert report.results[0].checksum_sha256 is not None


def test_run_ingestion_jobs_collects_failures(tmp_path: Path) -> None:
    registry_path = _write_registry(tmp_path / "registry.json")

    def fetcher(source: SourceRegistryEntry, _: FetchContext) -> FetchResult:
        if source.source_id == "SRC_WEEKLY":
            raise RuntimeError("source unavailable")
        return FetchResult(payload=b"ok", http_status=200)

    report = run_ingestion_jobs(registry_path=registry_path, fetcher=fetcher)

    assert report.total == 3
    assert report.succeeded == 2
    assert report.not_modified == 0
    assert report.failed == 1
    errors = [result for result in report.results if result.status == "error"]
    assert len(errors) == 1
    assert errors[0].source_id == "SRC_WEEKLY"
    assert "source unavailable" in (errors[0].error or "")


def test_run_ingestion_jobs_uses_checkpoint_conditional_context(tmp_path: Path) -> None:
    registry_path = _write_registry(tmp_path / "registry.json")
    state_path = tmp_path / "checkpoints.json"

    def initial_fetcher(source: SourceRegistryEntry, context: FetchContext) -> FetchResult:
        assert context.etag is None
        assert context.last_modified is None
        if source.source_id == "SRC_DAILY":
            return FetchResult(
                payload=b"daily-v1",
                http_status=200,
                etag='"daily-v1"',
                last_modified="Mon, 24 Feb 2026 00:00:00 GMT",
            )
        return FetchResult(payload=b"other", http_status=200)

    first_report = run_ingestion_jobs(
        cadence="daily",
        registry_path=registry_path,
        state_path=state_path,
        fetcher=initial_fetcher,
    )
    assert first_report.succeeded == 1
    assert first_report.not_modified == 0

    def conditional_fetcher(source: SourceRegistryEntry, context: FetchContext) -> FetchResult:
        assert source.source_id == "SRC_DAILY"
        assert context.etag == '"daily-v1"'
        assert context.last_modified == "Mon, 24 Feb 2026 00:00:00 GMT"
        return FetchResult(payload=None, http_status=304)

    second_report = run_ingestion_jobs(
        cadence="daily",
        registry_path=registry_path,
        state_path=state_path,
        fetcher=conditional_fetcher,
    )

    assert second_report.total == 1
    assert second_report.succeeded == 0
    assert second_report.not_modified == 1
    assert second_report.failed == 0
    assert second_report.results[0].status == "not_modified"
    assert second_report.results[0].bytes_fetched == 0
