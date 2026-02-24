#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from immcad_api.ingestion import build_ingestion_plan  # noqa: E402


def main() -> None:
    plan = build_ingestion_plan()
    payload = {
        "jurisdiction": plan.jurisdiction,
        "version": plan.version,
        "cadence_to_sources": plan.cadence_to_sources,
    }
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
