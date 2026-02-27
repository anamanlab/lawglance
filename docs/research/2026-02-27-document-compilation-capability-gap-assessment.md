# Document Compilation Capability Gap Assessment (Canada Immigration)

Date: 2026-02-27  
Owner: IMMCAD platform maintainers

## Purpose

Answer the operational question: what the current document compilation system can do now, what it cannot yet do, key risks, and the next improvements required for production-safe usage across Federal Court JR and IRB tribunals.

## Current Capability Snapshot

### What the system can do now

- Forum-aware rule evaluation for these forums:
  - `federal_court_jr` (profiles: `federal_court_jr_leave`, `federal_court_jr_hearing`)
  - `rpd`
  - `rad`
  - `id`
  - `iad` (profiles: `iad`, `iad_sponsorship`, `iad_residency`, `iad_admissibility`)
  - `ircc_application` (profile: `ircc_pr_card_renewal`)
- Profile-level required/conditional document checks from a versioned, source-cited catalog (`data/policy/document_compilation_rules.ca.json`).
- Translation conditional enforcement (`translation -> translator_declaration`).
- Ranked document-type classification candidates plus confidence scoring are implemented in the active code stream (effective in shared runtime once that stream lands).
- Deterministic assembly planning:
  - ordered TOC entries
  - page ranges per document
  - package pagination summary
- Readiness/package API outputs include:
  - `rule_violations[]` (blocking/warning with `rule_source_url`)
  - `toc_entries[]` with `start_page`/`end_page`
  - `pagination_summary`
  - `compilation_profile` (`id` + catalog `version`)
  - `compilation_output_mode` contract (`metadata_plan_only` or `compiled_pdf`), with current runtime mode `metadata_plan_only`
- Feature-flagged compiled binder path exists for `compiled_pdf` mode in controlled environments, but it is not the default runtime path.
- Intake OCR/extraction support:
  - native text extraction for supported signatures (`pdf/png/jpeg/tiff`)
  - optional Tesseract OCR fallback for scanned pages
  - OCR capability/confidence metadata per file
- Matter-level persistence of selected compilation profile ID (`compilation_profile_id`) in in-memory/Redis stores.
- Blocking compile enforcement at package endpoint (`409 POLICY_BLOCKED`) when readiness/rule violations fail.

### What the system cannot do yet

- Compiled output PDF binder generation is only partially implemented behind a feature flag; default/shared runtime remains metadata-only assembly (no generally available emitted merged filing PDF).
- No page-stamp mutation/bookmark writing into final PDF artifacts (TOC/page map is computed metadata only).
- No portal filing automation (Federal Court/IRB upload submission is out of scope).
- Procedural deadline engine is not yet comprehensive; core profile windows and override handling are implemented, but full tribunal-specific edge-case timing rules remain incomplete.
- No legal advice layer (procedural drafting only; not strategy/legal opinions).
- No broad immigration application profile coverage beyond current litigation forums (e.g., H&C/PRRA/work permit/study permit packages).

### Residual Limitations (Feature-Flagged Binder Path)

- Flag-off/default path still returns `metadata_plan_only`; binder artifacts are not the operational default.
- Coverage is incomplete for edge-case inputs (mixed scans, malformed PDFs, and OCR-heavy packages), so deterministic output quality is not yet guaranteed across all supported forums.
- Bookmark/page-stamp fidelity and validation guardrails are not yet fully enforced end-to-end in shared runtime operations.
- Operational controls for broad rollout (full CI matrix, runtime observability, and rollback playbook tied to binder mode) remain incomplete.

## Tribunal/Court Readiness Matrix

| Forum/Profile | Rule Checks | TOC + Page Ranges | Package Blocking | Notes |
|---|---|---|---|---|
| FC JR Leave (`federal_court_jr_leave`) | Yes | Yes (metadata) | Yes | Default FC JR profile |
| FC JR Hearing (`federal_court_jr_hearing`) | Yes | Yes (metadata) | Yes | Selectable via `compilation_profile_id` |
| RPD (`rpd`) | Yes | Yes (metadata) | Yes | Translation conditional enforced |
| RAD (`rad`) | Yes | Yes (metadata) | Yes | Decision-under-review requirement present |
| ID (`id`) | Yes | Yes (metadata) | Yes | Witness list requirement present |
| IAD (`iad`) | Yes | Yes (metadata) | Yes | Current rules source points to `SOR/2022-277` |
| IAD Sponsorship (`iad_sponsorship`) | Yes | Yes (metadata) | Yes | Explicit subtype profile; forum default remains `iad` |
| IAD Residency (`iad_residency`) | Yes | Yes (metadata) | Yes | Explicit subtype profile; forum default remains `iad` |
| IAD Admissibility (`iad_admissibility`) | Yes | Yes (metadata) | Yes | Explicit subtype profile; forum default remains `iad` |
| IRCC PR Card Renewal (`ircc_pr_card_renewal`) | Yes | Yes (metadata) | Yes | First non-litigation profile via `ircc_application` forum |

## Key Risk Areas / Potential Issues

1. Classification risk (partially mitigated): ranked candidates + confidence now reduce silent misclassification, but heuristic classification can still mislabel low-text/noisy files and trigger false missing-doc violations when confidence is low.
2. Metadata vs artifact gap (partially mitigated): API now declares `compilation_output_mode`, but users may still assume numbered/stamped final PDFs without checking mode.
3. Rule depth gap: some nuanced procedural constraints (timing, subtype variants, memorandum-length validation by path) remain partial.
4. OCR variability: scan quality, language quality, and OCR limits can cause `needs_review` outcomes and false negatives.
5. Record-section integration gap (in progress): record-builder wiring into package outputs has started, but a shared doc-type dictionary and full section coverage are still incomplete.

## Recommended Improvement Plan

### P0 (Immediate)

1. Implemented ambiguity mitigation: explicit `compilation_output_mode` contract (`metadata_plan_only` vs `compiled_pdf`) is now present in API outputs; current mode is `metadata_plan_only`.
2. Implemented: classification confidence + top alternatives to reduce silent misclassification.
3. Implemented: integration tests for profile selection defaults/overrides per forum and persisted matter state.

### P1 (Near-Term)

1. Complete and harden the feature-flagged binder PDF path (merge + bookmarks + stamped page numbering), then promote from flag-gated rollout once deterministic validation gates are in place.
2. Complete record-section wiring by normalizing doc-type mappings across classifier/catalog/builders and closing remaining section-coverage gaps.
3. Refine IAD subtype profiles (`sponsorship`, `residency`, `admissibility`) from shared baseline constraints to subtype-distinct procedural requirements.
4. Expand non-litigation profile families beyond PR card renewal (H&C, PRRA, work permit, study permit, citizenship proof) with source-cited constraints.

### P2 (Next)

1. Add procedural timing validator inputs (decision date, hearing date, service date) and deterministic deadline checks.
2. Add operational channel preflight checks (file size/count/channel-specific submission limits).
3. Add multilingual OCR quality evaluation + confidence calibration for French/other-language evidentiary sets.

## Operational Recommendation

Use current runtime as a **rule-aware readiness and compilation planning engine** (strong for completeness/ordering checks), not as a full filing-automation or final-PDF production engine yet.
