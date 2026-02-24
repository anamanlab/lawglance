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


def _write_court_registry(path: Path) -> Path:
    payload = {
        "version": "2026-02-24",
        "jurisdiction": "ca",
        "sources": [
            {
                "source_id": "FC_DECISIONS",
                "source_type": "case_law",
                "instrument": "Federal Court Decisions Feed",
                "url": "https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/rss.do?req=3",
                "update_cadence": "scheduled_incremental",
            }
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _mixed_fc_rss_payload() -> bytes:
    return b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>Doe v Canada, 2024 FC 10</title>
      <link>https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/item/987/index.do</link>
      <pubDate>Mon, 19 Feb 2024 09:00:00 GMT</pubDate>
      <description>Sample case description</description>
    </item>
    <item>
      <title>Example without expected citation format</title>
      <link>https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/item/111/index.do</link>
      <pubDate>Thu, 22 Feb 2024 12:00:00 GMT</pubDate>
      <description>Missing citation text</description>
    </item>
  </channel>
</rss>
"""


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


def test_run_ingestion_jobs_tolerates_small_court_invalid_ratio(tmp_path: Path) -> None:
    registry_path = _write_court_registry(tmp_path / "court-registry.json")

    def fetcher(source: SourceRegistryEntry, _: FetchContext) -> FetchResult:
        assert source.source_id == "FC_DECISIONS"
        return FetchResult(payload=_mixed_fc_rss_payload(), http_status=200)

    report = run_ingestion_jobs(
        registry_path=registry_path,
        fetcher=fetcher,
        court_validation_max_invalid_ratio=0.50,
        court_validation_min_valid_records=1,
    )

    assert report.total == 1
    assert report.succeeded == 1
    assert report.failed == 0
    assert report.results[0].status == "success"
    assert report.results[0].records_total == 2
    assert report.results[0].records_valid == 1
    assert report.results[0].records_invalid == 1


def test_run_ingestion_jobs_fails_when_court_invalid_ratio_exceeds_threshold(tmp_path: Path) -> None:
    registry_path = _write_court_registry(tmp_path / "court-registry.json")

    def fetcher(source: SourceRegistryEntry, _: FetchContext) -> FetchResult:
        assert source.source_id == "FC_DECISIONS"
        return FetchResult(payload=_mixed_fc_rss_payload(), http_status=200)

    report = run_ingestion_jobs(
        registry_path=registry_path,
        fetcher=fetcher,
        court_validation_max_invalid_ratio=0.25,
        court_validation_min_valid_records=1,
    )

    assert report.total == 1
    assert report.succeeded == 0
    assert report.failed == 1
    assert report.results[0].status == "error"
    assert "invalid ratio" in (report.results[0].error or "")
