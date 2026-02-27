from __future__ import annotations

import json
from pathlib import Path

from immcad_api.sources.required_sources import PRODUCTION_REQUIRED_SOURCE_IDS


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

    assert PRODUCTION_REQUIRED_SOURCE_IDS.issubset(source_ids)


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


def test_registry_uses_canonical_tribunal_and_compliance_urls() -> None:
    payload = _load_registry()
    source_urls = {
        entry["source_id"]: entry["url"]
        for entry in payload.get("sources", [])
        if entry.get("source_id") and entry.get("url")
    }

    expected = {
        "IRB_ID_RULES": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-2002-229/index.html",
        "IRB_IAD_RULES": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-2002-230/index.html",
        "IRB_RPD_RULES": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-2012-256/index.html",
        "IRB_RAD_RULES": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-2012-257/index.html",
        "PIPEDA": "https://laws-lois.justice.gc.ca/eng/acts/P-8.6/index.html",
        "CASL": "https://laws-lois.justice.gc.ca/eng/acts/E-1.6/",
        "FEDERAL_LAWS_BULK_XML": "https://laws-lois.justice.gc.ca/eng/XML/Legis.xml",
        "CANLII_TERMS": "https://www.canlii.org/info/terms.html",
    }

    for source_id, expected_url in expected.items():
        assert source_urls[source_id] == expected_url
