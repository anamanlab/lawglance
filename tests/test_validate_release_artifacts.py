from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "validate_release_artifacts.py"
SPEC = importlib.util.spec_from_file_location("validate_release_artifacts", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _create_required_artifacts(tmp_path: Path) -> None:
    eval_dir = tmp_path / "artifacts" / "evals"
    eval_dir.mkdir(parents=True, exist_ok=True)
    (eval_dir / "jurisdiction-eval-report.json").write_text(
        '{"jurisdiction":"ca","status":"pass"}',
        encoding="utf-8",
    )
    (eval_dir / "jurisdiction-eval-report.md").write_text(
        "# Eval\n\nStatus: pass",
        encoding="utf-8",
    )
    (eval_dir / "jurisdictional-suite-report.json").write_text(
        '{"status":"pass","total_cases":18}',
        encoding="utf-8",
    )
    (eval_dir / "jurisdictional-suite-report.md").write_text(
        "# Suite\n\nStatus: pass",
        encoding="utf-8",
    )
    (eval_dir / "frontend-test-summary.xml").write_text(
        "<testsuite name=\"frontend-contract\"><testcase name=\"chat-contract\"/></testsuite>",
        encoding="utf-8",
    )


def test_validate_release_artifacts_passes_with_required_files(tmp_path: Path) -> None:
    _create_required_artifacts(tmp_path)
    MODULE.validate_release_artifacts(base_dir=tmp_path)


def test_validate_release_artifacts_reports_missing_and_empty_files(tmp_path: Path) -> None:
    _create_required_artifacts(tmp_path)
    (tmp_path / "artifacts" / "evals" / "jurisdictional-suite-report.md").write_text(
        "   ",
        encoding="utf-8",
    )
    (tmp_path / "artifacts" / "evals" / "jurisdiction-eval-report.md").unlink()

    with pytest.raises(ValueError) as exc_info:
        MODULE.validate_release_artifacts(base_dir=tmp_path)

    message = str(exc_info.value)
    assert "Missing required artifact(s): artifacts/evals/jurisdiction-eval-report.md" in message
    assert "Empty artifact(s): artifacts/evals/jurisdictional-suite-report.md" in message


def test_validate_release_artifacts_reports_invalid_json(tmp_path: Path) -> None:
    _create_required_artifacts(tmp_path)
    (tmp_path / "artifacts" / "evals" / "jurisdictional-suite-report.json").write_text(
        "{not-valid-json}",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Invalid JSON artifact\\(s\\)"):
        MODULE.validate_release_artifacts(base_dir=tmp_path)
