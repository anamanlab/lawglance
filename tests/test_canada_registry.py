from __future__ import annotations

import json
from pathlib import Path


REGISTRY_PATH = Path("data/sources/canada-immigration/registry.json")


def _load_registry() -> dict:
    with REGISTRY_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def test_registry_file_exists() -> None:
    assert REGISTRY_PATH.exists()


def test_registry_has_required_sources() -> None:
    payload = _load_registry()
    assert payload.get("jurisdiction") == "ca"

    sources = payload.get("sources", [])
    source_ids = {item.get("source_id") for item in sources}

    required_ids = {
        "IRPA",
        "IRPR",
        "CIT_ACT",
        "CIT_REG",
        "CIT_REG_NO2",
        "IRCC_PDI",
        "EE_MI_CURRENT",
        "EE_MI_INVITES",
        "CANLII_CASE_BROWSE",
        "CANLII_CASE_CITATOR",
    }

    assert required_ids.issubset(source_ids)


def test_registry_source_shape_and_values() -> None:
    payload = _load_registry()
    allowed_types = {"statute", "regulation", "policy", "case_law"}
    allowed_cadence = {"daily", "weekly", "scheduled_incremental"}

    for entry in payload.get("sources", []):
        assert entry.get("source_id")
        assert entry.get("source_type") in allowed_types
        assert entry.get("instrument")
        assert entry.get("url", "").startswith("https://")
        assert entry.get("update_cadence") in allowed_cadence
