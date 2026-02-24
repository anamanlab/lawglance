# Legacy Local-RAG Archive

This directory contains archived pre-convergence modules:

- `lawglance_main.py`
- `chains.py`
- `cache.py`
- `prompts.py`

These files are retained only for historical compatibility and reference.

Production runtime uses:

- `frontend-web/` (UI)
- `src/immcad_api/` (API, policy, providers, grounding)

Do not import modules from this archive into active codepaths.

## Supported Legacy Usage

- Import archived modules via package path, not root-level module names.
- Example:
  - `from legacy.local_rag.lawglance_main import Lawglance`
- Avoid direct script execution of archived modules; use package imports from notebooks/tools.

## Dependency Notes

- Archived local-RAG modules rely on optional legacy dependencies (`langchain*`, `redis`).
- Importing the package path is supported without eagerly importing all optional dependencies.
- Instantiating legacy runtime classes still requires those dependencies to be installed.
