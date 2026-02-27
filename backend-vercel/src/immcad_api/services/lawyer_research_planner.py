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
    (
        "residency_obligation",
        re.compile(r"residency obligation|pr card|permanent resident"),
    ),
)
_CITATION_PATTERN = re.compile(
    r"\b(?:19|20)\d{2}\s+(?:FCA|CAF|FC|SCC)\s+\d+\b",
    re.IGNORECASE,
)
_DOCKET_PATTERN = re.compile(
    r"\b[a-z]{1,5}\s*-\s*\d{1,8}\s*-\s*\d{2,4}\b",
    re.IGNORECASE,
)


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def _normalize_anchor(value: str) -> str:
    return re.sub(r"\s*-\s*", "-", _normalize_whitespace(value))


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


def _extract_anchor_references(text: str) -> list[str]:
    anchors: list[str] = []
    for match in _CITATION_PATTERN.finditer(text):
        anchors.append(_normalize_whitespace(match.group(0)))
    for match in _DOCKET_PATTERN.finditer(text):
        anchors.append(_normalize_anchor(match.group(0)))
    return _dedupe(anchors)


def _normalize_intake_list(
    intake: dict[str, object],
    *,
    key: str,
    max_items: int = 12,
) -> list[str]:
    raw_values = intake.get(key)
    if not isinstance(raw_values, list):
        return []
    values: list[str] = []
    for raw_item in raw_values:
        if not isinstance(raw_item, str):
            continue
        normalized = _normalize_whitespace(raw_item)
        if not normalized:
            continue
        values.append(normalized)
    return _dedupe(values)[:max_items]


def _normalize_issue_tag(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _normalize_optional_intake_string(
    intake: dict[str, object],
    *,
    key: str,
    to_lower: bool = False,
) -> str | None:
    raw_value = intake.get(key)
    if not isinstance(raw_value, str):
        return None
    normalized = raw_value.strip()
    if not normalized:
        return None
    if to_lower:
        return normalized.lower()
    return normalized


def _profile_list(profile: dict[str, list[str] | str | None], *, key: str) -> list[str]:
    raw_value = profile.get(key)
    if isinstance(raw_value, list):
        return list(raw_value)
    return []


def extract_matter_profile(
    matter_summary: str,
    *,
    intake: dict[str, object] | None = None,
) -> dict[str, list[str] | str | None]:
    normalized = _normalize_whitespace(matter_summary.lower())

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
        [token for token in tokens if len(token) >= 5 and token not in _STOPWORDS]
    )[:12]
    target_court = _extract_target_court(normalized)
    anchor_references = _extract_anchor_references(matter_summary)
    objective: str | None = None
    date_from: str | None = None
    date_to: str | None = None

    if isinstance(intake, dict):
        intake_issue_tags = [
            _normalize_issue_tag(value)
            for value in _normalize_intake_list(intake, key="issue_tags")
        ]
        issue_tags = _dedupe([*issue_tags, *intake_issue_tags])

        intake_target_court = _normalize_optional_intake_string(
            intake,
            key="target_court",
            to_lower=True,
        )
        if intake_target_court is not None:
            target_court = intake_target_court

        intake_posture = _normalize_optional_intake_string(
            intake,
            key="procedural_posture",
            to_lower=True,
        )
        if intake_posture is not None:
            procedural_posture = intake_posture

        intake_fact_keywords = [
            keyword.lower()
            for keyword in _normalize_intake_list(
                intake,
                key="fact_keywords",
                max_items=12,
            )
        ]
        fact_keywords = _dedupe([*fact_keywords, *intake_fact_keywords])[:12]

        intake_anchors = _normalize_intake_list(
            intake,
            key="anchor_citations",
            max_items=6,
        ) + _normalize_intake_list(
            intake,
            key="anchor_dockets",
            max_items=6,
        )
        normalized_anchors = [_normalize_anchor(value) for value in intake_anchors]
        anchor_references = _dedupe([*anchor_references, *normalized_anchors])

        intake_objective = _normalize_optional_intake_string(
            intake,
            key="objective",
            to_lower=True,
        )
        if intake_objective is not None:
            objective = intake_objective

        intake_date_from = _normalize_optional_intake_string(intake, key="date_from")
        if intake_date_from is not None:
            date_from = intake_date_from

        intake_date_to = _normalize_optional_intake_string(intake, key="date_to")
        if intake_date_to is not None:
            date_to = intake_date_to

    return {
        "issue_tags": issue_tags,
        "target_court": target_court,
        "procedural_posture": procedural_posture,
        "fact_keywords": fact_keywords,
        "anchor_references": anchor_references,
        "objective": objective,
        "date_from": date_from,
        "date_to": date_to,
    }


def build_research_queries(
    matter_summary: str,
    court: str | None = None,
    intake: dict[str, object] | None = None,
) -> list[str]:
    normalized = _normalize_whitespace(matter_summary)
    profile = extract_matter_profile(normalized, intake=intake)
    target_court = (court or profile.get("target_court") or "").strip().lower()
    anchor_references = _profile_list(profile, key="anchor_references")
    if not anchor_references:
        anchor_references = _extract_anchor_references(normalized)

    queries = [normalized]

    for anchor in anchor_references:
        queries.append(f"{anchor} precedent")

    issue_tags = _profile_list(profile, key="issue_tags")
    if issue_tags:
        issue_fragment = " ".join(issue_tags[:2]).replace("_", " ")
        queries.append(f"{normalized} {issue_fragment}")

    if target_court:
        queries.append(f"{normalized} {target_court} precedent")

    procedural_posture = profile.get("procedural_posture")
    if isinstance(procedural_posture, str) and procedural_posture:
        posture_fragment = procedural_posture.replace("_", " ")
        queries.append(f"{normalized} {posture_fragment} immigration")

    fact_keywords = _profile_list(profile, key="fact_keywords")
    if fact_keywords:
        queries.append(f"{' '.join(fact_keywords[:6])} immigration precedent")

    objective = profile.get("objective")
    if objective == "distinguish_precedent":
        queries.append(f"{normalized} distinguish precedent")
    elif objective == "support_precedent":
        queries.append(f"{normalized} supporting precedent")
    elif objective == "background_research":
        queries.append(f"{normalized} leading immigration precedent")

    return _dedupe(queries)
