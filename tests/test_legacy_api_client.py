from __future__ import annotations

import httpx

from legacy_api_client import LegacyApiClient, build_backend_api_url


def _build_response(
    *,
    status_code: int,
    body: dict,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    request = httpx.Request("POST", "https://immcad.example/api/chat")
    return httpx.Response(
        status_code=status_code,
        json=body,
        headers=headers or {},
        request=request,
    )


def test_build_backend_api_url_handles_api_suffix() -> None:
    assert (
        build_backend_api_url("https://immcad.example", "/chat")
        == "https://immcad.example/api/chat"
    )
    assert (
        build_backend_api_url("https://immcad.example/api", "/chat")
        == "https://immcad.example/api/chat"
    )


def test_send_chat_success_response() -> None:
    def fake_post(*_args, **_kwargs) -> httpx.Response:
        return _build_response(
            status_code=200,
            body={
                "answer": "IRPA section 11 sets application requirements.",
                "disclaimer": "Informational only.",
                "citations": [
                    {
                        "title": "IRPA section 11",
                        "url": "https://laws-lois.justice.gc.ca/eng/acts/I-2.5/section-11.html",
                        "pin": "s.11",
                    }
                ],
            },
            headers={"x-trace-id": "trace-123"},
        )

    client = LegacyApiClient(
        api_base_url="https://immcad.example",
        bearer_token="token",
        post_func=fake_post,
    )
    result = client.send_chat(session_id="session-123456", message="What is IRPA section 11?")

    assert result.ok is True
    assert result.answer == "IRPA section 11 sets application requirements."
    assert result.disclaimer == "Informational only."
    assert result.trace_id == "trace-123"
    assert len(result.citations) == 1


def test_send_chat_returns_error_envelope_details() -> None:
    def fake_post(*_args, **_kwargs) -> httpx.Response:
        return _build_response(
            status_code=429,
            body={
                "error": {
                    "code": "RATE_LIMITED",
                    "message": "Request rate exceeded allowed threshold",
                    "trace_id": "trace-429",
                }
            },
        )

    client = LegacyApiClient(api_base_url="https://immcad.example", post_func=fake_post)
    result = client.send_chat(session_id="session-123456", message="hello")

    assert result.ok is False
    assert result.error_code == "RATE_LIMITED"
    assert result.error_message == "Request rate exceeded allowed threshold"
    assert result.trace_id == "trace-429"


def test_send_chat_handles_network_failure() -> None:
    def fake_post(*_args, **_kwargs) -> httpx.Response:
        raise httpx.ConnectError("network unreachable")

    client = LegacyApiClient(api_base_url="https://immcad.example", post_func=fake_post)
    result = client.send_chat(session_id="session-123456", message="hello")

    assert result.ok is False
    assert result.error_code == "PROVIDER_ERROR"
    assert "Unable to reach" in (result.error_message or "")
