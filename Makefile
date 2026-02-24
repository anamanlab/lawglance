.PHONY: setup verify dev api-dev frontend-install frontend-dev frontend-build frontend-typecheck lint lint-api format test arch-generate arch-validate docs-audit docs-fix source-registry-validate backend-vercel-sync-validate legal-review-validate domain-leak-scan jurisdiction-eval jurisdiction-suite ingestion-run ingestion-smoke ops-alert-eval staging-smoke canlii-key-verify canlii-live-smoke hygiene quality integration-quality ralph-run ralph-run-codex ralph-run-amp ralph-run-claude ralph-check ralph-status vercel-env-analyze vercel-env-pull vercel-env-diff vercel-env-validate vercel-env-push-dry-run vercel-env-backup vercel-env-restore

PROJECT_DIR ?= frontend-web
ENV ?= development
TS ?=

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

docs-audit:
	./scripts/venv_exec.sh python scripts/doc_maintenance/main.py --dry-run

docs-fix:
	./scripts/venv_exec.sh python scripts/doc_maintenance/main.py --fix

source-registry-validate:
	./scripts/venv_exec.sh python scripts/validate_source_registry.py

backend-vercel-sync-validate:
	./scripts/venv_exec.sh python scripts/validate_backend_vercel_source_sync.py

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

ingestion-smoke:
	./scripts/venv_exec.sh python scripts/run_ingestion_smoke.py

ops-alert-eval:
	mkdir -p artifacts/ops
	./scripts/venv_exec.sh python scripts/evaluate_ops_alerts.py --thresholds config/ops_alert_thresholds.json --output artifacts/ops/ops-alert-eval.json

staging-smoke:
	bash scripts/run_api_smoke_tests.sh

canlii-key-verify:
	bash scripts/verify_canlii_api_key.sh

canlii-live-smoke:
	bash scripts/run_canlii_live_smoke.sh

hygiene:
	bash scripts/check_repository_hygiene.sh

quality: lint-api test arch-validate docs-audit source-registry-validate backend-vercel-sync-validate legal-review-validate domain-leak-scan jurisdiction-eval jurisdiction-suite hygiene

integration-quality: quality ingestion-smoke

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

vercel-env-analyze:
	./scripts/venv_exec.sh python scripts/vercel_env_sync.py analyze --project-dir $(PROJECT_DIR)

vercel-env-pull:
	./scripts/venv_exec.sh python scripts/vercel_env_sync.py pull --project-dir $(PROJECT_DIR) --environment $(ENV)

vercel-env-diff:
	./scripts/venv_exec.sh python scripts/vercel_env_sync.py diff --project-dir $(PROJECT_DIR) --environment $(ENV)

vercel-env-validate:
	./scripts/venv_exec.sh python scripts/vercel_env_sync.py validate --project-dir $(PROJECT_DIR) --environment $(ENV)

vercel-env-push-dry-run:
	./scripts/venv_exec.sh python scripts/vercel_env_sync.py push --project-dir $(PROJECT_DIR) --environment $(ENV) --dry-run

vercel-env-backup:
	./scripts/venv_exec.sh python scripts/vercel_env_sync.py backup --project-dir $(PROJECT_DIR)

vercel-env-restore:
	$(if $(strip $(TS)),,$(error TS is required for vercel-env-restore (e.g. TS=YYYYMMDD_HHMMSS)))
	./scripts/venv_exec.sh python scripts/vercel_env_sync.py restore --project-dir $(PROJECT_DIR) --timestamp $(TS)
