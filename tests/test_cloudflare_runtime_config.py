from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "cloudflare_runtime_config.py"
)
SPEC = importlib.util.spec_from_file_location("cloudflare_runtime_config", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules["cloudflare_runtime_config"] = MODULE
SPEC.loader.exec_module(MODULE)


def test_resolve_backend_base_url_from_json_file(tmp_path: Path) -> None:
    wrangler = tmp_path / "wrangler.jsonc"
    wrangler.write_text(
        """
{
  "vars": {
    "IMMCAD_API_BASE_URL": "https://api.immcad.example.ca"
  }
}
""".strip(),
        encoding="utf-8",
    )
    assert MODULE.resolve_backend_base_url(wrangler) == "https://api.immcad.example.ca"


def test_resolve_backend_base_url_from_jsonc_with_comments_and_https_urls(
    tmp_path: Path,
) -> None:
    wrangler = tmp_path / "wrangler.jsonc"
    wrangler.write_text(
        """
{
  // frontend runtime config
  "vars": {
    "IMMCAD_API_BASE_URL": "https://immcad-backend.example.workers.dev", // keep scheme
  },
  /* schema URL should not break parser */
  "$schema": "node_modules/wrangler/config-schema.json",
}
""".strip(),
        encoding="utf-8",
    )
    assert (
        MODULE.resolve_backend_base_url(wrangler)
        == "https://immcad-backend.example.workers.dev"
    )


def test_resolve_backend_base_url_returns_none_for_missing_var(tmp_path: Path) -> None:
    wrangler = tmp_path / "wrangler.jsonc"
    wrangler.write_text('{"vars": {}}', encoding="utf-8")
    assert MODULE.resolve_backend_base_url(wrangler) is None

