from __future__ import annotations

import json
from pathlib import Path

import pytest

import immcad_api.sources.source_registry as source_registry_module
from immcad_api.sources import SourceRegistry, load_source_registry


def test_load_source_registry_default_file() -> None:
    registry = load_source_registry()
    assert isinstance(registry, SourceRegistry)
    assert registry.jurisdiction.lower() == "ca"
    assert registry.get_source("IRPA") is not None


def test_load_source_registry_rejects_duplicate_source_ids(tmp_path: Path) -> None:
    payload = {
        "version": "2026-02-23",
        "jurisdiction": "ca",
        "sources": [
            {
                "source_id": "IRPA",
                "source_type": "statute",
                "instrument": "Immigration and Refugee Protection Act",
                "url": "https://laws-lois.justice.gc.ca/eng/acts/I-2.5/FullText.html",
                "update_cadence": "weekly",
            },
            {
                "source_id": "IRPA",
                "source_type": "policy",
                "instrument": "Duplicate source id",
                "url": "https://www.canada.ca/",
                "update_cadence": "daily",
            },
        ],
    }
    path = tmp_path / "registry.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="Duplicate source_id"):
        load_source_registry(path)


def test_load_source_registry_rejects_invalid_source_type(tmp_path: Path) -> None:
    payload = {
        "version": "2026-02-23",
        "jurisdiction": "ca",
        "sources": [
            {
                "source_id": "BAD_TYPE",
                "source_type": "unknown_type",
                "instrument": "Invalid source type",
                "url": "https://www.canada.ca/",
                "update_cadence": "daily",
            }
        ],
    }
    path = tmp_path / "registry.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError):
        load_source_registry(path)


def test_load_source_registry_uses_embedded_payload_when_files_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    missing_path = tmp_path / "missing-registry.json"
    monkeypatch.setattr(
        source_registry_module,
        "DEFAULT_REGISTRY_RELATIVE_PATH",
        missing_path,
    )
    monkeypatch.setattr(
        source_registry_module,
        "DEFAULT_REGISTRY_PACKAGE_PATH",
        missing_path,
    )
    monkeypatch.setattr(
        source_registry_module,
        "DEFAULT_REGISTRY_REPO_PATH",
        missing_path,
    )

    registry = source_registry_module.load_source_registry()
    assert isinstance(registry, SourceRegistry)
    assert registry.get_source("IRPA") is not None
