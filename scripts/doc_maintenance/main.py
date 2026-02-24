from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from audit import AuditIssue, FileAudit, analyze_markdown_file, discover_markdown_files
from optimizer import inject_toc
from styler import validate_style
from validator import check_images, extract_links, validate_external_links, validate_relative_link

SEVERITY_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1}
LOGGER = logging.getLogger(__name__)


def _load_config(config_path: Path) -> dict[str, Any]:
    with config_path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}
    return config


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _counts_by_severity(issues: list[AuditIssue]) -> dict[str, int]:
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "unknown": 0}
    for issue in issues:
        severity = issue.severity.lower()
        if severity in counts:
            counts[severity] += 1
        else:
            counts["unknown"] += 1
            LOGGER.warning("Unexpected audit severity '%s' in category '%s'", issue.severity, issue.category)
    return counts


def _sort_issues(issues: list[AuditIssue]) -> list[AuditIssue]:
    return sorted(issues, key=lambda i: SEVERITY_ORDER.get(i.severity, 0), reverse=True)


def _should_fail(audits: list[FileAudit], fail_on: str) -> bool:
    threshold = SEVERITY_ORDER.get(fail_on, 99)
    if threshold == 99:
        return False
    for audit in audits:
        for issue in audit.issues:
            if SEVERITY_ORDER.get(issue.severity, 0) >= threshold:
                return True
    return False


def _render_markdown_report(
    *,
    audits: list[FileAudit],
    report_generated_at: str,
    fix_applied: bool,
    external_link_validation: bool,
) -> str:
    all_issues = [issue for audit in audits for issue in audit.issues]
    counts = _counts_by_severity(all_issues)
    files_with_issues = sum(1 for audit in audits if audit.issues)
    health_score = int((1 - (files_with_issues / len(audits))) * 100) if audits else 100

    lines: list[str] = [
        "# Documentation Maintenance Report",
        "",
        f"- Generated at (UTC): `{report_generated_at}`",
        f"- Total files audited: `{len(audits)}`",
        f"- Files with issues: `{files_with_issues}`",
        f"- Health score: `{health_score}%`",
        f"- External link validation: `{'enabled' if external_link_validation else 'disabled'}`",
        f"- Auto-fix mode: `{'enabled' if fix_applied else 'disabled'}`",
        "",
        "## Severity Summary",
        "",
        f"- Critical: `{counts.get('critical', 0)}`",
        f"- High: `{counts.get('high', 0)}`",
        f"- Medium: `{counts.get('medium', 0)}`",
        f"- Low: `{counts.get('low', 0)}`",
        f"- Unknown: `{counts.get('unknown', 0)}`",
        "",
        "## File Findings",
        "",
    ]

    for audit in audits:
        status = "✅" if not audit.issues else "❌"
        lines.append(f"### {status} `{audit.path}`")
        lines.append(f"- Word count: `{audit.word_count}`")
        lines.append(f"- Last commit: `{audit.last_commit_iso or 'unknown'}`")
        lines.append(f"- Age days: `{audit.age_days if audit.age_days is not None else 'unknown'}`")
        if audit.todos:
            lines.append(f"- TODO/FIXME markers: `{len(audit.todos)}`")
        if audit.issues:
            lines.append("- Issues:")
            for issue in _sort_issues(audit.issues):
                hint_suffix = f" | Hint: {issue.hint}" if issue.hint else ""
                lines.append(
                    f"  - [{issue.severity.upper()}][{issue.category}] {issue.message}{hint_suffix}"
                )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _serialize_audits(audits: list[FileAudit]) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for audit in audits:
        serialized = asdict(audit)
        serialized["issues"] = [asdict(issue) for issue in audit.issues]
        payload.append(serialized)
    return payload


