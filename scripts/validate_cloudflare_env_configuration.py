#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import tomllib


REQUIRED_RUNTIME_ENV_KEYS: tuple[str, ...] = ("ENVIRONMENT", "IMMCAD_ENVIRONMENT")


def _load_frontend_wrangler_vars(path: Path) -> dict[str, str]:
    content = json.loads(path.read_text(encoding="utf-8"))
    raw_vars = content.get("vars")
    if raw_vars is None:
        return {}
    if not isinstance(raw_vars, dict):
        raise ValueError(f"{path} `vars` must be a JSON object")
    return {
        str(key): str(value)
        for key, value in raw_vars.items()
        if isinstance(key, str) and isinstance(value, (str, int, float, bool))
    }


def _load_backend_wrangler_vars(path: Path) -> dict[str, str]:
    content = tomllib.loads(path.read_text(encoding="utf-8"))
    raw_vars = content.get("vars")
    if raw_vars is None:
        return {}
    if not isinstance(raw_vars, dict):
        raise ValueError(f"{path} [vars] must be a TOML table")
    return {
        str(key): str(value)
        for key, value in raw_vars.items()
        if isinstance(key, str) and isinstance(value, (str, int, float, bool))
    }


def _validate_runtime_env_vars(
    *,
    vars_by_target: dict[str, dict[str, str]],
    expected_environment: str,
) -> list[str]:
    errors: list[str] = []
    expected_environment_normalized = expected_environment.strip().lower()
    for target, values in vars_by_target.items():
        for key in REQUIRED_RUNTIME_ENV_KEYS:
            if not values.get(key):
                errors.append(f"{target}: missing required var `{key}`")

        environment = (values.get("ENVIRONMENT") or "").strip().lower()
        immcad_environment = (values.get("IMMCAD_ENVIRONMENT") or "").strip().lower()
        if environment and immcad_environment and environment != immcad_environment:
            errors.append(
                f"{target}: ENVIRONMENT and IMMCAD_ENVIRONMENT must match "
                f"(got `{environment}` vs `{immcad_environment}`)"
            )
        if environment and environment != expected_environment_normalized:
            errors.append(
                f"{target}: ENVIRONMENT must be `{expected_environment_normalized}` "
                f"(got `{environment}`)"
            )
    return errors


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate Cloudflare runtime environment configuration for frontend/backend "
            "Wrangler files."
        )
    )
    parser.add_argument(
        "--frontend-wrangler",
        default="frontend-web/wrangler.jsonc",
        help="Path to frontend Wrangler JSONC file.",
    )
    parser.add_argument(
        "--backend-wrangler",
        default="backend-cloudflare/wrangler.toml",
        help="Path to backend native Wrangler TOML file.",
    )
    parser.add_argument(
        "--expected-environment",
        default="production",
        help="Expected runtime environment value for Cloudflare deploy config.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    frontend_wrangler_path = Path(args.frontend_wrangler)
    backend_wrangler_path = Path(args.backend_wrangler)

    if not frontend_wrangler_path.exists():
        raise FileNotFoundError(
            f"Frontend Wrangler config not found: {frontend_wrangler_path}"
        )
    if not backend_wrangler_path.exists():
        raise FileNotFoundError(f"Backend Wrangler config not found: {backend_wrangler_path}")

    frontend_vars = _load_frontend_wrangler_vars(frontend_wrangler_path)
    backend_vars = _load_backend_wrangler_vars(backend_wrangler_path)

    errors = _validate_runtime_env_vars(
        vars_by_target={
            str(frontend_wrangler_path): frontend_vars,
            str(backend_wrangler_path): backend_vars,
        },
        expected_environment=args.expected_environment,
    )
    if errors:
        print("Cloudflare environment configuration check failed:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(
        "Cloudflare environment configuration check passed: "
        f"{frontend_wrangler_path} and {backend_wrangler_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
