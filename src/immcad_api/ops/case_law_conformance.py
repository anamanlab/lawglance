from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import httpx

from immcad_api.sources import load_source_registry, validate_court_source_payload


COURT_SOURCE_IDS = ("SCC_DECISIONS", "FC_DECISIONS", "FCA_DECISIONS")


Fetcher = Callable[[str], tuple[int, dict[str, str], bytes]]


@dataclass(frozen=True)
class CaseLawConformanceSourceResult:
    source_id: str
    url: str
    status: str
    http_status: int | None
    content_type: str | None
    records_total: int | None = None
    records_valid: int | None = None
    records_invalid: int | None = None
    invalid_ratio: float | None = None
    error: str | None = None


@dataclass(frozen=True)
class CaseLawConformanceReport:
    generated_at: str
    overall_status: str
    strict: bool
    max_invalid_ratio: float
    min_records: int
    results: list[CaseLawConformanceSourceResult]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _default_fetcher(url: str, *, timeout_seconds: float) -> tuple[int, dict[str, str], bytes]:
    response = httpx.get(url, timeout=timeout_seconds, follow_redirects=True)
    headers = {key.lower(): value for key, value in response.headers.items()}
    return response.status_code, headers, response.content


def _evaluate_source_payload(
    *,
    source_id: str,
    url: str,
    status_code: int,
    headers: dict[str, str],
    payload: bytes,
    max_invalid_ratio: float,
    min_records: int,
) -> CaseLawConformanceSourceResult:
    content_type = headers.get("content-type")
    if status_code != 200:
        return CaseLawConformanceSourceResult(
            source_id=source_id,
            url=url,
            status="fail",
            http_status=status_code,
            content_type=content_type,
            error=f"unexpected_http_status:{status_code}",
        )

    summary = validate_court_source_payload(source_id, payload)
    if summary is None:
        return CaseLawConformanceSourceResult(
            source_id=source_id,
            url=url,
            status="fail",
            http_status=status_code,
            content_type=content_type,
            error="unsupported_source",
        )

    invalid_ratio = summary.invalid_ratio
    if summary.records_total < min_records:
        source_status = "fail"
        error = f"too_few_records:{summary.records_total}<{min_records}"
    elif invalid_ratio > max_invalid_ratio:
        source_status = "fail"
        error = (
            f"invalid_ratio_exceeded:{invalid_ratio:.4f}>{max_invalid_ratio:.4f}"
        )
    elif summary.records_invalid > 0:
        source_status = "warn"
        error = summary.errors[0] if summary.errors else "invalid_records_within_threshold"
    else:
        source_status = "pass"
        error = None

    return CaseLawConformanceSourceResult(
        source_id=source_id,
        url=url,
        status=source_status,
        http_status=status_code,
        content_type=content_type,
        records_total=summary.records_total,
        records_valid=summary.records_valid,
        records_invalid=summary.records_invalid,
        invalid_ratio=invalid_ratio,
        error=error,
    )


def run_case_law_conformance(
    *,
    registry_path: str | Path | None = None,
    timeout_seconds: float = 20.0,
    strict: bool = False,
    max_invalid_ratio: float = 0.10,
    min_records: int = 1,
    fetcher: Callable[[str], tuple[int, dict[str, str], bytes]] | None = None,
) -> dict[str, object]:
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be > 0")
    if not 0.0 <= max_invalid_ratio <= 1.0:
        raise ValueError("max_invalid_ratio must be between 0.0 and 1.0")
    if min_records < 0:
        raise ValueError("min_records must be >= 0")

    registry = load_source_registry(registry_path)
    fetch_impl = fetcher or (lambda url, *, timeout_seconds: _default_fetcher(url, timeout_seconds=timeout_seconds))
    registry_sources = {entry.source_id: entry for entry in registry.sources}

    results: list[CaseLawConformanceSourceResult] = []
    for source_id in COURT_SOURCE_IDS:
        entry = registry_sources.get(source_id)
        if entry is None:
            results.append(
                CaseLawConformanceSourceResult(
                    source_id=source_id,
                    url="",
                    status="fail",
                    http_status=None,
                    content_type=None,
                    error="source_missing_from_registry",
                )
            )
            continue

        url = str(entry.url)
        try:
            status_code, headers, payload = fetch_impl(url, timeout_seconds=timeout_seconds)
            result = _evaluate_source_payload(
                source_id=source_id,
                url=url,
                status_code=status_code,
                headers=headers,
                payload=payload,
                max_invalid_ratio=max_invalid_ratio,
                min_records=min_records,
            )
        except Exception as exc:
            result = CaseLawConformanceSourceResult(
                source_id=source_id,
                url=url,
                status="fail",
                http_status=None,
                content_type=None,
                error=f"{type(exc).__name__}: {exc}",
            )
        results.append(result)

    statuses = {item.status for item in results}
    if "fail" in statuses:
        overall_status = "fail"
    elif "warn" in statuses:
        overall_status = "warn"
    else:
        overall_status = "pass"

    report = CaseLawConformanceReport(
        generated_at=_utc_now_iso(),
        overall_status=overall_status,
        strict=strict,
        max_invalid_ratio=max_invalid_ratio,
        min_records=min_records,
        results=results,
    )
    return report.to_dict()
