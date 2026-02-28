#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

primary_src="${repo_root}/src/immcad_api"
native_src="${repo_root}/backend-cloudflare/src/immcad_api"
primary_policy="${repo_root}/config/source_policy.yaml"
native_policy="${repo_root}/backend-cloudflare/config/source_policy.yaml"
primary_registry="${repo_root}/data/sources/canada-immigration/registry.json"
native_registry="${repo_root}/backend-cloudflare/data/sources/canada-immigration/registry.json"
primary_compilation_rules="${repo_root}/data/policy/document_compilation_rules.ca.json"
native_compilation_rules="${repo_root}/backend-cloudflare/data/policy/document_compilation_rules.ca.json"
native_package_compilation_rules="${repo_root}/backend-cloudflare/src/immcad_api/policy/document_compilation_rules.ca.json"

if [ ! -d "$primary_src" ]; then
  echo "ERROR: Primary backend source tree not found: $primary_src"
  exit 1
fi

if [ ! -f "$primary_policy" ]; then
  echo "ERROR: Source policy file not found: $primary_policy"
  exit 1
fi

if [ ! -f "$primary_registry" ]; then
  echo "ERROR: Source registry file not found: $primary_registry"
  exit 1
fi

if [ ! -f "$primary_compilation_rules" ]; then
  echo "ERROR: Document compilation rules file not found: $primary_compilation_rules"
  exit 1
fi

mkdir -p "$native_src"
rsync -a --delete --exclude "__pycache__/" --exclude "*.pyc" "$primary_src/" "$native_src/"

mkdir -p "$(dirname "$native_policy")"
cp "$primary_policy" "$native_policy"

mkdir -p "$(dirname "$native_registry")"
cp "$primary_registry" "$native_registry"

mkdir -p "$(dirname "$native_compilation_rules")"
cp "$primary_compilation_rules" "$native_compilation_rules"

mkdir -p "$(dirname "$native_package_compilation_rules")"
cp "$primary_compilation_rules" "$native_package_compilation_rules"

echo "[OK] Synced backend source/config/data for Cloudflare native Python Worker."
