from __future__ import annotations

from immcad_api.policy.prompts import (
    QA_PROMPT,
    RUNTIME_CONTEXT_TEMPLATE,
    SYSTEM_PROMPT,
)
from immcad_api.schemas import Citation

_MAX_PROMPT_CITATIONS = 8


def _format_prompt_citations(citations: list[Citation]) -> str:
    if not citations:
        return "- No grounded citations were provided."

    lines: list[str] = []
    for citation in citations[:_MAX_PROMPT_CITATIONS]:
        source_id = citation.source_id.strip() if citation.source_id else "SOURCE"
        title = citation.title.strip() if citation.title else "Untitled citation"
        pin = citation.pin.strip() if citation.pin else "n/a"
        url = citation.url.strip() if citation.url else ""
        snippet = citation.snippet.strip() if citation.snippet else ""

        parts = [f"- [{source_id}] {title} ({pin})"]
        if url:
            parts.append(url)
        if snippet:
            parts.append(f'Excerpt: "{snippet}"')
        lines.append(" ".join(parts))

    return "\n".join(lines)


def build_runtime_prompts(
    *,
    message: str,
    citations: list[Citation],
    locale: str,
) -> tuple[str, str]:
    context = RUNTIME_CONTEXT_TEMPLATE.format(
        locale=locale,
        citations=_format_prompt_citations(citations),
    )
    user_prompt = QA_PROMPT.format(
        input=message.strip(),
        context=context,
    ).strip()
    return SYSTEM_PROMPT.strip(), user_prompt


def build_combined_runtime_prompt(
    *,
    message: str,
    citations: list[Citation],
    locale: str,
) -> str:
    system_prompt, user_prompt = build_runtime_prompts(
        message=message,
        citations=citations,
        locale=locale,
    )
    return f"{system_prompt}\n\n{user_prompt}"
