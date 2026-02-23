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
    enable_scaffold_provider: bool
    api_rate_limit_per_minute: int


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
    enable_scaffold_provider = os.getenv("ENABLE_SCAFFOLD_PROVIDER", "true").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    return Settings(
        app_name=os.getenv("API_APP_NAME", "IMMCAD API"),
        environment=os.getenv("ENVIRONMENT", "development"),
        default_locale=os.getenv("DEFAULT_LOCALE", "en-CA"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        canlii_api_key=os.getenv("CANLII_API_KEY"),
        canlii_base_url=os.getenv("CANLII_BASE_URL", "https://api.canlii.org/v1"),
        api_bearer_token=os.getenv("API_BEARER_TOKEN"),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        provider_timeout_seconds=parse_float_env("PROVIDER_TIMEOUT_SECONDS", 15.0),
        provider_max_retries=parse_int_env("PROVIDER_MAX_RETRIES", 1),
        enable_scaffold_provider=enable_scaffold_provider,
        api_rate_limit_per_minute=parse_int_env("API_RATE_LIMIT_PER_MINUTE", 120),
    )
