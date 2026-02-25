from __future__ import annotations

from dataclasses import dataclass
import os
import re

from immcad_api.policy.compliance import (
    DEFAULT_TRUSTED_CITATION_DOMAINS,
    normalize_trusted_domains,
)


_UNSTABLE_MODEL_TOKENS = ("preview", "experimental", "exp")
_HARDENED_ENVIRONMENT_PATTERN = re.compile(r"^(production|prod|ci)(?:[-_].+)?$")


@dataclass(frozen=True)
class Settings:
    app_name: str
    environment: str
    default_locale: str
    openai_api_key: str | None
    gemini_api_key: str | None
    canlii_api_key: str | None
    enable_openai_provider: bool
    primary_provider: str
    canlii_base_url: str
    enable_case_search: bool
    enable_official_case_sources: bool
    case_search_official_only_results: bool
    official_case_cache_ttl_seconds: float
    official_case_stale_cache_ttl_seconds: float
    api_bearer_token: str | None
    redis_url: str
    openai_model: str
    gemini_model: str
    gemini_model_fallbacks: tuple[str, ...]
    provider_timeout_seconds: float
    provider_max_retries: int
    provider_circuit_breaker_failure_threshold: int
    provider_circuit_breaker_open_seconds: float
    enable_scaffold_provider: bool
    allow_scaffold_synthetic_citations: bool
    export_policy_gate_enabled: bool
    export_max_download_bytes: int
    citation_trusted_domains: tuple[str, ...]
    api_rate_limit_per_minute: int
    cors_allowed_origins: tuple[str, ...]


def parse_str_env(name: str, default: str | None = None) -> str | None:
    raw = os.getenv(name)
    if raw is None:
        return default
    normalized = raw.strip()
    if not normalized:
        return default
    return normalized


def parse_float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a numeric value, got {raw!r}") from exc


def parse_int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer value, got {raw!r}") from exc


