from __future__ import annotations

import json
from pathlib import Path

import pytest

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


@pytest.mark.parametrize(
    "environment",
    ["production", "prod", "ci", "production-us-east", "prod_blue", "ci-smoke"],
)
def test_run_ingestion_jobs_blocks_source_by_policy_in_production(
    tmp_path: Path,
    environment: str,
) -> None:
    registry_path = tmp_path / "registry.json"
    registry_payload = {
        "version": "2026-02-24",
        "jurisdiction": "ca",
        "sources": [
            {
                "source_id": "A2AJ",
                "source_type": "case_law",
                "instrument": "A2AJ feed",
                "url": "https://example.com/a2aj",
                "update_cadence": "scheduled_incremental",
            }
        ],
    }
    registry_path.write_text(json.dumps(registry_payload), encoding="utf-8")

    def fetcher(_: SourceRegistryEntry, __: FetchContext) -> FetchResult:
        raise AssertionError("Fetcher should not run for policy-blocked source")

    report = run_ingestion_jobs(
        registry_path=registry_path,
        environment=environment,
        fetcher=fetcher,
    )

    assert report.total == 1
    assert report.succeeded == 0
    assert report.not_modified == 0
    assert report.blocked == 1
    assert report.failed == 0
    assert report.results[0].status == "blocked_policy"
    assert report.results[0].policy_reason == "production_ingest_blocked_by_policy"


@pytest.mark.parametrize("environment", ["development", "internal_runtime"])
def test_run_ingestion_jobs_allows_source_by_policy_in_internal_runtime(
    tmp_path: Path,
    environment: str,
) -> None:
    registry_path = tmp_path / "registry.json"
    registry_payload = {
        "version": "2026-02-24",
        "jurisdiction": "ca",
        "sources": [
            {
                "source_id": "A2AJ",
                "source_type": "case_law",
                "instrument": "A2AJ feed",
                "url": "https://example.com/a2aj",
                "update_cadence": "scheduled_incremental",
            }
        ],
    }
    registry_path.write_text(json.dumps(registry_payload), encoding="utf-8")

    def fetcher(source: SourceRegistryEntry, _: FetchContext) -> FetchResult:
        return FetchResult(payload=source.source_id.encode("utf-8"), http_status=200)

    report = run_ingestion_jobs(
        registry_path=registry_path,
        environment=environment,
        fetcher=fetcher,
    )

    assert report.total == 1
    assert report.succeeded == 1
    assert report.not_modified == 0
    assert report.blocked == 0
    assert report.failed == 0
    assert report.results[0].status == "success"
    assert report.results[0].policy_reason == "internal_ingest_allowed"


