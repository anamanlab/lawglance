from __future__ import annotations

import json
from pathlib import Path

import pytest

from immcad_api.policy.source_policy import (
    SourcePolicy,
    is_source_export_allowed,
    is_source_ingest_allowed,
    load_source_policy,
    normalize_runtime_environment,
)


def test_load_source_policy_default_file() -> None:
    policy = load_source_policy()
    assert isinstance(policy, SourcePolicy)
    assert policy.jurisdiction.lower() == "ca"
    assert policy.get_source("IRPA") is not None


def test_load_source_policy_rejects_duplicate_source_ids(tmp_path: Path) -> None:
    payload = {
        "version": "2026-02-24",
        "jurisdiction": "ca",
        "sources": [
            {
                "source_id": "DUP",
                "source_class": "official",
                "internal_ingest_allowed": True,
                "production_ingest_allowed": True,
                "answer_citation_allowed": True,
                "export_fulltext_allowed": True,
                "license_notes": "first",
                "review_owner": "legal",
                "review_date": "2026-02-24",
            },
            {
                "source_id": "DUP",
                "source_class": "official",
                "internal_ingest_allowed": True,
                "production_ingest_allowed": True,
                "answer_citation_allowed": True,
                "export_fulltext_allowed": True,
                "license_notes": "second",
                "review_owner": "legal",
                "review_date": "2026-02-24",
            },
        ],
    }
    path = tmp_path / "source_policy.yaml"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="Duplicate source_id"):
        load_source_policy(path)


def test_source_ingest_policy_blocks_internal_only_source_in_production() -> None:
    policy = load_source_policy()

    allowed, reason = is_source_ingest_allowed(
        "A2AJ",
        source_policy=policy,
        environment="production",
    )

    assert not allowed
    assert reason == "production_ingest_blocked_by_policy"


def test_source_ingest_policy_allows_internal_only_source_in_development() -> None:
    policy = load_source_policy()

    allowed, reason = is_source_ingest_allowed(
        "A2AJ",
        source_policy=policy,
        environment="development",
    )

    assert allowed
    assert reason == "internal_ingest_allowed"


def test_source_ingest_policy_blocks_unknown_source_in_production() -> None:
    policy = load_source_policy()

    allowed, reason = is_source_ingest_allowed(
        "UNKNOWN_SOURCE",
        source_policy=policy,
        environment="production",
    )

    assert not allowed
    assert reason == "source_not_in_policy_for_production"


def test_source_export_policy_blocks_when_disabled() -> None:
    policy = load_source_policy()

    allowed, reason = is_source_export_allowed(
        "A2AJ",
        source_policy=policy,
    )

    assert not allowed
    assert reason == "source_export_blocked_by_policy"


@pytest.mark.parametrize(
    ("source_id", "expected_production_ingest", "expected_answer_citation", "expected_export"),
    [
        ("CANLII_TERMS", True, False, False),
        ("A2AJ", False, False, False),
        ("REFUGEE_LAW_LAB", False, False, False),
    ],
)
def test_source_policy_restricted_source_flags(
    source_id: str,
    expected_production_ingest: bool,
    expected_answer_citation: bool,
    expected_export: bool,
) -> None:
    policy = load_source_policy()
    source = policy.get_source(source_id)

    assert source is not None
    assert source.production_ingest_allowed is expected_production_ingest
    assert source.answer_citation_allowed is expected_answer_citation
    assert source.export_fulltext_allowed is expected_export


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("production", "production"),
        ("prod", "production"),
        ("ci", "production"),
        ("production-us-east", "production"),
        ("prod_blue", "production"),
        ("ci-smoke", "production"),
        ("staging", "internal"),
        ("development", "internal"),
        (None, "internal"),
    ],
)
def test_normalize_runtime_environment(value: str | None, expected: str) -> None:
    assert normalize_runtime_environment(value) == expected
