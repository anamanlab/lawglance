from __future__ import annotations

import re
from urllib.parse import urlparse, urlunparse

from immcad_api.schemas import Citation

DISCLAIMER_TEXT = (
    "IMMCAD is an informational tool and not legal advice. "
    "Consult a licensed Canadian immigration lawyer or RCIC for advice on your case."
)

POLICY_REFUSAL_TEXT = (
    "I can provide general informational guidance only. "
    "I cannot provide personalized legal advice or represent you in legal proceedings."
)

SAFE_CONSTRAINED_RESPONSE = (
    "I do not have enough grounded legal context to answer safely. "
    "Please refine your question or provide more details."
)

DEFAULT_TRUSTED_CITATION_DOMAINS: tuple[str, ...] = (
    "laws-lois.justice.gc.ca",
    "justice.gc.ca",
    "canada.ca",
    "ircc.canada.ca",
    "canlii.org",
    "decisions.scc-csc.ca",
    "decisions.fct-cf.gc.ca",
    "decisions.fca-caf.gc.ca",
)


def normalize_trusted_domains(domains: tuple[str, ...] | list[str] | None) -> tuple[str, ...]:
    if not domains:
        return ()
    normalized: list[str] = []
    seen: set[str] = set()
    for domain in domains:
        candidate = domain.strip().lower().strip(".")
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        normalized.append(candidate)
    return tuple(normalized)


def _is_domain_trusted(url: str, trusted_domains: tuple[str, ...]) -> bool:
    if not trusted_domains:
        return False
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").strip().lower().strip(".")
    if not hostname:
        return False
    for domain in trusted_domains:
        if hostname == domain or hostname.endswith(f".{domain}"):
            return True
    return False


def _coerce_citation(value: Citation | dict[str, object] | object) -> Citation | None:
    if isinstance(value, Citation):
        return value
    if isinstance(value, dict):
        try:
            return Citation.model_validate(value)
        except Exception:
            return None
    return None


def _citation_lookup_key(citation: Citation) -> tuple[str, str, str]:
    parsed = urlparse(citation.url.strip())
    normalized_url = urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment,
        )
    )
    return (
        citation.source_id.strip().lower(),
        normalized_url,
        citation.pin.strip().lower(),
    )


def _is_well_formed_citation(citation: Citation, *, trusted_domains: tuple[str, ...]) -> bool:
    if not citation.source_id.strip():
        return False
    if not citation.title.strip():
        return False
    if not citation.pin.strip():
        return False
    if not citation.snippet.strip():
        return False
    url = citation.url.strip().lower()
    if not url.startswith("https://"):
        return False
    if not _is_domain_trusted(url, trusted_domains):
        return False
    return True


def verify_grounded_citations(
    citations: list[Citation | dict[str, object] | object],
    *,
    grounded_citations: list[Citation],
    trusted_domains: tuple[str, ...],
) -> list[Citation]:
    if not grounded_citations:
        return []
    normalized_trusted_domains = normalize_trusted_domains(trusted_domains)
    if not normalized_trusted_domains:
        return []

    grounded_index: dict[tuple[str, str, str], Citation] = {}
    for grounded in grounded_citations:
        if not _is_well_formed_citation(grounded, trusted_domains=normalized_trusted_domains):
            continue
        grounded_index[_citation_lookup_key(grounded)] = grounded.model_copy(deep=True)

    if not grounded_index:
        return []

    verified: list[Citation] = []
    seen: set[tuple[str, str, str]] = set()
    for raw_citation in citations:
        citation = _coerce_citation(raw_citation)
        if citation is None:
            continue
        if not _is_well_formed_citation(citation, trusted_domains=normalized_trusted_domains):
            continue
        key = _citation_lookup_key(citation)
        matched_grounded = grounded_index.get(key)
        if matched_grounded is None or key in seen:
            continue
        verified.append(matched_grounded.model_copy(deep=True))
        seen.add(key)
    return verified


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


def enforce_citation_requirement(
    answer: str,
    citations: list[Citation | dict[str, object] | object],
    *,
    grounded_citations: list[Citation],
    trusted_domains: tuple[str, ...] | list[str] | None = None,
) -> tuple[str, list[Citation], str]:
    if not trusted_domains:
        effective_trusted_domains: tuple[str, ...] | list[str] | None = (
            DEFAULT_TRUSTED_CITATION_DOMAINS
        )
    else:
        effective_trusted_domains = trusted_domains
    normalized_trusted_domains = normalize_trusted_domains(effective_trusted_domains)
    validated_citations = verify_grounded_citations(
        citations,
        grounded_citations=grounded_citations,
        trusted_domains=normalized_trusted_domains,
    )
    if validated_citations:
        return answer, validated_citations, "medium"

    return (SAFE_CONSTRAINED_RESPONSE, [], "low")
