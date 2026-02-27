from __future__ import annotations

import ipaddress
import json
import logging
import os
import secrets
import time
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from immcad_api.errors import AuthError, ProviderApiError
from immcad_api.api.routes import (
    build_case_router,
    build_case_router_disabled,
    build_chat_router,
    build_documents_router,
    build_lawyer_research_router,
    build_lawyer_research_router_disabled,
    build_source_transparency_router,
)
from immcad_api.api.routes.source_transparency import (
    build_source_transparency_payload,
)
from immcad_api.middleware.rate_limit import build_rate_limiter
from immcad_api.policy import load_source_policy
from immcad_api.providers import (
    GeminiProvider,
    OpenAIProvider,
    ProviderRouter,
    ScaffoldProvider,
)
from immcad_api.schemas import ErrorEnvelope
from immcad_api.services import (
    CaseSearchService,
    ChatService,
    InMemoryDocumentMatterStore,
    KeywordGroundingAdapter,
    LawyerCaseResearchService,
    RedisDocumentMatterStore,
    StaticGroundingAdapter,
    build_document_matter_store,
    official_grounding_catalog,
    scaffold_grounded_citations,
)
from immcad_api.settings import is_hardened_environment, load_settings
from immcad_api.sources import CanLIIClient, OfficialCaseLawClient, load_source_registry
from immcad_api.sources.canlii_usage_limiter import build_canlii_usage_limiter
from immcad_api.sources.priority_sources import (
    PRIORITY_CASELAW_SOURCE_IDS,
    build_priority_source_status_snapshot,
)
from immcad_api.telemetry import ProviderMetrics, RequestMetrics, generate_trace_id

LOGGER = logging.getLogger(__name__)
_DEFAULT_INGESTION_CHECKPOINT_STATE_PATH = ".cache/immcad/ingestion-checkpoints.json"


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
    forwarded_first = (
        _parse_ip(x_forwarded_for.split(",")[0].strip()) if x_forwarded_for else None
    )

    if x_real_ip and forwarded_first and x_real_ip == forwarded_first:
        return x_real_ip
    if x_real_ip and not forwarded_first:
        return x_real_ip
    return None


def _cloudflare_proxy_client_id(request: Request) -> str | None:
    # Cloudflare forwards the original client address via canonical headers.
    cf_connecting_ip = _parse_ip(request.headers.get("cf-connecting-ip"))
    if cf_connecting_ip:
        return cf_connecting_ip
    return _parse_ip(request.headers.get("true-client-ip"))


def _resolve_rate_limit_client_id(request: Request) -> str | None:
    direct_host = request.client.host if request.client else None
    direct_ip = _parse_ip(direct_host)
    if direct_ip:
        parsed_direct = ipaddress.ip_address(direct_ip)
        # Only trust forwarded headers when the direct source is a trusted proxy hop.
        if (
            parsed_direct.is_private
            or parsed_direct.is_loopback
            or parsed_direct.is_link_local
        ):
            forwarded_ip = _trusted_forwarded_client_id(request)
            if forwarded_ip:
                return forwarded_ip
        return direct_ip
    direct_host_id = _sanitize_client_host(direct_host)
    if direct_host_id:
        return direct_host_id
    trusted_forwarded_id = _trusted_forwarded_client_id(request)
    if trusted_forwarded_id:
        return trusted_forwarded_id

    cloudflare_client_id = _cloudflare_proxy_client_id(request)
    if cloudflare_client_id:
        return cloudflare_client_id

    # Final fallback when request.client is unavailable (common in worker shims).
    return _sanitize_client_host(request.headers.get("host"))


def _extract_forwarded_proto(value: str | None) -> str | None:
    if not value:
        return None
    first_value = value.split(",", 1)[0].strip().lower()
    return first_value or None


def _request_has_https_scheme(request: Request) -> bool:
    if str(request.url.scheme or "").strip().lower() == "https":
        return True
    for header_name in ("x-forwarded-proto", "x-forwarded-protocol"):
        forwarded_proto = _extract_forwarded_proto(request.headers.get(header_name))
        if forwarded_proto == "https":
            return True
    cf_visitor = request.headers.get("cf-visitor")
    if cf_visitor:
        try:
            visitor_payload = json.loads(cf_visitor)
        except json.JSONDecodeError:
            visitor_payload = None
        if isinstance(visitor_payload, dict):
            visitor_scheme = str(visitor_payload.get("scheme", "")).strip().lower()
            if visitor_scheme == "https":
                return True
    return False


