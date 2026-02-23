#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from immcad_api.sources import PRODUCTION_REQUIRED_SOURCE_IDS, SourceRegistry, load_source_registry


def validate_source_registry_requirements(registry: SourceRegistry) -> None:
    errors: list[str] = []

    if registry.jurisdiction.lower() != "ca":
        errors.append(f"Registry jurisdiction must be 'ca' (found '{registry.jurisdiction.lower()}').")

    source_ids = {source.source_id for source in registry.sources}
    missing = sorted(PRODUCTION_REQUIRED_SOURCE_IDS - source_ids)
    if missing:
        errors.append(f"Missing required source IDs: {', '.join(missing)}")

    if errors:
        raise ValueError("; ".join(errors))


def main() -> int:
    try:
        registry = load_source_registry()
        validate_source_registry_requirements(registry)
    except (FileNotFoundError, ValueError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    print(f"[OK] Source registry loaded ({len(registry.sources)} sources)")
    print(f"[OK] Jurisdiction: {registry.jurisdiction.lower()}")
    print(f"[OK] Version: {registry.version}")
    print(f"[OK] Required source IDs present ({len(PRODUCTION_REQUIRED_SOURCE_IDS)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
