#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ipaddress
import json
from pathlib import Path
import tomllib
from urllib.parse import urlparse


REQUIRED_RUNTIME_ENV_KEYS: tuple[str, ...] = ("ENVIRONMENT", "IMMCAD_ENVIRONMENT")
REQUIRED_BACKEND_HARDENED_KEYS: tuple[str, ...] = (
    "ENABLE_SCAFFOLD_PROVIDER",
    "ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS",
    "ENABLE_OPENAI_PROVIDER",
    "PRIMARY_PROVIDER",
    "ENABLE_CASE_SEARCH",
    "ENABLE_OFFICIAL_CASE_SOURCES",
    "CASE_SEARCH_OFFICIAL_ONLY_RESULTS",
    "EXPORT_POLICY_GATE_ENABLED",
    "DOCUMENT_REQUIRE_HTTPS",
    "GEMINI_MODEL",
    "CITATION_TRUSTED_DOMAINS",
)


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


def _validate_cloud_only_defaults(
    *,
    frontend_wrangler_path: Path,
    frontend_vars: dict[str, str],
    backend_wrangler_path: Path,
    backend_vars: dict[str, str],
) -> list[str]:
    errors: list[str] = []
    frontend_label = str(frontend_wrangler_path)
    backend_label = str(backend_wrangler_path)

    frontend_backend_url = (frontend_vars.get("IMMCAD_API_BASE_URL") or "").strip()
    if not frontend_backend_url:
        errors.append(f"{frontend_label}: missing required var `IMMCAD_API_BASE_URL`")
    elif not frontend_backend_url.startswith("https://"):
        errors.append(
            f"{frontend_label}: IMMCAD_API_BASE_URL must start with `https://` "
            f"(got `{frontend_backend_url}`)"
        )
    else:
        parsed_backend_url = urlparse(frontend_backend_url)
        backend_hostname = (parsed_backend_url.hostname or "").strip().lower()
        if not backend_hostname:
            errors.append(
                f"{frontend_label}: IMMCAD_API_BASE_URL must include a valid hostname "
                f"(got `{frontend_backend_url}`)"
            )
        elif backend_hostname in {"localhost", "127.0.0.1", "::1"}:
            errors.append(
                f"{frontend_label}: IMMCAD_API_BASE_URL must not target localhost "
                f"(got `{frontend_backend_url}`)"
            )
        elif backend_hostname.endswith(".vercel.app"):
            errors.append(
                f"{frontend_label}: IMMCAD_API_BASE_URL must target Cloudflare backend "
                f"(workers.dev or custom domain), not Vercel (`{frontend_backend_url}`)"
            )
        else:
            try:
                parsed_ip = ipaddress.ip_address(backend_hostname)
            except ValueError:
                parsed_ip = None
            if parsed_ip and (
                parsed_ip.is_private or parsed_ip.is_loopback or parsed_ip.is_link_local
            ):
                errors.append(
                    f"{frontend_label}: IMMCAD_API_BASE_URL must not target private/link-local IP "
                    f"(got `{frontend_backend_url}`)"
                )

    fallback_backend_url = (frontend_vars.get("IMMCAD_API_BASE_URL_FALLBACK") or "").strip()
    if fallback_backend_url:
        errors.append(
            f"{frontend_label}: IMMCAD_API_BASE_URL_FALLBACK must be unset for "
            "cloud-only production baseline"
        )

    for required_key in REQUIRED_BACKEND_HARDENED_KEYS:
        if not (backend_vars.get(required_key) or "").strip():
            errors.append(f"{backend_label}: missing required var `{required_key}`")

    required_backend_flags = {
        "ENABLE_SCAFFOLD_PROVIDER": "false",
        "ALLOW_SCAFFOLD_SYNTHETIC_CITATIONS": "false",
        "ENABLE_OPENAI_PROVIDER": "false",
        "PRIMARY_PROVIDER": "gemini",
        "CASE_SEARCH_OFFICIAL_ONLY_RESULTS": "true",
        "EXPORT_POLICY_GATE_ENABLED": "true",
        "DOCUMENT_REQUIRE_HTTPS": "true",
    }
    for key, expected in required_backend_flags.items():
        actual = (backend_vars.get(key) or "").strip().lower()
        if actual and actual != expected:
            errors.append(
                f"{backend_label}: {key} must be `{expected}` for cloud-only production "
                f"baseline (got `{actual}`)"
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
    errors.extend(
        _validate_cloud_only_defaults(
            frontend_wrangler_path=frontend_wrangler_path,
            frontend_vars=frontend_vars,
            backend_wrangler_path=backend_wrangler_path,
            backend_vars=backend_vars,
        )
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
