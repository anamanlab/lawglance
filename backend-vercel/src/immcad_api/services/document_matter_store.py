from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import date
import hashlib
import importlib
import json
import logging
from threading import Lock
from typing import Any, Protocol, cast, get_args

from immcad_api.policy.document_filing_deadlines import (
    FilingDeadlineContext,
    normalize_submission_channel,
)
from immcad_api.policy.document_requirements import FilingForum
from immcad_api.schemas import DocumentCompilationProfileId, DocumentIntakeResult


LOGGER = logging.getLogger(__name__)
_VALID_COMPILATION_PROFILE_IDS = frozenset(get_args(DocumentCompilationProfileId))

CompilationProfileIdInput = DocumentCompilationProfileId | str | None


def _normalize_compilation_profile_id(
    raw_profile_id: CompilationProfileIdInput,
) -> DocumentCompilationProfileId | None:
    normalized = str(raw_profile_id or "").strip().lower()
    if not normalized:
        return None
    if normalized not in _VALID_COMPILATION_PROFILE_IDS:
        return None
    return cast(DocumentCompilationProfileId, normalized)


@dataclass(frozen=True)
class StoredSourceFile:
    file_id: str
    filename: str
    payload_bytes: bytes


def _normalize_source_files(
    source_files: list[StoredSourceFile] | tuple[StoredSourceFile, ...] | None,
) -> tuple[StoredSourceFile, ...]:
    if not source_files:
        return ()
    normalized_files: list[StoredSourceFile] = []
    for source_file in source_files:
        file_id = str(getattr(source_file, "file_id", "")).strip()
        filename = str(getattr(source_file, "filename", "")).strip()
        raw_payload = getattr(source_file, "payload_bytes", b"")
        if isinstance(raw_payload, memoryview):
            payload_bytes = raw_payload.tobytes()
        elif isinstance(raw_payload, bytearray):
            payload_bytes = bytes(raw_payload)
        elif isinstance(raw_payload, bytes):
            payload_bytes = raw_payload
        else:
            continue
        if not file_id or not filename:
            continue
        normalized_files.append(
            StoredSourceFile(
                file_id=file_id,
                filename=filename,
                payload_bytes=payload_bytes,
            )
        )
    return tuple(normalized_files)


def _normalize_filing_context(
    filing_context: FilingDeadlineContext | dict[str, Any] | None,
) -> FilingDeadlineContext:
    if filing_context is None:
        return FilingDeadlineContext()
    if isinstance(filing_context, FilingDeadlineContext):
        normalized_reason = (
            filing_context.deadline_override_reason.strip()
            if filing_context.deadline_override_reason
            else None
        )
        return FilingDeadlineContext(
            submission_channel=normalize_submission_channel(
                filing_context.submission_channel
            ),
            decision_date=filing_context.decision_date,
            hearing_date=filing_context.hearing_date,
            service_date=filing_context.service_date,
            filing_date=filing_context.filing_date,
            deadline_override_reason=normalized_reason or None,
            preflight_warnings=tuple(
                sorted(
                    {
                        str(warning).strip().lower()
                        for warning in filing_context.preflight_warnings
                        if str(warning).strip()
                    }
                )
            ),
        )
    if isinstance(filing_context, dict):
        decision_date = _parse_optional_date(filing_context.get("decision_date"))
        hearing_date = _parse_optional_date(filing_context.get("hearing_date"))
        service_date = _parse_optional_date(filing_context.get("service_date"))
        filing_date = _parse_optional_date(filing_context.get("filing_date"))
        raw_override_reason = filing_context.get("deadline_override_reason")
        override_reason = (
            str(raw_override_reason).strip() if raw_override_reason else ""
        )
        raw_warnings = filing_context.get("preflight_warnings")
        if isinstance(raw_warnings, list):
            preflight_warnings = tuple(
                sorted(
                    {
                        str(item).strip().lower()
                        for item in raw_warnings
                        if str(item).strip()
                    }
                )
            )
        else:
            preflight_warnings = ()
        return FilingDeadlineContext(
            submission_channel=normalize_submission_channel(
                str(filing_context.get("submission_channel", "")).strip().lower()
                or "portal"
            ),
            decision_date=decision_date,
            hearing_date=hearing_date,
            service_date=service_date,
            filing_date=filing_date,
            deadline_override_reason=override_reason or None,
            preflight_warnings=preflight_warnings,
        )
    return FilingDeadlineContext()


def _parse_optional_date(value: Any) -> date | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


@dataclass(frozen=True)
class StoredDocumentMatter:
    forum: FilingForum
    results: tuple[DocumentIntakeResult, ...]
    compilation_profile_id: DocumentCompilationProfileId | None = None
    source_files: tuple[StoredSourceFile, ...] = ()
    filing_context: FilingDeadlineContext = FilingDeadlineContext()


