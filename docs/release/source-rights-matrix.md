# Source Rights Matrix (Canada Legal AI)

**Version:** 2026-02-24  
**Owner:** legal-compliance

This matrix is the human-readable counterpart to `config/source_policy.yaml`.

## Policy Summary

- `CanLII`: production-approved for metadata ingestion only; no full-text export.
- `A2AJ`: internal-only; blocked in production.
- `Refugee Law Lab`: internal-only; blocked in production.
- `SCC/FC/FCA` official endpoints: production-approved with citation requirements (see requirements below).

## Per-Source Controls

| source_id | class | internal ingest | production ingest | citation in answers | full-text export | notes |
|---|---|---|---|---|---|---|
| IRPA | official | yes | yes | yes | yes | Justice Laws statute text |
| IRPR | official | yes | yes | yes | yes | Justice Laws regulation text |
| CIT_ACT | official | yes | yes | yes | yes | Justice Laws statute text |
| CIT_REG | official | yes | yes | yes | yes | Justice Laws regulation text |
| CIT_REG_NO2 | official | yes | yes | yes | yes | Justice Laws regulation text |
| IRB_ID_RULES | official | yes | yes | yes | yes | Justice Laws regulation text |
| IRB_IAD_RULES | official | yes | yes | yes | yes | Justice Laws regulation text |
| IRB_RPD_RULES | official | yes | yes | yes | yes | Justice Laws regulation text |
| IRB_RAD_RULES | official | yes | yes | yes | yes | Justice Laws regulation text |
| PIPEDA | official | yes | yes | yes | yes | Justice Laws statute text |
| CASL | official | yes | yes | yes | yes | Justice Laws statute text |
| IRCC_PDI | official | yes | yes | yes | no | web policy pages |
| EE_MI_CURRENT | official | yes | yes | yes | no | web policy pages |
| EE_MI_INVITES | official | yes | yes | yes | no | web policy pages |
| CANLII_CASE_BROWSE | unofficial | yes | yes | yes | no | metadata-only API |
| CANLII_CASE_CITATOR | unofficial | yes | yes | yes | no | metadata-only API |
| CANLII_TERMS | unofficial | yes | yes | no | no | compliance reference |
| SCC_DECISIONS | official | yes | yes | yes | yes | official court source; cite style required (see below) |
| FC_DECISIONS | official | yes | yes | yes | yes | official court source; cite style required (see below) |
| FCA_DECISIONS | official | yes | yes | yes | yes | official court source; cite style required (see below) |
| A2AJ | unofficial | yes | no | no | no | internal-only pending sign-off |
| REFUGEE_LAW_LAB | unofficial | yes | no | no | no | internal-only pending sign-off |

## Enforcement Requirements

1. Ingestion must block production runs for any source with `production_ingest_allowed = false`.
2. Unknown/unlisted sources must be blocked in production.
3. Full-text export must be denied for any source with `export_fulltext_allowed = false`.
4. All blocked actions must emit a structured audit event with source ID and policy reason.
5. Production responses must suppress citations when `answer_citation_allowed = false` (for example `CANLII_TERMS`) and emit a structured audit event with source ID and suppression reason.

### Citation requirements for SCC/FC/FCA

- Include the decision title (or neutral citation when available) and identify the court (`SCC`, `FC`, or `FCA`).
- Link citations to the official decision URL (HTTPS) in the answer body.
- Quote or summarize only the relevant passage and include a pinpoint/reference marker when available.
