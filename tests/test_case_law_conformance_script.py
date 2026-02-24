from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "run_case_law_conformance.py"


def _load_script_module():
    assert SCRIPT_PATH.exists(), "Expected scripts/run_case_law_conformance.py to exist"
    spec = importlib.util.spec_from_file_location("run_case_law_conformance", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_registry(tmp_path: Path, sources: list[dict[str, Any]]) -> Path:
    payload = {
        "version": "test-v1",
        "jurisdiction": "ca",
        "sources": sources,
    }
    path = tmp_path / "registry.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _scc_valid_payload() -> bytes:
    return json.dumps(
        {
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
    ).encode("utf-8")


def _fc_invalid_payload() -> bytes:
    return b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>Example without expected citation format</title>
      <link>https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/item/111/index.do</link>
      <pubDate>Thu, 22 Feb 2024 12:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""


def test_run_case_law_conformance_builds_report_with_pass_warn_fail(tmp_path: Path) -> None:
    from immcad_api.ops.case_law_conformance import run_case_law_conformance

    registry_path = _write_registry(
        tmp_path,
        [
            {
                "source_id": "SCC_DECISIONS",
                "source_type": "case_law",
                "instrument": "SCC feed",
                "url": "https://example.test/scc",
                "update_cadence": "scheduled_incremental",
            },
            {
                "source_id": "FC_DECISIONS",
                "source_type": "case_law",
                "instrument": "FC feed",
                "url": "https://example.test/fc",
                "update_cadence": "scheduled_incremental",
            },
            {
                "source_id": "FCA_DECISIONS",
                "source_type": "case_law",
                "instrument": "FCA feed",
                "url": "https://example.test/fca",
                "update_cadence": "scheduled_incremental",
            },
        ],
    )

    responses = {
        "https://example.test/scc": (200, {"content-type": "application/json"}, _scc_valid_payload()),
        "https://example.test/fc": (200, {"content-type": "text/xml"}, _fc_invalid_payload()),
        "https://example.test/fca": (404, {"content-type": "application/json"}, b'{"error":"not found"}'),
    }

    def fetcher(url: str, *, timeout_seconds: float):
        assert timeout_seconds == 5.0
        status, headers, payload = responses[url]
        return status, headers, payload

    report = run_case_law_conformance(
        registry_path=registry_path,
        timeout_seconds=5.0,
        max_invalid_ratio=1.0,
        min_records=1,
        fetcher=fetcher,
    )

    assert report["overall_status"] == "fail"
    results = {item["source_id"]: item for item in report["results"]}
    assert results["SCC_DECISIONS"]["status"] == "pass"
    assert results["FC_DECISIONS"]["status"] == "warn"
    assert results["FC_DECISIONS"]["records_invalid"] == 1
    assert results["FCA_DECISIONS"]["status"] == "fail"
    assert results["FCA_DECISIONS"]["http_status"] == 404


def test_script_main_non_strict_writes_report_and_returns_zero(monkeypatch, tmp_path: Path) -> None:
    module = _load_script_module()
    output_path = tmp_path / "conformance.json"

    def fake_runner(**kwargs):
        assert kwargs["strict"] is False
        return {
            "generated_at": "2026-02-24T00:00:00Z",
            "overall_status": "fail",
            "results": [],
        }

    monkeypatch.setattr(module, "run_case_law_conformance", fake_runner)
    exit_code = module.main(["--output", str(output_path)])

    assert exit_code == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["overall_status"] == "fail"


def test_script_main_strict_returns_nonzero_on_fail(monkeypatch, tmp_path: Path) -> None:
    module = _load_script_module()
    output_path = tmp_path / "conformance.json"

    def fake_runner(**kwargs):
        assert kwargs["strict"] is True
        return {
            "generated_at": "2026-02-24T00:00:00Z",
            "overall_status": "fail",
            "results": [],
        }

    monkeypatch.setattr(module, "run_case_law_conformance", fake_runner)
    exit_code = module.main(["--output", str(output_path), "--strict"])

    assert exit_code == 1
