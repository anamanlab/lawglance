# Backup and Recovery Operational Targets (Canada Scope)

Use this runbook to define and execute backup/recovery operations for IMMCAD production workloads that serve Canada immigration and citizenship workflows.

## Scope and Ownership

- Scope: production data paths required for Canada legal assistant continuity.
- Incident commander: on-call SRE (declares incident and drives recovery execution).
- Service recovery owner: backend lead (validates API/data integrity after restore).
- Compliance sign-off owner: legal/compliance lead (approves data handling before reopening traffic).

## Backup Frequency and Coverage

- Vector store persistence (`chroma_db_legal_bot_part1/` volume):
  - Incremental snapshot every hour.
  - Full backup daily at `02:00 UTC`.
- Ingestion metadata and checkpoint artifacts (`artifacts/ingestion/`):
  - Snapshot every hour aligned to vector incremental snapshots.
  - Full backup daily at `02:15 UTC`.
- Backup integrity:
  - Weekly restore verification of latest full backup plus incrementals.

## Retention and Pruning Policy

- Hourly snapshots retained for 7 days.
- Daily full backups retained for 90 days.
- Monthly compliance snapshots retained for 365 days.
- Pruning policy:
  - Run automated pruning daily after successful checksum verification.
  - Delete only snapshots that exceed retention windows and are not marked for incident/legal hold.

## Recovery Targets (RTO/RPO) and Responsible Roles

| Objective | Target | Responsible role | Notes |
| --- | --- | --- | --- |
| RTO (service recovery) | 4 hours | On-call SRE | Time to restore API service and reopen traffic safely |
| RPO (data loss tolerance) | 60 minutes | Backend lead | Maximum acceptable data loss for vector + ingestion metadata |

## Restore Verification Checklist

Use this checklist before traffic cutover:

- [ ] DR event declared; incident ticket opened with recovery start timestamp.
- [ ] Latest valid full backup selected and checksum verified.
- [ ] Required incremental snapshots applied in order.
- [ ] Ingestion metadata restored and replayed as needed.
- [ ] API health endpoint passes:

```bash
curl -sS http://localhost:8000/healthz | jq .
```

- [ ] Smoke checks pass (`/healthz`, sample chat request, sample case-search request).
- [ ] Traceability confirmed (request `x-trace-id` maps to structured logs).
- [ ] Legal/compliance sign-off recorded before reopening production traffic.

## Drill Cadence and Evidence

- Tabletop disaster-recovery drill: quarterly.
- Full failover simulation: annually.
- Drill owners:
  - On-call SRE runs execution timeline.
  - Backend lead validates service correctness.
  - Legal/compliance lead verifies Canada-only scope and data handling controls.
- Post-drill evidence:
  - Store checklist, timings, and gaps in incident records.
  - Track corrective actions to closure before the next drill window.
