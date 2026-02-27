from __future__ import annotations

from immcad_api.policy.document_requirements import FilingForum
from immcad_api.schemas import DocumentIntakeResult
from immcad_api.services.document_matter_store import (
    InMemoryDocumentMatterStore,
    RedisDocumentMatterStore,
)


def _sample_result(file_id: str = "file-1") -> DocumentIntakeResult:
    return DocumentIntakeResult(
        file_id=file_id,
        original_filename="notice.pdf",
        normalized_filename="notice-file.pdf",
        classification="notice_of_application",
        quality_status="processed",
        issues=[],
    )


def test_in_memory_matter_store_scopes_records_by_client() -> None:
    store = InMemoryDocumentMatterStore()
    store.put(
        client_id="198.51.100.10",
        matter_id="matter-1",
        forum=FilingForum.FEDERAL_COURT_JR,
        results=[_sample_result("file-a")],
    )

    assert store.get(client_id="198.51.100.10", matter_id="matter-1") is not None
    assert store.get(client_id="198.51.100.99", matter_id="matter-1") is None


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

    store.put(
        client_id="198.51.100.10",
        matter_id="matter-redis",
        forum=FilingForum.RPD,
        results=[stored_result],
    )
    loaded = store.get(client_id="198.51.100.10", matter_id="matter-redis")

    assert loaded is not None
    assert loaded.forum == FilingForum.RPD
    assert [result.file_id for result in loaded.results] == ["file-redis"]
    assert redis_client.setex_calls[0][1] == 3600


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
