from __future__ import annotations

_THREADPOOL_UNAVAILABLE_RUNTIME_ERROR_MARKERS = (
    "can't start new thread",
    "cannot start new thread",
)


def is_threadpool_unavailable_runtime_error(exc: RuntimeError) -> bool:
    normalized_message = str(exc).strip().lower()
    if not normalized_message:
        return False
    return any(
        marker in normalized_message
        for marker in _THREADPOOL_UNAVAILABLE_RUNTIME_ERROR_MARKERS
    )

