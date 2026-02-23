from __future__ import annotations

import re

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
    normalized = re.sub(r"\s+", " ", message.lower()).strip()
    blocked_patterns = [
        r"\brepresent me\b",
        r"\bfile my(?: [a-z]+)* application\b",
        r"\bact as my (?:lawyer|counsel)\b",
        r"\bguarantee(?: that i will get)?(?: [a-z]+)* visa\b",
    ]
    return any(re.search(pattern, normalized) for pattern in blocked_patterns)


def enforce_citation_requirement(answer: str, citations: list[Citation]) -> tuple[str, list[Citation], str]:
    if citations:
        return answer, citations, "medium"

    return (
        "I do not have enough grounded legal context to answer safely. "
        "Please refine your question or provide more details.",
        [],
        "low",
    )
