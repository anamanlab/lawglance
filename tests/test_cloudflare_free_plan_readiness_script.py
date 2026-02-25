from __future__ import annotations

from pathlib import Path
import os
import subprocess


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "check_cloudflare_free_plan_readiness.sh"
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


def _prepare_workspace(tmp_path: Path) -> None:
    frontend = tmp_path / "frontend-web"
    backend = tmp_path / "backend-cloudflare"
    frontend.mkdir()
    backend.mkdir()
    (frontend / "wrangler.jsonc").write_text("{}", encoding="utf-8")
    (backend / "wrangler.backend-proxy.jsonc").write_text("{}", encoding="utf-8")
    (backend / "wrangler.toml").write_text("", encoding="utf-8")


def _write_fake_npx(
    fake_bin: Path,
    *,
    frontend_gzip_kib: str = "500",
    proxy_gzip_kib: str = "1",
    native_gzip_kib: str = "6000",
    fail_native: bool = False,
) -> None:
    fake_npx = fake_bin / "npx"
    script = f"""#!/usr/bin/env bash
set -euo pipefail
args="$*"
if [[ "$args" == *"--version"* ]]; then
  echo "wrangler 4.68.1"
  exit 0
fi
if [[ "$args" == *"wrangler.jsonc"* ]]; then
  echo "Total Upload: 2000.00 KiB / gzip: {frontend_gzip_kib} KiB"
  exit 0
fi
if [[ "$args" == *"wrangler.backend-proxy.jsonc"* ]]; then
  echo "Total Upload: 10.00 KiB / gzip: {proxy_gzip_kib} KiB"
  exit 0
fi
if [[ "$args" == *"wrangler.toml"* ]]; then
  if [[ "{str(fail_native).lower()}" == "true" ]]; then
    echo "native dry-run failed" >&2
    exit 1
  fi
  echo "Total Upload: 27000.00 KiB / gzip: {native_gzip_kib} KiB"
  exit 0
fi
echo "Unexpected npx args: $args" >&2
exit 1
"""
    fake_npx.write_text(script, encoding="utf-8")
    fake_npx.chmod(0o755)


def test_cloudflare_free_plan_readiness_proxy_mode_warns_on_native_size(
    tmp_path: Path,
) -> None:
    _prepare_workspace(tmp_path)
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    _write_fake_npx(fake_bin, native_gzip_kib="6000")

    result = _run(
        ["bash", str(SCRIPT_PATH)],
        cwd=tmp_path,
        env={"PATH": f"{fake_bin}:{os.environ['PATH']}"},
    )

    assert result.returncode == 0
    assert "Native backend is blocked on free plan" in result.stdout
    assert "Cloudflare free-plan readiness checks passed" in result.stdout


def test_cloudflare_free_plan_readiness_native_mode_fails_when_native_too_large(
    tmp_path: Path,
) -> None:
    _prepare_workspace(tmp_path)
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    _write_fake_npx(fake_bin, native_gzip_kib="6000")

    result = _run(
        ["bash", str(SCRIPT_PATH)],
        cwd=tmp_path,
        env={
            "PATH": f"{fake_bin}:{os.environ['PATH']}",
            "CLOUDFLARE_BACKEND_MODE": "native",
        },
    )

    assert result.returncode == 1
    assert "Native backend bundle exceeds free-plan gzip size limit" in result.stdout


def test_cloudflare_free_plan_readiness_fails_when_proxy_too_large(
    tmp_path: Path,
) -> None:
    _prepare_workspace(tmp_path)
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    _write_fake_npx(fake_bin, proxy_gzip_kib="4000")

    result = _run(
        ["bash", str(SCRIPT_PATH)],
        cwd=tmp_path,
        env={"PATH": f"{fake_bin}:{os.environ['PATH']}"},
    )

    assert result.returncode == 1
    assert "Backend proxy bundle exceeds free-plan gzip size limit" in result.stdout
