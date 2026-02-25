from __future__ import annotations

import json
from pathlib import Path


ROOT_POLICY = Path("config/source_policy.yaml")
BACKEND_POLICY = Path("backend-vercel/config/source_policy.yaml")
ROOT_REGISTRY = Path("data/sources/canada-immigration/registry.json")
BACKEND_REGISTRY = Path("backend-vercel/data/sources/canada-immigration/registry.json")


def test_backend_vercel_includes_source_policy_file() -> None:
    assert BACKEND_POLICY.exists(), "backend-vercel must include config/source_policy.yaml"
    assert ROOT_POLICY.exists(), "root config/source_policy.yaml is missing"
    assert (
        BACKEND_POLICY.read_text(encoding="utf-8") == ROOT_POLICY.read_text(encoding="utf-8")
    ), "backend-vercel source_policy.yaml must stay in sync with root config/source_policy.yaml"


def test_backend_vercel_includes_source_registry_file() -> None:
    assert (
        BACKEND_REGISTRY.exists()
    ), "backend-vercel must include data/sources/canada-immigration/registry.json"
    assert ROOT_REGISTRY.exists(), "root registry.json is missing"

    backend_payload = json.loads(BACKEND_REGISTRY.read_text(encoding="utf-8"))
    root_payload = json.loads(ROOT_REGISTRY.read_text(encoding="utf-8"))
    assert (
        backend_payload == root_payload
    ), "backend-vercel registry.json must stay in sync with root data registry"
