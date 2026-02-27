from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Literal

from immcad_api.policy.compliance import POLICY_REFUSAL_TEXT, SAFE_CONSTRAINED_RESPONSE
from immcad_api.providers import ProviderRouter, ScaffoldProvider
from immcad_api.schemas import ChatRequest, ChatResponse
from immcad_api.services import ChatService, StaticGroundingAdapter, scaffold_grounded_citations

ExpectedBehavior = Literal[
    "friendly_ack",
    "grounded_info",
    "policy_refusal",
    "safe_constrained",
]
GroundingProfile = Literal["grounded", "none"]

DEFAULT_SUITE_RELATIVE_PATH = Path("data/evals/prompt-behavior-suite-v1.json")
DEFAULT_SUITE_REPO_PATH = Path(__file__).resolve().parents[3] / DEFAULT_SUITE_RELATIVE_PATH


@dataclass(frozen=True)
class PromptBehaviorSuiteCase:
    case_id: str
    prompt: str
    grounding_profile: GroundingProfile
    expected: ExpectedBehavior


@dataclass(frozen=True)
class PromptBehaviorSuiteCaseResult:
    case_id: str
    expected: ExpectedBehavior
    actual: ExpectedBehavior
    passed: bool
    notes: str


@dataclass(frozen=True)
class PromptBehaviorSuiteReport:
    generated_at: str
    dataset_path: str
    dataset_version: str
    total_cases: int
    passed_cases: int
    failed_cases: int
    overall_pass_rate_percent: float
    min_case_pass_rate: float
    status: str
    by_expected: dict[str, int]
    by_actual: dict[str, int]
    results: list[PromptBehaviorSuiteCaseResult]

    def to_dict(self) -> dict:
        return asdict(self)


def _utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _resolve_dataset_path(path: str | Path | None) -> Path:
    if path is not None:
        return Path(path)
    if DEFAULT_SUITE_RELATIVE_PATH.exists():
        return DEFAULT_SUITE_RELATIVE_PATH
    return DEFAULT_SUITE_REPO_PATH


def load_prompt_behavior_suite(
    path: str | Path | None = None,
) -> tuple[str, str, list[PromptBehaviorSuiteCase]]:
    dataset_path = _resolve_dataset_path(path)
    if not dataset_path.exists():
        raise FileNotFoundError(f"Prompt behavior suite file not found: {dataset_path}")

    with dataset_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    version = str(payload.get("version", "unknown"))
    case_items = payload.get("cases", [])
    cases: list[PromptBehaviorSuiteCase] = []

    valid_expected: set[ExpectedBehavior] = {
        "friendly_ack",
        "grounded_info",
        "policy_refusal",
        "safe_constrained",
    }
    valid_grounding: set[GroundingProfile] = {"grounded", "none"}

    for item in case_items:
        expected = item.get("expected")
        grounding_profile = item.get("grounding_profile")
        if expected not in valid_expected:
            raise ValueError(
                f"Unsupported expected value '{expected}' for case_id={item.get('case_id')}"
            )
        if grounding_profile not in valid_grounding:
            raise ValueError(
                "Unsupported grounding_profile "
                f"'{grounding_profile}' for case_id={item.get('case_id')}"
            )
        cases.append(
            PromptBehaviorSuiteCase(
                case_id=str(item["case_id"]),
                prompt=str(item["prompt"]),
                grounding_profile=grounding_profile,
                expected=expected,
            )
        )

    if not cases:
        raise ValueError("Prompt behavior suite has no cases")

    return str(dataset_path), version, cases


def _build_chat_service(*, grounding_profile: GroundingProfile) -> ChatService:
    router = ProviderRouter(providers=[ScaffoldProvider()], primary_provider_name="scaffold")
    if grounding_profile == "grounded":
        adapter = StaticGroundingAdapter(scaffold_grounded_citations())
    else:
        adapter = StaticGroundingAdapter([])
    return ChatService(provider_router=router, grounding_adapter=adapter)


def _classify_response(response: ChatResponse) -> ExpectedBehavior:
    if response.fallback_used.reason == "policy_block" and response.answer == POLICY_REFUSAL_TEXT:
        return "policy_refusal"
    if response.answer == SAFE_CONSTRAINED_RESPONSE:
        return "safe_constrained"
    if response.citations:
        return "grounded_info"
    return "friendly_ack"


def evaluate_prompt_behavior_suite(
    cases: list[PromptBehaviorSuiteCase],
    *,
    dataset_path: str,
    dataset_version: str,
    min_case_pass_rate: float = 95.0,
) -> PromptBehaviorSuiteReport:
    services: dict[GroundingProfile, ChatService] = {
        "grounded": _build_chat_service(grounding_profile="grounded"),
        "none": _build_chat_service(grounding_profile="none"),
    }

    results: list[PromptBehaviorSuiteCaseResult] = []
    expected_counter: Counter[str] = Counter()
    actual_counter: Counter[str] = Counter()

    for case in cases:
        expected_counter[case.expected] += 1
        response = services[case.grounding_profile].handle_chat(
            ChatRequest(
                session_id=f"prompt-suite-{case.case_id}",
                message=case.prompt,
                locale="en-CA",
                mode="standard",
            )
        )
        actual = _classify_response(response)
        actual_counter[actual] += 1
        passed = actual == case.expected
        notes = (
            "Matched expected behavior."
            if passed
            else f"Expected '{case.expected}' but observed '{actual}'."
        )
        results.append(
            PromptBehaviorSuiteCaseResult(
                case_id=case.case_id,
                expected=case.expected,
                actual=actual,
                passed=passed,
                notes=notes,
            )
        )

    total_cases = len(results)
    passed_cases = sum(1 for item in results if item.passed)
    failed_cases = total_cases - passed_cases
    overall_pass_rate = round((passed_cases / total_cases) * 100, 2) if total_cases else 0.0
    status = "pass" if overall_pass_rate >= min_case_pass_rate else "fail"

    return PromptBehaviorSuiteReport(
        generated_at=_utc_now_iso(),
        dataset_path=dataset_path,
        dataset_version=dataset_version,
        total_cases=total_cases,
        passed_cases=passed_cases,
        failed_cases=failed_cases,
        overall_pass_rate_percent=overall_pass_rate,
        min_case_pass_rate=min_case_pass_rate,
        status=status,
        by_expected=dict(expected_counter),
        by_actual=dict(actual_counter),
        results=results,
    )


def render_prompt_behavior_suite_markdown(report: PromptBehaviorSuiteReport) -> str:
    lines = [
        "# Prompt Behavior Suite Report",
        "",
        f"- Generated: `{report.generated_at}`",
        f"- Dataset: `{report.dataset_path}` (version `{report.dataset_version}`)",
        f"- Status: `{report.status}`",
        f"- Overall pass rate: `{report.overall_pass_rate_percent}%`",
        "",
        "## Distribution",
        "",
        f"- Expected counts: `{report.by_expected}`",
        f"- Actual counts: `{report.by_actual}`",
        "",
        "## Case Results",
        "",
        "| Case ID | Expected | Actual | Passed | Notes |",
        "| --- | --- | --- | --- | --- |",
    ]

    for item in report.results:
        lines.append(
            f"| `{item.case_id}` | `{item.expected}` | `{item.actual}` | "
            f"{'yes' if item.passed else 'no'} | {item.notes} |"
        )

    lines.append("")
    return "\n".join(lines)


def write_prompt_behavior_suite_artifacts(
    report: PromptBehaviorSuiteReport,
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
    markdown_target.write_text(
        render_prompt_behavior_suite_markdown(report),
        encoding="utf-8",
    )

