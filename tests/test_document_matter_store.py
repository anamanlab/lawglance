from __future__ import annotations

from immcad_api.policy.document_requirements import FilingForum
from immcad_api.schemas import DocumentIntakeResult
from immcad_api.services.document_matter_store import (
    InMemoryDocumentMatterStore,
    RedisDocumentMatterStore,
    StoredSourceFile,
)


def _sample_result(file_id: str = "file-1") -> DocumentIntakeResult:
    return DocumentIntakeResult(
        file_id=file_id,
        original_filename="notice.pdf",
        normalized_filename="notice-file.pdf",
        classification="notice_of_application",
        quality_status="processed",
        issues=[],
        total_pages=2,
        page_char_counts=[
            {"page_number": 1, "extracted_char_count": 125},
            {"page_number": 2, "extracted_char_count": 88},
        ],
        file_hash="8d7f2f4b",
        ocr_confidence_class="high",
        ocr_capability="tesseract_available",
    )


def test_in_memory_matter_store_scopes_records_by_client() -> None:
    store = InMemoryDocumentMatterStore()
    store.put(
        client_id="198.51.100.10",
        matter_id="matter-1",
        forum=FilingForum.FEDERAL_COURT_JR,
        compilation_profile_id="federal_court_jr_leave",
        results=[_sample_result("file-a")],
    )

    loaded = store.get(client_id="198.51.100.10", matter_id="matter-1")
    assert loaded is not None
    assert loaded.compilation_profile_id == "federal_court_jr_leave"
    assert store.get(client_id="198.51.100.99", matter_id="matter-1") is None


def test_in_memory_matter_store_persists_optional_compilation_profile_id() -> None:
    store = InMemoryDocumentMatterStore()
    store.put(
        client_id="198.51.100.10",
        matter_id="matter-optional-profile",
        forum=FilingForum.RPD,
        compilation_profile_id=None,
        results=[_sample_result("file-optional")],
    )

    loaded = store.get(client_id="198.51.100.10", matter_id="matter-optional-profile")
    assert loaded is not None
    assert loaded.compilation_profile_id is None


def test_in_memory_matter_store_round_trips_source_files() -> None:
    store = InMemoryDocumentMatterStore()
    source_files = [
        StoredSourceFile(
            file_id="file-source-1",
            filename="notice.pdf",
            payload_bytes=b"%PDF-source-1",
        ),
        StoredSourceFile(
            file_id="file-source-2",
            filename="decision.pdf",
            payload_bytes=b"%PDF-source-2",
        ),
    ]

    store.put(
        client_id="198.51.100.10",
        matter_id="matter-source-files",
        forum=FilingForum.FEDERAL_COURT_JR,
        compilation_profile_id="federal_court_jr_leave",
        results=[_sample_result("file-source-1"), _sample_result("file-source-2")],
        source_files=source_files,
    )

    loaded = store.get(client_id="198.51.100.10", matter_id="matter-source-files")
    assert loaded is not None
    assert [
        (source.file_id, source.filename, source.payload_bytes)
        for source in loaded.source_files
    ] == [
        ("file-source-1", "notice.pdf", b"%PDF-source-1"),
        ("file-source-2", "decision.pdf", b"%PDF-source-2"),
    ]


class _FakeRedis:
    def __init__(self) -> None:
        self._store: dict[str, bytes] = {}
        self.setex_calls: list[tuple[str, int, bytes]] = []

    def setex(self, key: str, ttl_seconds: int, value: str) -> None:
        payload = value.encode("utf-8")
        self._store[key] = payload
        self.setex_calls.append((key, ttl_seconds, payload))

    def get(self, key: str):
        return self._store.get(key)


class _FailingRedis:
    def setex(self, key: str, ttl_seconds: int, value: str) -> None:
        del key, ttl_seconds, value
        raise RuntimeError("redis unavailable")

    def get(self, key: str):
        del key
        raise RuntimeError("redis unavailable")


def test_redis_matter_store_round_trips_records() -> None:
    redis_client = _FakeRedis()
    store = RedisDocumentMatterStore(redis_client, ttl_seconds=3600)
    stored_result = _sample_result("file-redis")
    source_files = [
        StoredSourceFile(
            file_id="file-redis",
            filename="notice.pdf",
            payload_bytes=b"%PDF-redis-source",
        )
    ]

    store.put(
        client_id="198.51.100.10",
        matter_id="matter-redis",
        forum=FilingForum.RPD,
        compilation_profile_id="rpd",
        results=[stored_result],
        source_files=source_files,
    )
    loaded = store.get(client_id="198.51.100.10", matter_id="matter-redis")

    assert loaded is not None
    assert loaded.forum == FilingForum.RPD
    assert loaded.compilation_profile_id == "rpd"
    assert [result.file_id for result in loaded.results] == ["file-redis"]
    assert loaded.results[0].total_pages == 2
    assert loaded.results[0].page_char_counts[0].extracted_char_count == 125
    assert loaded.results[0].file_hash == "8d7f2f4b"
    assert len(loaded.source_files) == 1
    assert loaded.source_files[0].file_id == "file-redis"
    assert loaded.source_files[0].filename == "notice.pdf"
    assert loaded.source_files[0].payload_bytes == b"%PDF-redis-source"
    assert redis_client.setex_calls[0][1] == 3600


def test_redis_matter_store_decodes_legacy_records_missing_compilation_fields() -> None:
    redis_client = _FakeRedis()
    store = RedisDocumentMatterStore(redis_client, ttl_seconds=3600)
    key = store._key(client_id="198.51.100.10", matter_id="matter-redis-legacy")
    redis_client._store[key] = (
        b'{"forum":"rpd","results":[{"file_id":"legacy-file","original_filename":"legacy.pdf",'
        b'"normalized_filename":"legacy.pdf","classification":"disclosure_package",'
        b'"quality_status":"processed","issues":[]}]}'
    )

    loaded = store.get(client_id="198.51.100.10", matter_id="matter-redis-legacy")

    assert loaded is not None
    assert loaded.compilation_profile_id is None
    assert loaded.results[0].file_id == "legacy-file"
    assert loaded.results[0].total_pages == 0
    assert loaded.results[0].page_char_counts == []
    assert loaded.results[0].file_hash is None
    assert loaded.source_files == ()


def test_redis_matter_store_put_ignores_transient_write_failures() -> None:
    store = RedisDocumentMatterStore(_FailingRedis(), ttl_seconds=3600)
    store.put(
        client_id="198.51.100.10",
        matter_id="matter-redis-write-failure",
        forum=FilingForum.RPD,
        results=[_sample_result("file-write-failure")],
    )


def test_redis_matter_store_get_returns_none_on_read_failures() -> None:
    store = RedisDocumentMatterStore(_FailingRedis(), ttl_seconds=3600)
    loaded = store.get(
        client_id="198.51.100.10",
        matter_id="matter-redis-read-failure",
    )
    assert loaded is None


def test_redis_matter_store_get_returns_none_on_non_utf8_payload() -> None:
    redis_client = _FakeRedis()
    store = RedisDocumentMatterStore(redis_client, ttl_seconds=3600)
    key = store._key(client_id="198.51.100.10", matter_id="matter-redis-corrupt")
    redis_client._store[key] = b"\xff\xfe\xfd"

    loaded = store.get(
        client_id="198.51.100.10",
        matter_id="matter-redis-corrupt",
    )

    assert loaded is None
