from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ApiError(Exception):
    code: str
    message: str
    status_code: int

    def __post_init__(self) -> None:
        Exception.__init__(self, self.message)


class AuthError(ApiError):
    def __init__(self, message: str = "Unauthorized") -> None:
        super().__init__(code="UNAUTHORIZED", message=message, status_code=401)


class RateLimitError(ApiError):
    def __init__(self, message: str = "Rate limit exceeded") -> None:
        super().__init__(code="RATE_LIMITED", message=message, status_code=429)


class PolicyBlockedError(ApiError):
    def __init__(self, message: str = "Request blocked by policy") -> None:
        super().__init__(code="POLICY_BLOCKED", message=message, status_code=422)


class ProviderApiError(ApiError):
    def __init__(self, message: str = "Provider error") -> None:
        super().__init__(code="PROVIDER_ERROR", message=message, status_code=502)
