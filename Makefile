.PHONY: setup verify dev api-dev frontend-install frontend-dev frontend-build frontend-typecheck lint lint-api format test arch-generate arch-validate source-registry-validate legal-review-validate domain-leak-scan jurisdiction-eval jurisdiction-suite ingestion-run staging-smoke hygiene quality ralph-run ralph-run-codex ralph-run-amp ralph-run-claude ralph-check ralph-status

setup:
	./scripts/setup_dev_env.sh

verify:
	./scripts/verify_dev_env.sh

dev:
	./scripts/venv_exec.sh streamlit run app.py

api-dev:
	./scripts/venv_exec.sh uvicorn immcad_api.main:app --app-dir src --reload --port 8000

frontend-install:
	cd frontend-web && npm install

frontend-dev:
	cd frontend-web && npm run dev

frontend-build:
	cd frontend-web && npm run build

frontend-typecheck:
	cd frontend-web && npm run typecheck

lint:
	./scripts/venv_exec.sh ruff check .

lint-api:
	./scripts/venv_exec.sh ruff check src/immcad_api tests

format:
	./scripts/venv_exec.sh ruff format .

test:
	./scripts/venv_exec.sh pytest -q

arch-generate:
	./scripts/venv_exec.sh python scripts/generate_module_dependency_diagram.py

arch-validate:
	./scripts/validate_architecture_docs.sh

source-registry-validate:
	./scripts/venv_exec.sh python scripts/validate_source_registry.py

legal-review-validate:
	./scripts/venv_exec.sh python scripts/validate_legal_review_checklist.py

domain-leak-scan:
	./scripts/venv_exec.sh python scripts/scan_domain_leaks.py

jurisdiction-eval:
	./scripts/venv_exec.sh python scripts/generate_jurisdiction_eval_report.py

jurisdiction-suite:
	./scripts/venv_exec.sh python scripts/run_jurisdictional_test_suite.py

ingestion-run:
	./scripts/venv_exec.sh python scripts/run_ingestion_jobs.py

staging-smoke:
	bash scripts/run_api_smoke_tests.sh

hygiene:
	bash scripts/check_repository_hygiene.sh

quality: lint-api test arch-validate source-registry-validate legal-review-validate domain-leak-scan jurisdiction-eval jurisdiction-suite hygiene

ralph-run:
	bash scripts/ralph/ralph.sh --tool codex 10

ralph-run-codex:
	bash scripts/ralph/ralph.sh --tool codex 10

ralph-run-amp:
	bash scripts/ralph/ralph.sh --tool amp 10

ralph-run-claude:
	bash scripts/ralph/ralph.sh --tool claude 10

ralph-check:
	bash scripts/ralph/ralph.sh --tool codex --check

ralph-status:
	jq '.userStories[] | {id, title, priority, passes}' scripts/ralph/prd.json
