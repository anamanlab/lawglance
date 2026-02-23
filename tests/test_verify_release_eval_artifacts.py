from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "verify_release_eval_artifacts.py"
)
SPEC = importlib.util.spec_from_file_location("verify_release_eval_artifacts", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_validate_artifacts_reports_missing_and_empty_files(tmp_path: Path) -> None:
    empty_artifact = tmp_path / "artifacts" / "evals" / "empty.md"
    empty_artifact.parent.mkdir(parents=True)
    empty_artifact.write_text("   \n", encoding="utf-8")

    populated_artifact = tmp_path / "artifacts" / "evals" / "report.json"
    populated_artifact.write_text('{"status":"pass"}\n', encoding="utf-8")

    missing_artifact = tmp_path / "artifacts" / "evals" / "missing.md"
    failures = MODULE.validate_artifacts(
        (empty_artifact, populated_artifact, missing_artifact)
    )

    assert len(failures) == 2
    assert any("empty artifact:" in failure for failure in failures)
    assert any("missing artifact:" in failure for failure in failures)


def test_main_returns_nonzero_when_any_artifact_is_missing(
    tmp_path: Path, capsys
) -> None:
    present_artifact = tmp_path / "artifacts" / "evals" / "jurisdiction-eval-report.json"
    present_artifact.parent.mkdir(parents=True)
    present_artifact.write_text('{"status":"pass"}\n', encoding="utf-8")

    missing_artifact = tmp_path / "artifacts" / "evals" / "jurisdiction-eval-report.md"
    exit_code = MODULE.main(
        [
            "--artifact",
            str(present_artifact),
            "--artifact",
            str(missing_artifact),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "[FAIL] Release artifact verification failed." in captured.out
    assert "missing artifact:" in captured.out


def test_main_returns_zero_for_non_empty_artifacts(tmp_path: Path, capsys) -> None:
    artifact_paths = [
        tmp_path / "artifacts" / "evals" / "jurisdiction-eval-report.json",
        tmp_path / "artifacts" / "evals" / "jurisdiction-eval-report.md",
    ]
    artifact_paths[0].parent.mkdir(parents=True)
    artifact_paths[0].write_text('{"status":"pass"}\n', encoding="utf-8")
    artifact_paths[1].write_text("# Jurisdiction Eval\n\npass\n", encoding="utf-8")

    exit_code = MODULE.main(
        [
            "--artifact",
            str(artifact_paths[0]),
            "--artifact",
            str(artifact_paths[1]),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "[OK] Release artifact verification passed" in captured.out
