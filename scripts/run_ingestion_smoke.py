#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from immcad_api.ingestion import FetchContext, FetchResult, run_ingestion_jobs  # noqa: E402
from immcad_api.sources import SourceRegistryEntry  # noqa: E402


def _build_registry_payload() -> dict[str, object]:
    return {
        "version": "2026-02-24",
        "jurisdiction": "ca",
        "sources": [
            {
                "source_id": "IRCC_PDI",
                "source_type": "policy",
                "instrument": "IMMCAD ingestion smoke source",
                "url": "https://example.com/immcad/ingestion-smoke",
                "update_cadence": "scheduled_incremental",
            }
        ],
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run deterministic IMMCAD ingestion smoke checks.")
    parser.add_argument(
        "--output",
        default="artifacts/ingestion/ingestion-smoke-report.json",
        help="Output path for smoke report JSON.",
    )
    parser.add_argument(
        "--state-path",
        default="artifacts/ingestion/ingestion-smoke-checkpoints.json",
        help="Checkpoint state path used to verify 304 conditional behavior.",
    )
    return parser.parse_args()


def run_ingestion_smoke(*, output_path: Path, state_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    if state_path.exists():
        state_path.unlink()

    with tempfile.TemporaryDirectory(prefix="immcad-ingestion-smoke-") as temp_dir:
        registry_path = Path(temp_dir) / "smoke-registry.json"
        registry_path.write_text(json.dumps(_build_registry_payload()), encoding="utf-8")

        def smoke_fetcher(source: SourceRegistryEntry, context: FetchContext) -> FetchResult:
            if context.etag:
                return FetchResult(
                    payload=None,
                    http_status=304,
                    etag=context.etag,
                    last_modified=context.last_modified,
                )
            payload = json.dumps(
                {"source_id": source.source_id, "smoke": True},
                sort_keys=True,
            ).encode("utf-8")
            return FetchResult(
                payload=payload,
                http_status=200,
                etag=f'"{source.source_id}-etag"',
                last_modified="Tue, 24 Feb 2026 00:00:00 GMT",
            )

        first_run = run_ingestion_jobs(
            cadence="scheduled_incremental",
            registry_path=registry_path,
            state_path=state_path,
            fetcher=smoke_fetcher,
        )
        second_run = run_ingestion_jobs(
            cadence="scheduled_incremental",
            registry_path=registry_path,
            state_path=state_path,
            fetcher=smoke_fetcher,
        )

    passed = (
        first_run.total == 1
        and first_run.succeeded == 1
        and first_run.blocked == 0
        and first_run.failed == 0
        and second_run.total == 1
        and second_run.not_modified == 1
        and second_run.blocked == 0
        and second_run.failed == 0
    )

    report = {
        "status": "pass" if passed else "fail",
        "first_run": first_run.to_dict(),
        "second_run": second_run.to_dict(),
        "state_path": str(state_path),
    }
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Ingestion smoke report: {output_path}")
    print(f"Ingestion smoke status: {report['status']}")
    return 0 if passed else 1


def main() -> int:
    args = _parse_args()
    return run_ingestion_smoke(output_path=Path(args.output), state_path=Path(args.state_path))


if __name__ == "__main__":
    raise SystemExit(main())
