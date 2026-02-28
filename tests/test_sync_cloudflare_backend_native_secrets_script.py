from __future__ import annotations

from pathlib import Path


SCRIPT_PATH = Path("scripts/sync_cloudflare_backend_native_secrets.sh")


def test_sync_cloudflare_backend_native_secrets_defaults_include_openai() -> None:
    script = SCRIPT_PATH.read_text(encoding="utf-8")
    assert "Default secret set (when no args are passed):" in script
    assert "OPENAI_API_KEY" in script
    assert '  "OPENAI_API_KEY"' in script
