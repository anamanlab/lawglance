from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path

from immcad_api.policy.compliance import should_refuse_for_policy
from immcad_api.policy.prompts import QA_PROMPT, SYSTEM_PROMPT
from immcad_api.sources import PRODUCTION_REQUIRED_SOURCE_IDS, load_source_registry

_DISALLOWED_INDIA_TERMS = (
    "indian constitution",
    "bharatiya",
    "bnss",
    "bns",
    "bsa",
    "india",
)

# FCA decisions are also served under the Federal Court host/path namespace.
_ALLOWED_URL_MARKERS = (
    "canada.ca",
    "justice.gc.ca",
    "canlii.org",
    "github.com/canlii",
    "decisions.scc-csc.ca",
    "decisions.fct-cf.gc.ca",
)


@dataclass(frozen=True)
class JurisdictionCheck:
    check_id: str
    name: str
    weight: int
    passed: bool
    details: str


@dataclass(frozen=True)
class JurisdictionEvaluationReport:
    generated_at: str
    threshold: int
    score: int
    max_score: int
    pass_rate_percent: float
    status: str
    checks: list[JurisdictionCheck]

    def to_dict(self) -> dict:
        return asdict(self)


def _utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _load_prompts() -> tuple[str, str]:
    return SYSTEM_PROMPT, QA_PROMPT


def _check_prompt_scope(system_prompt: str) -> JurisdictionCheck:
    required = ["canadian immigration", "citizenship", "canada"]
    lowered = system_prompt.lower()
    missing = [item for item in required if item not in lowered]
    if missing:
        return JurisdictionCheck(
            check_id="prompt_scope",
            name="System prompt is Canada-scoped",
            weight=20,
            passed=False,
            details=f"Missing scope terms: {', '.join(missing)}",
        )
    return JurisdictionCheck(
        check_id="prompt_scope",
        name="System prompt is Canada-scoped",
        weight=20,
        passed=True,
        details="Required Canada scope terms are present.",
    )


def _check_prompt_india_artifacts(system_prompt: str, qa_prompt: str) -> JurisdictionCheck:
    lowered = f"{system_prompt}\n{qa_prompt}".lower()
    found = [term for term in _DISALLOWED_INDIA_TERMS if term in lowered]
    if found:
        return JurisdictionCheck(
            check_id="prompt_no_india_artifacts",
            name="Prompts avoid India-domain artifacts",
            weight=20,
            passed=False,
            details=f"Found disallowed terms: {', '.join(found)}",
        )
    return JurisdictionCheck(
        check_id="prompt_no_india_artifacts",
        name="Prompts avoid India-domain artifacts",
        weight=20,
        passed=True,
        details="No disallowed India terms were detected in prompts.",
    )


def _check_policy_refusal_gate() -> JurisdictionCheck:
    blocked_examples = [
        "Can you represent me before the IRB?",
        "Please file my application and act as my lawyer",
        "Can you guarantee visa approval?",
        "Give me a personalized strategy for my case.",
        "Please submit forms on my behalf.",
    ]
    allowed_examples = [
        "Summarize IRPA inadmissibility grounds in plain language.",
        "What are common strategies people use for Express Entry?",
    ]

    blocked_ok = all(should_refuse_for_policy(item) for item in blocked_examples)
    allowed_ok = all(not should_refuse_for_policy(item) for item in allowed_examples)
    passed = blocked_ok and allowed_ok

    details = (
        "Policy refusal triggers for representation/legal-advice phrases and stays open for neutral"
        " informational queries."
        if passed
        else "Policy refusal checks failed for blocked or allowed sample prompts."
    )

    return JurisdictionCheck(
        check_id="policy_refusal_gate",
        name="Policy refusal gate behavior",
        weight=20,
        passed=passed,
        details=details,
    )


