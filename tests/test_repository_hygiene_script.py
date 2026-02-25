from __future__ import annotations

from pathlib import Path
import subprocess


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "check_repository_hygiene.sh"


def _run(cmd: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)


def _init_git_repo(path: Path) -> None:
    _run(["git", "init", "-q"], cwd=path)
    _run(["git", "config", "user.name", "Test User"], cwd=path)
    _run(["git", "config", "user.email", "test@example.com"], cwd=path)


def test_repository_hygiene_script_passes_for_clean_repo(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / "README.md").write_text("clean repo\n", encoding="utf-8")
    _run(["git", "add", "README.md"], cwd=tmp_path)
    _run(["git", "commit", "-qm", "init"], cwd=tmp_path)

    result = _run(["bash", str(SCRIPT_PATH)], cwd=tmp_path)

    assert result.returncode == 0
    assert "[OK] Repository hygiene checks passed." in result.stdout


def test_repository_hygiene_script_fails_when_env_file_is_tracked(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / ".env").write_text("OPENAI_API_KEY=test\n", encoding="utf-8")
    _run(["git", "add", ".env"], cwd=tmp_path)
    _run(["git", "commit", "-qm", "track env"], cwd=tmp_path)

    result = _run(["bash", str(SCRIPT_PATH)], cwd=tmp_path)

    assert result.returncode == 1
    assert ".env is tracked in git" in result.stdout


def test_repository_hygiene_script_reports_git_grep_failures(tmp_path: Path) -> None:
    result = _run(["bash", str(SCRIPT_PATH)], cwd=tmp_path)

    assert result.returncode == 2
    assert "git grep failed during secret scan" in result.stdout
