from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    app_name: str
    environment: str
    default_locale: str
    openai_api_key: str | None
    gemini_api_key: str | None
    canlii_api_key: str | None
    canlii_base_url: str
    api_bearer_token: str | None
    redis_url: str
    openai_model: str
    gemini_model: str
    provider_timeout_seconds: float
    provider_max_retries: int
    provider_circuit_breaker_failure_threshold: int
    provider_circuit_breaker_open_seconds: float
    enable_scaffold_provider: bool
    allow_scaffold_synthetic_citations: bool
    enable_chat_grounding: bool
    chat_retriever_backend: str
    chat_grounding_top_k: int
    api_rate_limit_per_minute: int


def parse_bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    normalized = raw.strip().lower()
    truthy = {"1", "true", "yes", "on"}
    falsy = {"0", "false", "no", "off"}
    if normalized in truthy:
        return True
    if normalized in falsy:
        return False
    raise ValueError(f"{name} must be a boolean value, got {raw!r}")


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


def load_settings() -> Settings:
    environment = os.getenv("ENVIRONMENT", "development")
    environment_lower = environment.lower()
    enable_scaffold_provider = parse_bool_env("ENABLE_SCAFFOLD_PROVIDER", True)
    allow_scaffold_synthetic_citations = parse_bool_env(
        "ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS",
        environment_lower not in {"production", "prod", "ci"},
    )
    enable_chat_grounding = parse_bool_env("ENABLE_CHAT_GROUNDING", False)
    chat_retriever_backend = os.getenv("CHAT_RETRIEVER_BACKEND", "none").strip().lower() or "none"
    allowed_chat_retriever_backends = {"none", "chroma"}
    if chat_retriever_backend not in allowed_chat_retriever_backends:
        allowed_values = ", ".join(sorted(allowed_chat_retriever_backends))
        raise ValueError(f"CHAT_RETRIEVER_BACKEND must be one of: {allowed_values}")
    chat_grounding_top_k = parse_int_env("CHAT_GROUNDING_TOP_K", 3)
    if chat_grounding_top_k < 1:
        raise ValueError("CHAT_GROUNDING_TOP_K must be >= 1")
    api_bearer_token = os.getenv("API_BEARER_TOKEN")
    if environment_lower in {"production", "prod", "ci"} and not api_bearer_token:
        raise ValueError("API_BEARER_TOKEN is required when ENVIRONMENT is production/prod/ci")
    if environment_lower in {"production", "prod", "ci"} and allow_scaffold_synthetic_citations:
        raise ValueError(
            "ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS must be disabled in production/prod/ci"
        )

    return Settings(
        app_name=os.getenv("API_APP_NAME", "IMMCAD API"),
        environment=environment,
        default_locale=os.getenv("DEFAULT_LOCALE", "en-CA"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        canlii_api_key=os.getenv("CANLII_API_KEY"),
        canlii_base_url=os.getenv("CANLII_BASE_URL", "https://api.canlii.org/v1"),
        api_bearer_token=api_bearer_token,
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
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
        enable_chat_grounding=enable_chat_grounding,
        chat_retriever_backend=chat_retriever_backend,
        chat_grounding_top_k=chat_grounding_top_k,
        api_rate_limit_per_minute=parse_int_env("API_RATE_LIMIT_PER_MINUTE", 120),
    )
