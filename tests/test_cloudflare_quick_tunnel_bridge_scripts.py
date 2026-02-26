from __future__ import annotations

from pathlib import Path
import os
import subprocess

import pytest


RUN_SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "run_cloudflare_quick_tunnel_bridge.sh"
)
STOP_SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "stop_cloudflare_quick_tunnel_bridge.sh"
)


def _run(
    cmd: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        env=merged_env,
    )


@pytest.mark.parametrize(
    "option_name",
    ["--env-file", "--host", "--port", "--state-dir", "--cloudflared-bin"],
)
def test_run_bridge_script_requires_option_values(
    option_name: str,
    tmp_path: Path,
) -> None:
    result = _run(["bash", str(RUN_SCRIPT_PATH), option_name], cwd=tmp_path)

    assert result.returncode == 1
    assert f"ERROR: {option_name} requires a value." in result.stderr


def test_run_bridge_script_has_port_probe_fallback_for_minimal_hosts() -> None:
    script = RUN_SCRIPT_PATH.read_text(encoding="utf-8")

    assert "port_is_listening()" in script
    assert "command -v ss" in script
    assert "command -v lsof" in script
    assert "neither ss nor lsof is available" in script


def test_stop_bridge_script_does_not_execute_state_env_file(tmp_path: Path) -> None:
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    (state_dir / "state.env").write_text("this_is_not_a_command\n", encoding="utf-8")

    result = _run(["bash", str(STOP_SCRIPT_PATH), str(state_dir)], cwd=tmp_path)

    assert result.returncode == 0
    assert "[done] Bridge processes stopped" in result.stdout
