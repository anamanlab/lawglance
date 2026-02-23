# Canada Immigration Source Registry

This folder stores the canonical source registry for Canada-focused ingestion.

- `registry.json`: authoritative list of legal/policy/case-law sources for MVP.

Validation:

```bash
uv run pytest -q tests/test_canada_registry.py
```
