# Git-Secret Adoption Implementation Plan

> **For Claude/Codex:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task.

**Goal:** Add a repo-native `git-secret` workflow for encrypted environment bundles and team-shared configuration in IMMCAD, while preserving the existing policy that live production secrets remain in platform secret managers (GitHub/Vercel) and are not committed in plaintext.

**Architecture:** Use `git-secret` + GPG to store encrypted `.secret` artifacts for approved local/team workflows (for example, shared non-production env bundles or CI bootstrap files used only to populate platform-managed secrets). Keep decrypted `.env*` files local-only and continue using Vercel/GitHub secrets as the runtime source of truth for production/staging. Add repository hygiene checks, docs/runbooks, and optional CI reveal steps with explicit guardrails.

**Tech Stack:** `git-secret`, GnuPG (`gpg`), Bash, Make, GitHub Actions, Python 3.11 + `pytest`, Ruff.

---

## Notes From Crawled `git-secret` Docs (Plan Inputs)

- Core flow: `git secret init` -> `git secret tell <email>` -> `git secret add <files...>` -> `git secret hide` -> commit encrypted outputs -> `git secret reveal` when needed.
- `git secret init` creates `.gitsecret/`; the docs note that `.gitsecret/keys/random_seed` should remain ignored, while the rest of `.gitsecret/` should be tracked.
- `git secret add` updates `.gitignore` to help prevent accidental plaintext commits.
- The docs recommend using `git secret hide` from a pre-commit hook to avoid forgetting to re-encrypt changes.
- CI/CD pattern from docs: import a CI GPG private key (`gpg --batch --yes --pinentry-mode loopback --import`), then `git secret reveal` (optionally with passphrase) before build/deploy steps.
- Important compatibility caveat: keep local and CI `gpg` versions interoperable (ideally the same version), otherwise `reveal` can fail.

## Scope Decision (Recommended Before Implementation)

Use `git-secret` in this repo for:

- Team-shared encrypted env bundles used for local development and controlled bootstrap workflows.
- Optional CI bootstrap files (only if needed) that are decrypted in ephemeral runners.
- Key rotation / access management runbook for maintainers.

Do **not** use `git-secret` as a replacement for:

- GitHub Actions `secrets.*` values used directly in workflows.
- Vercel project environment variables used by deployed `frontend-web` / `backend-vercel`.
- Ad hoc storage of long-lived production secrets in developer machines.

This keeps IMMCAD aligned with existing docs that require platform secret managers for production.

## Proposed File/Secret Conventions

- Encrypted files: keep default `.secret` extension (example: `backend-vercel/.env.production.secret`).
- Decrypted files remain ignored (`.env`, `.env.*`) and are generated locally via `git secret reveal`.
- Track `.gitsecret/` contents except `.gitsecret/keys/random_seed`.
- Keep `.env.example` files as the schema/contract for required variables (unchanged role).

## Execution Order (Low Risk First)

1. Policy + naming decision and docs/runbook
2. Local tooling (`git-secret` wrappers / Make targets)
3. Repository hygiene guards + tests
4. CI support (optional, gated)
5. Pilot rollout with one encrypted sample env bundle (non-production only)

---

### Task 1: Define IMMCAD `git-secret` Scope, Naming, and Guardrails

**Files:**
- Modify: `README.md`
- Modify: `docs/development-environment.md`
- Modify: `docs/onboarding/developer-onboarding-guide.md`
- Create: `docs/release/git-secret-runbook.md`

**Step 1: Document the scope decision (what is allowed / not allowed)**
- State that production runtime secrets remain in GitHub/Vercel secrets managers.
- Define approved use cases for encrypted `.secret` files in git.

**Step 2: Define naming conventions**
- Standardize encrypted filename patterns for repo root and project subdirs (for example `frontend-web/.env.preview.secret`, `backend-vercel/.env.production.secret`).
- Document where decrypted files are expected after `reveal`.

