from __future__ import annotations

from pathlib import Path

import pytest

from immcad_api.ingestion.source_fetch_policy import (
    SourceFetchPolicy,
    load_fetch_policy,
)


def test_load_fetch_policy_raises_when_explicit_file_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_fetch_policy(
            tmp_path / "missing-fetch-policy.yaml",
            default_timeout_seconds=15.0,
        )


def test_load_fetch_policy_uses_repo_default_file() -> None:
    policy = load_fetch_policy()
    assert isinstance(policy, SourceFetchPolicy)
    assert policy.default.timeout_seconds > 0
    assert policy.default.max_retries >= 0
    assert policy.default.retry_backoff_seconds >= 0


def test_load_fetch_policy_parses_default_and_source_overrides(tmp_path: Path) -> None:
    fetch_policy_path = tmp_path / "fetch_policy.yaml"
    fetch_policy_path.write_text(
        "\n".join(
            [
                "default:",
                "  timeout_seconds: 40",
                "  max_retries: 3",
                "  retry_backoff_seconds: 1.5",
                "sources:",
                "  SCC_DECISIONS:",
                "    timeout_seconds: 12",
                "    max_retries: 2",
                "    retry_backoff_seconds: 0.25",
            ]
        ),
        encoding="utf-8",
    )

    policy = load_fetch_policy(fetch_policy_path, default_timeout_seconds=30.0)
    scc_policy = policy.for_source("SCC_DECISIONS")
    fallback_policy = policy.for_source("FC_DECISIONS")

    assert scc_policy.timeout_seconds == 12
    assert scc_policy.max_retries == 2
    assert scc_policy.retry_backoff_seconds == 0.25

    assert fallback_policy.timeout_seconds == 40
    assert fallback_policy.max_retries == 3
    assert fallback_policy.retry_backoff_seconds == 1.5


def test_load_fetch_policy_rejects_invalid_sources_shape(tmp_path: Path) -> None:
    fetch_policy_path = tmp_path / "fetch_policy.yaml"
    fetch_policy_path.write_text(
        "\n".join(
            [
                "default:",
                "  timeout_seconds: 30",
                "sources:",
                "  - SCC_DECISIONS",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Fetch policy 'sources' must be an object"):
        load_fetch_policy(fetch_policy_path)
