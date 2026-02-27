from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from immcad_api.main import create_app


def _build_client(
    monkeypatch: pytest.MonkeyPatch,
    checkpoint_state_path: Path | None = None,
) -> TestClient:
    if checkpoint_state_path is None:
        monkeypatch.delenv("INGESTION_CHECKPOINT_STATE_PATH", raising=False)
    else:
        monkeypatch.setenv("INGESTION_CHECKPOINT_STATE_PATH", str(checkpoint_state_path))
    return TestClient(create_app())


def test_source_transparency_endpoint_lists_fc_fca_scc_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _build_client(monkeypatch)

    response = client.get("/api/sources/transparency")

    assert response.status_code == 200
    body = response.json()
    assert body["jurisdiction"] == "ca"
    assert body["checkpoint"]["path"] == ".cache/immcad/ingestion-checkpoints.json"
    assert {"SCC", "FC", "FCA"}.issubset(set(body["supported_courts"]))

    sources_by_id = {item["source_id"]: item for item in body["case_law_sources"]}
    assert sources_by_id["SCC_DECISIONS"]["court"] == "SCC"
    assert sources_by_id["FC_DECISIONS"]["court"] == "FC"
    assert sources_by_id["FCA_DECISIONS"]["court"] == "FCA"


def test_source_transparency_endpoint_reads_checkpoint_freshness_status(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    now = datetime.now(tz=timezone.utc)
    fc_success_at = now - timedelta(hours=1)
    scc_success_at = now - timedelta(days=3)

    checkpoint_state_path = tmp_path / "ingestion-checkpoints.json"
    checkpoint_state_path.write_text(
        json.dumps(
            {
                "version": 1,
                "updated_at": now.isoformat().replace("+00:00", "Z"),
                "checkpoints": {
                    "FC_DECISIONS": {
                        "etag": "etag-fc",
                        "last_modified": None,
                        "checksum_sha256": "abc123",
                        "last_http_status": 200,
                        "last_success_at": fc_success_at.isoformat().replace(
                            "+00:00", "Z"
                        ),
                    },
                    "SCC_DECISIONS": {
                        "etag": "etag-scc",
                        "last_modified": None,
                        "checksum_sha256": "def456",
                        "last_http_status": 200,
                        "last_success_at": scc_success_at.isoformat().replace(
                            "+00:00", "Z"
                        ),
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    client = _build_client(monkeypatch, checkpoint_state_path=checkpoint_state_path)

    response = client.get("/api/sources/transparency")

    assert response.status_code == 200
    body = response.json()
    assert body["checkpoint"]["path"] == str(checkpoint_state_path)
    assert body["checkpoint"]["exists"] is True

    sources_by_id = {item["source_id"]: item for item in body["case_law_sources"]}
    assert sources_by_id["FC_DECISIONS"]["last_http_status"] == 200
    assert sources_by_id["FC_DECISIONS"]["freshness_status"] == "fresh"
    assert sources_by_id["SCC_DECISIONS"]["freshness_status"] == "stale"
