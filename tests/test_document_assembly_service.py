from __future__ import annotations

from immcad_api.services.document_assembly_service import (
    AssemblyDocumentMetadata,
    DocumentAssemblyService,
)


def _doc(
    *,
    document_id: str,
    document_type: str,
    filename: str,
    page_count: int,
) -> AssemblyDocumentMetadata:
    return AssemblyDocumentMetadata(
        document_id=document_id,
        document_type=document_type,
        filename=filename,
        page_count=page_count,
    )


def test_assembly_service_builds_deterministic_toc_and_monotonic_page_map() -> None:
    service = DocumentAssemblyService()

    plan = service.plan_assembly(
        profile_id="rad",
        documents=[
            _doc(
                document_id="doc-4",
                document_type="memorandum",
                filename="memo.pdf",
                page_count=6,
            ),
            _doc(
                document_id="doc-1",
                document_type="appeal_record",
                filename="appeal.pdf",
                page_count=3,
            ),
            _doc(
                document_id="doc-5",
                document_type="supporting_material",
                filename="supporting.pdf",
                page_count=2,
            ),
            _doc(
                document_id="doc-2",
                document_type="translation",
                filename="translation.pdf",
                page_count=2,
            ),
            _doc(
                document_id="doc-3",
                document_type="decision_under_review",
                filename="decision.pdf",
                page_count=4,
            ),
        ],
    )

    assert [entry.document_type for entry in plan.table_of_contents] == [
        "appeal_record",
        "decision_under_review",
        "memorandum",
        "translation",
        "supporting_material",
    ]
    assert [(entry.start_page, entry.end_page) for entry in plan.table_of_contents] == [
        (1, 3),
        (4, 7),
        (8, 13),
        (14, 15),
        (16, 17),
    ]
    assert [item.package_page for item in plan.page_map] == list(range(1, 18))


def test_assembly_service_surfaces_validator_violations() -> None:
    service = DocumentAssemblyService()

    plan = service.plan_assembly(
        profile_id="federal_court_jr_leave",
        documents=[
            _doc(
                document_id="doc-1",
                document_type="notice_of_application",
                filename="notice.pdf",
                page_count=2,
            ),
            _doc(
                document_id="doc-2",
                document_type="decision_under_review",
                filename="decision.pdf",
                page_count=3,
            ),
            _doc(
                document_id="doc-3",
                document_type="affidavit",
                filename="affidavit.pdf",
                page_count=4,
            ),
            _doc(
                document_id="doc-4",
                document_type="memorandum",
                filename="memo.pdf",
                page_count=5,
            ),
            _doc(
                document_id="doc-5",
                document_type="translation",
                filename="translation.pdf",
                page_count=2,
            ),
        ],
    )

    assert any(
        item.violation_code == "missing_conditional_document" for item in plan.violations
    )


def test_assembly_service_orders_unknown_document_types_deterministically() -> None:
    service = DocumentAssemblyService()

    plan = service.plan_assembly(
        profile_id="id",
        documents=[
            _doc(
                document_id="doc-2",
                document_type="custom_exhibit",
                filename="z-last.pdf",
                page_count=1,
            ),
            _doc(
                document_id="doc-1",
                document_type="custom_exhibit",
                filename="a-first.pdf",
                page_count=1,
            ),
            _doc(
                document_id="doc-3",
                document_type="witness_list",
                filename="witness.pdf",
                page_count=1,
            ),
            _doc(
                document_id="doc-4",
                document_type="disclosure_package",
                filename="disclosure.pdf",
                page_count=1,
            ),
            _doc(
                document_id="doc-5",
                document_type="index",
                filename="index.pdf",
                page_count=1,
            ),
        ],
    )

    assert [entry.filename for entry in plan.table_of_contents] == [
        "disclosure.pdf",
        "witness.pdf",
        "a-first.pdf",
        "z-last.pdf",
        "index.pdf",
    ]
