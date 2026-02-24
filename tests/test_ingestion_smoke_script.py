from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


def test_run_ingestion_smoke_script_generates_pass_report(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / "scripts" / "run_ingestion_smoke.py"
    output_path = tmp_path / "ingestion-smoke-report.json"
    state_path = tmp_path / "ingestion-smoke-state.json"

    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--output",
            str(output_path),
            "--state-path",
            str(state_path),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )

    assert result.returncode == 0, result.stderr
    assert output_path.exists()
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert "first_run" in payload
    assert "second_run" in payload
    assert "succeeded" in payload["first_run"]
    assert "failed" in payload["first_run"]
    assert "succeeded" in payload["second_run"]
    assert "failed" in payload["second_run"]
    assert "not_modified" in payload["second_run"]
    assert payload["status"] == "pass"
    assert payload["first_run"]["succeeded"] == 1
    assert payload["first_run"]["failed"] == 0
    assert payload["second_run"]["succeeded"] == 0
    assert payload["second_run"]["not_modified"] == 1
    assert payload["second_run"]["failed"] == 0
