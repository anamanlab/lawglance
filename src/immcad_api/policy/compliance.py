from __future__ import annotations

from immcad_api.schemas import Citation

DISCLAIMER_TEXT = (
    "IMMCAD is an informational tool and not legal advice. "
    "Consult a licensed Canadian immigration lawyer or RCIC for advice on your case."
)

POLICY_REFUSAL_TEXT = (
    "I can provide general informational guidance only. "
    "I cannot provide personalized legal advice or represent you in legal proceedings."
)


def should_refuse_for_policy(message: str) -> bool:
    normalized = message.lower()
    blocked_phrases = [
        "represent me",
        "file my application",
        "act as my lawyer",
        "guarantee visa",
    ]
    return any(phrase in normalized for phrase in blocked_phrases)


def enforce_citation_requirement(answer: str, citations: list[Citation]) -> tuple[str, list[Citation], str]:
    if citations:
        return answer, citations, "medium"

    return (
        "I do not have enough grounded legal context to answer safely. "
        "Please refine your question or provide more details.",
        [],
        "low",
    )
