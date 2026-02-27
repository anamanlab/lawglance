from __future__ import annotations

import json
from pathlib import Path

import pytest

from immcad_api.policy import document_compilation_rules
from immcad_api.policy.document_compilation_rules import (
    DocumentCompilationCatalog,
    load_document_compilation_rules,
)


def _payload_with_profiles(*profiles: dict[str, object]) -> dict[str, object]:
    return {
        "version": "2026-02-24",
        "jurisdiction": "ca",
        "profiles": list(profiles),
    }


def _minimal_profile(*, profile_id: str, forum: str = "rpd") -> dict[str, object]:
    return {
        "profile_id": profile_id,
        "forum": forum,
        "title": f"Profile {profile_id}",
        "required_documents": [
            {
                "rule_id": f"{profile_id}_required_disclosure_package",
                "document_type": "disclosure_package",
                "severity": "blocking",
                "source_url": "https://laws-lois.justice.gc.ca/eng/regulations/SOR-2012-256/index.html",
                "remediation": "Add disclosure package to the record.",
            }
        ],
        "conditional_rules": [
            {
                "rule_id": f"{profile_id}_translation_requires_declaration",
                "when_document_type": "translation",
                "requires_document_type": "translator_declaration",
                "severity": "blocking",
                "source_url": "https://irb.gc.ca/en/legal-policy/procedure/Pages/Rules2012.aspx",
                "remediation": "Add translator declaration when filing translations.",
            }
        ],
        "order_requirements": {
            "rule_id": f"{profile_id}_ordering",
            "document_types": ["disclosure_package", "translation", "translator_declaration"],
            "source_url": "https://irb.gc.ca/en/legal-policy/procedure/Pages/Rules2012.aspx",
            "remediation": "Order package according to profile sequence.",
        },
        "pagination_requirements": {
            "rule_id": f"{profile_id}_pagination",
            "require_continuous_package_pagination": True,
            "require_index_document": True,
            "index_document_type": "index",
            "source_url": "https://irb.gc.ca/en/legal-policy/procedure/Pages/Rules2012.aspx",
            "remediation": "Add index and ensure pages are continuous.",
        },
    }


def test_load_default_catalog_includes_expected_profiles() -> None:
    catalog = load_document_compilation_rules()

    assert isinstance(catalog, DocumentCompilationCatalog)
    assert catalog.version
    assert {
        "federal_court_jr_leave",
        "federal_court_jr_hearing",
        "rpd",
        "rad",
        "id",
        "iad",
        "iad_sponsorship",
        "iad_residency",
        "iad_admissibility",
        "ircc_pr_card_renewal",
    } == {profile.profile_id for profile in catalog.profiles}

    for profile in catalog.profiles:
        assert profile.required_documents
        assert profile.conditional_rules
        assert profile.order_requirements.document_types
        assert profile.pagination_requirements.source_url


def test_load_rules_rejects_missing_source_url(tmp_path: Path) -> None:
    payload = _payload_with_profiles(_minimal_profile(profile_id="rpd"))
    payload["profiles"][0]["required_documents"][0]["source_url"] = ""

    path = tmp_path / "rules.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="Missing source_url"):
        load_document_compilation_rules(path)


def test_load_rules_rejects_duplicate_rule_ids(tmp_path: Path) -> None:
    payload = _payload_with_profiles(_minimal_profile(profile_id="rpd"))
    payload["profiles"][0]["conditional_rules"][0]["rule_id"] = payload["profiles"][0][
        "required_documents"
    ][0]["rule_id"]

    path = tmp_path / "rules.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="Duplicate rule_id"):
        load_document_compilation_rules(path)


def test_load_rules_rejects_unknown_forum(tmp_path: Path) -> None:
    payload = _payload_with_profiles(_minimal_profile(profile_id="mystery", forum="unknown_forum"))

    path = tmp_path / "rules.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="Unknown forum"):
        load_document_compilation_rules(path)


def test_load_rules_rejects_unknown_document_type(tmp_path: Path) -> None:
    payload = _payload_with_profiles(_minimal_profile(profile_id="rpd"))
    payload["profiles"][0]["required_documents"][0]["document_type"] = "unknown_document_type"

    path = tmp_path / "rules.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="Unknown document_type"):
        load_document_compilation_rules(path)


def test_load_rules_uses_embedded_payload_when_default_files_are_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    missing_paths = (
        Path("/tmp/immcad-missing-rules-1.json"),
        Path("/tmp/immcad-missing-rules-2.json"),
    )
    monkeypatch.setattr(
        document_compilation_rules,
        "_candidate_paths",
        lambda _path: missing_paths,
    )

    catalog = load_document_compilation_rules()

    assert isinstance(catalog, DocumentCompilationCatalog)
    assert catalog.profiles
