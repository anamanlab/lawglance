from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "vercel_env_sync.py"
SPEC = importlib.util.spec_from_file_location("vercel_env_sync", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules["vercel_env_sync"] = MODULE
SPEC.loader.exec_module(MODULE)


def test_parse_env_file_collapses_literal_newline_markers_only(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "EMPTY_MARKER=\\n\n"
        "DOUBLE_EMPTY_MARKER='\\n\\n'\n"
        'TRIPLE_EMPTY_MARKER="\\n\\n\\n"\n',
        encoding="utf-8",
    )

    parsed = MODULE.parse_env_file(env_path)

    assert parsed["EMPTY_MARKER"] == ""
    assert parsed["DOUBLE_EMPTY_MARKER"] == ""
    assert parsed["TRIPLE_EMPTY_MARKER"] == ""


def test_parse_env_file_preserves_structured_values_containing_newline_markers(
    tmp_path: Path,
) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "PRIVATE_KEY=-----BEGIN KEY-----\\nLINE1\\nLINE2\\n-----END KEY-----\\n\n"
        "JSON_PAYLOAD={\"notice\":\"line1\\\\nline2\"}\n"
        "URL_WITH_ESCAPE=https://example.test/path?value=hello\\nworld\n",
        encoding="utf-8",
    )

    parsed = MODULE.parse_env_file(env_path)

    assert (
        parsed["PRIVATE_KEY"]
        == "-----BEGIN KEY-----\\nLINE1\\nLINE2\\n-----END KEY-----\\n"
    )
    assert parsed["JSON_PAYLOAD"] == "{\"notice\":\"line1\\\\nline2\"}"
    assert parsed["URL_WITH_ESCAPE"] == "https://example.test/path?value=hello\\nworld"


def test_parse_env_file_keeps_explicit_empty_string_value(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text('EXPLICIT_EMPTY=""\n', encoding="utf-8")

    parsed = MODULE.parse_env_file(env_path)

    assert parsed["EXPLICIT_EMPTY"] == ""
