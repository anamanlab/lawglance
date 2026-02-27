from __future__ import annotations

from dataclasses import dataclass

from immcad_api.policy.document_compilation_rules import (
    DocumentCompilationCatalog,
    DocumentCompilationProfile,
    load_document_compilation_rules,
)
from immcad_api.policy.document_compilation_validator import (
    DocumentCompilationViolation,
    validate_document_compilation,
)


@dataclass(frozen=True)
class AssemblyDocumentMetadata:
    document_id: str
    document_type: str
    filename: str
    page_count: int


@dataclass(frozen=True)
class AssemblyTableOfContentsEntry:
    position: int
    document_id: str
    document_type: str
    filename: str
    start_page: int
    end_page: int


@dataclass(frozen=True)
class AssemblyPageMapEntry:
    package_page: int
    document_id: str
    document_type: str
    document_page: int


@dataclass(frozen=True)
class DocumentAssemblyPlan:
    profile_id: str
    forum: str
    catalog_version: str
    table_of_contents: tuple[AssemblyTableOfContentsEntry, ...]
    page_map: tuple[AssemblyPageMapEntry, ...]
    violations: tuple[DocumentCompilationViolation, ...]


class DocumentAssemblyService:
    def __init__(self, catalog: DocumentCompilationCatalog | None = None) -> None:
        self._catalog = catalog or load_document_compilation_rules()

    @staticmethod
    def _normalize_documents(
        documents: list[AssemblyDocumentMetadata] | tuple[AssemblyDocumentMetadata, ...],
    ) -> tuple[AssemblyDocumentMetadata, ...]:
        normalized: list[AssemblyDocumentMetadata] = []
        for item in documents:
            document_id = str(item.document_id).strip()
            document_type = str(item.document_type).strip().lower()
            filename = str(item.filename).strip()
            page_count = int(item.page_count)

            if not document_id:
                raise ValueError("document_id is required")
            if not document_type:
                raise ValueError(f"document_type is required for document_id='{document_id}'")
            if not filename:
                raise ValueError(f"filename is required for document_id='{document_id}'")
            if page_count < 1:
                raise ValueError(
                    f"page_count must be >= 1 for document_id='{document_id}', got {page_count}"
                )

            normalized.append(
                AssemblyDocumentMetadata(
                    document_id=document_id,
                    document_type=document_type,
                    filename=filename,
                    page_count=page_count,
                )
            )
        return tuple(normalized)

    @staticmethod
    def _order_documents(
        *,
        profile: DocumentCompilationProfile,
        documents: tuple[AssemblyDocumentMetadata, ...],
    ) -> tuple[AssemblyDocumentMetadata, ...]:
        rank = {
            doc_type: position
            for position, doc_type in enumerate(profile.order_requirements.document_types)
        }
        max_rank = len(rank)

        return tuple(
            sorted(
                documents,
                key=lambda item: (
                    rank.get(item.document_type, max_rank + 1),
                    item.document_type,
                    item.filename.lower(),
                    item.document_id,
                ),
            )
        )

    @staticmethod
    def _build_toc_and_page_map(
        *,
        ordered_documents: tuple[AssemblyDocumentMetadata, ...],
    ) -> tuple[tuple[AssemblyTableOfContentsEntry, ...], tuple[AssemblyPageMapEntry, ...]]:
        table_of_contents: list[AssemblyTableOfContentsEntry] = []
        page_map: list[AssemblyPageMapEntry] = []

        current_package_page = 1
        for position, document in enumerate(ordered_documents, start=1):
            start_page = current_package_page
            end_page = start_page + document.page_count - 1

            table_of_contents.append(
                AssemblyTableOfContentsEntry(
                    position=position,
                    document_id=document.document_id,
                    document_type=document.document_type,
                    filename=document.filename,
                    start_page=start_page,
                    end_page=end_page,
                )
            )

            for document_page in range(1, document.page_count + 1):
                page_map.append(
                    AssemblyPageMapEntry(
                        package_page=current_package_page,
                        document_id=document.document_id,
                        document_type=document.document_type,
                        document_page=document_page,
                    )
                )
                current_package_page += 1

        return tuple(table_of_contents), tuple(page_map)

    def plan_assembly(
        self,
        *,
        profile_id: str,
        documents: list[AssemblyDocumentMetadata] | tuple[AssemblyDocumentMetadata, ...],
    ) -> DocumentAssemblyPlan:
        profile = self._catalog.require_profile(profile_id)
        normalized_documents = self._normalize_documents(documents)
        ordered_documents = self._order_documents(profile=profile, documents=normalized_documents)
        table_of_contents, page_map = self._build_toc_and_page_map(ordered_documents=ordered_documents)

        provided_document_types = {item.document_type for item in ordered_documents}
        page_ranges = tuple((item.start_page, item.end_page) for item in table_of_contents)
        violations = validate_document_compilation(
            profile=profile,
            provided_document_types=provided_document_types,
            page_ranges=page_ranges,
        )

        return DocumentAssemblyPlan(
            profile_id=profile.profile_id,
            forum=profile.forum,
            catalog_version=self._catalog.version,
            table_of_contents=table_of_contents,
            page_map=page_map,
            violations=violations,
        )


__all__ = [
    "AssemblyDocumentMetadata",
    "AssemblyPageMapEntry",
    "AssemblyTableOfContentsEntry",
    "DocumentAssemblyPlan",
    "DocumentAssemblyService",
]
