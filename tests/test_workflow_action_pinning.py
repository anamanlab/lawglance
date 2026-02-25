from __future__ import annotations

import re
from pathlib import Path


WORKFLOWS_DIR = Path(__file__).resolve().parent.parent / ".github" / "workflows"
USES_PATTERN = re.compile(
    r"^\s*uses:\s+([A-Za-z0-9_.\-/]+)@([^\s#]+)(?:\s+#.*)?\s*$"
)
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


def test_all_github_actions_are_sha_pinned() -> None:
    mutable_refs: list[str] = []
    for workflow_path in sorted(WORKFLOWS_DIR.glob("*.yml")):
        for line_number, raw_line in enumerate(
            workflow_path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            match = USES_PATTERN.match(raw_line)
            if not match:
                continue
            action, ref = match.groups()
            if action.startswith("./"):
                continue
            if SHA_PATTERN.fullmatch(ref):
                continue
            mutable_refs.append(f"{workflow_path}:{line_number} -> {action}@{ref}")

    assert not mutable_refs, "Found non-SHA GitHub Action refs:\n" + "\n".join(mutable_refs)
