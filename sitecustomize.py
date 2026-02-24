"""Runtime compatibility shims for constrained local sandboxes.

This module is imported automatically by Python when present on ``sys.path``.
It intentionally does nothing unless explicitly enabled via environment flag.
"""

from __future__ import annotations

import os
import random
import threading
import time

_ENABLED_VALUES = {"1", "true", "yes", "on"}


def _urandom_fallback_enabled() -> bool:
    raw = os.getenv("IMMCAD_ENABLE_URANDOM_FALLBACK", "")
    return raw.strip().lower() in _ENABLED_VALUES


def _install_urandom_fallback() -> None:
    try:
        os.urandom(1)
        return
    except Exception:
        # Runtime has no secure entropy source available (sandbox limitation).
        pass

    seed = (os.getpid() << 32) ^ time.time_ns()
    generator = random.Random(seed)
    lock = threading.Lock()

    def _fallback_urandom(size: int) -> bytes:
        if size < 0:
            raise ValueError("number of bytes must be non-negative")
        with lock:
            return generator.randbytes(size)

    os.urandom = _fallback_urandom  # type: ignore[assignment]


def _asyncio_poll_fallback_enabled() -> bool:
    raw = os.getenv("IMMCAD_ENABLE_ASYNCIO_THREADSAFE_POLL", "")
    return raw.strip().lower() in _ENABLED_VALUES


def _install_asyncio_threadsafe_poll_fallback() -> None:
    import asyncio
    import types

    raw_interval = os.getenv("IMMCAD_ASYNCIO_POLL_INTERVAL_SECONDS", "0.02")
    try:
        poll_interval = float(raw_interval)
    except ValueError:
        poll_interval = 0.02
    poll_interval = min(max(poll_interval, 0.005), 1.0)

    def _attach_heartbeat(loop):
        if getattr(loop, "_immcad_threadsafe_poll_heartbeat", False):
            return loop
        setattr(loop, "_immcad_threadsafe_poll_heartbeat", True)

        def _heartbeat() -> None:
            if loop.is_closed():
                return
            loop.call_later(poll_interval, _heartbeat)

        # Keeps the event loop ticking in restricted sandboxes where
        # call_soon_threadsafe() cannot wake selectors via self-pipe socket.
        loop.call_soon(_heartbeat)
        return loop

    original_events_new_event_loop = asyncio.events.new_event_loop

    def _patched_events_new_event_loop():
        return _attach_heartbeat(original_events_new_event_loop())

    asyncio.events.new_event_loop = _patched_events_new_event_loop
    asyncio.new_event_loop = _patched_events_new_event_loop

    policy = asyncio.get_event_loop_policy()
    original_policy_new_event_loop = policy.new_event_loop

    def _patched_policy_new_event_loop(self):
        return _attach_heartbeat(original_policy_new_event_loop())

    policy.new_event_loop = types.MethodType(_patched_policy_new_event_loop, policy)


if _urandom_fallback_enabled():
    _install_urandom_fallback()

if _asyncio_poll_fallback_enabled():
    _install_asyncio_threadsafe_poll_fallback()
