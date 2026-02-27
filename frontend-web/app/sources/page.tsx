"use client";

import { useEffect, useMemo, useState } from "react";

type SourceTransparencyCheckpoint = {
  path: string;
  exists: boolean;
  updated_at?: string | null;
};

type CaseLawSourceTransparencyItem = {
  source_id: string;
  court?: string | null;
  instrument: string;
  url: string;
  update_cadence: string;
  source_class?: string | null;
  production_ingest_allowed?: boolean | null;
  answer_citation_allowed?: boolean | null;
  export_fulltext_allowed?: boolean | null;
  freshness_status: "fresh" | "stale" | "missing" | "unknown";
  freshness_seconds?: number | null;
  last_success_at?: string | null;
  last_http_status?: number | null;
};

type SourceTransparencyPayload = {
  jurisdiction: string;
  registry_version: string;
  generated_at: string;
  supported_courts: string[];
  checkpoint: SourceTransparencyCheckpoint;
  case_law_sources: CaseLawSourceTransparencyItem[];
};

function formatDate(value?: string | null): string {
  if (!value) {
    return "n/a";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.valueOf())) {
    return value;
  }
  return parsed.toISOString().replace(".000Z", "Z");
}

function formatFreshness(item: CaseLawSourceTransparencyItem): string {
  const seconds = item.freshness_seconds;
  if (typeof seconds !== "number" || !Number.isFinite(seconds)) {
    return item.freshness_status;
  }
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  if (hours >= 1) {
    return `${item.freshness_status} (${hours}h)`;
  }
  return `${item.freshness_status} (${minutes}m)`;
}

function formatPolicyFlag(value?: boolean | null): string {
  if (value === true) {
    return "yes";
  }
  if (value === false) {
    return "no";
  }
  return "n/a";
}

async function fetchSourceTransparency(): Promise<SourceTransparencyPayload> {
  const response = await fetch("/api/sources/transparency", {
    method: "GET",
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`source transparency request failed (${response.status})`);
  }
  return (await response.json()) as SourceTransparencyPayload;
}

export default function SourceTransparencyPage(): JSX.Element {
  const [payload, setPayload] = useState<SourceTransparencyPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load(): Promise<void> {
      try {
        const nextPayload = await fetchSourceTransparency();
        if (!cancelled) {
          setPayload(nextPayload);
        }
      } catch {
        if (!cancelled) {
          setError("Unable to load source transparency data.");
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  const supportedCourtsLabel = useMemo(() => {
    if (!payload || payload.supported_courts.length === 0) {
      return "Supported courts: n/a";
    }
    return `Supported courts: ${payload.supported_courts.join(", ")}`;
  }, [payload]);

  return (
    <main className="min-h-screen px-4 py-8 md:px-8">
      <div className="mx-auto w-full max-w-6xl space-y-4">
        <section className="rounded-2xl border border-[var(--imm-border-soft)] bg-[var(--imm-surface-soft)] p-6 shadow-sm">
          <h1 className="text-2xl font-semibold text-ink">Source Transparency</h1>
          <p className="mt-2 text-sm text-muted">
            Track case-law source coverage and ingestion freshness.
          </p>
          {payload ? (
            <div className="mt-3 space-y-1 text-sm text-[var(--imm-text-muted)]">
              <p>{supportedCourtsLabel}</p>
              <p>Registry version: {payload.registry_version}</p>
              <p>Checkpoint state path: {payload.checkpoint.path}</p>
              <p>Checkpoint updated: {formatDate(payload.checkpoint.updated_at)}</p>
            </div>
          ) : null}
        </section>

        {error ? (
          <section className="rounded-2xl border border-[rgba(172,63,47,0.22)] bg-[var(--imm-danger-soft)] p-4 text-sm text-[var(--imm-danger-ink)]">
            {error}
          </section>
        ) : null}

        {!payload && !error ? (
          <section className="rounded-2xl border border-[var(--imm-border-soft)] bg-[var(--imm-surface-soft)] p-4 text-sm text-muted">
            Loading source transparency data...
          </section>
        ) : null}

        {payload ? (
          <section className="rounded-2xl border border-[var(--imm-border-soft)] bg-[var(--imm-surface-soft)] p-4 shadow-sm">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-[var(--imm-border-soft)] text-left text-sm">
                <thead className="bg-[var(--imm-surface-warm)] text-xs uppercase tracking-wide text-muted">
                  <tr>
                    <th className="px-3 py-2">Source ID</th>
                    <th className="px-3 py-2">Court</th>
                    <th className="px-3 py-2">Class</th>
                    <th className="px-3 py-2">Cadence</th>
                    <th className="px-3 py-2">Freshness</th>
                    <th className="px-3 py-2">Last Success</th>
                    <th className="px-3 py-2">HTTP</th>
                    <th className="px-3 py-2">Policy</th>
                    <th className="px-3 py-2">URL</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[rgba(159,154,142,0.22)]">
                  {payload.case_law_sources.map((item) => (
                    <tr key={item.source_id} className="align-top">
                      <td className="px-3 py-2 font-medium text-ink">{item.source_id}</td>
                      <td className="px-3 py-2 text-[var(--imm-text-muted)]">
                        {item.court ?? "n/a"}
                        {item.source_id === "SCC_DECISIONS" || item.source_id === "FC_DECISIONS" ? (
                          <span className="ml-2 rounded-full border border-[rgba(95,132,171,0.35)] bg-[var(--imm-accent-soft)] px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-[0.08em] text-[var(--imm-accent-ink)]">
                            Priority
                          </span>
                        ) : null}
                      </td>
                      <td className="px-3 py-2 text-[var(--imm-text-muted)]">{item.source_class ?? "n/a"}</td>
                      <td className="px-3 py-2 text-[var(--imm-text-muted)]">{item.update_cadence}</td>
                      <td className="px-3 py-2 text-[var(--imm-text-muted)]">
                        {formatFreshness(item)}
                        {item.freshness_status === "stale" || item.freshness_status === "missing" ? (
                          <p className="mt-1 text-[11px] text-warning">Needs ingestion refresh.</p>
                        ) : null}
                      </td>
                      <td className="px-3 py-2 text-[var(--imm-text-muted)]">
                        {formatDate(item.last_success_at)}
                      </td>
                      <td className="px-3 py-2 text-[var(--imm-text-muted)]">
                        {item.last_http_status ?? "n/a"}
                      </td>
                      <td className="px-3 py-2 text-[var(--imm-text-muted)]">
                        ingest: {formatPolicyFlag(item.production_ingest_allowed)}
                        <br />
                        cite: {formatPolicyFlag(item.answer_citation_allowed)}
                        <br />
                        export: {formatPolicyFlag(item.export_fulltext_allowed)}
                      </td>
                      <td className="px-3 py-2 text-[var(--imm-text-muted)]">
                        <a
                          href={item.url}
                          rel="noreferrer"
                          target="_blank"
                          className="underline decoration-[rgba(159,154,142,0.75)] underline-offset-2 hover:decoration-[var(--imm-accent-ink)]"
                        >
                          Open source
                        </a>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        ) : null}
      </div>
    </main>
  );
}
