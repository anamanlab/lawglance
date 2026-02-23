#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

CHECKBOX_PATTERN = re.compile(r"^- \[(?P<checked>[ xX])\] (?P<label>.+)$")
REQUIRED_ITEMS = [
    "Jurisdiction scope validated (Canada-only legal domain)",
    "Citation-required behavior verified for legal factual responses",
    "Jurisdictional readiness report generated and passed",
    "Jurisdictional behavior suite generated and passed",
    "Legal disclaimer text reviewed and approved",
    "Privacy/PII handling reviewed (PIPEDA-oriented controls)",
    "CanLII terms-of-use compliance reviewed",
]


def parse_checklist(path: Path) -> dict[str, bool]:
    if not path.exists():
        raise FileNotFoundError(f"Checklist not found: {path}")

    item_states: dict[str, bool] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = CHECKBOX_PATTERN.match(line.strip())
        if not match:
            continue
        label = match.group("label").strip()
        checked = match.group("checked").lower() == "x"
        item_states[label] = checked
    return item_states


def validate(path: Path, *, require_checked: bool) -> None:
    states = parse_checklist(path)

    missing = [item for item in REQUIRED_ITEMS if item not in states]
    if missing:
        raise ValueError(f"Checklist missing required items: {', '.join(missing)}")

    if require_checked:
        unchecked = [item for item in REQUIRED_ITEMS if not states.get(item, False)]
        if unchecked:
            raise ValueError(f"Checklist contains unchecked required items: {', '.join(unchecked)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate legal review checklist.")
    parser.add_argument(
        "--path",
        default="docs/release/legal-review-checklist.md",
        help="Path to checklist file.",
    )
    parser.add_argument(
        "--require-checked",
        action="store_true",
        help="Require all mandatory checklist items to be checked.",
    )
    args = parser.parse_args()

    checklist_path = Path(args.path)
    validate(checklist_path, require_checked=args.require_checked)
    mode = "strict" if args.require_checked else "structure-only"
    print(f"[OK] Legal review checklist validation passed ({mode}).")


if __name__ == "__main__":
    main()
