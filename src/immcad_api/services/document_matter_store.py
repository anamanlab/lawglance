from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import logging
from threading import Lock
from typing import Protocol

from immcad_api.policy.document_requirements import FilingForum
from immcad_api.schemas import DocumentIntakeResult


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class StoredDocumentMatter:
    forum: FilingForum
    results: tuple[DocumentIntakeResult, ...]


class DocumentMatterStore(Protocol):
    def put(
        self,
        *,
        client_id: str,
        matter_id: str,
        forum: FilingForum,
        results: list[DocumentIntakeResult] | tuple[DocumentIntakeResult, ...],
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
        results: list[DocumentIntakeResult] | tuple[DocumentIntakeResult, ...],
    ) -> None:
        key = (client_id, matter_id)
        record = StoredDocumentMatter(forum=forum, results=tuple(results))
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

    def put(
        self,
        *,
        client_id: str,
        matter_id: str,
        forum: FilingForum,
        results: list[DocumentIntakeResult] | tuple[DocumentIntakeResult, ...],
    ) -> None:
        payload = json.dumps(
            {
                "forum": forum.value,
                "results": [result.model_dump(mode="json") for result in results],
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
            raw_results = data.get("results") or []
            results = tuple(DocumentIntakeResult.model_validate(item) for item in raw_results)
        except Exception:
            LOGGER.warning("Unable to decode stored document matter record", exc_info=True)
            return None

        return StoredDocumentMatter(forum=forum, results=results)


def build_document_matter_store(
    *,
    redis_url: str | None,
    ttl_seconds: int = 24 * 60 * 60,
) -> DocumentMatterStore:
    if not redis_url:
        LOGGER.info("Using in-memory document matter store (redis_url not configured)")
        return InMemoryDocumentMatterStore()

    try:
        import redis

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
    "build_document_matter_store",
]
