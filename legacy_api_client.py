from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any, Callable

import httpx


PostFunc = Callable[..., httpx.Response]
_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class LegacyChatResult:
    ok: bool
    answer: str | None = None
    disclaimer: str | None = None
    citations: tuple[dict[str, Any], ...] = ()
    trace_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None


def build_backend_api_url(base_url: str, path: str) -> str:
    normalized_base = base_url.strip().rstrip("/")
    normalized_path = path if path.startswith("/") else f"/{path}"
    if normalized_base.endswith("/api"):
        return f"{normalized_base}{normalized_path}"
    return f"{normalized_base}/api{normalized_path}"


def _normalize_trace_id(value: str | None) -> str | None:
    if not value:
        return None
    trimmed = value.strip()
    return trimmed or None


def _default_error_message(status_code: int) -> str:
    if status_code == 401:
        return "Missing or invalid API bearer token."
    if status_code == 422:
        return "Request validation failed. Check your prompt and try again."
    if status_code == 429:
        return "Request rate exceeded allowed threshold. Please retry shortly."
    if status_code == 503:
        return "Required source is currently unavailable."
    return "Unable to complete the request at this time."


def _extract_error(payload: Any) -> tuple[str | None, str | None, str | None]:
    if not isinstance(payload, dict):
        return None, None, None
    error = payload.get("error")
    if not isinstance(error, dict):
        return None, None, None
    code = error.get("code") if isinstance(error.get("code"), str) else None
    message = error.get("message") if isinstance(error.get("message"), str) else None
    trace_id = error.get("trace_id") if isinstance(error.get("trace_id"), str) else None
    return code, message, trace_id


class LegacyApiClient:
    def __init__(
        self,
        *,
        api_base_url: str,
        bearer_token: str | None = None,
        timeout_seconds: float = 30.0,
        post_func: PostFunc | None = None,
    ) -> None:
        self.api_base_url = api_base_url
        self.bearer_token = bearer_token
        self.timeout_seconds = timeout_seconds
        self._post_func = post_func or httpx.post

    def send_chat(
        self,
        *,
        session_id: str,
        message: str,
        locale: str = "en-CA",
        mode: str = "standard",
    ) -> LegacyChatResult:
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
        }
        if self.bearer_token:
            headers["authorization"] = f"Bearer {self.bearer_token}"

        payload = {
            "session_id": session_id,
            "message": message,
            "locale": locale,
            "mode": mode,
        }

        try:
            response = self._post_func(
                build_backend_api_url(self.api_base_url, "/chat"),
                json=payload,
                headers=headers,
                timeout=self.timeout_seconds,
            )
        except httpx.RequestError as exc:
            _log.warning(
                "Legacy API transport request failed: %s",
                exc,
                exc_info=True,
            )
            return LegacyChatResult(
                ok=False,
                error_code="PROVIDER_ERROR",
                error_message="Unable to reach the IMMCAD API endpoint.",
            )

        trace_id = _normalize_trace_id(response.headers.get("x-trace-id"))
        try:
            body = response.json()
        except ValueError:
            body = None

        if response.is_success:
            if not isinstance(body, dict):
                return LegacyChatResult(
                    ok=False,
                    trace_id=trace_id,
                    error_code="UNKNOWN_ERROR",
                    error_message="Invalid success response from IMMCAD API.",
                )
            answer = body.get("answer")
            disclaimer = body.get("disclaimer")
            citations_raw = body.get("citations", [])
            citations = (
                tuple(item for item in citations_raw if isinstance(item, dict))
                if isinstance(citations_raw, list)
                else ()
            )
            if not isinstance(answer, str):
                return LegacyChatResult(
                    ok=False,
                    trace_id=trace_id,
                    error_code="UNKNOWN_ERROR",
                    error_message="IMMCAD API success response is missing answer text.",
                )
            return LegacyChatResult(
                ok=True,
                answer=answer,
                disclaimer=disclaimer if isinstance(disclaimer, str) else None,
                citations=citations,
                trace_id=trace_id,
            )

        error_code, error_message, body_trace_id = _extract_error(body)
        return LegacyChatResult(
            ok=False,
            trace_id=trace_id or _normalize_trace_id(body_trace_id),
            error_code=error_code or "UNKNOWN_ERROR",
            error_message=error_message or _default_error_message(response.status_code),
        )