def parse_bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def parse_csv_env(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    values = tuple(item.strip() for item in raw.split(",") if item.strip())
    if not values:
        return default
    return values


def is_unstable_model_name(model_name: str) -> bool:
    normalized = model_name.strip().lower()
    return any(token in normalized for token in _UNSTABLE_MODEL_TOKENS)


def parse_api_bearer_token() -> str | None:
    canonical_token = parse_str_env("IMMCAD_API_BEARER_TOKEN")
    compatibility_token = parse_str_env("API_BEARER_TOKEN")
    if (
        canonical_token
        and compatibility_token
        and canonical_token != compatibility_token
    ):
        raise ValueError(
            "IMMCAD_API_BEARER_TOKEN and API_BEARER_TOKEN must match when both are set"
        )
    return canonical_token or compatibility_token


def resolve_runtime_environment() -> str:
    explicit_environment = parse_str_env("ENVIRONMENT")
    compatibility_environment = parse_str_env("IMMCAD_ENVIRONMENT")
    if (
        explicit_environment
        and compatibility_environment
        and explicit_environment.lower() != compatibility_environment.lower()
    ):
        raise ValueError(
            "ENVIRONMENT and IMMCAD_ENVIRONMENT must match when both are set"
        )
    if explicit_environment:
        return explicit_environment
    if compatibility_environment:
        return compatibility_environment

    vercel_environment = (parse_str_env("VERCEL_ENV") or "").lower()
    node_environment = (parse_str_env("NODE_ENV") or "").lower()
    if vercel_environment == "production" or node_environment == "production":
        return "production"

    return "development"


def is_hardened_environment(environment: str) -> bool:
    normalized = environment.strip().lower()
    if not normalized:
        return False
    return _HARDENED_ENVIRONMENT_PATTERN.fullmatch(normalized) is not None


def load_settings() -> Settings:
    environment = resolve_runtime_environment()
    hardened_environment = is_hardened_environment(environment)
    api_bearer_token = parse_api_bearer_token()
    openai_api_key = parse_str_env("OPENAI_API_KEY")
    gemini_api_key = parse_str_env("GEMINI_API_KEY")
    canlii_api_key = parse_str_env("CANLII_API_KEY")
    enable_case_search = parse_bool_env("ENABLE_CASE_SEARCH", True)
    enable_official_case_sources = parse_bool_env(
        "ENABLE_OFFICIAL_CASE_SOURCES",
        hardened_environment,
    )
    case_search_official_only_results = parse_bool_env(
        "CASE_SEARCH_OFFICIAL_ONLY_RESULTS",
        False,
    )
    official_case_cache_ttl_seconds = parse_float_env(
        "OFFICIAL_CASE_CACHE_TTL_SECONDS",
        300.0,
    )
    official_case_stale_cache_ttl_seconds = parse_float_env(
        "OFFICIAL_CASE_STALE_CACHE_TTL_SECONDS",
        900.0,
    )
    if official_case_cache_ttl_seconds <= 0:
        raise ValueError("OFFICIAL_CASE_CACHE_TTL_SECONDS must be > 0")
    if official_case_stale_cache_ttl_seconds < official_case_cache_ttl_seconds:
        raise ValueError(
            "OFFICIAL_CASE_STALE_CACHE_TTL_SECONDS must be >= OFFICIAL_CASE_CACHE_TTL_SECONDS"
        )
    enable_scaffold_provider = parse_bool_env("ENABLE_SCAFFOLD_PROVIDER", True)
    enable_openai_provider = parse_bool_env("ENABLE_OPENAI_PROVIDER", True)
    primary_provider = parse_str_env("PRIMARY_PROVIDER", "openai") or "openai"
    if primary_provider not in {"openai", "gemini", "scaffold"}:
        raise ValueError("PRIMARY_PROVIDER must be one of: openai, gemini, scaffold")
    if primary_provider == "openai" and not enable_openai_provider:
        raise ValueError("PRIMARY_PROVIDER=openai requires ENABLE_OPENAI_PROVIDER=true")
    allow_scaffold_synthetic_citations = parse_bool_env(
        "ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS",
        True,
    )
    raw_citation_trusted_domains = os.getenv("CITATION_TRUSTED_DOMAINS")
    parsed_citation_trusted_domains = (
        tuple(
            item.strip()
            for item in raw_citation_trusted_domains.split(",")
            if item.strip()
        )
        if raw_citation_trusted_domains is not None
        else None
    )
    citation_trusted_domains = normalize_trusted_domains(
        list(parsed_citation_trusted_domains or DEFAULT_TRUSTED_CITATION_DOMAINS)
    )

    if hardened_environment and not api_bearer_token:
        raise ValueError(
            "IMMCAD_API_BEARER_TOKEN is required when ENVIRONMENT is production/prod/ci (API_BEARER_TOKEN is supported as a compatibility alias)"
        )
    if hardened_environment and enable_scaffold_provider:
        raise ValueError(
            "ENABLE_SCAFFOLD_PROVIDER must be false when ENVIRONMENT is production/prod/ci"
        )
    if hardened_environment and primary_provider == "scaffold":
        raise ValueError(
            "PRIMARY_PROVIDER cannot be scaffold when ENVIRONMENT is production/prod/ci"
        )
    if hardened_environment and not gemini_api_key:
        raise ValueError(
            "GEMINI_API_KEY is required when ENVIRONMENT is production/prod/ci"
        )
    if (
        hardened_environment
        and enable_case_search
        and not canlii_api_key
        and not enable_official_case_sources
    ):
        raise ValueError(
            "Either CANLII_API_KEY or ENABLE_OFFICIAL_CASE_SOURCES=true is required when ENABLE_CASE_SEARCH=true in production/prod/ci"
        )
    if hardened_environment and enable_openai_provider and not openai_api_key:
        raise ValueError(
            "OPENAI_API_KEY is required when ENABLE_OPENAI_PROVIDER=true in production/prod/ci"
        )
    if hardened_environment and allow_scaffold_synthetic_citations:
        raise ValueError(
            "ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS must be false when ENVIRONMENT is production/prod/ci"
        )
    if hardened_environment and (
        raw_citation_trusted_domains is None or not raw_citation_trusted_domains.strip()
    ):
        raise ValueError(
            "CITATION_TRUSTED_DOMAINS must be explicitly set when ENVIRONMENT is production/prod/ci"
        )
    if hardened_environment and not parsed_citation_trusted_domains:
        raise ValueError(
            "CITATION_TRUSTED_DOMAINS must define at least one trusted domain in production/prod/ci"
        )
    export_policy_gate_enabled = parse_bool_env(
        "EXPORT_POLICY_GATE_ENABLED",
        hardened_environment,
    )
    if hardened_environment and not export_policy_gate_enabled:
        raise ValueError(
            "EXPORT_POLICY_GATE_ENABLED must be true when ENVIRONMENT is production/prod/ci"
        )
    export_max_download_bytes = parse_int_env(
        "EXPORT_MAX_DOWNLOAD_BYTES", 10 * 1024 * 1024
    )
    if export_max_download_bytes < 1:
        raise ValueError("EXPORT_MAX_DOWNLOAD_BYTES must be >= 1")

    raw_gemini_model = parse_str_env("GEMINI_MODEL")
    gemini_model = raw_gemini_model or "gemini-2.5-flash-lite"
    gemini_model_fallbacks = tuple(
        model
        for model in parse_csv_env(
            "GEMINI_MODEL_FALLBACKS",
            ("gemini-2.5-flash",),
        )
        if model != gemini_model
    )

    if hardened_environment and not raw_gemini_model:
        raise ValueError(
            "GEMINI_MODEL must be explicitly set when ENVIRONMENT is production/prod/ci"
        )
    if hardened_environment and is_unstable_model_name(gemini_model):
        raise ValueError(
            "GEMINI_MODEL must use a stable Gemini model in production/prod/ci"
        )
    if hardened_environment and any(
        is_unstable_model_name(model) for model in gemini_model_fallbacks
    ):
        raise ValueError(
            "GEMINI_MODEL_FALLBACKS must use stable Gemini models in production/prod/ci"
        )

    return Settings(
        app_name=parse_str_env("API_APP_NAME", "IMMCAD API") or "IMMCAD API",
        environment=environment,
        default_locale=parse_str_env("DEFAULT_LOCALE", "en-CA") or "en-CA",
        openai_api_key=openai_api_key,
        gemini_api_key=gemini_api_key,
        canlii_api_key=canlii_api_key,
        enable_openai_provider=enable_openai_provider,
        primary_provider=primary_provider,
        canlii_base_url=parse_str_env("CANLII_BASE_URL", "https://api.canlii.org/v1")
        or "https://api.canlii.org/v1",
        enable_case_search=enable_case_search,
        enable_official_case_sources=enable_official_case_sources,
        case_search_official_only_results=case_search_official_only_results,
        official_case_cache_ttl_seconds=official_case_cache_ttl_seconds,
        official_case_stale_cache_ttl_seconds=official_case_stale_cache_ttl_seconds,
        api_bearer_token=api_bearer_token,
        redis_url=parse_str_env("REDIS_URL", "redis://localhost:6379/0")
        or "redis://localhost:6379/0",
        openai_model=parse_str_env("OPENAI_MODEL", "gpt-4o-mini") or "gpt-4o-mini",
        gemini_model=gemini_model,
        gemini_model_fallbacks=gemini_model_fallbacks,
        provider_timeout_seconds=parse_float_env("PROVIDER_TIMEOUT_SECONDS", 15.0),
        provider_max_retries=parse_int_env("PROVIDER_MAX_RETRIES", 1),
        provider_circuit_breaker_failure_threshold=parse_int_env(
            "PROVIDER_CIRCUIT_BREAKER_FAILURE_THRESHOLD",
            3,
        ),
        provider_circuit_breaker_open_seconds=parse_float_env(
            "PROVIDER_CIRCUIT_BREAKER_OPEN_SECONDS",
            30.0,
        ),
        enable_scaffold_provider=enable_scaffold_provider,
        allow_scaffold_synthetic_citations=allow_scaffold_synthetic_citations,
        export_policy_gate_enabled=export_policy_gate_enabled,
        export_max_download_bytes=export_max_download_bytes,
        citation_trusted_domains=citation_trusted_domains,
        api_rate_limit_per_minute=parse_int_env("API_RATE_LIMIT_PER_MINUTE", 120),
        cors_allowed_origins=parse_csv_env(
            "CORS_ALLOWED_ORIGINS",
            ("http://127.0.0.1:3000", "http://localhost:3000"),
        ),
    )
