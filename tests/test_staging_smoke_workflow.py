from __future__ import annotations

from pathlib import Path

WORKFLOW_PATH = Path(".github/workflows/staging-smoke.yml")
SMOKE_SCRIPT_PATH = Path("scripts/run_api_smoke_tests.sh")


def test_staging_smoke_workflow_runs_contract_checks_with_report_artifact() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "Run staging smoke tests" in workflow
    assert 'ENVIRONMENT: staging' in workflow
    assert 'ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS: "true"' in workflow
    assert "STAGING_SMOKE_REPORT_PATH: artifacts/evals/staging-smoke-report.json" in workflow
    assert "Upload staging smoke artifacts" in workflow
    assert "artifacts/evals/staging-smoke-report.json" in workflow


def test_staging_smoke_workflow_has_failure_rollback_guidance() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "Rollback trigger guidance" in workflow
    assert "docs/release/staging-smoke-rollback-criteria.md" in workflow


def test_staging_smoke_script_validates_refusal_citations_and_trace_ids() -> None:
    script = SMOKE_SCRIPT_PATH.read_text(encoding="utf-8")
    assert '/api/chat' in script
    assert '/api/search/cases' in script
    assert "immcad_refusal.json" in script
    assert "fallback_used" in script
    assert "policy_block" in script
    assert "len(chat[\"citations\"]) >= 1" in script
    assert "x-trace-id" in script
    assert "staging-smoke-report.json" in script
