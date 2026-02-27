from __future__ import annotations

from immcad_api.policy.document_requirements import (
    FilingForum,
    evaluate_readiness,
    requirement_rules_for_forum,
    required_doc_types_for_forum,
)
from immcad_api.schemas import (
    DocumentDisclosureChecklistEntry,
    DocumentIntakeResult,
    DocumentPackageResponse,
    DocumentTableOfContentsEntry,
)


_TOC_PRIORITY_BY_FORUM: dict[FilingForum, tuple[str, ...]] = {
    FilingForum.FEDERAL_COURT_JR: (
        "notice_of_application",
        "decision_under_review",
        "affidavit",
        "memorandum",
        "translation",
        "translator_declaration",
    ),
    FilingForum.RPD: (
        "disclosure_package",
        "translation",
        "translator_declaration",
    ),
    FilingForum.RAD: (
        "appeal_record",
        "decision_under_review",
        "memorandum",
    ),
    FilingForum.IAD: (
        "appeal_record",
        "decision_under_review",
        "disclosure_package",
    ),
    FilingForum.ID: (
        "disclosure_package",
        "witness_list",
        "translation",
        "translator_declaration",
    ),
}


class DocumentPackageService:
    @staticmethod
    def _parse_forum(value: str) -> FilingForum:
        return FilingForum(value.strip().lower())

    @staticmethod
    def _collect_blocking_issues(intake_results: list[DocumentIntakeResult]) -> tuple[str, ...]:
        issues: set[str] = set()
        for result in intake_results:
            if result.quality_status in {"failed", "needs_review"}:
                issues.update(result.issues)
        return tuple(sorted(issues))

    @staticmethod
    def _build_toc(
        *,
        forum: FilingForum,
        intake_results: list[DocumentIntakeResult],
    ) -> list[DocumentTableOfContentsEntry]:
        priority = _TOC_PRIORITY_BY_FORUM[forum]
        rank = {doc_type: index for index, doc_type in enumerate(priority)}

        ordered_results = sorted(
            intake_results,
            key=lambda result: (
                rank.get(result.classification, len(priority) + 1),
                result.normalized_filename,
            ),
        )

        return [
            DocumentTableOfContentsEntry(
                position=index + 1,
                document_type=result.classification,
                filename=result.normalized_filename,
            )
            for index, result in enumerate(ordered_results)
        ]

    @staticmethod
    def _build_checklist(
        *,
        forum: FilingForum,
        classified_doc_types: set[str],
    ) -> list[DocumentDisclosureChecklistEntry]:
        required_items = required_doc_types_for_forum(
            forum=forum,
            classified_doc_types=classified_doc_types,
        )
        requirement_rules = requirement_rules_for_forum(
            forum=forum,
            classified_doc_types=classified_doc_types,
        )
        rule_by_item = {rule.item: rule for rule in requirement_rules}
        checklist: list[DocumentDisclosureChecklistEntry] = []
        for required_doc_type in required_items:
            status = "present" if required_doc_type in classified_doc_types else "missing"
            rule = rule_by_item.get(required_doc_type)
            checklist.append(
                DocumentDisclosureChecklistEntry(
                    item=required_doc_type,
                    status=status,
                    rule_scope=rule.rule_scope if rule is not None else "base",
                    reason=rule.reason if rule is not None else None,
                )
            )
        return checklist

    @staticmethod
    def _build_cover_letter_draft(
        *,
        forum: FilingForum,
        matter_id: str,
        missing_required_items: tuple[str, ...],
        blocking_issues: tuple[str, ...],
    ) -> str:
        lines = [
            f"Re: Procedural filing package draft for matter {matter_id}",
            f"Forum: {forum.value}",
            "",
            "Please find enclosed the current document package prepared for procedural review.",
        ]
        if missing_required_items:
            lines.append(
                "The following required items are currently missing: "
                + ", ".join(missing_required_items)
                + "."
            )
        if blocking_issues:
            lines.append(
                "The following blocking issues must be resolved before filing: "
                + ", ".join(blocking_issues)
                + "."
            )
        if not missing_required_items and not blocking_issues:
            lines.append("No blocking completeness gaps were detected in this package.")

        lines.append("")
        lines.append("This is a procedural draft and requires legal review before filing.")
        return "\n".join(lines)

    def build_package(
        self,
        *,
        matter_id: str,
        forum: str,
        intake_results: list[DocumentIntakeResult],
    ) -> DocumentPackageResponse:
        parsed_forum = self._parse_forum(forum)
        classified_doc_types = {
            result.classification.strip().lower()
            for result in intake_results
            if result.classification.strip()
        }
        blocking_issues = self._collect_blocking_issues(intake_results)
        readiness = evaluate_readiness(
            forum=parsed_forum,
            classified_doc_types=classified_doc_types,
            blocking_issues=blocking_issues,
        )

        table_of_contents = self._build_toc(forum=parsed_forum, intake_results=intake_results)
        disclosure_checklist = self._build_checklist(
            forum=parsed_forum,
            classified_doc_types=classified_doc_types,
        )
        cover_letter_draft = self._build_cover_letter_draft(
            forum=parsed_forum,
            matter_id=matter_id,
            missing_required_items=readiness.missing_required_items,
            blocking_issues=readiness.blocking_issues,
        )

        return DocumentPackageResponse(
            matter_id=matter_id,
            forum=parsed_forum.value,
            is_ready=readiness.is_ready,
            table_of_contents=table_of_contents,
            disclosure_checklist=disclosure_checklist,
            cover_letter_draft=cover_letter_draft,
        )


__all__ = ["DocumentPackageService"]
