from __future__ import annotations


_THREADPOOL_UNAVAILABLE_MARKERS = (
    "threadpool",
    "thread pool",
    "threadless",
    "can't start new thread",
    "cannot start new thread",
    "thread unavailable",
    "threads are not supported",
)


def is_threadpool_unavailable_runtime_error(exc: RuntimeError) -> bool:
    message = str(exc).strip().lower()
    if "thread" not in message:
        return False
    return any(marker in message for marker in _THREADPOOL_UNAVAILABLE_MARKERS)

