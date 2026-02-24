#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from immcad_api.policy.source_policy import SourcePolicy, load_source_policy  # noqa: E402
from immcad_api.sources import (  # noqa: E402
    PRODUCTION_REQUIRED_SOURCE_IDS,
    SourceRegistry,
    load_source_registry,
)


def validate_source_registry_requirements(
    registry: SourceRegistry,
    source_policy: SourcePolicy,
) -> None:
    errors: list[str] = []

    if registry.jurisdiction.lower() != "ca":
        errors.append(f"Registry jurisdiction must be 'ca' (found '{registry.jurisdiction.lower()}').")

    source_ids = {source.source_id for source in registry.sources}
    missing = sorted(PRODUCTION_REQUIRED_SOURCE_IDS - source_ids)
    if missing:
        errors.append(f"Missing required source IDs: {', '.join(missing)}")

    policy_source_ids = {source.source_id for source in source_policy.sources}
    missing_in_policy = sorted(source_id for source_id in source_ids if source_id not in policy_source_ids)
    if missing_in_policy:
        errors.append(f"Sources missing in source policy: {', '.join(missing_in_policy)}")

    if errors:
        raise ValueError("; ".join(errors))


def main() -> int:
    try:
        registry = load_source_registry()
        source_policy = load_source_policy()
        validate_source_registry_requirements(registry, source_policy)
    except (FileNotFoundError, ValueError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    print(f"[OK] Source registry loaded ({len(registry.sources)} sources)")
    print(f"[OK] Jurisdiction: {registry.jurisdiction.lower()}")
    print(f"[OK] Version: {registry.version}")
    print(f"[OK] Required source IDs present ({len(PRODUCTION_REQUIRED_SOURCE_IDS)})")
    print(f"[OK] Source policy coverage validated ({len(source_policy.sources)} policy entries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
