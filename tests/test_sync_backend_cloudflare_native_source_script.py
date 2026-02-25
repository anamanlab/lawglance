from __future__ import annotations

from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parent.parent
    / "scripts"
    / "sync_backend_cloudflare_native_source.sh"
)


def test_sync_backend_cloudflare_native_source_script_exists() -> None:
    assert SCRIPT_PATH.exists()


def test_sync_backend_cloudflare_native_source_script_syncs_expected_paths() -> None:
    script = SCRIPT_PATH.read_text(encoding="utf-8")
    assert "src/immcad_api" in script
    assert "backend-cloudflare/src/immcad_api" in script
    assert "config/source_policy.yaml" in script
    assert "data/sources/canada-immigration/registry.json" in script
    assert "rsync -a --delete" in script
