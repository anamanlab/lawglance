from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import sys

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "run_cloudflare_ingestion_hourly.py"
SPEC = importlib.util.spec_from_file_location("run_cloudflare_ingestion_hourly", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules["run_cloudflare_ingestion_hourly"] = MODULE
SPEC.loader.exec_module(MODULE)


def test_hourly_schedule_runs_fc_each_hour() -> None:
    schedule = MODULE.build_hourly_schedule(
        datetime(2026, 2, 27, 1, 0, tzinfo=timezone.utc)
    )

    assert schedule["source_ids"] == ["FC_DECISIONS"]
    assert schedule["scc_due"] is False
    assert schedule["laws_due"] is False
    assert schedule["laws_full_sync_due"] is False


def test_hourly_schedule_runs_scc_every_six_hours() -> None:
    schedule = MODULE.build_hourly_schedule(
        datetime(2026, 2, 27, 6, 0, tzinfo=timezone.utc)
    )

    assert schedule["source_ids"] == ["FC_DECISIONS", "SCC_DECISIONS"]
    assert schedule["scc_due"] is True
    assert schedule["laws_due"] is False
    assert schedule["laws_full_sync_due"] is False


def test_hourly_schedule_runs_laws_daily_and_flags_full_sync_windows() -> None:
    daily_schedule = MODULE.build_hourly_schedule(
        datetime(2026, 2, 26, 3, 0, tzinfo=timezone.utc)
    )
    assert daily_schedule["source_ids"] == ["FC_DECISIONS", "FEDERAL_LAWS_BULK_XML"]
    assert daily_schedule["laws_due"] is True
    assert daily_schedule["laws_full_sync_due"] is False

    full_sync_schedule = MODULE.build_hourly_schedule(
        datetime(2026, 2, 27, 4, 0, tzinfo=timezone.utc)
    )
    assert full_sync_schedule["source_ids"] == ["FC_DECISIONS", "FEDERAL_LAWS_BULK_XML"]
    assert full_sync_schedule["laws_due"] is False
    assert full_sync_schedule["laws_full_sync_due"] is True


def _write_federal_laws_registry(path: Path) -> Path:
    payload = {
        "version": "2026-02-27",
        "jurisdiction": "ca",
        "sources": [
            {
                "source_id": "FEDERAL_LAWS_BULK_XML",
                "source_type": "statute",
                "instrument": "Justice Laws bulk XML",
                "url": "https://laws-lois.justice.gc.ca/eng/XML/Legis.xml",
                "update_cadence": "daily",
            },
            {
                "source_id": "IRPA",
                "source_type": "statute",
                "instrument": "IRPA",
                "url": "https://laws-lois.justice.gc.ca/eng/acts/I-2.5/FullText.html",
                "update_cadence": "weekly",
            },
            {
                "source_id": "IRPR",
                "source_type": "regulation",
                "instrument": "IRPR",
                "url": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-2002-227/FullText.html",
                "update_cadence": "weekly",
            },
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _federal_index_payload() -> bytes:
    return b"""<?xml version="1.0" encoding="UTF-8"?>
<ActsRegsList>
  <Acts>
    <Act>
      <UniqueId>I-2.5</UniqueId>
      <OfficialNumber>I-2.5</OfficialNumber>
      <Language>eng</Language>
      <LinkToXML>https://laws-lois.justice.gc.ca/eng/XML/I-2.5.xml</LinkToXML>
      <LinkToHTMLToC>https://laws-lois.justice.gc.ca/eng/acts/I-2.5/index.html</LinkToHTMLToC>
      <Title>Immigration and Refugee Protection Act</Title>
      <CurrentToDate>2026-02-18</CurrentToDate>
    </Act>
  </Acts>
  <Regulations>
    <Regulation>
      <UniqueId>SOR-2002-227</UniqueId>
      <OfficialNumber>SOR-2002-227</OfficialNumber>
      <Language>eng</Language>
      <LinkToXML>https://laws-lois.justice.gc.ca/eng/XML/SOR-2002-227.xml</LinkToXML>
      <LinkToHTMLToC>https://laws-lois.justice.gc.ca/eng/regulations/SOR-2002-227/index.html</LinkToHTMLToC>
      <Title>Immigration and Refugee Protection Regulations</Title>
      <CurrentToDate>2026-02-18</CurrentToDate>
    </Regulation>
  </Regulations>
</ActsRegsList>
"""


def _act_payload(section_label: str, text: str) -> bytes:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Statute>
  <Body>
    <Section>
      <Label>{section_label}</Label>
      <MarginalNote>Example</MarginalNote>
      <Subsection>
        <Label>(1)</Label>
        <Text>{text}</Text>
      </Subsection>
    </Section>
  </Body>
</Statute>
""".encode("utf-8")


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


class _FakeResponse:
    def __init__(self, *, content: bytes, status_code: int = 200) -> None:
        self.content = content
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"unexpected status {self.status_code}")


class _FakeHttpClient:
    def __init__(
        self,
        *,
        responses: dict[str, _FakeResponse],
        calls: list[str],
    ) -> None:
        self._responses = responses
        self._calls = calls

    def __enter__(self) -> "_FakeHttpClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def get(self, url: str) -> _FakeResponse:
        self._calls.append(url)
        response = self._responses.get(url)
        if response is None:
            raise AssertionError(f"missing fake response for {url}")
        return response


class _FakeHttpClientFactory:
    def __init__(self, responses: dict[str, _FakeResponse]) -> None:
        self.calls: list[str] = []
        self._responses = responses

    def __call__(self, *args, **kwargs) -> _FakeHttpClient:
        return _FakeHttpClient(responses=self._responses, calls=self.calls)


def test_materialization_skips_unchanged_federal_law_acts_between_runs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry_path = _write_federal_laws_registry(tmp_path / "registry.json")
    output_path = tmp_path / "federal-laws-sections.jsonl"
    checkpoint_path = tmp_path / "federal-laws-checkpoints.json"
    cache_dir = tmp_path / "federal-laws-cache"
    legis_url = "https://laws-lois.justice.gc.ca/eng/XML/Legis.xml"
    irpa_xml_url = "https://laws-lois.justice.gc.ca/eng/XML/I-2.5.xml"
    irpr_xml_url = "https://laws-lois.justice.gc.ca/eng/XML/SOR-2002-227.xml"
    client_factory = _FakeHttpClientFactory(
        {
            legis_url: _FakeResponse(content=_federal_index_payload()),
            irpa_xml_url: _FakeResponse(content=_act_payload("3", "IRPA objectives")),
            irpr_xml_url: _FakeResponse(content=_act_payload("2", "IRPR objectives")),
        }
    )
    monkeypatch.setattr(MODULE.httpx, "Client", client_factory)

    first_result = MODULE.materialize_federal_laws_sections(
        registry_path=str(registry_path),
        output_path=output_path,
        timeout_seconds=5.0,
        checkpoint_path=checkpoint_path,
        cache_dir=cache_dir,
        force_full_sync=False,
    )
    assert first_result["acts_processed"] == 2
    assert first_result["acts_skipped_checkpoint"] == 0
    assert first_result["chunks_written"] == 2
    assert client_factory.calls.count(irpa_xml_url) == 1
    assert client_factory.calls.count(irpr_xml_url) == 1
    assert {chunk["source_id"] for chunk in _read_jsonl(output_path)} == {"IRPA", "IRPR"}

    client_factory.calls.clear()
    second_result = MODULE.materialize_federal_laws_sections(
        registry_path=str(registry_path),
        output_path=output_path,
        timeout_seconds=5.0,
        checkpoint_path=checkpoint_path,
        cache_dir=cache_dir,
        force_full_sync=False,
    )
    assert second_result["acts_processed"] == 0
    assert second_result["acts_skipped_checkpoint"] == 2
    assert second_result["chunks_written"] == 2
    assert client_factory.calls == [legis_url]


def test_materialization_full_sync_window_forces_per_act_refresh(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry_path = _write_federal_laws_registry(tmp_path / "registry.json")
    output_path = tmp_path / "federal-laws-sections.jsonl"
    checkpoint_path = tmp_path / "federal-laws-checkpoints.json"
    cache_dir = tmp_path / "federal-laws-cache"
    irpa_xml_url = "https://laws-lois.justice.gc.ca/eng/XML/I-2.5.xml"
    irpr_xml_url = "https://laws-lois.justice.gc.ca/eng/XML/SOR-2002-227.xml"
    client_factory = _FakeHttpClientFactory(
        {
            "https://laws-lois.justice.gc.ca/eng/XML/Legis.xml": _FakeResponse(
                content=_federal_index_payload()
            ),
            irpa_xml_url: _FakeResponse(content=_act_payload("3", "IRPA objectives")),
            irpr_xml_url: _FakeResponse(content=_act_payload("2", "IRPR objectives")),
        }
    )
    monkeypatch.setattr(MODULE.httpx, "Client", client_factory)

    MODULE.materialize_federal_laws_sections(
        registry_path=str(registry_path),
        output_path=output_path,
        timeout_seconds=5.0,
        checkpoint_path=checkpoint_path,
        cache_dir=cache_dir,
        force_full_sync=False,
    )

    client_factory.calls.clear()
    full_sync_result = MODULE.materialize_federal_laws_sections(
        registry_path=str(registry_path),
        output_path=output_path,
        timeout_seconds=5.0,
        checkpoint_path=checkpoint_path,
        cache_dir=cache_dir,
        force_full_sync=True,
    )

    assert full_sync_result["acts_processed"] == 2
    assert full_sync_result["acts_skipped_checkpoint"] == 0
    assert client_factory.calls.count(irpa_xml_url) == 1
    assert client_factory.calls.count(irpr_xml_url) == 1
