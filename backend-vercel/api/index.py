from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT_DIR.parent

# Canonical runtime source lives under src/immcad_api.
CANONICAL_SRC_DIR = REPO_ROOT / "src"
LEGACY_VERCEL_SRC_DIR = ROOT_DIR / "src"
for candidate in (CANONICAL_SRC_DIR, LEGACY_VERCEL_SRC_DIR):
    candidate_package = candidate / "immcad_api"
    candidate_str = str(candidate)
    if candidate_package.exists() and candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)
        break

from immcad_api.main import app  # noqa: E402

__all__ = ["app"]