**Step 3: Add operator runbook**
- Add maintainer procedures for:
  - generating GPG keys,
  - adding/removing users (`tell`, `removeperson`),
  - re-encrypting after access changes,
  - emergency revocation and rotation.

**Step 4: Verify docs consistency**
- Run: `./scripts/validate_architecture_docs.sh`
- Run: `./scripts/venv_exec.sh python scripts/doc_maintenance/main.py --dry-run`
- Expected: docs checks pass; no instruction contradicts platform-managed production secret policy.

---

### Task 2: Add Local `git-secret` Tooling and Make Targets

**Files:**
- Modify: `Makefile`
- Create: `scripts/git_secret_env.sh`
- Modify: `scripts/setup_dev_env.sh`
- Modify: `scripts/verify_dev_env.sh`

**Step 1: Add a thin wrapper script for consistent local usage**
- Implement `scripts/git_secret_env.sh` to:
  - check `git secret --version`,
  - check `gpg --version`,
  - emit actionable install help,
  - optionally enforce/configure `SECRETS_GPG_COMMAND`.

**Step 2: Add Make targets**
- Add non-destructive targets such as:
  - `git-secret-check`
  - `git-secret-reveal`
  - `git-secret-hide`
  - `git-secret-list`
  - `git-secret-changes`
- Make targets should call the wrapper and fail clearly when tools are missing.

**Step 3: Add setup/verify hints (not hard requirement)**
- `setup_dev_env.sh`: print optional `git-secret` setup guidance without forcing install.
- `verify_dev_env.sh`: detect presence/absence of `git-secret` and `gpg` and report status (warning, not failure, unless a repo marker indicates secrets are required).

**Step 4: Verify locally**
- Run: `make git-secret-check`
- Run: `make verify`
- Expected: no plaintext secrets are created; commands provide clear status/help.

---

### Task 3: Bootstrap Repository `git-secret` Metadata Safely

**Files:**
- Modify: `.gitignore`
- Create (generated by command, then reviewed/committed): `.gitsecret/`
- Modify: `scripts/check_repository_hygiene.sh`
- Modify: `tests/test_repository_hygiene_script.py`

**Step 1: Initialize `git-secret` metadata in a controlled branch**
- Run `git secret init` once after agreeing on scope.
- Review `.gitignore` changes and `.gitsecret/` contents before commit.

**Step 2: Harden `.gitignore` expectations**
- Ensure:
  - `.gitsecret/keys/random_seed` stays ignored
  - encrypted `*.secret` files can be tracked (especially alongside `.env.*` ignore rules)
- Keep existing `.env` / `.env.*` plaintext ignore behavior intact.

**Step 3: Extend repository hygiene checks**
- Update `scripts/check_repository_hygiene.sh` to validate `git-secret` invariants if `.gitsecret/` exists:
  - fail if `.gitsecret/keys/random_seed` is tracked,
  - fail on tracked plaintext `.env*` files (excluding documented templates like `.env.example`) across repo subprojects, with remediation hints,
  - exclude tracked `*.secret` encrypted artifacts (and `/.gitsecret/` internals where appropriate) from regex secret-pattern scans to avoid false positives on encrypted blobs,
  - preserve existing high-risk secret pattern scan.

**Step 4: Add/extend regression tests**
- Extend `tests/test_repository_hygiene_script.py` for the new pass/fail contracts, including:
  - tracked `.gitsecret/keys/random_seed` failure,
  - encrypted `*.secret` fixture does not trigger regex secret-scan false positive.

**Step 5: Verify**
- Run: `./scripts/venv_exec.sh pytest -q tests/test_repository_hygiene_script.py`
- Run: `git check-ignore -v backend-vercel/.env.preview.secret` (after pilot init) to confirm encrypted artifact is not ignored by `.env.*` patterns
- Run: `bash scripts/check_repository_hygiene.sh`
- Expected: script passes for clean repos and fails with explicit messages for `git-secret` misuse.