def _resolve_ingestion_checkpoint_state_path() -> str:
    override = os.getenv("INGESTION_CHECKPOINT_STATE_PATH", "").strip()
    if override:
        return override
    return _DEFAULT_INGESTION_CHECKPOINT_STATE_PATH


def _build_priority_source_freshness_snapshot(
    *,
    source_registry,
    source_policy,
    checkpoint_state_path: str,
) -> dict[str, Any]:
    if source_registry is None or source_policy is None:
        return {
            "checkpoint_path": checkpoint_state_path,
            "available": False,
            "priority_sources": {},
            "status_counts": {},
        }

    try:
        transparency = build_source_transparency_payload(
            source_registry=source_registry,
            source_policy=source_policy,
            checkpoint_state_path=checkpoint_state_path,
        )
    except Exception:
        return {
            "checkpoint_path": checkpoint_state_path,
            "available": False,
            "priority_sources": {},
            "status_counts": {},
        }

    source_items = {
        item.source_id: item for item in transparency.case_law_sources
    }
    priority_sources: dict[str, dict[str, Any]] = {}
    status_counts: dict[str, int] = {}
    for source_id in PRIORITY_CASELAW_SOURCE_IDS:
        source_item = source_items.get(source_id)
        if source_item is None:
            priority_sources[source_id] = {
                "source_id": source_id,
                "court": None,
                "freshness_status": "missing",
                "freshness_seconds": None,
                "last_success_at": None,
                "last_http_status": None,
            }
            status_counts["missing"] = status_counts.get("missing", 0) + 1
            continue
        source_snapshot = {
            "source_id": source_id,
            "court": source_item.court,
            "freshness_status": source_item.freshness_status,
            "freshness_seconds": source_item.freshness_seconds,
            "last_success_at": source_item.last_success_at,
            "last_http_status": source_item.last_http_status,
        }
        priority_sources[source_id] = source_snapshot
        status_key = source_item.freshness_status
        status_counts[status_key] = status_counts.get(status_key, 0) + 1

    return {
        "checkpoint_path": checkpoint_state_path,
        "available": True,
        "priority_sources": priority_sources,
        "status_counts": status_counts,
    }


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
        reordered = [
            provider for provider in providers if provider.name == primary_provider_name
        ]
        reordered.extend(
            provider for provider in providers if provider.name != primary_provider_name
        )
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
    hardened_environment = is_hardened_environment(settings.environment)
    case_search_service: CaseSearchService | None = None
    lawyer_case_research_service: LawyerCaseResearchService | None = None
    source_transparency_state_path = _resolve_ingestion_checkpoint_state_path()
    canlii_usage_limiter = None
    source_policy = None
    source_registry = None
    if settings.enable_case_search:
        try:
            source_registry = load_source_registry()
            source_policy = load_source_policy()
        except FileNotFoundError as exc:
            if hardened_environment:
                raise ValueError(
                    "Case-search assets are required in hardened environments; missing source registry or source policy files"
                ) from exc
            LOGGER.warning(
                "Case-search assets missing; disabling case-search routes",
                exc_info=exc,
            )
        else:
            allow_canlii_scaffold_fallback = not hardened_environment
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
                official_client=OfficialCaseLawClient(
                    source_registry=source_registry,
                    cache_ttl_seconds=settings.official_case_cache_ttl_seconds,
                    stale_cache_ttl_seconds=settings.official_case_stale_cache_ttl_seconds,
                )
                if settings.enable_official_case_sources
                else None,
            )
            lawyer_case_research_service = LawyerCaseResearchService(
                case_search_service=case_search_service,
                source_policy=source_policy,
                source_registry=source_registry,
                priority_source_status_provider=lambda: build_priority_source_status_snapshot(
                    source_registry=source_registry,
                    source_policy=source_policy,
                    checkpoint_state_path=source_transparency_state_path,
                ),
            )

    source_registry_for_transparency = source_registry
    source_policy_for_transparency = source_policy
    if (
        source_registry_for_transparency is None
        or source_policy_for_transparency is None
    ):
        try:
            source_registry_for_transparency = load_source_registry()
            source_policy_for_transparency = load_source_policy()
        except FileNotFoundError:
            source_registry_for_transparency = None
            source_policy_for_transparency = None

    chat_service = ChatService(
        provider_router,
        grounding_adapter=grounding_adapter,
        trusted_citation_domains=settings.citation_trusted_domains,
        source_policy=source_policy,
        case_search_tool=case_search_service,
        lawyer_research_service=lawyer_case_research_service,
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
    document_matter_store = build_document_matter_store(redis_url=settings.redis_url)
    if isinstance(document_matter_store, RedisDocumentMatterStore):
        document_matter_store_backend = "redis"
    elif isinstance(document_matter_store, InMemoryDocumentMatterStore):
        document_matter_store_backend = "in_memory"
    else:
        document_matter_store_backend = "unknown"
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
        is_document_api_request = request_path.startswith("/api/documents")
        requires_bearer_auth = is_ops_request or (
            is_api_request and has_api_bearer_token
        )
        try:
            if requires_bearer_auth:
                if is_ops_request and not has_api_bearer_token:
                    error = ErrorEnvelope(
                        error={
                            "code": "UNAUTHORIZED",
                            "message": "IMMCAD_API_BEARER_TOKEN must be configured to access ops endpoints (API_BEARER_TOKEN is supported as a compatibility alias)",
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
            if (
                is_document_api_request
                and settings.document_require_https
                and not _request_has_https_scheme(request)
            ):
                error = ErrorEnvelope(
                    error={
                        "code": "VALIDATION_ERROR",
                        "message": "HTTPS is required for document upload and retrieval endpoints",
                        "trace_id": request.state.trace_id,
                        "policy_reason": "document_https_required",
                    }
                )
                status_code = 400
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
                request.state.client_id = client_id

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
    async def request_validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
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
        payload = ErrorEnvelope(
            error={"code": exc.code, "message": exc.message, "trace_id": trace_id}
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=payload.model_dump(),
            headers={"x-trace-id": trace_id},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        trace_id = getattr(request.state, "trace_id", generate_trace_id())
        LOGGER.exception("Unhandled API exception", exc_info=exc)
        message = "Unexpected server error"
        if not is_hardened_environment(settings.environment):
            message = str(exc) or message
        payload = ErrorEnvelope(
            error={
                "code": "PROVIDER_ERROR",
                "message": message,
                "trace_id": trace_id,
            }
        )
        return JSONResponse(
            status_code=500,
            content=payload.model_dump(),
            headers={"x-trace-id": trace_id},
        )

    app.include_router(build_chat_router(chat_service, request_metrics=request_metrics))
    app.include_router(
        build_documents_router(
            request_metrics=request_metrics,
            matter_store=document_matter_store,
            upload_max_bytes=settings.document_upload_max_bytes,
            upload_max_files=settings.document_upload_max_files,
            allowed_content_types=settings.document_allowed_content_types,
        )
    )
    app.include_router(
        build_source_transparency_router(
            source_registry=source_registry_for_transparency,
            source_policy=source_policy_for_transparency,
            checkpoint_state_path=source_transparency_state_path,
        )
    )
    if case_search_service and source_policy and source_registry:
        app.include_router(
            build_case_router(
                case_search_service,
                source_policy=source_policy,
                source_registry=source_registry,
                request_metrics=request_metrics,
                export_policy_gate_enabled=settings.export_policy_gate_enabled,
                export_max_download_bytes=settings.export_max_download_bytes,
                case_search_official_only_results=settings.case_search_official_only_results,
                export_approval_token_secret=settings.api_bearer_token
                or "dev-export-approval-secret",
                require_signed_export_approval=True,
            )
        )
    else:
        app.include_router(
            build_case_router_disabled(policy_reason="case_search_disabled")
        )
    if lawyer_case_research_service:
        app.include_router(
            build_lawyer_research_router(
                lawyer_case_research_service,
                request_metrics=request_metrics,
            )
        )
    else:
        app.include_router(
            build_lawyer_research_router_disabled(policy_reason="case_search_disabled")
        )

    @app.get("/healthz", tags=["health"])
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "service": settings.app_name}

    @app.get("/ops/metrics", tags=["ops"])
    async def ops_metrics() -> dict[str, object]:
        canlii_metrics_snapshot = (
            canlii_usage_limiter.snapshot()
            if canlii_usage_limiter and hasattr(canlii_usage_limiter, "snapshot")
            else {}
        )
        priority_source_freshness = _build_priority_source_freshness_snapshot(
            source_registry=source_registry_for_transparency,
            source_policy=source_policy_for_transparency,
            checkpoint_state_path=source_transparency_state_path,
        )
        return {
            "request_metrics": request_metrics.snapshot(),
            "document_matter_store": {
                "backend": document_matter_store_backend,
            },
            "provider_routing_metrics": provider_router.telemetry_snapshot(),
            "canlii_usage_metrics": canlii_metrics_snapshot,
            "official_source_freshness": priority_source_freshness,
        }

    return app


app = create_app()
