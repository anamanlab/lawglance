#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def _strip_jsonc_comments(raw: str) -> str:
    output: list[str] = []
    in_string = False
    escape_next = False
    i = 0
    length = len(raw)
    while i < length:
        char = raw[i]
        next_char = raw[i + 1] if i + 1 < length else ""

        if in_string:
            output.append(char)
            if escape_next:
                escape_next = False
            elif char == "\\":
                escape_next = True
            elif char == '"':
                in_string = False
            i += 1
            continue

        if char == '"':
            in_string = True
            output.append(char)
            i += 1
            continue

        if char == "/" and next_char == "/":
            i += 2
            while i < length and raw[i] not in {"\n", "\r"}:
                i += 1
            continue

        if char == "/" and next_char == "*":
            i += 2
            while i + 1 < length and not (raw[i] == "*" and raw[i + 1] == "/"):
                i += 1
            i += 2
            continue

        output.append(char)
        i += 1

    return "".join(output)


def _strip_trailing_commas(raw: str) -> str:
    output: list[str] = []
    in_string = False
    escape_next = False
    i = 0
    length = len(raw)
    while i < length:
        char = raw[i]

        if in_string:
            output.append(char)
            if escape_next:
                escape_next = False
            elif char == "\\":
                escape_next = True
            elif char == '"':
                in_string = False
            i += 1
            continue

        if char == '"':
            in_string = True
            output.append(char)
            i += 1
            continue

        if char == ",":
            j = i + 1
            while j < length and raw[j] in {" ", "\t", "\n", "\r"}:
                j += 1
            if j < length and raw[j] in {"]", "}"}:
                i += 1
                continue

        output.append(char)
        i += 1

    return "".join(output)


def parse_json_or_jsonc(raw: str) -> dict[str, object] | None:
    try:
        payload = json.loads(raw)
        return payload if isinstance(payload, dict) else None
    except json.JSONDecodeError:
        pass

    sanitized = _strip_jsonc_comments(raw)
    sanitized = _strip_trailing_commas(sanitized)
    try:
        payload = json.loads(sanitized)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def resolve_backend_base_url(frontend_wrangler_path: Path) -> str | None:
    if not frontend_wrangler_path.exists():
        return None
    raw = frontend_wrangler_path.read_text(encoding="utf-8")
    payload = parse_json_or_jsonc(raw)
    if payload is None:
        return None
    vars_payload = payload.get("vars")
    if not isinstance(vars_payload, dict):
        return None
    raw_url = vars_payload.get("IMMCAD_API_BASE_URL")
    if raw_url is None:
        return None
    value = str(raw_url).strip()
    return value or None


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Resolve Cloudflare frontend IMMCAD backend runtime URL."
    )
    parser.add_argument(
        "--frontend-wrangler",
        default="frontend-web/wrangler.jsonc",
        help="Path to frontend Wrangler JSON/JSONC configuration.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    url = resolve_backend_base_url(Path(args.frontend_wrangler)) or ""
    print(url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