def _check_registry_required_sources() -> JurisdictionCheck:
    registry = load_source_registry()
    source_ids = {source.source_id for source in registry.sources}
    missing = sorted(PRODUCTION_REQUIRED_SOURCE_IDS - source_ids)
    if registry.jurisdiction.lower() != "ca" or missing:
        details = [f"jurisdiction={registry.jurisdiction.lower()}"]
        if missing:
            details.append(f"missing sources={', '.join(missing)}")
        return JurisdictionCheck(
            check_id="registry_required_sources",
            name="Source registry has required Canada corpus",
            weight=20,
            passed=False,
            details="; ".join(details),
        )
    return JurisdictionCheck(
        check_id="registry_required_sources",
        name="Source registry has required Canada corpus",
        weight=20,
        passed=True,
        details="Jurisdiction is ca and required source IDs are present.",
    )


def _check_registry_source_domains() -> JurisdictionCheck:
    registry = load_source_registry()
    invalid: list[str] = []
    for source in registry.sources:
        url = str(source.url).lower()
        if not url.startswith("https://"):
            invalid.append(f"{source.source_id} (non-https)")
            continue
        if not any(marker in url for marker in _ALLOWED_URL_MARKERS):
            invalid.append(f"{source.source_id} ({url})")

    if invalid:
        return JurisdictionCheck(
            check_id="registry_source_domains",
            name="Source registry URLs are trusted Canada/legal domains",
            weight=20,
            passed=False,
            details=f"Unapproved source domains: {', '.join(invalid)}",
        )

    return JurisdictionCheck(
        check_id="registry_source_domains",
        name="Source registry URLs are trusted Canada/legal domains",
        weight=20,
        passed=True,
        details="All source URLs are HTTPS and map to approved legal/government domains.",
    )


def evaluate_jurisdictional_readiness(*, threshold: int = 95) -> JurisdictionEvaluationReport:
    system_prompt, qa_prompt = _load_prompts()

    checks = [
        _check_prompt_scope(system_prompt),
        _check_prompt_india_artifacts(system_prompt, qa_prompt),
        _check_policy_refusal_gate(),
        _check_registry_required_sources(),
        _check_registry_source_domains(),
    ]
    max_score = sum(check.weight for check in checks)
    score = sum(check.weight for check in checks if check.passed)
    pass_rate_percent = round((score / max_score) * 100, 2) if max_score else 0.0
    status = "pass" if score >= threshold else "fail"

    return JurisdictionEvaluationReport(
        generated_at=_utc_now_iso(),
        threshold=threshold,
        score=score,
        max_score=max_score,
        pass_rate_percent=pass_rate_percent,
        status=status,
        checks=checks,
    )


def render_jurisdiction_report_markdown(report: JurisdictionEvaluationReport) -> str:
    lines = [
        "# Jurisdiction Evaluation Report",
        "",
        f"- Generated: `{report.generated_at}`",
        f"- Score: `{report.score}/{report.max_score}` ({report.pass_rate_percent}%)",
        f"- Threshold: `{report.threshold}`",
        f"- Status: `{report.status}`",
        "",
        "## Checks",
        "",
        "| Check | Passed | Weight | Details |",
        "| --- | --- | ---: | --- |",
    ]

    for check in report.checks:
        passed = "yes" if check.passed else "no"
        lines.append(
            f"| `{check.check_id}` | {passed} | {check.weight} | {check.details} |"
        )

    lines.append("")
    return "\n".join(lines)


def write_jurisdiction_report_artifacts(
    report: JurisdictionEvaluationReport,
    *,
    json_path: str | Path,
    markdown_path: str | Path,
) -> None:
    json_target = Path(json_path)
    markdown_target = Path(markdown_path)

    json_target.parent.mkdir(parents=True, exist_ok=True)
    markdown_target.parent.mkdir(parents=True, exist_ok=True)

    json_target.write_text(
        json.dumps(report.to_dict(), indent=2),
        encoding="utf-8",
    )
    markdown_target.write_text(render_jurisdiction_report_markdown(report), encoding="utf-8")
