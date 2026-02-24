from __future__ import annotations

import importlib.abc
import importlib.util
from pathlib import Path
import sys
from typing import cast

import pytest

from immcad_api.policy.prompts import QA_PROMPT as POLICY_QA_PROMPT
from immcad_api.policy.prompts import SYSTEM_PROMPT as POLICY_SYSTEM_PROMPT

REPO_ROOT = Path(__file__).resolve().parents[1]
LEGACY_PROMPTS_PATH = REPO_ROOT / "legacy" / "local_rag" / "prompts.py"


def _load_legacy_prompt_module():
    if not LEGACY_PROMPTS_PATH.exists():
        pytest.skip(f"legacy prompts file not found: {LEGACY_PROMPTS_PATH}")
    spec = importlib.util.spec_from_file_location("legacy_prompts", LEGACY_PROMPTS_PATH)
    if spec is None or spec.loader is None:
        raise FileNotFoundError(f"Unable to load legacy prompts module spec: {LEGACY_PROMPTS_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    loader = cast(importlib.abc.Loader, spec.loader)
    loader.exec_module(module)
    return module


def test_legacy_prompt_constants_match_policy_prompt_constants() -> None:
    module = _load_legacy_prompt_module()
    assert module.SYSTEM_PROMPT == POLICY_SYSTEM_PROMPT
    assert module.QA_PROMPT == POLICY_QA_PROMPT
