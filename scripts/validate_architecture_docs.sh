#!/usr/bin/env bash
set -euo pipefail

required_files=(
  "docs/architecture/README.md"
  "docs/architecture/01-system-context.md"
  "docs/architecture/02-container-and-service-architecture.md"
  "docs/architecture/03-component-and-module-architecture.md"
  "docs/architecture/04-data-architecture.md"
  "docs/architecture/05-security-and-compliance-architecture.md"
  "docs/architecture/06-quality-attributes-and-cross-cutting.md"
  "docs/architecture/07-deployment-and-operations.md"
  "docs/architecture/08-architecture-debt-and-improvement-plan.md"
  "docs/architecture/09-documentation-automation.md"
  "docs/architecture/arc42-overview.md"
  "docs/architecture/api-contracts.md"
  "docs/architecture/adr/ADR-000-template.md"
)

for file in "${required_files[@]}"; do
  if [[ ! -f "$file" ]]; then
    echo "Missing required architecture file: $file"
    exit 1
  fi
  echo "[OK] $file"
done

adr_count="$(find docs/architecture/adr -maxdepth 1 -type f -name 'ADR-*.md' ! -name 'ADR-000-template.md' | wc -l | tr -d ' ')"
if [[ "$adr_count" -lt 3 ]]; then
  echo "Expected at least 3 ADR decision files, found $adr_count"
  exit 1
fi

echo "[OK] ADR count: $adr_count"

mermaid_count="$(rg -n '```mermaid' docs/architecture | wc -l | tr -d ' ')"
if [[ "$mermaid_count" -lt 3 ]]; then
  echo "Expected at least 3 Mermaid diagrams, found $mermaid_count"
  exit 1
fi

echo "[OK] Mermaid diagrams: $mermaid_count"

if [[ ! -f docs/architecture/diagrams/generated-module-dependencies.mmd ]]; then
  echo "Missing generated module dependency diagram"
  exit 1
fi

echo "Architecture documentation validation passed."
