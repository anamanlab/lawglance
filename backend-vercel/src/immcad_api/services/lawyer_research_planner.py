from __future__ import annotations

import re

_STOPWORDS = {
    "about",
    "against",
    "appeal",
    "before",
    "between",
    "court",
    "decision",
    "finding",
    "findings",
    "federal",
    "immigration",
    "legal",
    "matter",
    "regarding",
    "review",
    "support",
    "under",
    "with",
}

_ISSUE_TAG_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("procedural_fairness", re.compile(r"procedural fairness|natural justice")),
    ("inadmissibility", re.compile(r"inadmiss")),
    ("admissibility", re.compile(r"admissib")),
    ("credibility", re.compile(r"credib")),
    ("refugee_protection", re.compile(r"refugee|asylum")),
    ("humanitarian_compassionate", re.compile(r"humanitarian|compassionate|h&c")),
    ("judicial_review", re.compile(r"judicial review")),
    ("removal_order", re.compile(r"removal order|deport|exclusion order")),
    ("residency_obligation", re.compile(r"residency obligation|pr card|permanent resident")),
)


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        normalized = item.strip()
        key = normalized.lower()
        if not normalized or key in seen:
            continue
        seen.add(key)
        ordered.append(normalized)
    return ordered


def _extract_target_court(text: str) -> str | None:
    normalized = text.lower()
    if re.search(r"\bfca\b|federal court of appeal", normalized):
        return "fca"
    if re.search(r"\bscc\b|supreme court", normalized):
        return "scc"
    if re.search(r"\bfc\b|\bfct\b|federal court", normalized):
        return "fc"
    return None


def extract_matter_profile(matter_summary: str) -> dict[str, list[str] | str | None]:
    normalized = re.sub(r"\s+", " ", matter_summary.lower()).strip()

    issue_tags = [
        issue_tag
        for issue_tag, pattern in _ISSUE_TAG_PATTERNS
        if pattern.search(normalized)
    ]

    procedural_posture = None
    if "appeal" in normalized:
        procedural_posture = "appeal"
    elif "judicial review" in normalized:
        procedural_posture = "judicial_review"

    tokens = re.findall(r"[a-z0-9]+", normalized)
    fact_keywords = _dedupe(
        [
            token
            for token in tokens
            if len(token) >= 5 and token not in _STOPWORDS
        ]
    )[:12]

    return {
        "issue_tags": issue_tags,
        "target_court": _extract_target_court(normalized),
        "procedural_posture": procedural_posture,
        "fact_keywords": fact_keywords,
    }


def build_research_queries(matter_summary: str, court: str | None = None) -> list[str]:
    normalized = re.sub(r"\s+", " ", matter_summary).strip()
    profile = extract_matter_profile(normalized)
    target_court = (court or profile.get("target_court") or "").strip().lower()

    queries = [normalized]

    issue_tags = profile.get("issue_tags") or []
    if isinstance(issue_tags, list) and issue_tags:
        issue_fragment = " ".join(issue_tags[:2]).replace("_", " ")
        queries.append(f"{normalized} {issue_fragment}")

    if target_court:
        queries.append(f"{normalized} {target_court} precedent")

    procedural_posture = profile.get("procedural_posture")
    if isinstance(procedural_posture, str) and procedural_posture:
        posture_fragment = procedural_posture.replace("_", " ")
        queries.append(f"{normalized} {posture_fragment} immigration")

    fact_keywords = profile.get("fact_keywords") or []
    if isinstance(fact_keywords, list) and fact_keywords:
        queries.append(f"{' '.join(fact_keywords[:6])} immigration precedent")

    return _dedupe(queries)
