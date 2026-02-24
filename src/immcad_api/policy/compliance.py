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
        r"\brepresent (?:me|my case)\b",
        r"\bbe my (?:representative|lawyer|counsel)\b",
        r"\bspeak for me\b",
        r"\b(?:appear|argue)(?: [a-z]+){0,6} for me\b",
        r"\b(?:handle|take over)(?: [a-z]+){0,6} my (?:case|appeal|hearing)\b",
        r"\bfile my(?: [a-z]+)* application\b",
        r"\b(?:submit|prepare)(?: [a-z]+){0,6} my (?:forms|documents|paperwork) for me\b",
        r"\b(?:fill out|complete|draft)(?: [a-z]+){0,6} my (?:forms|application|paperwork)\b",
        r"\b(?:file|submit|prepare)(?: [a-z]+){0,6} on my behalf\b",
        r"\bact as my (?:lawyer|counsel)\b",
        r"\b(?:personalized|personalised|tailored|custom)(?: [a-z]+){0,6} (?:strategy|plan|advice)\b",
        r"\b(?:strategy|plan)(?: [a-z]+){0,6} for my (?:case|situation|application)\b",
        r"\bguarantee(?: that i will get)?(?: [a-z]+){0,6} (?:visa|pr|permanent residence|citizenship|approval|success)\b",
        r"\b(?:promise|assure)(?: [a-z]+){0,6} (?:visa|pr|permanent residence|citizenship|approval|success)\b",
        r"\b(?:guarantee|promise|assure)(?: [a-z]+){0,8} (?:i(?:'ll| will) (?:be )?(?:approved|accepted)|approval)\b",
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
