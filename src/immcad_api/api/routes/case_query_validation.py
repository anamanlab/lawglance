from __future__ import annotations

import re

_CASE_SEARCH_QUERY_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "be",
        "by",
        "for",
        "from",
        "how",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "the",
        "to",
        "was",
        "what",
        "when",
        "where",
        "who",
        "why",
        "with",
    }
)
_CASE_SEARCH_SHORT_TOKEN_ALLOWLIST = frozenset(
    {"fc", "fca", "scc", "irpa", "irpr", "pr", "ee", "pnp"}
)
_CASE_DOCKET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^[a-z]{1,5}-\d{1,8}-\d{2,4}$"),
    re.compile(r"^[a-z]{1,5}\s*-\s*\d{1,8}\s*-\s*\d{2,4}$"),
)


def is_specific_case_query(query: str) -> bool:
    normalized_query = re.sub(r"\s+", " ", query.strip().lower())
    if any(pattern.fullmatch(normalized_query) for pattern in _CASE_DOCKET_PATTERNS):
        return True

    tokens = re.findall(r"[a-z0-9]+", query.lower())
    if not tokens:
        return False
    meaningful_tokens = [
        token
        for token in tokens
        if token not in _CASE_SEARCH_QUERY_STOPWORDS
        and (len(token) >= 3 or token in _CASE_SEARCH_SHORT_TOKEN_ALLOWLIST)
    ]
    if not meaningful_tokens:
        return False
    return any(any(char.isalpha() for char in token) for token in meaningful_tokens)
