from __future__ import annotations

from pathlib import Path


BACKEND_REQUIREMENTS_PATH = Path("backend-vercel/requirements.txt")
SOURCE_POLICY_PATH = Path("src/immcad_api/policy/source_policy.py")


def _load_backend_requirements() -> tuple[str, ...]:
    lines = BACKEND_REQUIREMENTS_PATH.read_text(encoding="utf-8").splitlines()
    return tuple(
        line.strip().lower()
        for line in lines
        if line.strip() and not line.strip().startswith("#")
    )


def test_backend_vercel_runtime_includes_yaml_parser_dependency() -> None:
    source_policy_module = SOURCE_POLICY_PATH.read_text(encoding="utf-8")
    if "import yaml" not in source_policy_module:
        return

    requirements = _load_backend_requirements()
    assert any(
        requirement.startswith("pyyaml") for requirement in requirements
    ), (
        "backend-vercel/requirements.txt must include a PyYAML dependency because "
        "src/immcad_api/policy/source_policy.py imports yaml."
    )
