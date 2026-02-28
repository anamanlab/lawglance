from __future__ import annotations

import logging
from typing import Dict

from immcad_api.policy import SourcePolicy
from immcad_api.schemas import SourceFreshnessStatus
from immcad_api.services.source_transparency_service import (
    build_source_transparency_payload,
)
from immcad_api.sources import SourceRegistry

PRIORITY_CASELAW_SOURCE_IDS = ("SCC_DECISIONS", "FC_DECISIONS")
LOGGER = logging.getLogger(__name__)


def build_priority_source_status_snapshot(
    *,
    source_registry: SourceRegistry,
    source_policy: SourcePolicy,
    checkpoint_state_path: str,
) -> Dict[str, SourceFreshnessStatus]:
    snapshot: Dict[str, SourceFreshnessStatus] = {
        source_id: "missing" for source_id in PRIORITY_CASELAW_SOURCE_IDS
    }

    try:
        transparency = build_source_transparency_payload(
            source_registry=source_registry,
            source_policy=source_policy,
            checkpoint_state_path=checkpoint_state_path,
        )
    except Exception:
        LOGGER.exception(
            "Failed to build priority source status snapshot",
            extra={"checkpoint_state_path": checkpoint_state_path},
        )
        return snapshot

    items = {item.source_id: item for item in transparency.case_law_sources}
    for source_id in PRIORITY_CASELAW_SOURCE_IDS:
        item = items.get(source_id)
        if item is None:
            continue
        snapshot[source_id] = item.freshness_status
    return snapshot