---

### Task 4: Add Safe Encrypted Env Bundle Workflow (Pilot)

**Files:**
- Create (example encrypted artifacts during pilot): `backend-vercel/.env.preview.secret` (or agreed pilot target)
- Modify: `docs/development-environment.md`
- Modify: `docs/release/git-secret-runbook.md`
- Optional Create: `scripts/git_secret_reencrypt_all.sh`

**Step 1: Choose one pilot target (non-production)**
- Recommended first target: preview/staging env bundle for one subproject (`backend-vercel` or `frontend-web`).
- Avoid starting with production secrets.

**Step 2: Add and encrypt the pilot file**
- Use `git secret add <file>`
- Run `git secret hide` (or `hide -d` if the team agrees to delete the plaintext after encryption)
- Confirm encrypted output is present and plaintext remains ignored.

**Step 3: Document the exact local workflow**
- How to `reveal`, edit, `hide`, and verify diff without leaking plaintext.
- How to rotate values and re-encrypt.

**Step 4: Verify with existing env tooling**
- Run `scripts/vercel_env_sync.py validate` / `diff` using revealed file(s) in a local-only session.
- Confirm backups remain in `.env-backups/` and plaintext files are not accidentally tracked.
- Explicitly document that `.env-backups/` artifacts are plaintext local backups (ignored by git) and are not a `git-secret` replacement or commit target.

**Step 5: Verification commands**
- Run: `./scripts/venv_exec.sh pytest -q tests/test_vercel_env_sync.py`
- Run: `make vercel-env-validate PROJECT_DIR=backend-vercel ENV=preview` (using local revealed env file, if available)
- Expected: existing env sync tooling still works with the documented reveal/hide workflow.

---

### Task 5: Add Optional Pre-Commit Guard / Helper for Re-encryption

**Files:**
- Create: `.githooks/pre-commit` (or project hook installer script if preferred)
- Create/Modify: `scripts/install_git_hooks.sh` (if adding managed hooks)
- Modify: `docs/onboarding/developer-onboarding-guide.md`
- Modify: `docs/release/git-secret-runbook.md`

**Step 1: Implement an opt-in pre-commit helper**
- Recommended behavior:
  - detect if `git-secret` is installed and `.gitsecret/` exists,
  - run `git secret hide` only when tracked secret source files changed,
  - fail safely with a clear message if re-encryption is required but fails.

**Step 2: Keep it opt-in initially**
- Do not block all contributors until the team validates UX and false-positive rate.

**Step 3: Document installation**
- Add one command to enable hooks locally (for example `git config core.hooksPath .githooks`).

**Step 4: Verify**
- Test on a sample change to a revealed file and confirm encrypted artifacts are updated before commit.

---

### Task 6: Add CI Reveal Workflow (Gated, Optional)

**Files:**
- Modify: `.github/workflows/quality-gates.yml` (only if CI decryption is needed for tests)
- Modify: `.github/workflows/release-gates.yml` (only if CI decryption is needed for release prep)
- Modify: `tests/test_quality_gates_workflow.py`
- Modify: `tests/test_release_gates_workflow.py`
- Modify: `docs/release/git-secret-runbook.md`

**Step 1: Decide if CI actually needs `git-secret reveal`**
- If CI can keep using `secrets.*` directly, skip workflow changes and document local-only usage.
- If CI needs encrypted env bundles, proceed with explicit security review.

**Step 2: Add secure CI import/reveal steps (if approved)**
- Install `git-secret` and ensure `gpg` is present.
- Avoid copy-pasting deprecated package-install snippets (for example `apt-key`) from older docs into GitHub Actions; prefer runner-supported packages or a pinned/manual install step documented in the runbook.
- Import CI private key using non-interactive flags (`--batch --yes --pinentry-mode loopback`).
- Run `git secret reveal` before steps that consume the decrypted files.
- Clean up temporary private key material after reveal/import.
- Log `git secret --version` and `gpg --version` (non-sensitive) in CI for interoperability troubleshooting.

