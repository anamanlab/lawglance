#!/usr/bin/env python3
from __future__ import annotations

from immcad_api.sources import load_source_registry


def main() -> None:
    registry = load_source_registry()
    print(f"[OK] Source registry loaded ({len(registry.sources)} sources)")
    print(f"[OK] Jurisdiction: {registry.jurisdiction.lower()}")
    print(f"[OK] Version: {registry.version}")


if __name__ == "__main__":
    main()
