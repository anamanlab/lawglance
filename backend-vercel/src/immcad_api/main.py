from __future__ import annotations

import ipaddress
import logging
import secrets
import time

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from immcad_api.errors import AuthError, ProviderApiError
from immcad_api.api.routes import (
    build_case_router,
    build_case_router_disabled,
    build_chat_router,
)
from immcad_api.middleware.rate_limit import build_rate_limiter
from immcad_api.policy import load_source_policy
from immcad_api.providers import GeminiProvider, OpenAIProvider, ProviderRouter, ScaffoldProvider
from immcad_api.schemas import ErrorEnvelope
from immcad_api.services import (
    CaseSearchService,
    ChatService,
    KeywordGroundingAdapter,
    StaticGroundingAdapter,
    official_grounding_catalog,
    scaffold_grounded_citations,
)
from immcad_api.settings import load_settings
from immcad_api.sources import CanLIIClient, OfficialCaseLawClient, load_source_registry
from immcad_api.sources.canlii_usage_limiter import build_canlii_usage_limiter
from immcad_api.telemetry import ProviderMetrics, RequestMetrics, generate_trace_id

LOGGER = logging.getLogger(__name__)


def _parse_ip(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return str(ipaddress.ip_address(value.strip()))
    except ValueError:
        return None


def _sanitize_client_host(value: str | None) -> str | None:
    if not value:
        return None
    trimmed = value.strip().lower()
    if not trimmed or len(trimmed) > 128:
        return None
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789-._:")
    if any(char not in allowed for char in trimmed):
        return None
    return f"host:{trimmed}"


def _trusted_forwarded_client_id(request: Request) -> str | None:
    x_real_ip = _parse_ip(request.headers.get("x-real-ip"))
    x_forwarded_for = request.headers.get("x-forwarded-for", "")
    forwarded_first = _parse_ip(x_forwarded_for.split(",")[0].strip()) if x_forwarded_for else None

    if x_real_ip and forwarded_first and x_real_ip == forwarded_first:
        return x_real_ip
    if x_real_ip and not forwarded_first:
        return x_real_ip
    return None


def _resolve_rate_limit_client_id(request: Request) -> str | None:
    direct_host = request.client.host if request.client else None
    direct_ip = _parse_ip(direct_host)
    if direct_ip:
        parsed_direct = ipaddress.ip_address(direct_ip)
        # Only trust forwarded headers when the direct source is a trusted proxy hop.
        if parsed_direct.is_private or parsed_direct.is_loopback or parsed_direct.is_link_local:
            forwarded_ip = _trusted_forwarded_client_id(request)
            if forwarded_ip:
                return forwarded_ip
        return direct_ip
    direct_host_id = _sanitize_client_host(direct_host)
    if direct_host_id:
        return direct_host_id
    return _trusted_forwarded_client_id(request)


def create_app() -> FastAPI:
    settings = load_settings()

    provider_registry = {
        "openai": OpenAIProvider(
            settings.openai_api_key,
            model=settings.openai_model,
            timeout_seconds=settings.provider_timeout_seconds,
            max_retries=settings.provider_max_retries,
        ),
        "gemini": GeminiProvider(
            settings.gemini_api_key,
            model=settings.gemini_model,
            fallback_models=settings.gemini_model_fallbacks,
            timeout_seconds=settings.provider_timeout_seconds,
            max_retries=settings.provider_max_retries,
        ),
    }

    providers = []
    if settings.enable_openai_provider:
        providers.append(provider_registry["openai"])
    providers.append(provider_registry["gemini"])
    if settings.enable_scaffold_provider:
        providers.append(ScaffoldProvider())
    if not providers:
        raise ValueError(
            "At least one provider must be enabled. Configure PRIMARY_PROVIDER and provider flags."
        )

    provider_names = [provider.name for provider in providers]
    if settings.primary_provider in provider_names:
        primary_provider_name = settings.primary_provider
    else:
        primary_provider_name = provider_names[0]

    if providers[0].name != primary_provider_name:
        reordered = [provider for provider in providers if provider.name == primary_provider_name]
        reordered.extend(provider for provider in providers if provider.name != primary_provider_name)
        providers = reordered

    provider_router = ProviderRouter(
        providers=providers,
        primary_provider_name=primary_provider_name,
        circuit_breaker_failure_threshold=settings.provider_circuit_breaker_failure_threshold,
        circuit_breaker_open_seconds=settings.provider_circuit_breaker_open_seconds,
        telemetry=ProviderMetrics(),
    )

    if settings.allow_scaffold_synthetic_citations:
        grounding_adapter = StaticGroundingAdapter(scaffold_grounded_citations())
    else:
        grounding_adapter = KeywordGroundingAdapter(official_grounding_catalog())
    chat_service = ChatService(
        provider_router,
        grounding_adapter=grounding_adapter,
        trusted_citation_domains=settings.citation_trusted_domains,
    )
    case_search_service: CaseSearchService | None = None
    canlii_usage_limiter = None
    source_policy = None
    source_registry = None
    if settings.enable_case_search:
        try:
            source_registry = load_source_registry()
            source_policy = load_source_policy()
        except FileNotFoundError as exc:
            LOGGER.warning(
                "Case-search assets missing; disabling case-search routes",
                exc_info=exc,
            )
        else:
            allow_canlii_scaffold_fallback = settings.environment.lower() not in {
                "production",
                "prod",
                "ci",
            }
            canlii_usage_limiter = build_canlii_usage_limiter(
                redis_url=settings.redis_url,
                lock_ttl_seconds=max(settings.provider_timeout_seconds + 2.0, 6.0),
            )
            case_search_service = CaseSearchService(
                canlii_client=CanLIIClient(
                    api_key=settings.canlii_api_key,
                    base_url=settings.canlii_base_url,
                    allow_scaffold_fallback=allow_canlii_scaffold_fallback,
                    usage_limiter=canlii_usage_limiter,
                ),
                official_client=OfficialCaseLawClient(source_registry=source_registry)
                if settings.enable_official_case_sources
                else None,
            )

    has_api_bearer_token = bool(settings.api_bearer_token)

    app = FastAPI(title=settings.app_name, version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_allowed_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept"],
        expose_headers=["x-trace-id"],
        max_age=600,
    )
    request_metrics = RequestMetrics()
    rate_limiter = build_rate_limiter(
        limit_per_minute=settings.api_rate_limit_per_minute,
        redis_url=settings.redis_url,
    )

    @app.middleware("http")
    async def trace_middleware(request: Request, call_next):
        request.state.trace_id = generate_trace_id()
        start_time = time.perf_counter()
        status_code = 500
        request_path = request.url.path
        is_api_request = request_path.startswith("/api")
        is_ops_request = request_path.startswith("/ops")
        requires_bearer_auth = is_ops_request or (is_api_request and has_api_bearer_token)
        try:
            if requires_bearer_auth:
                if is_ops_request and not has_api_bearer_token:
                    error = ErrorEnvelope(
                        error={
                            "code": "UNAUTHORIZED",
                            "message": "API_BEARER_TOKEN must be configured to access ops endpoints",
                            "trace_id": request.state.trace_id,
                        }
                    )
                    status_code = 401
                    return JSONResponse(
                        status_code=status_code,
                        content=error.model_dump(),
                        headers={"x-trace-id": request.state.trace_id},
                    )
                auth_header = request.headers.get("authorization", "")
                expected = f"Bearer {settings.api_bearer_token}"
                if not secrets.compare_digest(auth_header, expected):
                    error = ErrorEnvelope(
                        error={
                            "code": "UNAUTHORIZED",
                            "message": "Missing or invalid bearer token",
                            "trace_id": request.state.trace_id,
                        }
                    )
                    status_code = 401
                    return JSONResponse(
                        status_code=status_code,
                        content=error.model_dump(),
                        headers={"x-trace-id": request.state.trace_id},
                    )

            if is_api_request:
                client_id = _resolve_rate_limit_client_id(request)
                if not client_id:
                    error = ErrorEnvelope(
                        error={
                            "code": "VALIDATION_ERROR",
                            "message": "Unable to determine client identifier for rate limiting",
                            "trace_id": request.state.trace_id,
                        }
                    )
                    status_code = 400
                    return JSONResponse(
                        status_code=status_code,
                        content=error.model_dump(),
                        headers={"x-trace-id": request.state.trace_id},
                    )

                allowed = rate_limiter.allow(client_id)
                if not allowed:
                    error = ErrorEnvelope(
                        error={
                            "code": "RATE_LIMITED",
                            "message": "Request rate exceeded allowed threshold",
                            "trace_id": request.state.trace_id,
                        }
                    )
                    status_code = 429
                    return JSONResponse(
                        status_code=status_code,
                        content=error.model_dump(),
                        headers={"x-trace-id": request.state.trace_id},
                    )

            response = await call_next(request)
            status_code = response.status_code
            response.headers["x-trace-id"] = request.state.trace_id
            return response
        finally:
            if is_api_request:
                request_metrics.record_api_response(
                    status_code=status_code,
                    duration_seconds=time.perf_counter() - start_time,
                )

    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
        trace_id = getattr(request.state, "trace_id", generate_trace_id())
        payload = ErrorEnvelope(
            error={
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "trace_id": trace_id,
            }
        )
        return JSONResponse(
            status_code=422,
            content=payload.model_dump(),
            headers={"x-trace-id": trace_id},
        )

    @app.exception_handler(AuthError)
    async def auth_exception_handler(request: Request, exc: AuthError):
        trace_id = getattr(request.state, "trace_id", generate_trace_id())
        payload = ErrorEnvelope(
            error={"code": "UNAUTHORIZED", "message": exc.message, "trace_id": trace_id}
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=payload.model_dump(),
            headers={"x-trace-id": trace_id},
        )

    @app.exception_handler(ProviderApiError)
    async def provider_exception_handler(request: Request, exc: ProviderApiError):
        trace_id = getattr(request.state, "trace_id", generate_trace_id())
        payload = ErrorEnvelope(error={"code": exc.code, "message": exc.message, "trace_id": trace_id})
        return JSONResponse(
            status_code=exc.status_code,
            content=payload.model_dump(),
            headers={"x-trace-id": trace_id},
        )

    app.include_router(build_chat_router(chat_service, request_metrics=request_metrics))
    if case_search_service and source_policy and source_registry:
        app.include_router(
            build_case_router(
                case_search_service,
                source_policy=source_policy,
                source_registry=source_registry,
                request_metrics=request_metrics,
                export_policy_gate_enabled=settings.export_policy_gate_enabled,
                export_max_download_bytes=settings.export_max_download_bytes,
            )
        )
    else:
        app.include_router(
            build_case_router_disabled(policy_reason="case_search_disabled")
        )

    @app.get("/healthz", tags=["health"])
    def healthz() -> dict[str, str]:
        return {"status": "ok", "service": settings.app_name}

    @app.get("/ops/metrics", tags=["ops"])
    def ops_metrics() -> dict[str, object]:
        canlii_metrics_snapshot = (
            canlii_usage_limiter.snapshot()
            if canlii_usage_limiter and hasattr(canlii_usage_limiter, "snapshot")
            else {}
        )
        return {
            "request_metrics": request_metrics.snapshot(),
            "provider_routing_metrics": provider_router.telemetry_snapshot(),
            "canlii_usage_metrics": canlii_metrics_snapshot,
        }

    return app


app = create_app()
