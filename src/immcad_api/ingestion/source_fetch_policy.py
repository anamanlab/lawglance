from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

DEFAULT_FETCH_POLICY_RELATIVE_PATH = Path("config/fetch_policy.yaml")
CONFIG_FETCH_POLICY_PATH = (
    Path(__file__).resolve().parents[3] / DEFAULT_FETCH_POLICY_RELATIVE_PATH
)


@dataclass(frozen=True)
class FetchPolicyRule:
    timeout_seconds: float
    max_retries: int
    retry_backoff_seconds: float


@dataclass(frozen=True)
class SourceFetchPolicy:
    default: FetchPolicyRule
    by_source: dict[str, FetchPolicyRule]

    def for_source(self, source_id: str) -> FetchPolicyRule:
        return self.by_source.get(source_id, self.default)


def _default_rule(*, timeout_seconds: float) -> FetchPolicyRule:
    return FetchPolicyRule(
        timeout_seconds=max(timeout_seconds, 1.0),
        max_retries=1,
        retry_backoff_seconds=0.5,
    )


def _coerce_float(value: Any, fallback: float) -> float:
    try:
        coerced = float(value)
    except (TypeError, ValueError):
        return fallback
    return coerced if coerced > 0 else fallback


def _coerce_nonnegative_int(value: Any, fallback: int) -> int:
    try:
        coerced = int(value)
    except (TypeError, ValueError):
        return fallback
    return coerced if coerced >= 0 else fallback


def _coerce_nonnegative_float(value: Any, fallback: float) -> float:
    try:
        coerced = float(value)
    except (TypeError, ValueError):
        return fallback
    return coerced if coerced >= 0 else fallback


def _parse_rule(raw: Any, fallback: FetchPolicyRule) -> FetchPolicyRule:
    if not isinstance(raw, dict):
        return fallback
    return FetchPolicyRule(
        timeout_seconds=_coerce_float(
            raw.get("timeout_seconds"),
            fallback.timeout_seconds,
        ),
        max_retries=_coerce_nonnegative_int(
            raw.get("max_retries"),
            fallback.max_retries,
        ),
        retry_backoff_seconds=_coerce_nonnegative_float(
            raw.get("retry_backoff_seconds"),
            fallback.retry_backoff_seconds,
        ),
    )


def load_fetch_policy(
    path: str | Path | None = None,
    *,
    default_timeout_seconds: float = 30.0,
) -> SourceFetchPolicy:
    baseline_default = _default_rule(timeout_seconds=default_timeout_seconds)
    candidate = Path(path) if path is not None else CONFIG_FETCH_POLICY_PATH

    if not candidate.exists():
        if path is not None:
            raise FileNotFoundError(f"Fetch policy file not found: {candidate}")
        return SourceFetchPolicy(default=baseline_default, by_source={})

    payload = yaml.safe_load(candidate.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"Fetch policy payload must be an object: {candidate}")

    parsed_default = _parse_rule(payload.get("default"), baseline_default)
    sources_raw = payload.get("sources", {})
    if not isinstance(sources_raw, dict):
        raise ValueError("Fetch policy 'sources' must be an object keyed by source_id")

    by_source: dict[str, FetchPolicyRule] = {}
    for source_id, source_policy_raw in sources_raw.items():
        normalized_source_id = str(source_id).strip()
        if not normalized_source_id:
            continue
        by_source[normalized_source_id] = _parse_rule(
            source_policy_raw,
            parsed_default,
        )

    return SourceFetchPolicy(default=parsed_default, by_source=by_source)


__all__ = [
    "CONFIG_FETCH_POLICY_PATH",
    "DEFAULT_FETCH_POLICY_RELATIVE_PATH",
    "FetchPolicyRule",
    "SourceFetchPolicy",
    "load_fetch_policy",
]