**Step 3: Add workflow contract tests**
- Extend workflow tests to assert:
  - presence of guarded reveal step(s),
  - no plaintext secret echoing/logging,
  - use of GitHub secrets for CI GPG key/passphrase,
  - no deprecated `apt-key`-based install snippet in workflows (if install step is introduced),
  - cleanup steps.

**Step 4: Verify**
- Run: `./scripts/venv_exec.sh pytest -q tests/test_quality_gates_workflow.py tests/test_release_gates_workflow.py`
- Expected: workflow contract tests remain green with the new steps.

---

### Task 7: Add Team Access-Management and Rotation Procedure

**Files:**
- Modify: `docs/release/git-secret-runbook.md`
- Modify: `README.md` (link to runbook)

**Step 1: Document onboarding flow**
- Public key export/import, secure transfer expectations, `git secret tell`, and required re-encryption after adding users.

**Step 2: Document offboarding flow**
- `git secret removeperson`, immediate rotation/re-encryption expectations, and verification checklist.

**Step 3: Document GPG compatibility requirements**
- Pin/recommend supported `gpg` version(s) for local and CI.
- Add troubleshooting for common `reveal` failures caused by incompatible keyrings/versions.

**Step 4: Verify**
- Dry-run the documented commands with test keys in a scratch repo before marking the runbook complete.

---

### Task 8: Rollout Checklist and Final Verification

**Files:**
- Modify: `tasks/todo.md` (track rollout status + evidence)
- Modify: `docs/development-environment.md` / `README.md` links if moved during implementation

**Step 1: Pilot completion criteria**
- One encrypted non-production env bundle committed successfully.
- At least two maintainers can reveal/hide successfully.
- Repository hygiene checks catch `git-secret` misuse cases.

**Step 2: Final verification**
- Run:
  - `./scripts/venv_exec.sh pytest -q tests/test_repository_hygiene_script.py tests/test_vercel_env_sync.py tests/test_quality_gates_workflow.py tests/test_release_gates_workflow.py`
  - `./scripts/venv_exec.sh ruff check scripts tests`
  - `bash scripts/check_repository_hygiene.sh`
  - `make verify`
- Expected: all pass; no tracked plaintext `.env*` files; `.gitsecret/keys/random_seed` untracked.

**Step 3: Review and evidence**
- Add a `## Review` section entry in `tasks/todo.md` documenting:
  - files changed
  - pilot target used
  - verification commands + outputs
  - any CI decision (enabled vs deferred)

---

## Implementation Risks / Watchouts

- **Policy drift risk:** `git-secret` can be misread as permission to store production secrets in git. Keep docs explicit that encrypted-in-git is a controlled workflow, not a replacement for platform secret managers.
- **GPG version interoperability:** The `git-secret` docs warn about keyring compatibility issues across `gpg` versions. Pin/test local and CI versions before rollout.
- **DX friction:** Contributors without GPG / `git-secret` installed should not be blocked unless they need to modify encrypted env bundles.
- **Accidental plaintext commits:** Mitigate with `.gitignore`, hygiene checks, and optional pre-commit helper.
- **Secret-scan false positives on encrypted files:** `git grep`-based regex scanning can produce false positives/noisy output on tracked encrypted blobs; exclude `*.secret` from plaintext secret regex scans while retaining other hygiene checks.
- **Workflow sprawl:** Only add CI reveal steps if there is a concrete need; otherwise keep the first rollout local-only.

## Suggested Pilot Choice (Recommended)

- Start with `backend-vercel/.env.preview` (encrypted as `backend-vercel/.env.preview.secret`) because:
  - it is lower risk than production,
  - it directly supports existing `scripts/vercel_env_sync.py` workflows,
  - it exercises the repo’s current environment management path without changing runtime code.
