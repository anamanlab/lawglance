from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "validate_legal_review_checklist.py"
SPEC = importlib.util.spec_from_file_location("validate_legal_review_checklist", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_checklist_structure_validation_passes() -> None:
    checklist_path = Path("docs/release/legal-review-checklist.md")
    MODULE.validate(checklist_path, require_checked=False)


def test_checklist_strict_validation_fails_when_unchecked(tmp_path: Path) -> None:
    checklist = tmp_path / "checklist.md"
    checklist.write_text(
        "\n".join(
            [
                "- [x] Jurisdiction scope validated (Canada-only legal domain)",
                "- [ ] Citation-required behavior verified for legal factual responses",
                "- [x] Legal disclaimer text reviewed and approved",
                "- [x] Privacy/PII handling reviewed (PIPEDA-oriented controls)",
                "- [x] CanLII terms-of-use compliance reviewed",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unchecked required items"):
        MODULE.validate(checklist, require_checked=True)
