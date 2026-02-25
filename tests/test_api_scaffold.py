from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from immcad_api.main import create_app  # noqa: E402
from immcad_api.policy.compliance import DISCLAIMER_TEXT, POLICY_REFUSAL_TEXT  # noqa: E402
from immcad_api.errors import SourceUnavailableError  # noqa: E402
from immcad_api.providers import ProviderError, ProviderResult  # noqa: E402


client = TestClient(create_app())


def test_chat_endpoint_contract_shape() -> None:
    response = client.post(
        "/api/chat",
        json={
            "session_id": "session-123456",
            "message": "What are the basic PR eligibility pathways?",
            "locale": "en-CA",
            "mode": "standard",
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert "answer" in body
    assert "citations" in body
    assert "confidence" in body
    assert "disclaimer" in body
    assert "fallback_used" in body
    assert body["citations"]
    assert "x-trace-id" in response.headers


def test_chat_policy_block_response() -> None:
    response = client.post(
        "/api/chat",
        json={
            "session_id": "session-123456",
            "message": "Please represent me and file my application",
            "locale": "en-CA",
            "mode": "standard",
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert body["answer"] == POLICY_REFUSAL_TEXT
    assert body["citations"] == []
    assert body["confidence"] == "low"
    assert body["disclaimer"] == DISCLAIMER_TEXT
    assert body["fallback_used"]["used"] is False
    assert body["fallback_used"]["reason"] == "policy_block"


def test_case_search_contract_shape() -> None:
    response = client.post(
        "/api/search/cases",
        json={
            "query": "express entry inadmissibility",
            "jurisdiction": "ca",
            "court": "fct",
            "limit": 2,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert "results" in body
    assert len(body["results"]) == 2
    assert "case_id" in body["results"][0]
    assert "url" in body["results"][0]
    assert "export_allowed" in body["results"][0]
    assert "export_policy_reason" in body["results"][0]


def test_case_search_rejects_broad_stopword_query() -> None:
    response = client.post(
        "/api/search/cases",
        json={
            "query": "to be",
            "jurisdiction": "ca",
            "court": "fct",
            "limit": 2,
        },
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["policy_reason"] == "case_search_query_too_broad"
    assert "specific terms" in body["error"]["message"]


def test_chat_case_law_query_uses_case_search_tool_citations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from datetime import date

    from immcad_api.schemas import CaseSearchResponse, CaseSearchResult

    def _mock_case_search(self, request):
        del self, request
        return CaseSearchResponse(
            results=[
                CaseSearchResult(
                    case_id="2026-FC-101",
                    title="Example v Canada (Citizenship and Immigration)",
                    citation="2026 FC 101",
                    decision_date=date(2026, 2, 1),
                    url="https://www.canlii.org/en/ca/fct/doc/2026/2026fc101/2026fc101.html",
                    source_id="FC_DECISIONS",
                    document_url="https://www.canlii.org/en/ca/fct/doc/2026/2026fc101/2026fc101.html",
                )
            ]
        )

    monkeypatch.setattr(
        "immcad_api.services.case_search_service.CaseSearchService.search",
        _mock_case_search,
    )
    chat_client = TestClient(create_app())

    response = chat_client.post(
        "/api/chat",
        json={
            "session_id": "session-123456",
            "message": "Find case law about inadmissibility decisions.",
            "locale": "en-CA",
            "mode": "standard",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert any(citation["source_id"] == "FC_DECISIONS" for citation in body["citations"])
    assert body["confidence"] == "medium"


def test_case_search_disabled_returns_structured_unavailable_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENABLE_CASE_SEARCH", "false")
    disabled_client = TestClient(create_app())

    response = disabled_client.post(
        "/api/search/cases",
        json={
            "query": "express entry inadmissibility",
            "jurisdiction": "ca",
            "court": "fct",
            "limit": 2,
        },
    )

    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "SOURCE_UNAVAILABLE"
    assert body["error"]["policy_reason"] == "case_search_disabled"
    assert response.headers["x-trace-id"] == body["error"]["trace_id"]


def test_case_export_approval_disabled_returns_structured_unavailable_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENABLE_CASE_SEARCH", "false")
    disabled_client = TestClient(create_app())

    response = disabled_client.post(
        "/api/export/cases/approval",
        json={
            "source_id": "SCC_DECISIONS",
            "case_id": "scc-2024-3",
            "document_url": "https://decisions.scc-csc.ca/scc-csc/scc-csc/en/item/123/index.do",
            "user_approved": True,
        },
    )

    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "SOURCE_UNAVAILABLE"
    assert body["error"]["policy_reason"] == "case_search_disabled"
    assert response.headers["x-trace-id"] == body["error"]["trace_id"]


def test_create_app_fails_fast_when_case_assets_missing_in_hardened_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production-us-east")
    monkeypatch.setenv("IMMCAD_API_BEARER_TOKEN", "secret-token")
    monkeypatch.setenv("API_BEARER_TOKEN", "secret-token")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("ENABLE_SCAFFOLD_PROVIDER", "false")
    monkeypatch.setenv("ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS", "false")
    monkeypatch.setenv("CITATION_TRUSTED_DOMAINS", "laws-lois.justice.gc.ca,canlii.org")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    monkeypatch.setenv("GEMINI_MODEL_FALLBACKS", "gemini-2.5-flash")
    monkeypatch.setenv("ENABLE_CASE_SEARCH", "true")
    monkeypatch.setenv("ENABLE_OFFICIAL_CASE_SOURCES", "true")
    monkeypatch.setenv("EXPORT_POLICY_GATE_ENABLED", "true")

    def _missing_registry():
        raise FileNotFoundError("registry missing")

    monkeypatch.setattr("immcad_api.main.load_source_registry", _missing_registry)

    with pytest.raises(
        ValueError,
        match="Case-search assets are required in hardened environments",
    ):
        create_app()


def test_validation_error_uses_error_envelope() -> None:
    response = client.post(
        "/api/chat",
        json={
            "session_id": "short",
            "message": "",
        },
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["trace_id"]
    assert "x-trace-id" in response.headers


def test_chat_validation_error_for_unsupported_locale_and_mode() -> None:
    response = client.post(
        "/api/chat",
        json={
            "session_id": "session-123456",
            "message": "What are the eligibility pathways?",
            "locale": "en-US",
            "mode": "expert",
        },
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["trace_id"]
    assert "x-trace-id" in response.headers


def test_optional_bearer_auth_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IMMCAD_API_BEARER_TOKEN", "secret-token")
    monkeypatch.setenv("API_BEARER_TOKEN", "secret-token")
    secured_client = TestClient(create_app())

    unauthorized = secured_client.post(
        "/api/chat",
        json={
            "session_id": "session-123456",
            "message": "What is IRPA section 11 about?",
            "locale": "en-CA",
            "mode": "standard",
        },
    )
    assert unauthorized.status_code == 401
    unauthorized_body = unauthorized.json()
    assert unauthorized_body["error"]["code"] == "UNAUTHORIZED"
    assert unauthorized_body["error"]["trace_id"]
    assert unauthorized.headers["x-trace-id"] == unauthorized_body["error"]["trace_id"]

    authorized = secured_client.post(
        "/api/chat",
        headers={"Authorization": "Bearer secret-token"},
        json={
            "session_id": "session-123456",
            "message": "What is IRPA section 11 about?",
            "locale": "en-CA",
            "mode": "standard",
        },
    )
    assert authorized.status_code == 200


@pytest.mark.parametrize("environment", ["production", "prod", "ci"])
def test_bearer_auth_enforced_for_production_modes(
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", environment)
    monkeypatch.setenv("IMMCAD_API_BEARER_TOKEN", "secret-token")
    monkeypatch.setenv("API_BEARER_TOKEN", "secret-token")
    monkeypatch.setenv("ENABLE_SCAFFOLD_PROVIDER", "false")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    monkeypatch.setenv("GEMINI_MODEL_FALLBACKS", "gemini-2.5-flash")
    monkeypatch.setenv("CANLII_API_KEY", "test-canlii-key")
    monkeypatch.setenv("CITATION_TRUSTED_DOMAINS", "laws-lois.justice.gc.ca,canlii.org")
    monkeypatch.setenv("ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS", "false")
    secured_client = TestClient(create_app())

    unauthorized = secured_client.post(
        "/api/chat",
        json={
            "session_id": "session-123456",
            "message": "What is IRPA section 11 about?",
            "locale": "en-CA",
            "mode": "standard",
        },
    )

    assert unauthorized.status_code == 401
    body = unauthorized.json()
    assert body["error"]["code"] == "UNAUTHORIZED"
    assert body["error"]["trace_id"]
    assert unauthorized.headers["x-trace-id"] == body["error"]["trace_id"]


def test_provider_error_envelope_when_scaffold_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENABLE_SCAFFOLD_PROVIDER", "false")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    provider_error_client = TestClient(create_app())

    response = provider_error_client.post(
        "/api/chat",
        json={
            "session_id": "session-123456",
            "message": "Summarize IRPA section 11.",
            "locale": "en-CA",
            "mode": "standard",
        },
    )

    assert response.status_code == 502
    body = response.json()
    assert body["error"]["code"] == "PROVIDER_ERROR"
    assert body["error"]["trace_id"]


def test_transient_openai_failure_falls_back_to_gemini_with_timeout_reason(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENABLE_SCAFFOLD_PROVIDER", "false")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")

    openai_calls = {"count": 0}

    def flaky_openai_generate(
        self, *, message: str, citations, locale: str
    ) -> ProviderResult:
        del self, message, citations, locale
        openai_calls["count"] += 1
        if openai_calls["count"] == 1:
            raise ProviderError("openai", "timeout", "transient timeout")
        return ProviderResult(
            provider="openai",
            answer="Recovered primary response",
            citations=[
                {
                    "source_id": "IRPA_s11",
                    "title": "IRPA section 11",
                    "url": "https://laws-lois.justice.gc.ca/eng/acts/I-2.5/section-11.html",
                    "pin": "s.11",
                    "snippet": "A foreign national must apply before entering Canada.",
                }
            ],
            confidence="medium",
        )

    def gemini_fallback_generate(
        self, *, message: str, citations, locale: str
    ) -> ProviderResult:
        del self, message, citations, locale
        return ProviderResult(
            provider="gemini",
            answer="Fallback response",
            citations=[
                {
                    "source_id": "IRPA_s11",
                    "title": "IRPA section 11",
                    "url": "https://laws-lois.justice.gc.ca/eng/acts/I-2.5/section-11.html",
                    "pin": "s.11",
                    "snippet": "A foreign national must apply before entering Canada.",
                }
            ],
            confidence="medium",
        )

    monkeypatch.setattr(
        "immcad_api.main.OpenAIProvider.generate", flaky_openai_generate
    )
    monkeypatch.setattr(
        "immcad_api.main.GeminiProvider.generate", gemini_fallback_generate
    )

    transient_client = TestClient(create_app())
    first = transient_client.post(
        "/api/chat",
        json={
            "session_id": "session-123456",
            "message": "Summarize IRPA section 11.",
            "locale": "en-CA",
            "mode": "standard",
        },
    )
    second = transient_client.post(
        "/api/chat",
        json={
            "session_id": "session-123456",
            "message": "Summarize IRPA section 11.",
            "locale": "en-CA",
            "mode": "standard",
        },
    )

    assert first.status_code == 200
    assert first.headers["x-trace-id"]
    first_body = first.json()
    assert first_body["fallback_used"]["used"] is True
    assert first_body["fallback_used"]["provider"] == "gemini"
    assert first_body["fallback_used"]["reason"] == "timeout"

    assert second.status_code == 200
    second_body = second.json()
    assert second_body["fallback_used"]["used"] is False
    assert second_body["fallback_used"]["provider"] is None
    assert second_body["fallback_used"]["reason"] is None


def test_curated_grounded_response_when_synthetic_citations_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENABLE_OPENAI_PROVIDER", "false")
    monkeypatch.setenv("PRIMARY_PROVIDER", "scaffold")
    monkeypatch.setenv("ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS", "false")
    constrained_client = TestClient(create_app())

    response = constrained_client.post(
        "/api/chat",
        json={
            "session_id": "session-123456",
            "message": "What are the basic PR eligibility pathways?",
            "locale": "en-CA",
            "mode": "standard",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"].startswith("Scaffold response:")
    assert len(body["citations"]) >= 1
    assert body["confidence"] == "medium"
    assert body["disclaimer"] == DISCLAIMER_TEXT


def test_safe_constrained_response_when_trusted_domain_allowlist_excludes_grounding_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CITATION_TRUSTED_DOMAINS", "canlii.org")
    allowlist_client = TestClient(create_app())

    response = allowlist_client.post(
        "/api/chat",
        json={
            "session_id": "session-123456",
            "message": "What are the basic PR eligibility pathways?",
            "locale": "en-CA",
            "mode": "standard",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["citations"] == []
    assert body["confidence"] == "low"
    assert body["answer"].startswith("I do not have enough grounded legal context")
    assert body["disclaimer"] == DISCLAIMER_TEXT


def test_rate_limit_envelope(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_RATE_LIMIT_PER_MINUTE", "1")
    throttled_client = TestClient(create_app())

    first = throttled_client.post(
        "/api/chat",
        json={
            "session_id": "session-123456",
            "message": "Explain PR pathways in brief.",
            "locale": "en-CA",
            "mode": "standard",
        },
    )
    second = throttled_client.post(
        "/api/chat",
        json={
            "session_id": "session-123456",
            "message": "Explain PR pathways in brief.",
            "locale": "en-CA",
            "mode": "standard",
        },
    )

    assert first.status_code == 200
    assert second.status_code == 429
    body = second.json()
    assert body["error"]["code"] == "RATE_LIMITED"
    assert body["error"]["trace_id"]
    assert second.headers["x-trace-id"] == body["error"]["trace_id"]


def test_rate_limit_client_id_resolution_failure_returns_validation_envelope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def no_client_id(*_args, **_kwargs):
        return None

    monkeypatch.setattr("immcad_api.main._resolve_rate_limit_client_id", no_client_id)
    validation_client = TestClient(create_app())

    response = validation_client.post(
        "/api/chat",
        json={
            "session_id": "session-123456",
            "message": "Explain PR pathways in brief.",
            "locale": "en-CA",
            "mode": "standard",
        },
    )

    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert (
        body["error"]["message"]
        == "Unable to determine client identifier for rate limiting"
    )
    assert body["error"]["trace_id"]
    assert response.headers["x-trace-id"] == body["error"]["trace_id"]


def test_rate_limit_client_id_uses_cloudflare_connecting_ip_when_direct_host_missing() -> None:
    from immcad_api.main import _resolve_rate_limit_client_id

    class _Request:
        client = None
        headers = {"cf-connecting-ip": "203.0.113.10"}

    assert _resolve_rate_limit_client_id(_Request()) == "203.0.113.10"


def test_rate_limit_client_id_falls_back_to_host_header_when_proxy_headers_missing() -> None:
    from immcad_api.main import _resolve_rate_limit_client_id

    class _Request:
        client = None
        headers = {"host": "api.immcad.example"}

    assert _resolve_rate_limit_client_id(_Request()) == "host:api.immcad.example"


@pytest.mark.parametrize("environment", ["production", "prod", "ci"])
def test_case_search_returns_source_unavailable_envelope_in_hardened_modes_when_canlii_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
) -> None:
    def unavailable_case_search(*_args, **_kwargs):
        raise SourceUnavailableError(
            "Case-law source is currently unavailable. Please retry later."
        )

    monkeypatch.setattr(
        "immcad_api.sources.canlii_client.CanLIIClient.search_cases",
        unavailable_case_search,
    )
    monkeypatch.setenv("ENVIRONMENT", environment)
    monkeypatch.setenv("IMMCAD_API_BEARER_TOKEN", "secret-token")
    monkeypatch.setenv("API_BEARER_TOKEN", "secret-token")
    monkeypatch.setenv("ENABLE_SCAFFOLD_PROVIDER", "false")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    monkeypatch.setenv("GEMINI_MODEL_FALLBACKS", "gemini-2.5-flash")
    monkeypatch.setenv("CANLII_API_KEY", "test-canlii-key")
    monkeypatch.setenv("CITATION_TRUSTED_DOMAINS", "laws-lois.justice.gc.ca,canlii.org")
    monkeypatch.setenv("ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS", "false")
    monkeypatch.setenv("ENABLE_OFFICIAL_CASE_SOURCES", "false")
    hardened_client = TestClient(create_app())

    response = hardened_client.post(
        "/api/search/cases",
        headers={"Authorization": "Bearer secret-token"},
        json={
            "query": "express entry inadmissibility",
            "jurisdiction": "ca",
            "court": "fct",
            "limit": 2,
        },
    )

    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "SOURCE_UNAVAILABLE"
    assert body["error"]["trace_id"]
    assert response.headers["x-trace-id"] == body["error"]["trace_id"]


@pytest.mark.parametrize("environment", ["production-us-east", "prod_blue", "ci-smoke"])
def test_case_search_disables_canlii_scaffold_fallback_for_hardened_environment_aliases(
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
) -> None:
    class _FailingCanLIIHttpClient:
        def __init__(self, *args, **kwargs) -> None:
            del args, kwargs

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            del exc_type, exc, tb
            return False

        def get(self, *args, **kwargs):
            del args, kwargs
            raise RuntimeError("canlii unavailable")

    monkeypatch.setattr(
        "immcad_api.sources.canlii_client.httpx.Client",
        _FailingCanLIIHttpClient,
    )
    monkeypatch.setenv("ENVIRONMENT", environment)
    monkeypatch.setenv("IMMCAD_API_BEARER_TOKEN", "secret-token")
    monkeypatch.setenv("API_BEARER_TOKEN", "secret-token")
    monkeypatch.setenv("ENABLE_SCAFFOLD_PROVIDER", "false")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    monkeypatch.setenv("GEMINI_MODEL_FALLBACKS", "gemini-2.5-flash")
    monkeypatch.setenv("CANLII_API_KEY", "test-canlii-key")
    monkeypatch.setenv("CITATION_TRUSTED_DOMAINS", "laws-lois.justice.gc.ca,canlii.org")
    monkeypatch.setenv("ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS", "false")
    monkeypatch.setenv("ENABLE_OFFICIAL_CASE_SOURCES", "false")
    hardened_alias_client = TestClient(create_app())

    response = hardened_alias_client.post(
        "/api/search/cases",
        headers={"Authorization": "Bearer secret-token"},
        json={
            "query": "express entry inadmissibility",
            "jurisdiction": "ca",
            "court": "fct",
            "limit": 2,
        },
    )

    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "SOURCE_UNAVAILABLE"
    assert body["error"]["trace_id"]
    assert response.headers["x-trace-id"] == body["error"]["trace_id"]


@pytest.mark.parametrize("environment", ["production", "prod", "ci"])
def test_case_search_uses_official_sources_without_canlii_key(
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
) -> None:
    from datetime import date

    from immcad_api.schemas import CaseSearchResponse, CaseSearchResult

    def official_search(self, request):
        del self, request
        return CaseSearchResponse(
            results=[
                CaseSearchResult(
                    case_id="2026-FC-101",
                    title="Example v Canada (Citizenship and Immigration)",
                    citation="2026 FC 101",
                    decision_date=date(2026, 2, 1),
                    url="https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/item/123456/index.do",
                    source_id="FC_DECISIONS",
                    document_url="https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/item/123456/index.do",
                )
            ]
        )

    monkeypatch.setattr(
        "immcad_api.sources.official_case_law_client.OfficialCaseLawClient.search_cases",
        official_search,
    )
    monkeypatch.setenv("ENVIRONMENT", environment)
    monkeypatch.setenv("IMMCAD_API_BEARER_TOKEN", "secret-token")
    monkeypatch.setenv("API_BEARER_TOKEN", "secret-token")
    monkeypatch.setenv("ENABLE_SCAFFOLD_PROVIDER", "false")
    monkeypatch.setenv("ENABLE_OFFICIAL_CASE_SOURCES", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    monkeypatch.setenv("GEMINI_MODEL_FALLBACKS", "gemini-2.5-flash")
    monkeypatch.delenv("CANLII_API_KEY", raising=False)
    monkeypatch.setenv("CITATION_TRUSTED_DOMAINS", "laws-lois.justice.gc.ca,canlii.org")
    monkeypatch.setenv("ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS", "false")
    client = TestClient(create_app())

    response = client.post(
        "/api/search/cases",
        headers={"Authorization": "Bearer secret-token"},
        json={
            "query": "citizenship",
            "jurisdiction": "ca",
            "court": "fc",
            "limit": 2,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["results"]
    assert body["results"][0]["export_allowed"] is True
    assert body["results"][0]["export_policy_reason"] == "source_export_allowed"


def test_case_search_official_only_mode_filters_non_exportable_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("IMMCAD_API_BEARER_TOKEN", raising=False)
    monkeypatch.delenv("API_BEARER_TOKEN", raising=False)
    monkeypatch.setenv("CASE_SEARCH_OFFICIAL_ONLY_RESULTS", "true")
    monkeypatch.setenv("ENABLE_OFFICIAL_CASE_SOURCES", "false")
    monkeypatch.delenv("CANLII_API_KEY", raising=False)
    client = TestClient(create_app())

    response = client.post(
        "/api/search/cases",
        json={
            "query": "citizenship",
            "jurisdiction": "ca",
            "court": "fc",
            "limit": 5,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["results"] == []


def test_ops_metrics_endpoint_exposes_observability_baseline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IMMCAD_API_BEARER_TOKEN", "secret-token")
    monkeypatch.setenv("API_BEARER_TOKEN", "secret-token")
    metrics_client = TestClient(create_app())
    auth_headers = {"Authorization": "Bearer secret-token"}

    ok_response = metrics_client.post(
        "/api/chat",
        headers=auth_headers,
        json={
            "session_id": "session-123456",
            "message": "Summarize IRPA section 11.",
            "locale": "en-CA",
            "mode": "standard",
        },
    )
    refusal_response = metrics_client.post(
        "/api/chat",
        headers=auth_headers,
        json={
            "session_id": "session-123456",
            "message": "Please represent me and file my application",
            "locale": "en-CA",
            "mode": "standard",
        },
    )
    validation_error_response = metrics_client.post(
        "/api/chat",
        headers=auth_headers,
        json={"session_id": "short", "message": ""},
    )
    lawyer_research_response = metrics_client.post(
        "/api/research/lawyer-cases",
        headers=auth_headers,
        json={
            "session_id": "session-123456",
            "matter_summary": "Federal Court appeal on procedural fairness and inadmissibility",
            "jurisdiction": "ca",
            "court": "fc",
            "limit": 3,
        },
    )
    metrics = metrics_client.get("/ops/metrics", headers=auth_headers)

    assert ok_response.status_code == 200
    assert refusal_response.status_code == 200
    assert validation_error_response.status_code == 422
    assert lawyer_research_response.status_code in {200, 503}
    assert metrics.status_code == 200

    payload = metrics.json()
    request_metrics = payload["request_metrics"]

    assert request_metrics["requests"]["total"] >= 3
    assert request_metrics["requests"]["rate_per_minute"] > 0
    assert request_metrics["errors"]["total"] >= 1
    assert request_metrics["refusal"]["total"] >= 1
    assert "fallback" in request_metrics
    assert "export" in request_metrics
    assert "lawyer_research" in request_metrics
    assert "audit_recent" in request_metrics["export"]
    assert request_metrics["lawyer_research"]["requests"] >= 1
    assert request_metrics["lawyer_research"]["cases_per_request"] >= 0
    assert request_metrics["latency_ms"]["sample_count"] >= 3
    assert request_metrics["latency_ms"]["p50"] >= 0
    assert request_metrics["latency_ms"]["p95"] >= request_metrics["latency_ms"]["p50"]
    assert "provider_routing_metrics" in payload
    assert "canlii_usage_metrics" in payload


def test_ops_metrics_requires_auth_when_bearer_token_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IMMCAD_API_BEARER_TOKEN", "secret-token")
    monkeypatch.setenv("API_BEARER_TOKEN", "secret-token")
    secured_client = TestClient(create_app())

    unauthorized = secured_client.get("/ops/metrics")
    assert unauthorized.status_code == 401
    unauthorized_body = unauthorized.json()
    assert unauthorized_body["error"]["code"] == "UNAUTHORIZED"
    assert unauthorized_body["error"]["trace_id"]
    assert unauthorized.headers["x-trace-id"] == unauthorized_body["error"]["trace_id"]

    authorized = secured_client.get(
        "/ops/metrics",
        headers={"Authorization": "Bearer secret-token"},
    )
    assert authorized.status_code == 200


def test_ops_metrics_requires_bearer_token_configuration_when_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("IMMCAD_API_BEARER_TOKEN", raising=False)
    monkeypatch.delenv("API_BEARER_TOKEN", raising=False)
    open_client = TestClient(create_app())

    response = open_client.get("/ops/metrics")

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "UNAUTHORIZED"
    assert body["error"]["trace_id"]
    assert response.headers["x-trace-id"] == body["error"]["trace_id"]
