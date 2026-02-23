#!/usr/bin/env python3
from __future__ import annotations

from collections.abc import Mapping
import os

PROD_LIKE_ENVIRONMENTS = {"production", "prod", "ci"}
TRUTHY_VALUES = {"1", "true", "yes", "on"}
FALSY_VALUES = {"0", "false", "no", "off"}


def _parse_required_bool(env: Mapping[str, str | None], name: str) -> bool:
    raw = env.get(name)
    if raw is None or not raw.strip():
        raise ValueError(f"{name} is required and must be set to a boolean value")

    normalized = raw.strip().lower()
    if normalized in TRUTHY_VALUES:
        return True
    if normalized in FALSY_VALUES:
        return False
    raise ValueError(f"{name} must be a boolean value, got {raw!r}")


def validate_env(env: Mapping[str, str | None]) -> None:
    errors: list[str] = []

    raw_environment = env.get("ENVIRONMENT")
    if raw_environment is None or not raw_environment.strip():
        errors.append("ENVIRONMENT is required and must be one of production/prod/ci")
    else:
        normalized_environment = raw_environment.strip().lower()
        if normalized_environment not in PROD_LIKE_ENVIRONMENTS:
            errors.append(
                "ENVIRONMENT must be production/prod/ci for release-gates validation "
                f"(got {raw_environment!r})"
            )

    api_bearer_token = env.get("API_BEARER_TOKEN")
    if api_bearer_token is None or not api_bearer_token.strip():
        errors.append("API_BEARER_TOKEN is required for prod-like release validation")

    for flag_name in ("ENABLE_SCAFFOLD_PROVIDER", "ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS"):
        try:
            is_enabled = _parse_required_bool(env, flag_name)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if is_enabled:
            errors.append(f"{flag_name} must be false for prod-like release validation")

    if errors:
        joined = "\n".join(f"- {message}" for message in errors)
        raise ValueError(joined)


def main() -> int:
    try:
        validate_env(os.environ)
    except ValueError as exc:
        print("[FAIL] Release runtime flag validation failed.")
        print(str(exc))
        return 1

    print("[OK] Release runtime flags are production-safe for prod-like release validation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