class DocumentMatterStore(Protocol):
    def put(
        self,
        *,
        client_id: str,
        matter_id: str,
        forum: FilingForum,
        compilation_profile_id: CompilationProfileIdInput = None,
        results: list[DocumentIntakeResult] | tuple[DocumentIntakeResult, ...],
        source_files: list[StoredSourceFile]
        | tuple[StoredSourceFile, ...]
        | None = None,
        filing_context: FilingDeadlineContext | None = None,
    ) -> None: ...

    def get(self, *, client_id: str, matter_id: str) -> StoredDocumentMatter | None: ...


class InMemoryDocumentMatterStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._store: dict[tuple[str, str], StoredDocumentMatter] = {}

    def put(
        self,
        *,
        client_id: str,
        matter_id: str,
        forum: FilingForum,
        compilation_profile_id: CompilationProfileIdInput = None,
        results: list[DocumentIntakeResult] | tuple[DocumentIntakeResult, ...],
        source_files: list[StoredSourceFile]
        | tuple[StoredSourceFile, ...]
        | None = None,
        filing_context: FilingDeadlineContext | None = None,
    ) -> None:
        key = (client_id, matter_id)
        normalized_profile_id = _normalize_compilation_profile_id(
            compilation_profile_id
        )
        record = StoredDocumentMatter(
            forum=forum,
            compilation_profile_id=normalized_profile_id,
            results=tuple(results),
            source_files=_normalize_source_files(source_files),
            filing_context=_normalize_filing_context(filing_context),
        )
        with self._lock:
            self._store[key] = record

    def get(self, *, client_id: str, matter_id: str) -> StoredDocumentMatter | None:
        key = (client_id, matter_id)
        with self._lock:
            return self._store.get(key)


