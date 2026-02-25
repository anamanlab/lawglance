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


def test_repository_hygiene_script_fails_when_env_variant_file_is_tracked(
    tmp_path: Path,
) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / "backend-vercel").mkdir()
    (tmp_path / "backend-vercel" / ".env.preview").write_text(
        "SAFE_VALUE=1\n",
        encoding="utf-8",
    )
    _run(["git", "add", "backend-vercel/.env.preview"], cwd=tmp_path)
    _run(["git", "commit", "-qm", "track env variant"], cwd=tmp_path)

    result = _run(["bash", str(SCRIPT_PATH)], cwd=tmp_path)

    assert result.returncode == 1
    assert "tracked plaintext .env" in result.stdout
    assert "backend-vercel/.env.preview" in result.stdout


def test_repository_hygiene_script_fails_when_gitsecret_random_seed_is_tracked(
    tmp_path: Path,
) -> None:
    _init_git_repo(tmp_path)
    random_seed = tmp_path / ".gitsecret" / "keys" / "random_seed"
    random_seed.parent.mkdir(parents=True)
    random_seed.write_text("seed\n", encoding="utf-8")
    _run(["git", "add", ".gitsecret/keys/random_seed"], cwd=tmp_path)
    _run(["git", "commit", "-qm", "track random seed"], cwd=tmp_path)

    result = _run(["bash", str(SCRIPT_PATH)], cwd=tmp_path)

    assert result.returncode == 1
    assert ".gitsecret/keys/random_seed is tracked" in result.stdout


def test_repository_hygiene_script_ignores_encrypted_secret_artifacts_in_regex_scan(
    tmp_path: Path,
) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / "backend-vercel").mkdir()
    # Simulate encrypted artifact content that happens to match the plaintext secret regex.
    simulated_secret = "sk-proj-" + ("a" * 36)
    (tmp_path / "backend-vercel" / ".env.preview.secret").write_text(
        f"{simulated_secret}\n",
        encoding="utf-8",
    )
    _run(["git", "add", "backend-vercel/.env.preview.secret"], cwd=tmp_path)
    _run(["git", "commit", "-qm", "track encrypted artifact"], cwd=tmp_path)

    result = _run(["bash", str(SCRIPT_PATH)], cwd=tmp_path)

    assert result.returncode == 0
    assert "[OK] Repository hygiene checks passed." in result.stdout


def test_repository_hygiene_script_fails_when_backend_prebuilt_manifest_references_env_files(
    tmp_path: Path,
) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / "README.md").write_text("clean repo\n", encoding="utf-8")
    _run(["git", "add", "README.md"], cwd=tmp_path)
    _run(["git", "commit", "-qm", "init"], cwd=tmp_path)

    prebuilt_config = (
        tmp_path / "backend-vercel" / ".vercel" / "output" / "functions" / "index.func"
    )
    prebuilt_config.mkdir(parents=True)
    (prebuilt_config / ".vc-config.json").write_text(
        (
            '{\n'
            '  "filePathMap": {\n'
            '    ".env.example": ".env.example",\n'
            '    ".env.production.vercel": ".env.production.vercel"\n'
            "  }\n"
            "}\n"
        ),
        encoding="utf-8",
    )

    result = _run(["bash", str(SCRIPT_PATH)], cwd=tmp_path)

    assert result.returncode == 1
    assert "prebuilt artifact references local .env" in result.stdout
    assert ".env.production.vercel" in result.stdout


def test_repository_hygiene_script_allows_prebuilt_manifest_env_example_only(
    tmp_path: Path,
) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / "README.md").write_text("clean repo\n", encoding="utf-8")
    _run(["git", "add", "README.md"], cwd=tmp_path)
    _run(["git", "commit", "-qm", "init"], cwd=tmp_path)

    prebuilt_config = (
        tmp_path / "backend-vercel" / ".vercel" / "output" / "functions" / "index.func"
    )
    prebuilt_config.mkdir(parents=True)
    (prebuilt_config / ".vc-config.json").write_text(
        '{\n  "filePathMap": {\n    ".env.example": ".env.example"\n  }\n}\n',
        encoding="utf-8",
    )

    result = _run(["bash", str(SCRIPT_PATH)], cwd=tmp_path)

    assert result.returncode == 0
    assert "[OK] Repository hygiene checks passed." in result.stdout


def test_repository_hygiene_script_reports_git_grep_failures(tmp_path: Path) -> None:
    result = _run(["bash", str(SCRIPT_PATH)], cwd=tmp_path)

    assert result.returncode == 2
    assert "git grep failed during secret scan" in result.stdout
