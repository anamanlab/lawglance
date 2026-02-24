from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from immcad_api.policy.source_policy import load_source_policy
from immcad_api.sources import SourceRegistry
from immcad_api.sources.required_sources import PRODUCTION_REQUIRED_SOURCE_IDS

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "validate_source_registry.py"
SPEC = importlib.util.spec_from_file_location("validate_source_registry", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _build_registry(*, source_ids: set[str], jurisdiction: str = "ca") -> SourceRegistry:
    sources = [
        {
            "source_id": source_id,
            "source_type": "policy",
            "instrument": f"Source {source_id}",
            "url": f"https://example.ca/{source_id.lower()}",
            "update_cadence": "weekly",
        }
        for source_id in sorted(source_ids)
    ]
    return SourceRegistry.model_validate(
        {
            "version": "test-v1",
            "jurisdiction": jurisdiction,
            "sources": sources,
        }
    )


def test_validate_source_registry_requirements_passes_with_all_required_ids() -> None:
    registry = _build_registry(source_ids=set(PRODUCTION_REQUIRED_SOURCE_IDS))
    MODULE.validate_source_registry_requirements(registry, load_source_policy())


def test_validate_source_registry_requirements_reports_missing_required_ids() -> None:
    source_ids = set(PRODUCTION_REQUIRED_SOURCE_IDS)
    source_ids.discard("IRB_ID_RULES")
    source_ids.discard("CANLII_TERMS")
    registry = _build_registry(source_ids=source_ids)

    with pytest.raises(ValueError) as exc_info:
        MODULE.validate_source_registry_requirements(registry, load_source_policy())

    message = str(exc_info.value)
    assert "Missing required source IDs:" in message
    assert "CANLII_TERMS" in message
    assert "IRB_ID_RULES" in message


def test_validate_source_registry_requirements_rejects_non_canadian_jurisdiction() -> None:
    registry = _build_registry(
        source_ids=set(PRODUCTION_REQUIRED_SOURCE_IDS),
        jurisdiction="us",
    )

    with pytest.raises(ValueError, match="Registry jurisdiction must be 'ca'"):
        MODULE.validate_source_registry_requirements(registry, load_source_policy())


def test_validate_source_registry_requirements_reports_sources_missing_in_policy() -> None:
    source_ids = set(PRODUCTION_REQUIRED_SOURCE_IDS)
    source_ids.add("UNLISTED_SOURCE")
    registry = _build_registry(source_ids=source_ids)

    with pytest.raises(ValueError) as exc_info:
        MODULE.validate_source_registry_requirements(registry, load_source_policy())

    message = str(exc_info.value)
    assert "Sources missing in source policy:" in message
    assert "UNLISTED_SOURCE" in message
