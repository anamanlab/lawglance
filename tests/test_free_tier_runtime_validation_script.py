from __future__ import annotations

from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "run_free_tier_runtime_validation.sh"
)


def test_free_tier_runtime_validation_script_exists() -> None:
    assert SCRIPT_PATH.exists()


def test_free_tier_runtime_validation_script_checks_expected_paths() -> None:
    script = SCRIPT_PATH.read_text(encoding="utf-8")
    assert "/healthz" in script
    assert "/api/search/cases" in script
    assert "/api/research/lawyer-cases" in script
    assert "run_chat_case_law_tool_smoke.sh" in script
    assert "run_canlii_live_smoke.sh" in script

