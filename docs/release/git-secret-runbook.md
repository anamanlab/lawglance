# Git-Secret Runbook (IMMCAD)

Use this runbook to manage `git-secret` safely in IMMCAD for encrypted repository-stored configuration bundles.

This is a **controlled workflow** for encrypted files in git. It is **not** a replacement for GitHub Actions secrets, Vercel environment variables, or production secret management policy.

## Scope and Production Readiness Position

### Allowed (recommended)

- Encrypted non-production env bundles in git (for example preview/staging files).
- Team-shared local development/bootstrap config files that are safe to store encrypted in git.
- Optional CI bootstrap files only when a job cannot rely on platform-managed secrets directly.

### Not allowed (production policy)

- Replacing GitHub Actions `secrets.*` with repo-committed encrypted files for normal runtime secret delivery.
- Replacing Vercel environment variables for deployed `frontend-web` / `backend-vercel`.
- Treating `git-secret` re-encryption alone as offboarding/credential revocation.

## Core Risks (Read Before Use)

1. `git-secret` protects files in git at rest, but it does not provide secret-manager audit controls or runtime secret governance.
2. Removing a user from the `git-secret` keyring does **not** revoke access to old secrets they already decrypted or old commits they already cloned.
3. GPG version mismatches can break decryption/keyring operations across developer machines and CI.

## IMMCAD Defaults and Conventions

- Keep default encrypted extension: `.secret`
- Keep default metadata directory: `.gitsecret/`
- Track `.gitsecret/` contents **except** `.gitsecret/keys/random_seed`
- Keep plaintext env files ignored (`.env`, `.env.*`)
- Keep templates as `.env.example` (tracked)

Recommended pilot target:

- `backend-vercel/.env.preview` -> encrypted artifact `backend-vercel/.env.preview.secret`

## Prerequisites

- `git`
- `gpg`
- `git-secret`

Version guidance:

- Use the same (or explicitly tested interoperable) `gpg` version across local machines and CI.
- Record the validated versions during rollout (`git secret --version`, `gpg --version`) in release evidence.

## Local Setup (Maintainer / First-Time Repository Enablement)

1. Generate or confirm your GPG key pair:

```bash
gpg --gen-key
gpg --armor --export you@example.com > public-key.gpg
```

2. Initialize `git-secret` in the repo:

```bash
git secret init
```

3. Add the first authorized user:

```bash
git secret tell you@example.com
```

4. Add a file to be encrypted (pilot with non-production env file):

```bash
git secret add backend-vercel/.env.preview
```

5. Encrypt the tracked secret files:

```bash
git secret hide
```

6. Verify repo hygiene before commit:

```bash
bash scripts/check_repository_hygiene.sh
! git check-ignore -q backend-vercel/.env.preview.secret
```

The `git check-ignore` command above should succeed (exit `0`) only when a file **is** ignored, so this verification intentionally asserts the encrypted artifact is **not** ignored.

7. Stage and commit the encrypted artifact(s) plus `git-secret` metadata:

```bash
git add .gitsecret backend-vercel/.env.preview.secret .gitignore
git commit -m "chore(secrets): initialize git-secret for preview env bundle"
```

Notes:

- `git secret add` updates `.gitignore` to help prevent plaintext commits.
- Use `git secret hide -d` only if you intentionally want to delete the unencrypted file after encryption.

## Daily Workflow (Edit / Re-encrypt)

1. Reveal secrets locally:

```bash
git secret reveal
```

2. Edit the plaintext file(s) locally (for example `backend-vercel/.env.preview`).

3. Re-encrypt and optionally remove plaintext:

```bash
git secret hide
# or: git secret hide -d
```

4. Review encrypted changes:

```bash
git secret changes
git status
```

5. Run hygiene check before commit:

```bash
bash scripts/check_repository_hygiene.sh
```

## Optional Make Helpers (IMMCAD)

IMMCAD provides convenience wrappers that call `scripts/git_secret_env.sh` and preserve the same policy guidance:

```bash
make git-secret-check
make git-secret-reveal
make git-secret-hide
make git-secret-list
make git-secret-changes
```

Pass through extra command arguments (for example pathspecs/password flags) with `GIT_SECRET_ARGS`:

```bash
make git-secret-changes GIT_SECRET_ARGS="backend-vercel/.env.preview"
```

## Adding a Collaborator (Trusted Access)

1. Obtain their **public** key only.
2. Verify the key fingerprint out-of-band (required for production-safe handling):

```bash
gpg --show-keys --fingerprint public_key.gpg
```

3. Import the public key:

```bash
gpg --import public_key.gpg
```

4. Add them to the repo keyring:

```bash
git secret tell collaborator@example.com
```

5. Re-encrypt files with the updated keyring and push:

```bash
git secret reveal
git secret hide -d
git commit -am "chore(secrets): re-encrypt secrets for new collaborator"
git push
```

Important:

- A newly added collaborator cannot decrypt previously encrypted files until another authorized user re-encrypts and pushes them.

## Offboarding / Access Removal (Mandatory Rotation)

`git secret removeperson` is **not enough** for production-grade offboarding.

Required process:

1. Remove the collaborator from the `git-secret` keyring:

```bash
git secret removeperson collaborator@example.com
```

2. Re-encrypt files and commit:

```bash
git secret reveal
git secret hide -d
git commit -am "chore(secrets): remove collaborator and re-encrypt"
git push
```

3. Rotate underlying credentials they may have known (mandatory):

- API tokens (`OPENAI_API_KEY`, `GEMINI_API_KEY`, etc.)
- `IMMCAD_API_BEARER_TOKEN`
- Any third-party service credentials
- Any preview/staging secrets they could access

4. Update platform-managed secrets after rotation:

- GitHub Actions secrets
- Vercel environment variables

5. Record completion in release/ops evidence.

Why rotation is mandatory:

- Former collaborators may still have old clones or previously decrypted files.
- Re-encrypting only prevents decryption of newly encrypted blobs, not already-compromised values.

## CI/CD Use (Optional, Gated)

Use this only when CI must decrypt an encrypted file committed in the repo. Prefer platform-managed secrets directly when possible.

### CI policy

- Use a **dedicated CI decrypt key** (not a personal key).
- Prefer an ephemeral runner.
- Do not enable shell tracing (`set -x`) in jobs that touch key material.
- Log tool versions only (`git-secret`, `gpg`), never plaintext secret values.

### Required CI secrets

- `GPG_PRIVATE_KEY_B64` (base64-encoded armored secret key)
- `GPG_PASSPHRASE` (only if your CI key has a passphrase)

### Hardened CI reveal snippet

```bash
set -euo pipefail
umask 077

export GNUPGHOME="$(mktemp -d)"
key_file="$(mktemp)"

cleanup() {
  rm -f "$key_file"
  gpgconf --kill all >/dev/null 2>&1 || true
  rm -rf "$GNUPGHOME"
}
trap cleanup EXIT

git secret --version
gpg --version

printf '%s' "$GPG_PRIVATE_KEY_B64" | base64 -d > "$key_file"
gpg --batch --yes --pinentry-mode loopback --import "$key_file"

if [ -n "${GPG_PASSPHRASE:-}" ]; then
  git secret reveal -p "$GPG_PASSPHRASE"
else
  git secret reveal
fi
```

### CI anti-patterns (do not use)

- Personal developer GPG keys in CI
- Deprecated package-install snippets copied blindly from old docs (for example `apt-key`)
- `echo` of secret values to logs
- Reusing long-lived decrypt material on self-hosted runners without cleanup

## Environment Files and Vercel Sync (IMMCAD)

`git-secret` does not replace `scripts/vercel_env_sync.py`.

Recommended usage:

1. Reveal non-production env file locally.
2. Validate with:

```bash
python scripts/vercel_env_sync.py validate --project-dir backend-vercel --environment preview
```

3. Push to Vercel with the existing flow (`--dry-run` first).
4. Re-encrypt local file with `git secret hide`.

Notes:

- `.env-backups/` files are local plaintext backups created by env sync operations and are ignored by git.
- Do not commit `.env-backups/` contents.

## Pre-Commit Hook Guidance (Optional)

A local pre-commit hook can reduce mistakes by running `git secret hide` before commit. Keep it opt-in unless the whole team has `gpg` + `git-secret` installed and validated.

Hook behavior recommendations:

- Run only if `.gitsecret/` exists
- Skip clean working trees
- Fail with a clear message if `git secret hide` fails
- Avoid printing secret file contents

## Troubleshooting

### `git secret reveal` fails with missing decrypted file / keybox errors

Likely cause:

- GPG version/keyring incompatibility between local and CI or between collaborators.

Actions:

1. Compare:
   - `git secret --version`
   - `gpg --version`
2. Align to the validated GPG version used by the team.
3. Re-import public keys and re-encrypt if keyring metadata was modified by an incompatible version.

### CI import fails with `Inappropriate ioctl for device`

Use:

```bash
gpg --batch --yes --pinentry-mode loopback --import "$key_file"
```

### Repo hygiene scan flags encrypted artifacts

Ensure `scripts/check_repository_hygiene.sh` includes exclusions for:

- `*.secret`
- `.gitsecret/*`

## Production Readiness Checklist (Git-Secret Workflow)

Use this checklist before declaring `git-secret` usage production-safe in IMMCAD:

- [ ] Scope limited to approved use cases (no replacement of GitHub/Vercel runtime secrets)
- [ ] Dedicated CI decrypt key created (if CI decrypt is used)
- [ ] CI key storage + cleanup procedure validated
- [ ] GPG versions pinned/tested across local + CI
- [ ] Offboarding runbook includes mandatory credential rotation
- [ ] `scripts/check_repository_hygiene.sh` blocks plaintext `.env*` and tracked `.gitsecret/keys/random_seed`
- [ ] Repo hygiene tests pass (`tests/test_repository_hygiene_script.py`)
- [ ] Pilot completed with non-production env bundle and documented evidence

## Verification Commands (IMMCAD)

```bash
./scripts/venv_exec.sh pytest -q tests/test_repository_hygiene_script.py
./scripts/venv_exec.sh ruff check tests/test_repository_hygiene_script.py
bash scripts/check_repository_hygiene.sh
```
