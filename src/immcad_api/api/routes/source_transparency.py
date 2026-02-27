from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from immcad_api.policy import SourcePolicy
from immcad_api.schemas import (
    CaseLawSourceTransparencyItem,
    ErrorEnvelope,
    SourceFreshnessStatus,
    SourceTransparencyCheckpoint,
    SourceTransparencyResponse,
)
from immcad_api.sources import SourceRegistry

_COURT_BY_SOURCE_ID = {
    "SCC_DECISIONS": "SCC",
    "FC_DECISIONS": "FC",
    "FCA_DECISIONS": "FCA",
}
_COURT_SORT_ORDER = {"SCC": 0, "FC": 1, "FCA": 2}
_FRESHNESS_THRESHOLD_SECONDS = {
    "scheduled_incremental": 12 * 60 * 60,
    "daily": 48 * 60 * 60,
    "weekly": 14 * 24 * 60 * 60,
}


def _utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_utc_iso(raw_value: object) -> datetime | None:
    if not isinstance(raw_value, str):
        return None
    normalized = raw_value.strip()
    if not normalized:
        return None
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _normalize_http_status(raw_status: object) -> int | None:
    if isinstance(raw_status, int):
        return raw_status
    return None


def _compute_freshness(
    *,
    last_success_at: object,
    update_cadence: str,
    now: datetime,
) -> tuple[int | None, SourceFreshnessStatus]:
    parsed_success_at = _parse_utc_iso(last_success_at)
    if parsed_success_at is None:
        if last_success_at is None:
            return None, "missing"
        if isinstance(last_success_at, str) and not last_success_at.strip():
            return None, "missing"
        return None, "unknown"

    freshness_seconds = max(0, int((now - parsed_success_at).total_seconds()))
    freshness_threshold = _FRESHNESS_THRESHOLD_SECONDS.get(update_cadence)
    if freshness_threshold is None:
        return freshness_seconds, "unknown"
    if freshness_seconds <= freshness_threshold:
        return freshness_seconds, "fresh"
    return freshness_seconds, "stale"


def _load_checkpoint_state(
    state_path: Path,
) -> tuple[bool, str | None, dict[str, dict[str, object]]]:
    if not state_path.exists():
        return False, None, {}

    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return True, None, {}
    if not isinstance(payload, dict):
        return True, None, {}

    updated_at = payload.get("updated_at")
    normalized_updated_at = updated_at if isinstance(updated_at, str) else None

    checkpoints_raw = payload.get("checkpoints")
    if not isinstance(checkpoints_raw, dict):
        return True, normalized_updated_at, {}

    checkpoints: dict[str, dict[str, object]] = {}
    for source_id, checkpoint in checkpoints_raw.items():
        if isinstance(source_id, str) and isinstance(checkpoint, dict):
            checkpoints[source_id] = checkpoint
    return True, normalized_updated_at, checkpoints


def build_source_transparency_payload(
    *,
    source_registry: SourceRegistry,
    source_policy: SourcePolicy,
    checkpoint_state_path: str,
) -> SourceTransparencyResponse:
    checkpoint_path = Path(checkpoint_state_path)
    checkpoint_exists, checkpoint_updated_at, checkpoints = _load_checkpoint_state(
        checkpoint_path
    )

    now = datetime.now(tz=timezone.utc)
    case_law_sources: list[CaseLawSourceTransparencyItem] = []
    supported_courts = {
        court
        for source_id, court in _COURT_BY_SOURCE_ID.items()
        if source_registry.get_source(source_id) is not None
    }

    for source in source_registry.sources:
        if source.source_type != "case_law":
            continue

        checkpoint = checkpoints.get(source.source_id, {})
        last_success_at_raw = checkpoint.get("last_success_at")
        freshness_seconds, freshness_status = _compute_freshness(
            last_success_at=last_success_at_raw,
            update_cadence=source.update_cadence,
            now=now,
        )
        policy_entry = source_policy.get_source(source.source_id)

        case_law_sources.append(
            CaseLawSourceTransparencyItem(
                source_id=source.source_id,
                court=_COURT_BY_SOURCE_ID.get(source.source_id),
                instrument=source.instrument,
                url=str(source.url),
                update_cadence=source.update_cadence,
                source_class=policy_entry.source_class if policy_entry else None,
                production_ingest_allowed=(
                    policy_entry.production_ingest_allowed if policy_entry else None
                ),
                answer_citation_allowed=(
                    policy_entry.answer_citation_allowed if policy_entry else None
                ),
                export_fulltext_allowed=(
                    policy_entry.export_fulltext_allowed if policy_entry else None
                ),
                last_success_at=(
                    last_success_at_raw
                    if isinstance(last_success_at_raw, str) and last_success_at_raw.strip()
                    else None
                ),
                last_http_status=_normalize_http_status(
                    checkpoint.get("last_http_status")
                ),
                freshness_seconds=freshness_seconds,
                freshness_status=freshness_status,
            )
        )

    case_law_sources.sort(
        key=lambda item: (
            _COURT_SORT_ORDER.get(item.court or "", 99),
            item.source_id,
        )
    )

    return SourceTransparencyResponse(
        jurisdiction=source_registry.jurisdiction,
        registry_version=source_registry.version,
        generated_at=_utc_now_iso(),
        supported_courts=sorted(
            supported_courts,
            key=lambda court: _COURT_SORT_ORDER.get(court, 99),
        ),
        checkpoint=SourceTransparencyCheckpoint(
            path=str(checkpoint_path),
            exists=checkpoint_exists,
            updated_at=checkpoint_updated_at,
        ),
        case_law_sources=case_law_sources,
    )


def build_source_transparency_router(
    *,
    source_registry: SourceRegistry | None,
    source_policy: SourcePolicy | None,
    checkpoint_state_path: str,
) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["source-transparency"])

    def _error_response(
        *,
        status_code: int,
        trace_id: str,
        code: str,
        message: str,
        policy_reason: str | None = None,
    ) -> JSONResponse:
        error = ErrorEnvelope(
            error={
                "code": code,
                "message": message,
                "trace_id": trace_id,
                "policy_reason": policy_reason,
            }
        )
        return JSONResponse(
            status_code=status_code,
            content=error.model_dump(mode="json"),
            headers={"x-trace-id": trace_id},
        )

    @router.get(
        "/sources/transparency",
        response_model=SourceTransparencyResponse,
    )
    async def source_transparency(
        request: Request,
        response: Response,
    ) -> SourceTransparencyResponse | JSONResponse:
        trace_id = getattr(request.state, "trace_id", "")
        response.headers["x-trace-id"] = trace_id

        if source_registry is None or source_policy is None:
            return _error_response(
                status_code=503,
                trace_id=trace_id,
                code="SOURCE_UNAVAILABLE",
                message=(
                    "Source transparency is unavailable because source registry/policy assets "
                    "could not be loaded."
                ),
                policy_reason="source_transparency_assets_missing",
            )

        return build_source_transparency_payload(
            source_registry=source_registry,
            source_policy=source_policy,
            checkpoint_state_path=checkpoint_state_path,
        )

    return router
