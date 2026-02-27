from __future__ import annotations

import pytest

from immcad_api.policy.document_requirements import FilingForum, evaluate_readiness


@pytest.mark.parametrize(
    ("forum", "classified_doc_types", "expected_ready", "expected_missing"),
    [
        (
            FilingForum.FEDERAL_COURT_JR,
            {
                "notice_of_application",
                "decision_under_review",
                "affidavit",
                "memorandum",
            },
            True,
            (),
        ),
        (
            FilingForum.FEDERAL_COURT_JR,
            {
                "notice_of_application",
                "decision_under_review",
                "affidavit",
            },
            False,
            ("memorandum",),
        ),
        (
            FilingForum.RPD,
            {"disclosure_package"},
            True,
            (),
        ),
        (
            FilingForum.RPD,
            {"disclosure_package", "translation"},
            False,
            ("translator_declaration",),
        ),
        (
            FilingForum.RAD,
            {"appeal_record", "decision_under_review", "memorandum"},
            True,
            (),
        ),
        (
            FilingForum.RAD,
            {"appeal_record", "memorandum"},
            False,
            ("decision_under_review",),
        ),
        (
            FilingForum.IAD,
            {"appeal_record", "decision_under_review", "disclosure_package"},
            True,
            (),
        ),
        (
            FilingForum.ID,
            {"disclosure_package", "witness_list"},
            True,
            (),
        ),
        (
            FilingForum.ID,
            {"disclosure_package"},
            False,
            ("witness_list",),
        ),
        (
            FilingForum.IRCC_APPLICATION,
            {"disclosure_package", "supporting_evidence"},
            True,
            (),
        ),
        (
            FilingForum.IRCC_APPLICATION,
            {"disclosure_package"},
            False,
            ("supporting_evidence",),
        ),
    ],
)
def test_forum_policy_matrix(
    forum: FilingForum,
    classified_doc_types: set[str],
    expected_ready: bool,
    expected_missing: tuple[str, ...],
) -> None:
    readiness = evaluate_readiness(
        forum=forum,
        classified_doc_types=classified_doc_types,
    )

    assert readiness.is_ready is expected_ready
    assert readiness.missing_required_items == expected_missing
