.PHONY: setup verify dev api-dev lint lint-api format test arch-generate arch-validate source-registry-validate hygiene quality

setup:
	./scripts/setup_dev_env.sh

verify:
	./scripts/verify_dev_env.sh

dev:
	uv run streamlit run app.py

api-dev:
	uv run uvicorn immcad_api.main:app --app-dir src --reload --port 8000

lint:
	uv run ruff check .

lint-api:
	uv run ruff check src/immcad_api tests

format:
	uv run ruff format .

test:
	uv run pytest -q

arch-generate:
	uv run python scripts/generate_module_dependency_diagram.py

arch-validate:
	./scripts/validate_architecture_docs.sh

source-registry-validate:
	uv run python scripts/validate_source_registry.py

hygiene:
	bash scripts/check_repository_hygiene.sh

quality: lint-api test arch-validate source-registry-validate hygiene