class RedisDocumentMatterStore:
    def __init__(
        self,
        redis_client,
        *,
        prefix: str = "immcad:documents:matters",
        ttl_seconds: int = 24 * 60 * 60,
    ) -> None:
        self.redis_client = redis_client
        self.prefix = prefix
        self.ttl_seconds = max(int(ttl_seconds), 1)

    def _key(self, *, client_id: str, matter_id: str) -> str:
        digest = hashlib.sha256(f"{client_id}:{matter_id}".encode("utf-8")).hexdigest()
        return f"{self.prefix}:{digest}"

    @staticmethod
    def _normalize_result_payload(raw_result: Any) -> Any:
        if not isinstance(raw_result, dict):
            return raw_result
        normalized = dict(raw_result)
        if "page_char_counts" not in normalized:
            legacy_page_signals = normalized.get("page_signals")
            if isinstance(legacy_page_signals, list):
                normalized["page_char_counts"] = [
                    {
                        "page_number": int(signal.get("page_number", index + 1)),
                        "extracted_char_count": int(
                            signal.get("extracted_char_count", 0)
                        ),
                    }
                    for index, signal in enumerate(legacy_page_signals)
                    if isinstance(signal, dict)
                ]
        if "total_pages" not in normalized:
            page_char_counts = normalized.get("page_char_counts")
            if isinstance(page_char_counts, list):
                normalized["total_pages"] = len(page_char_counts)
        return normalized

    @staticmethod
    def _serialize_source_file(source_file: StoredSourceFile) -> dict[str, str]:
        return {
            "file_id": source_file.file_id,
            "filename": source_file.filename,
            "payload_b64": base64.b64encode(source_file.payload_bytes).decode("ascii"),
        }

    @staticmethod
    def _deserialize_source_file(raw_source_file: Any) -> StoredSourceFile | None:
        if not isinstance(raw_source_file, dict):
            return None
        file_id = str(raw_source_file.get("file_id", "")).strip()
        filename = str(raw_source_file.get("filename", "")).strip()
        raw_payload = (
            raw_source_file.get("payload_b64")
            or raw_source_file.get("payload_base64")
            or raw_source_file.get("payload_bytes")
        )
        if not file_id or not filename:
            return None

        payload_bytes: bytes | None = None
        if isinstance(raw_payload, str):
            encoded_payload = raw_payload.strip()
            if encoded_payload:
                try:
                    payload_bytes = base64.b64decode(
                        encoded_payload.encode("ascii"),
                        validate=True,
                    )
                except Exception:
                    try:
                        payload_bytes = base64.b64decode(encoded_payload)
                    except Exception:
                        payload_bytes = None
        elif isinstance(raw_payload, memoryview):
            payload_bytes = raw_payload.tobytes()
        elif isinstance(raw_payload, bytearray):
            payload_bytes = bytes(raw_payload)
        elif isinstance(raw_payload, bytes):
            payload_bytes = raw_payload

        if payload_bytes is None:
            return None
        return StoredSourceFile(
            file_id=file_id,
            filename=filename,
            payload_bytes=payload_bytes,
        )

    @staticmethod
    def _serialize_filing_context(
        filing_context: FilingDeadlineContext,
    ) -> dict[str, object]:
        return {
            "submission_channel": filing_context.submission_channel,
            "decision_date": (
                filing_context.decision_date.isoformat()
                if filing_context.decision_date is not None
                else None
            ),
            "hearing_date": (
                filing_context.hearing_date.isoformat()
                if filing_context.hearing_date is not None
                else None
            ),
            "service_date": (
                filing_context.service_date.isoformat()
                if filing_context.service_date is not None
                else None
            ),
            "filing_date": (
                filing_context.filing_date.isoformat()
                if filing_context.filing_date is not None
                else None
            ),
            "deadline_override_reason": filing_context.deadline_override_reason,
            "preflight_warnings": list(filing_context.preflight_warnings),
        }

    @staticmethod
    def _deserialize_filing_context(raw_filing_context: Any) -> FilingDeadlineContext:
        return _normalize_filing_context(
            raw_filing_context if isinstance(raw_filing_context, dict) else None
        )

    def put(
        self,
        *,
        client_id: str,
        matter_id: str,
        forum: FilingForum,
        compilation_profile_id: CompilationProfileIdInput = None,
        results: list[DocumentIntakeResult] | tuple[DocumentIntakeResult, ...],
        source_files: list[StoredSourceFile]
        | tuple[StoredSourceFile, ...]
        | None = None,
        filing_context: FilingDeadlineContext | None = None,
    ) -> None:
        normalized_profile_id = _normalize_compilation_profile_id(
            compilation_profile_id
        )
        normalized_source_files = _normalize_source_files(source_files)
        normalized_filing_context = _normalize_filing_context(filing_context)
        payload = json.dumps(
            {
                "forum": forum.value,
                "compilation_profile_id": normalized_profile_id,
                "results": [result.model_dump(mode="json") for result in results],
                "source_files": [
                    self._serialize_source_file(source_file)
                    for source_file in normalized_source_files
                ],
                "filing_context": self._serialize_filing_context(
                    normalized_filing_context
                ),
            }
        )
        key = self._key(client_id=client_id, matter_id=matter_id)
        try:
            self.redis_client.setex(key, self.ttl_seconds, payload)
        except Exception:
            LOGGER.warning(
                "Unable to persist document matter in Redis",
                exc_info=True,
                extra={"key": key, "client_id": client_id, "matter_id": matter_id},
            )

    def get(self, *, client_id: str, matter_id: str) -> StoredDocumentMatter | None:
        key = self._key(client_id=client_id, matter_id=matter_id)
        try:
            payload = self.redis_client.get(key)
        except Exception:
            LOGGER.warning(
                "Unable to read document matter from Redis",
                exc_info=True,
                extra={"key": key, "client_id": client_id, "matter_id": matter_id},
            )
            return None
        if not payload:
            try:
                ttl_seconds = self.redis_client.ttl(key)
            except Exception:
                ttl_seconds = None
            if ttl_seconds == -2:
                LOGGER.info(
                    "Redis document matter key expired before read",
                    extra={"key": key, "client_id": client_id, "matter_id": matter_id},
                )
            return None

        try:
            if isinstance(payload, bytes):
                payload_text = payload.decode("utf-8")
            else:
                payload_text = str(payload)
            data = json.loads(payload_text)
            forum = FilingForum(str(data.get("forum", "")).strip().lower())
            compilation_profile_id = _normalize_compilation_profile_id(
                data.get("compilation_profile_id")
            )
            raw_results = data.get("results") or []
            results = tuple(
                DocumentIntakeResult.model_validate(
                    self._normalize_result_payload(item)
                )
                for item in raw_results
            )
            raw_source_files = data.get("source_files") or []
            source_files = tuple(
                source_file
                for source_file in (
                    self._deserialize_source_file(item) for item in raw_source_files
                )
                if source_file is not None
            )
            filing_context = self._deserialize_filing_context(
                data.get("filing_context")
            )
        except Exception:
            LOGGER.warning(
                "Unable to decode stored document matter record", exc_info=True
            )
            return None

        return StoredDocumentMatter(
            forum=forum,
            compilation_profile_id=compilation_profile_id,
            results=results,
            source_files=source_files,
            filing_context=filing_context,
        )


def build_document_matter_store(
    *,
    redis_url: str | None,
    ttl_seconds: int = 24 * 60 * 60,
) -> DocumentMatterStore:
    if not redis_url:
        LOGGER.info("Using in-memory document matter store (redis_url not configured)")
        return InMemoryDocumentMatterStore()

    try:
        redis = importlib.import_module("redis")

        redis_client = redis.Redis.from_url(
            redis_url,
            socket_timeout=0.5,
            socket_connect_timeout=0.5,
        )
        redis_client.ping()
        LOGGER.info("Using Redis-backed document matter store")
        return RedisDocumentMatterStore(redis_client, ttl_seconds=ttl_seconds)
    except Exception:
        LOGGER.warning(
            "Redis document matter store unavailable; falling back to in-memory store",
            exc_info=True,
        )
        return InMemoryDocumentMatterStore()


__all__ = [
    "DocumentMatterStore",
    "InMemoryDocumentMatterStore",
    "RedisDocumentMatterStore",
    "StoredDocumentMatter",
    "StoredSourceFile",
    "build_document_matter_store",
]