def run_main(
    *,
    config_path: Path,
    dry_run: bool = False,
    fix: bool = False,
    check_external: bool = False,
    fail_on: str | None = None,
) -> int:
    config = _load_config(config_path)
    root_dir = Path(config.get("root_dir", ".")).resolve()
    report_paths = config.get("reports", {})
    report_md_path = Path(report_paths.get("markdown", "artifacts/docs/doc-maintenance-report.md"))
    report_json_path = Path(report_paths.get("json", "artifacts/docs/doc-maintenance-report.json"))

    files = discover_markdown_files(root_dir, config)
    audits: list[FileAudit] = []
    external_urls: set[str] = set()

    toc_cfg = config.get("toc", {})
    toc_enabled = bool(toc_cfg.get("enabled", True))
    toc_min_headings = int(toc_cfg.get("min_headings", 4))

    for doc_path in files:
        audit = analyze_markdown_file(doc_path, root_dir, config)
        try:
            content = doc_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError, OSError) as exc:
            LOGGER.warning("Skipping unreadable file %s: %s", doc_path, exc)
            audits.append(audit)
            continue

        markdown_links, urls = extract_links(content)
        external_urls.update(urls)
        for _, target in markdown_links:
            link_issue = validate_relative_link(doc_path, target, root_dir)
            if link_issue:
                audit.issues.append(link_issue)

        audit.issues.extend(check_images(content, doc_path))
        audit.issues.extend(validate_style(content, config))

        if fix and not dry_run and toc_enabled:
            toc_result = inject_toc(content, min_headings=toc_min_headings)
            if toc_result.changed:
                doc_path.write_text(toc_result.updated_content, encoding="utf-8")

        audits.append(audit)

    if check_external:
        external_issues = validate_external_links(sorted(external_urls), config)
        if external_issues:
            global_audit = next((audit for audit in audits if audit.path == "<global>"), None)
            if global_audit is None:
                global_audit = FileAudit(
                    path="<global>",
                    word_count=0,
                    last_commit_iso=None,
                    age_days=None,
                    issues=[],
                    todos=[],
                )
                audits.append(global_audit)
            global_audit.issues.extend(external_issues)

    now_utc = datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    _ensure_parent(report_md_path)
    _ensure_parent(report_json_path)

    report_md = _render_markdown_report(
        audits=audits,
        report_generated_at=now_utc,
        fix_applied=(fix and not dry_run),
        external_link_validation=check_external,
    )
    report_md_path.write_text(report_md, encoding="utf-8")

    report_json = {
        "generated_at_utc": now_utc,
        "audited_files": len(audits),
        "external_link_validation": check_external,
        "fix_mode": bool(fix and not dry_run),
        "audits": _serialize_audits(audits),
    }
    report_json_path.write_text(json.dumps(report_json, indent=2) + "\n", encoding="utf-8")

    effective_fail_on = (fail_on or config.get("gates", {}).get("fail_on", "high")).lower()
    should_fail = _should_fail(audits, effective_fail_on) if effective_fail_on != "none" else False

    print(f"[docs-maintenance] audited files: {len(audits)}")
    print(f"[docs-maintenance] markdown report: {report_md_path}")
    print(f"[docs-maintenance] json report: {report_json_path}")
    if should_fail:
        print(
            f"[docs-maintenance] failing audit: found issues at or above '{effective_fail_on}' severity."
        )
        return 2
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Documentation maintenance and quality assurance runner")
    parser.add_argument(
        "--config",
        default="scripts/doc_maintenance/config.yaml",
        help="Path to docs maintenance config file",
    )
    parser.add_argument("--dry-run", action="store_true", help="Analyze only; do not modify files")
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Apply safe fixes (currently TOC generation/refresh based on config)",
    )
    parser.add_argument(
        "--check-external",
        action="store_true",
        help="Validate external links with retry logic (network-dependent)",
    )
    parser.add_argument(
        "--fail-on",
        choices=["none", "critical", "high", "medium", "low"],
        default=None,
        help="Override severity threshold that fails the command",
    )
    return parser


if __name__ == "__main__":
    cli_args = _build_parser().parse_args()
    raise SystemExit(
        run_main(
            config_path=Path(cli_args.config),
            dry_run=cli_args.dry_run,
            fix=cli_args.fix,
            check_external=cli_args.check_external,
            fail_on=cli_args.fail_on,
        )
    )
