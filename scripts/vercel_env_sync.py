#!/usr/bin/env python3
"""Vercel environment synchronization utility.

Supports:
- analyze
- pull
- push
- diff
- validate
- security-check
- backup
- restore

Examples:
  python scripts/vercel_env_sync.py analyze --project-dir frontend-web
  python scripts/vercel_env_sync.py pull --project-dir backend-vercel --environment production
  python scripts/vercel_env_sync.py push --project-dir frontend-web --file .env.production --environment production
  python scripts/vercel_env_sync.py diff --project-dir frontend-web --environment preview
  python scripts/vercel_env_sync.py validate --project-dir backend-vercel --file .env.example
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

SYSTEM_KEY_PREFIXES = (
    "VERCEL_",
    "TURBO_",
    "NX_",
)

PLACEHOLDER_PATTERNS = (
    "your-",
    "change-me",
    "replace-me",
    "example",
)

KNOWN_ENV_FILES = (
    ".env.local",
    ".env.development",
    ".env.development.local",
    ".env.preview",
    ".env.preview.local",
    ".env.staging",
    ".env.staging.local",
    ".env.production",
    ".env.production.local",
    ".env",
    ".env.example",
)

DEFAULT_PUSH_FILE_MAP = (
    (".env.production", "production"),
    (".env.staging", "preview"),
    (".env.preview", "preview"),
    (".env.development", "development"),
)


def _print(msg: str) -> None:
    print(msg)


def _warn(msg: str) -> None:
    print(f"WARN: {msg}", file=sys.stderr)


def _err(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)


def now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def infer_local_file_for_env(project_dir: Path, environment: str) -> Path:
    if environment == "production":
        candidates = [".env.production", ".env.production.local"]
    elif environment == "preview":
        candidates = [".env.preview", ".env.staging", ".env.preview.local", ".env.staging.local"]
    else:
        candidates = [".env.development", ".env.local", ".env.development.local", ".env"]

    for c in candidates:
        p = project_dir / c
        if p.exists():
            return p
    return project_dir / candidates[0]


def infer_output_file_for_pull(project_dir: Path, environment: str) -> Path:
    if environment == "production":
        return project_dir / ".env.production.local"
    if environment == "preview":
        return project_dir / ".env.preview.local"
    return project_dir / ".env.local"


def parse_env_file(path: Path) -> "OrderedDict[str, str]":
    data: "OrderedDict[str, str]" = OrderedDict()
    if not path.exists():
        return data

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("export "):
            line = line[len("export ") :].strip()

        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if not key:
            continue

        # strip inline comments for unquoted values
        if value and value[0] not in ('"', "'") and " #" in value:
            value = value.split(" #", 1)[0].rstrip()

        if len(value) >= 2 and ((value[0] == '"' and value[-1] == '"') or (value[0] == "'" and value[-1] == "'")):
            value = value[1:-1]

        # Only collapse values that are purely literal newline markers (for example "\\n" or "\\n\\n").
        # Preserve legitimate encoded multi-line values (PEM blocks, JSON blobs) that may end with "\\n".
        if re.fullmatch(r"(?:\\n)+", value):
            value = ""

        data[key] = value

    return data


def is_system_key(key: str) -> bool:
    return key == "VERCEL" or key.startswith(SYSTEM_KEY_PREFIXES)


def filter_keys(data: Dict[str, str], include_system: bool) -> Dict[str, str]:
    if include_system:
        return dict(data)
    return {k: v for k, v in data.items() if not is_system_key(k)}


def run_cmd(cmd: List[str], *, input_text: str | None = None, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        input=input_text,
        capture_output=True,
        text=True,
        check=check,
    )


def vercel_cmd(project_dir: Path, args: List[str]) -> List[str]:
    return ["vercel", "--cwd", str(project_dir)] + args


def load_linked_project(project_dir: Path) -> Dict[str, str] | None:
    project_json = project_dir / ".vercel" / "project.json"
    if not project_json.exists():
        return None
    try:
        return json.loads(project_json.read_text(encoding="utf-8"))
    except Exception:
        return None


def mask_sensitive(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}{'*' * (len(value) - 8)}{value[-4:]}"


@dataclass
class ValidationResult:
    valid: bool
    errors: List[str]
    warnings: List[str]


def validate_env_values(
    values: Dict[str, str],
    *,
    required_keys: Iterable[str],
    production_mode: bool,
) -> ValidationResult:
    errors: List[str] = []
    warnings: List[str] = []

    for key in required_keys:
        if key and key not in values:
            errors.append(f"Missing required variable: {key}")

    for key, value in values.items():
        lv = value.lower()
        if any(token in lv for token in PLACEHOLDER_PATTERNS):
            warnings.append(f"Placeholder-like value detected for {key}")

        if re.search(r"(SECRET|TOKEN|KEY|PASSWORD|PRIVATE)", key):
            if len(value) < 16:
                warnings.append(f"{key} appears too short for a secret ({len(value)} chars)")

        if production_mode and "localhost" in lv and (key.endswith("URL") or key.endswith("_HOST")):
            warnings.append(f"Production file contains localhost in {key}")

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


def backup_local_files(project_dir: Path, backup_dir: Path, timestamp: str) -> List[Path]:
    backup_dir.mkdir(parents=True, exist_ok=True)
    copied: List[Path] = []
    project_slug = project_dir.name or "project"

    for name in KNOWN_ENV_FILES:
        src = project_dir / name
        if not src.exists():
            continue
        dst = backup_dir / f"{project_slug}-{name}.{timestamp}"
        shutil.copy2(src, dst)
        copied.append(dst)

    return copied


def backup_remote_env(project_dir: Path, backup_dir: Path, timestamp: str) -> List[Path]:
    backed: List[Path] = []
    project_slug = project_dir.name or "project"
    for env in ("development", "preview", "production"):
        out_file = backup_dir / f"{project_slug}-vercel-{env}.{timestamp}.json"
        cmd = vercel_cmd(project_dir, ["env", "list", env, "--format", "json"])
        proc = run_cmd(cmd, check=False)
        if proc.returncode != 0:
            _warn(f"Skipping remote backup for {env}: {proc.stderr.strip() or proc.stdout.strip()}")
            continue
        out_file.write_text(proc.stdout, encoding="utf-8")
        backed.append(out_file)
    return backed


def pull_remote_values(project_dir: Path, environment: str) -> Dict[str, str]:
    with tempfile.NamedTemporaryFile(prefix="vercel-env-", suffix=".tmp", delete=False) as tf:
        temp_path = Path(tf.name)
    try:
        cmd = vercel_cmd(
            project_dir,
            [
                "env",
                "pull",
                str(temp_path),
                "--environment",
                environment,
                "--yes",
            ],
        )
        proc = run_cmd(cmd, check=False)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "vercel env pull failed")
        return parse_env_file(temp_path)
    finally:
        temp_path.unlink(missing_ok=True)


def op_analyze(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir).resolve()
    _print(f"Project directory: {project_dir}")

    linked = load_linked_project(project_dir)
    if linked:
        _print(f"Linked Vercel project: {linked.get('projectName', 'unknown')} ({linked.get('projectId', 'n/a')})")
    else:
        _warn("No .vercel/project.json found in selected project directory")

    _print("\nLocal environment files:")
    for name in KNOWN_ENV_FILES:
        path = project_dir / name
        if path.exists():
            vals = parse_env_file(path)
            _print(f"  - {name}: present ({len(vals)} variables)")
        else:
            _print(f"  - {name}: missing")

    version_cmd = ["vercel", "--version"]
    version = run_cmd(version_cmd, check=False)
    _print("\nVercel CLI status:")
    if version.returncode == 0:
        _print(f"  - {version.stdout.strip()}")
    else:
        _warn("Vercel CLI unavailable")

    if not args.no_remote:
        _print("\nRemote environment counts:")
        for env in ("development", "preview", "production"):
            cmd = vercel_cmd(project_dir, ["env", "list", env, "--format", "json"])
            proc = run_cmd(cmd, check=False)
            if proc.returncode != 0:
                _warn(f"  - {env}: unavailable ({proc.stderr.strip() or 'not linked/authenticated'})")
                continue
            try:
                payload = json.loads(proc.stdout)
                count = len(payload.get("envs", []))
                _print(f"  - {env}: {count} keys")
            except Exception:
                _warn(f"  - {env}: unable to parse output")

    return 0


def op_pull(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir).resolve()
    output = Path(args.output).resolve() if args.output else infer_output_file_for_pull(project_dir, args.environment)
    project_slug = project_dir.name or "project"

    backup_dir = Path(args.backup_dir).resolve()
    if output.exists() and not args.no_backup:
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_file = backup_dir / f"{project_slug}-{output.name}.{now_ts()}"
        shutil.copy2(output, backup_file)
        _print(f"Backup created: {backup_file}")

    cmd = vercel_cmd(
        project_dir,
        ["env", "pull", str(output), "--environment", args.environment, "--yes"],
    )
    proc = run_cmd(cmd, check=False)
    if proc.returncode != 0:
        _err(proc.stderr.strip() or proc.stdout.strip() or "vercel env pull failed")
        return 1

    values = parse_env_file(output)
    values = filter_keys(values, args.include_system)
    _print(f"Pulled {len(values)} variables to {output}")
    if values:
        _print("Variable names:")
        for key in sorted(values.keys()):
            _print(f"  - {key}")
    return 0


def iter_push_files(project_dir: Path, args: argparse.Namespace) -> List[Tuple[Path, str]]:
    pairs: List[Tuple[Path, str]] = []
    if args.file:
        if not args.environment:
            raise ValueError("--environment is required when --file is provided")
        file_path = Path(args.file)
        if not file_path.is_absolute():
            file_path = project_dir / file_path
        pairs.append((file_path, args.environment))
        return pairs

    for rel, env in DEFAULT_PUSH_FILE_MAP:
        p = project_dir / rel
        if p.exists():
            pairs.append((p, env))

    if args.include_local and (project_dir / ".env.local").exists():
        pairs.append((project_dir / ".env.local", "development"))

    return pairs


def op_push(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir).resolve()
    try:
        pairs = iter_push_files(project_dir, args)
    except ValueError as exc:
        _err(str(exc))
        return 1

    if not pairs:
        _err("No environment files found to push")
        return 1

    overall_failures = 0
    for path, env in pairs:
        if not path.exists():
            _warn(f"Skipping missing file: {path}")
            continue

        values = parse_env_file(path)
        values = filter_keys(values, args.include_system)

        _print(f"Pushing {len(values)} keys from {path} -> {env}")

        for key, value in values.items():
            if args.dry_run:
                _print(f"  [dry-run] set {key} ({env})")
                continue

            cmd = vercel_cmd(project_dir, ["env", "add", key, env, "--force", "--yes"])
            proc = run_cmd(cmd, input_text=value + "\n", check=False)
            if proc.returncode != 0:
                overall_failures += 1
                _warn(f"Failed setting {key} ({env}): {proc.stderr.strip() or proc.stdout.strip()}")
            else:
                _print(f"  set {key}")

    if overall_failures:
        _err(f"Push completed with {overall_failures} failures")
        return 1

    _print("Push completed successfully")
    return 0


def op_diff(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir).resolve()
    local_file = Path(args.file).resolve() if args.file else infer_local_file_for_env(project_dir, args.environment)

    local_values = parse_env_file(local_file)
    if not local_values:
        _warn(f"Local file has no parseable values or is missing: {local_file}")

    try:
        remote_values = pull_remote_values(project_dir, args.environment)
    except Exception as exc:
        _err(f"Unable to pull remote values: {exc}")
        return 1

    local_values = filter_keys(local_values, args.include_system)
    remote_values = filter_keys(remote_values, args.include_system)

    local_keys = set(local_values.keys())
    remote_keys = set(remote_values.keys())
    added = sorted(remote_keys - local_keys)
    removed = sorted(local_keys - remote_keys)
    common = sorted(local_keys & remote_keys)
    modified = [k for k in common if local_values[k] != remote_values[k]]
    unchanged = [k for k in common if local_values[k] == remote_values[k]]

    _print(f"Diff for {args.environment} ({project_dir})")
    _print(f"Local file: {local_file}")
    _print(f"Remote-only keys: {len(added)}")
    _print(f"Local-only keys: {len(removed)}")
    _print(f"Modified keys: {len(modified)}")
    _print(f"Unchanged keys: {len(unchanged)}")

    if added:
        _print("\nRemote-only:")
        for k in added:
            _print(f"  + {k}")
    if removed:
        _print("\nLocal-only:")
        for k in removed:
            _print(f"  - {k}")
    if modified:
        _print("\nModified:")
        for k in modified:
            _print(f"  ~ {k}: local={mask_sensitive(local_values[k])} remote={mask_sensitive(remote_values[k])}")

    return 0


def resolve_required_keys(project_dir: Path, explicit_required: List[str]) -> List[str]:
    required = list(explicit_required)

    # Prefer a project-local template, but fall back to repo root template
    # so subproject targets (frontend-web/backend-vercel) still validate
    # against shared required keys.
    candidate_files = [project_dir / ".env.example"]
    repo_root = Path(__file__).resolve().parents[1]
    root_example = repo_root / ".env.example"
    if root_example not in candidate_files:
        candidate_files.append(root_example)

    for example_file in candidate_files:
        if not example_file.exists():
            continue
        required_from_example = list(parse_env_file(example_file).keys())
        required.extend(required_from_example)
        break

    # stable unique order
    seen = set()
    result = []
    for k in required:
        if k not in seen:
            seen.add(k)
            result.append(k)
    return result


def run_validation(args: argparse.Namespace, *, strict_warnings: bool) -> int:
    project_dir = Path(args.project_dir).resolve()
    env_file = Path(args.file).resolve() if args.file else infer_local_file_for_env(project_dir, args.environment)

    values = parse_env_file(env_file)
    values = filter_keys(values, args.include_system)

    required = resolve_required_keys(project_dir, args.required or [])
    production_mode = args.environment == "production" or "production" in env_file.name

    result = validate_env_values(values, required_keys=required, production_mode=production_mode)

    _print(f"Validating: {env_file}")
    _print(f"Parsed variables: {len(values)}")
    _print(f"Required variables checked: {len(required)}")

    if result.errors:
        _print("\nErrors:")
        for e in result.errors:
            _print(f"  - {e}")

    if result.warnings:
        _print("\nWarnings:")
        for w in result.warnings:
            _print(f"  - {w}")

    if result.errors:
        return 1
    if strict_warnings and result.warnings:
        return 1

    _print("Validation passed")
    return 0


def op_backup(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir).resolve()
    backup_dir = Path(args.backup_dir).resolve()
    ts = now_ts()

    copied = backup_local_files(project_dir, backup_dir, ts)
    remote = [] if args.skip_remote else backup_remote_env(project_dir, backup_dir, ts)

    _print(f"Backup timestamp: {ts}")
    _print(f"Local backups: {len(copied)}")
    for p in copied:
        _print(f"  - {p}")

    _print(f"Remote backups: {len(remote)}")
    for p in remote:
        _print(f"  - {p}")

    return 0


def op_restore(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir).resolve()
    backup_dir = Path(args.backup_dir).resolve()
    ts = args.timestamp
    project_slug = project_dir.name or "project"

    if not ts:
        _err("--timestamp is required for restore")
        return 1

    restored = 0
    for name in KNOWN_ENV_FILES:
        # Prefer project-scoped backup files; fall back to legacy naming.
        candidates = [
            backup_dir / f"{project_slug}-{name}.{ts}",
            backup_dir / f"{name}.{ts}",
        ]
        src = next((c for c in candidates if c.exists()), None)
        if src is None:
            continue
        dst = project_dir / name
        shutil.copy2(src, dst)
        restored += 1
        _print(f"Restored {dst} from {src}")

    if restored == 0:
        _err(f"No backup files found for timestamp: {ts}")
        return 1

    _print(f"Restore completed: {restored} files")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Vercel environment sync utility")
    parser.add_argument("command", choices=["analyze", "pull", "push", "diff", "validate", "security-check", "backup", "restore"])
    parser.add_argument("--project-dir", default=".", help="Directory linked to a Vercel project (contains .vercel/project.json)")
    parser.add_argument("--environment", choices=["development", "preview", "production"], default="development")
    parser.add_argument("--file", help="Environment file path")
    parser.add_argument("--output", help="Output path for pull")
    parser.add_argument("--backup-dir", default=".env-backups", help="Backup directory")
    parser.add_argument("--timestamp", help="Backup timestamp for restore")
    parser.add_argument("--required", action="append", help="Additional required env key (repeatable)")
    parser.add_argument("--include-system", action="store_true", help="Include Vercel/Turbo system variables")
    parser.add_argument("--include-local", action="store_true", help="Include .env.local when pushing")
    parser.add_argument("--dry-run", action="store_true", help="Do not perform remote write operations")
    parser.add_argument("--no-remote", action="store_true", help="Skip remote checks in analyze")
    parser.add_argument("--no-backup", action="store_true", help="Do not create backup before pull")
    parser.add_argument("--skip-remote", action="store_true", help="Skip remote backup in backup command")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as failures for validate")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "analyze":
        return op_analyze(args)
    if args.command == "pull":
        return op_pull(args)
    if args.command == "push":
        return op_push(args)
    if args.command == "diff":
        return op_diff(args)
    if args.command == "validate":
        return run_validation(args, strict_warnings=args.strict)
    if args.command == "security-check":
        return run_validation(args, strict_warnings=True)
    if args.command == "backup":
        return op_backup(args)
    if args.command == "restore":
        return op_restore(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
