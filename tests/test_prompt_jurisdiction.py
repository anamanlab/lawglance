from __future__ import annotations

from immcad_api.policy.prompts import QA_PROMPT, SYSTEM_PROMPT


def test_system_prompt_is_canada_scoped() -> None:
    lowered = SYSTEM_PROMPT.lower()
    assert "canadian immigration" in lowered
    assert "citizenship" in lowered


def test_system_prompt_has_no_india_domain_artifacts() -> None:
    lowered = SYSTEM_PROMPT.lower()
    disallowed_terms = [
        "indian constitution",
        "bharatiya",
        "bnss",
        "bns",
        "bsa",
    ]
    for term in disallowed_terms:
        assert term not in lowered


def test_qa_prompt_includes_grounding_guardrails() -> None:
    lowered = QA_PROMPT.lower()
    assert "safe refusal" in lowered
    assert "do not invent citations" in lowered
