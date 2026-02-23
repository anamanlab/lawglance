from __future__ import annotations

import json
from pathlib import Path

from immcad_api.ingestion import build_ingestion_plan


def test_build_ingestion_plan_uses_registry_defaults() -> None:
    plan = build_ingestion_plan()
    assert plan.jurisdiction == "ca"
    assert "weekly" in plan.cadence_to_sources
    assert "daily" in plan.cadence_to_sources
    assert "IRPA" in plan.cadence_to_sources["weekly"]


def test_build_ingestion_plan_groups_by_cadence(tmp_path: Path) -> None:
    payload = {
        "version": "2026-02-23",
        "jurisdiction": "ca",
        "sources": [
            {
                "source_id": "SRC_A",
                "source_type": "statute",
                "instrument": "A law",
                "url": "https://example.com/a",
                "update_cadence": "weekly",
            },
            {
                "source_id": "SRC_B",
                "source_type": "policy",
                "instrument": "B policy",
                "url": "https://example.com/b",
                "update_cadence": "daily",
            },
            {
                "source_id": "SRC_C",
                "source_type": "policy",
                "instrument": "C policy",
                "url": "https://example.com/c",
                "update_cadence": "daily",
            },
        ],
    }
    registry = tmp_path / "registry.json"
    registry.write_text(json.dumps(payload), encoding="utf-8")

    plan = build_ingestion_plan(registry)
    assert plan.cadence_to_sources["daily"] == ["SRC_B", "SRC_C"]
    assert plan.cadence_to_sources["weekly"] == ["SRC_A"]
