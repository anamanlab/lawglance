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


def is_specific_case_query(query: str) -> bool:
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
