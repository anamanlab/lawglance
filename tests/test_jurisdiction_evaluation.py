from __future__ import annotations

import json
from pathlib import Path

from immcad_api.evaluation import (
    evaluate_jurisdictional_readiness,
    render_jurisdiction_report_markdown,
    write_jurisdiction_report_artifacts,
)


def test_evaluate_jurisdictional_readiness_passes_threshold() -> None:
    report = evaluate_jurisdictional_readiness(threshold=95)

    assert report.max_score == 100
    assert report.score >= 95
    assert report.status == "pass"
    assert len(report.checks) == 5


def test_jurisdiction_report_artifacts_are_written(tmp_path: Path) -> None:
    report = evaluate_jurisdictional_readiness(threshold=95)
    json_path = tmp_path / "eval-report.json"
    markdown_path = tmp_path / "eval-report.md"

    write_jurisdiction_report_artifacts(
        report,
        json_path=json_path,
        markdown_path=markdown_path,
    )

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["score"] == report.score
    assert payload["status"] == report.status

    markdown = markdown_path.read_text(encoding="utf-8")
    assert "# Jurisdiction Evaluation Report" in markdown
    assert "| Check | Passed | Weight | Details |" in markdown


def test_render_jurisdiction_report_markdown_contains_summary() -> None:
    report = evaluate_jurisdictional_readiness(threshold=95)
    rendered = render_jurisdiction_report_markdown(report)

    assert "Score:" in rendered
    assert "Threshold:" in rendered
    assert "`prompt_scope`" in rendered