def test_run_ingestion_jobs_validates_scc_payload_success(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.json"
    registry_payload = {
        "version": "2026-02-24",
        "jurisdiction": "ca",
        "sources": [
            {
                "source_id": "SCC_DECISIONS",
                "source_type": "case_law",
                "instrument": "SCC decisions feed",
                "url": "https://example.com/scc",
                "update_cadence": "scheduled_incremental",
            }
        ],
    }
    registry_path.write_text(json.dumps(registry_payload), encoding="utf-8")

    payload = {
        "rss": {
            "channel": {
                "item": [
                    {
                        "title": "Example v Canada, 2024 SCC 3",
                        "link": "https://decisions.scc-csc.ca/scc-csc/scc-csc/en/item/123/index.do",
                        "pubDate": "Tue, 20 Feb 2024 10:00:00 GMT",
                    }
                ]
            }
        }
    }

    def fetcher(_: SourceRegistryEntry, __: FetchContext) -> FetchResult:
        return FetchResult(payload=json.dumps(payload).encode("utf-8"), http_status=200)

    report = run_ingestion_jobs(
        registry_path=registry_path,
        environment="production",
        fetcher=fetcher,
    )

    assert report.total == 1
    assert report.succeeded == 1
    assert report.failed == 0
    assert report.results[0].status == "success"
    assert report.results[0].records_total == 1
    assert report.results[0].records_valid == 1
    assert report.results[0].records_invalid == 0


def test_run_ingestion_jobs_fails_on_invalid_scc_payload(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.json"
    registry_payload = {
        "version": "2026-02-24",
        "jurisdiction": "ca",
        "sources": [
            {
                "source_id": "SCC_DECISIONS",
                "source_type": "case_law",
                "instrument": "SCC decisions feed",
                "url": "https://example.com/scc",
                "update_cadence": "scheduled_incremental",
            }
        ],
    }
    registry_path.write_text(json.dumps(registry_payload), encoding="utf-8")

    bad_payload = {
        "rss": {
            "channel": {
                "item": [
                    {
                        "title": "Missing SCC citation",
                        "link": "https://decisions.scc-csc.ca/scc-csc/scc-csc/en/item/321/index.do",
                        "pubDate": "Tue, 20 Feb 2024 10:00:00 GMT",
                    }
                ]
            }
        }
    }

    def fetcher(_: SourceRegistryEntry, __: FetchContext) -> FetchResult:
        return FetchResult(payload=json.dumps(bad_payload).encode("utf-8"), http_status=200)

    report = run_ingestion_jobs(
        registry_path=registry_path,
        environment="production",
        fetcher=fetcher,
    )

    assert report.total == 1
    assert report.succeeded == 0
    assert report.failed == 1
    assert report.results[0].status == "error"
    assert "validation failed" in (report.results[0].error or "")


def test_run_ingestion_jobs_allows_partial_invalid_fc_payload(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.json"
    registry_payload = {
        "version": "2026-02-24",
        "jurisdiction": "ca",
        "sources": [
            {
                "source_id": "FC_DECISIONS",
                "source_type": "case_law",
                "instrument": "FC decisions feed",
                "url": "https://example.com/fc",
                "update_cadence": "scheduled_incremental",
            }
        ],
    }
    registry_path.write_text(json.dumps(registry_payload), encoding="utf-8")

    mixed_payload = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>Doe v Canada, 2026 FC 272</title>
      <link>https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/item/111111/index.do</link>
      <description>Neutral citation 2026 FC 272</description>
      <pubDate>Tue, 20 Feb 2024 10:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Missing citation entry</title>
      <link>https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/item/222222/index.do</link>
      <description>No neutral citation in this record</description>
      <pubDate>Tue, 20 Feb 2024 10:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""

    def fetcher(_: SourceRegistryEntry, __: FetchContext) -> FetchResult:
        return FetchResult(payload=mixed_payload, http_status=200)

    report = run_ingestion_jobs(
        registry_path=registry_path,
        environment="production",
        fetcher=fetcher,
    )

    assert report.total == 1
    assert report.succeeded == 1
    assert report.failed == 0
    assert report.results[0].status == "success"
    assert report.results[0].records_total == 2
    assert report.results[0].records_valid == 1
    assert report.results[0].records_invalid == 1
    assert "validation warning" in (report.results[0].error or "")


def test_run_ingestion_jobs_applies_retry_budget_from_fetch_policy(
    tmp_path: Path,
) -> None:
    registry_path = _write_registry(tmp_path / "registry.json")
    fetch_policy_path = tmp_path / "fetch_policy.yaml"
    fetch_policy_path.write_text(
        "\n".join(
            [
                "default:",
                "  timeout_seconds: 5",
                "  max_retries: 0",
                "  retry_backoff_seconds: 0",
                "sources:",
                "  SRC_DAILY:",
                "    timeout_seconds: 5",
                "    max_retries: 2",
                "    retry_backoff_seconds: 0",
            ]
        ),
        encoding="utf-8",
    )

    attempts = {"count": 0}

    def fetcher(_: SourceRegistryEntry, __: FetchContext) -> FetchResult:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RuntimeError("temporary upstream failure")
        return FetchResult(payload=b"daily-ok", http_status=200)

    report = run_ingestion_jobs(
        cadence="daily",
        registry_path=registry_path,
        fetch_policy_path=fetch_policy_path,
        fetcher=fetcher,
    )

    assert attempts["count"] == 3
    assert report.total == 1
    assert report.succeeded == 1
    assert report.failed == 0


def test_run_ingestion_jobs_fails_when_retry_budget_exhausted(
    tmp_path: Path,
) -> None:
    registry_path = _write_registry(tmp_path / "registry.json")
    fetch_policy_path = tmp_path / "fetch_policy.yaml"
    fetch_policy_path.write_text(
        "\n".join(
            [
                "default:",
                "  timeout_seconds: 5",
                "  max_retries: 1",
                "  retry_backoff_seconds: 0",
            ]
        ),
        encoding="utf-8",
    )

    attempts = {"count": 0}

    def fetcher(_: SourceRegistryEntry, __: FetchContext) -> FetchResult:
        attempts["count"] += 1
        raise RuntimeError("persistent upstream failure")

    report = run_ingestion_jobs(
        cadence="daily",
        registry_path=registry_path,
        fetch_policy_path=fetch_policy_path,
        fetcher=fetcher,
    )

    assert attempts["count"] == 2
    assert report.total == 1
    assert report.succeeded == 0
    assert report.failed == 1
    assert report.results[0].status == "error"
    assert "fetch failed after 2 attempts" in (report.results[0].error or "")


def test_run_ingestion_jobs_timeout_override_applies_to_all_sources(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry_path = _write_registry(tmp_path / "registry.json")
    fetch_policy_path = tmp_path / "fetch_policy.yaml"
    fetch_policy_path.write_text(
        "\n".join(
            [
                "default:",
                "  timeout_seconds: 5",
                "  max_retries: 1",
                "  retry_backoff_seconds: 0",
                "sources:",
                "  SRC_DAILY:",
                "    timeout_seconds: 2",
                "    max_retries: 1",
                "    retry_backoff_seconds: 0",
            ]
        ),
        encoding="utf-8",
    )

    captured: dict[str, float | None] = {"timeout": None}

    class _FakeResponse:
        status_code = 200
        headers: dict[str, str] = {}
        content = b"ok"

        @staticmethod
        def raise_for_status() -> None:
            return None

    class _FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self) -> "_FakeClient":
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

        def get(self, url: str, headers=None, timeout=None) -> _FakeResponse:
            captured["timeout"] = timeout
            return _FakeResponse()

    monkeypatch.setattr("immcad_api.ingestion.jobs.httpx.Client", _FakeClient)

    report = run_ingestion_jobs(
        cadence="daily",
        registry_path=registry_path,
        fetch_policy_path=fetch_policy_path,
        timeout_seconds=11.0,
    )

    assert report.total == 1
    assert report.succeeded == 1
    assert captured["timeout"] == 11.0


def test_run_ingestion_jobs_filters_by_explicit_source_ids(tmp_path: Path) -> None:
    registry_path = _write_registry(tmp_path / "registry.json")
    seen_source_ids: list[str] = []

    def fetcher(source: SourceRegistryEntry, _: FetchContext) -> FetchResult:
        seen_source_ids.append(source.source_id)
        return FetchResult(payload=b"ok", http_status=200)

    report = run_ingestion_jobs(
        registry_path=registry_path,
        source_ids=["SRC_WEEKLY"],
        fetcher=fetcher,
    )

    assert report.total == 1
    assert report.succeeded == 1
    assert report.results[0].source_id == "SRC_WEEKLY"
    assert seen_source_ids == ["SRC_WEEKLY"]


def test_run_ingestion_jobs_marks_unchanged_checksum_as_not_modified(tmp_path: Path) -> None:
    registry_path = _write_registry(tmp_path / "registry.json")
    state_path = tmp_path / "state.json"

    def initial_fetcher(_: SourceRegistryEntry, __: FetchContext) -> FetchResult:
        return FetchResult(payload=b"daily-v1", http_status=200)

    first_report = run_ingestion_jobs(
        cadence="daily",
        registry_path=registry_path,
        state_path=state_path,
        fetcher=initial_fetcher,
    )
    assert first_report.total == 1
    assert first_report.succeeded == 1
    assert first_report.not_modified == 0

    def unchanged_fetcher(source: SourceRegistryEntry, context: FetchContext) -> FetchResult:
        assert source.source_id == "SRC_DAILY"
        assert context.etag is None
        assert context.last_modified is None
        return FetchResult(payload=b"daily-v1", http_status=200)

    second_report = run_ingestion_jobs(
        cadence="daily",
        registry_path=registry_path,
        state_path=state_path,
        fetcher=unchanged_fetcher,
    )

    assert second_report.total == 1
    assert second_report.succeeded == 0
    assert second_report.not_modified == 1
    assert second_report.failed == 0
    assert second_report.results[0].status == "not_modified"
    assert second_report.results[0].bytes_fetched == 0


def test_run_ingestion_jobs_uses_head_probe_for_federal_laws_bulk_xml(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry_path = tmp_path / "registry.json"
    state_path = tmp_path / "state.json"
    registry_payload = {
        "version": "2026-02-27",
        "jurisdiction": "ca",
        "sources": [
            {
                "source_id": "FEDERAL_LAWS_BULK_XML",
                "source_type": "statute",
                "instrument": "Justice Laws website bulk XML index",
                "url": "https://laws-lois.justice.gc.ca/eng/XML/Legis.xml",
                "update_cadence": "daily",
            }
        ],
    }
    registry_path.write_text(json.dumps(registry_payload), encoding="utf-8")

    calls: list[str] = []
    etag = '"laws-v1"'
    last_modified = "Wed, 18 Feb 2026 16:43:54 GMT"

    class _FakeResponse:
        def __init__(
            self,
            *,
            status_code: int,
            headers: dict[str, str] | None = None,
            content: bytes = b"",
        ) -> None:
            self.status_code = status_code
            self.headers = headers or {}
            self.content = content

        def raise_for_status(self) -> None:
            return None

    class _FakeClient:
        def __enter__(self) -> "_FakeClient":
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

        def head(self, url: str, headers=None, timeout=None) -> _FakeResponse:
            del url, headers, timeout
            calls.append("HEAD")
            return _FakeResponse(
                status_code=200,
                headers={"ETag": etag, "Last-Modified": last_modified},
            )

        def get(self, url: str, headers=None, timeout=None) -> _FakeResponse:
            del url, headers, timeout
            calls.append("GET")
            return _FakeResponse(
                status_code=200,
                headers={"ETag": etag, "Last-Modified": last_modified},
                content=b"<Legis />",
            )

    monkeypatch.setattr("immcad_api.ingestion.jobs.httpx.Client", lambda *args, **kwargs: _FakeClient())

    first_report = run_ingestion_jobs(
        cadence="daily",
        registry_path=registry_path,
        state_path=state_path,
    )
    assert first_report.total == 1
    assert first_report.succeeded == 1
    assert calls == ["HEAD", "GET"]

    second_report = run_ingestion_jobs(
        cadence="daily",
        registry_path=registry_path,
        state_path=state_path,
    )
    assert second_report.total == 1
    assert second_report.succeeded == 0
    assert second_report.not_modified == 1
    assert second_report.results[0].status == "not_modified"
    assert calls == ["HEAD", "GET", "HEAD"]
