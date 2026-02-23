from __future__ import annotations

import json
from pathlib import Path


def test_ralph_prd_json_shape_and_ordering() -> None:
    path = Path("scripts/ralph/prd.json")
    assert path.exists(), "scripts/ralph/prd.json is missing"

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["project"] == "IMMCAD"
    assert payload["branchName"].startswith("ralph/")
    stories = payload["userStories"]
    assert stories, "userStories must not be empty"

    ids = [story["id"] for story in stories]
    assert ids == [f"US-{i:03d}" for i in range(1, len(stories) + 1)]

    priorities = [story["priority"] for story in stories]
    assert priorities == sorted(priorities)

    for story in stories:
        assert isinstance(story["passes"], bool)
        assert story["notes"] == ""
        assert "Typecheck passes" in story["acceptanceCriteria"]
