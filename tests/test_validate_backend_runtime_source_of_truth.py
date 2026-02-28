from __future__ import annotations

import pytest

from scripts.validate_backend_runtime_source_of_truth import (
    _read_changed_paths,
    find_blocked_paths,
    normalize_repo_path,
    validate_runtime_source_of_truth,
)


def test_normalize_repo_path_handles_windows_and_relative_notation() -> None:
    assert (
        normalize_repo_path(r".\backend-vercel\src\immcad_api\api\routes\chat.py")
        == "backend-vercel/src/immcad_api/api/routes/chat.py"
    )


def test_find_blocked_paths_only_blocks_protected_runtime_paths() -> None:
    blocked = find_blocked_paths(
        changed_paths=(
            "src/immcad_api/api/routes/chat.py",
            "backend-vercel/src/immcad_api/api/routes/chat.py",
            "backend-vercel/src/immcad_api/README.md",
        ),
        protected_root="backend-vercel/src/immcad_api",
        allow_paths=("backend-vercel/src/immcad_api/README.md",),
    )

    assert blocked == ("backend-vercel/src/immcad_api/api/routes/chat.py",)


def test_validate_runtime_source_of_truth_surfaces_blocked_paths(
    monkeypatch,
) -> None:
    def _fake_read_changed_paths(
        base_ref: str | None, head_ref: str | None
    ) -> tuple[tuple[str, ...], str]:
        assert base_ref == "base-sha"
        assert head_ref == "head-sha"
        return (
            (
                "backend-vercel/src/immcad_api/services/chat_service.py",
                "src/immcad_api/services/chat_service.py",
            ),
            "git diff base-sha...head-sha",
        )

    monkeypatch.setattr(
        "scripts.validate_backend_runtime_source_of_truth._read_changed_paths",
        _fake_read_changed_paths,
    )

    result = validate_runtime_source_of_truth(
        base_ref="base-sha",
        head_ref="head-sha",
    )

    assert result.is_valid is False
    assert result.blocked_paths == (
        "backend-vercel/src/immcad_api/services/chat_service.py",
    )


def test_read_changed_paths_fails_closed_for_unresolvable_explicit_refs(
    monkeypatch,
) -> None:
    def _fake_paths_from_command(args: list[str]) -> tuple[str, ...]:
        if args[:3] == ["diff", "--name-only", "--diff-filter=ACDMRTUXB"]:
            raise RuntimeError("missing explicit refs in checkout")
        raise AssertionError(f"unexpected command: {args}")

    monkeypatch.setattr(
        "scripts.validate_backend_runtime_source_of_truth._paths_from_command",
        _fake_paths_from_command,
    )

    with pytest.raises(RuntimeError, match="explicit diff refs could not be resolved"):
        _read_changed_paths("origin/main", "HEAD")


def test_read_changed_paths_prefers_current_worktree_without_refs(
    monkeypatch,
) -> None:
    calls: list[list[str]] = []

    def _fake_paths_from_command(args: list[str]) -> tuple[str, ...]:
        calls.append(args)
        if args == ["diff", "--name-only", "--cached"]:
            return ("backend-vercel/src/immcad_api/services/chat_service.py",)
        if args == ["diff", "--name-only"]:
            return ("backend-vercel/src/immcad_api/api/routes/chat.py",)
        raise AssertionError(f"unexpected command: {args}")

    def _fake_run_git(args: list[str]) -> str:
        raise AssertionError(f"should not resolve commit history: {args}")

    monkeypatch.setattr(
        "scripts.validate_backend_runtime_source_of_truth._paths_from_command",
        _fake_paths_from_command,
    )
    monkeypatch.setattr(
        "scripts.validate_backend_runtime_source_of_truth._run_git",
        _fake_run_git,
    )

    changed_paths, source = _read_changed_paths(None, None)

    assert source == "git diff (staged + unstaged)"
    assert changed_paths == (
        "backend-vercel/src/immcad_api/api/routes/chat.py",
        "backend-vercel/src/immcad_api/services/chat_service.py",
    )
    assert calls == [
        ["diff", "--name-only", "--cached"],
        ["diff", "--name-only"],
    ]
