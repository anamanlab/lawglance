import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import SourceTransparencyPage from "@/app/sources/page";

function jsonResponse(body: unknown, status: number = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "content-type": "application/json",
    },
  });
}

describe("source transparency page", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("renders supported courts and source freshness rows", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      jsonResponse({
        jurisdiction: "ca",
        registry_version: "2026-02-23",
        generated_at: "2026-02-27T00:00:00Z",
        supported_courts: ["SCC", "FC", "FCA"],
        checkpoint: {
          path: "artifacts/ingestion/checkpoints.json",
          exists: true,
          updated_at: "2026-02-27T00:00:00Z",
        },
        case_law_sources: [
          {
            source_id: "SCC_DECISIONS",
            court: "SCC",
            instrument: "Supreme Court of Canada decisions feed",
            url: "https://decisions.scc-csc.ca/scc-csc/scc-csc/en/json/rss.do",
            update_cadence: "scheduled_incremental",
            source_class: "official",
            production_ingest_allowed: true,
            answer_citation_allowed: true,
            export_fulltext_allowed: true,
            freshness_status: "fresh",
            freshness_seconds: 300,
            last_success_at: "2026-02-27T00:00:00Z",
            last_http_status: 200,
          },
          {
            source_id: "FC_DECISIONS",
            court: "FC",
            instrument: "Federal Court decisions RSS feed",
            url: "https://decisions.fct-cf.gc.ca/fc-cf/decisions/en/rss.do",
            update_cadence: "scheduled_incremental",
            source_class: "official",
            production_ingest_allowed: true,
            answer_citation_allowed: true,
            export_fulltext_allowed: true,
            freshness_status: "stale",
            freshness_seconds: 90000,
            last_success_at: "2026-02-25T00:00:00Z",
            last_http_status: 200,
          },
        ],
      })
    );

    render(<SourceTransparencyPage />);

    expect(screen.getByText("Source Transparency")).toBeTruthy();
    expect(await screen.findByText("Supported courts: SCC, FC, FCA")).toBeTruthy();
    expect(screen.getByText("SCC_DECISIONS")).toBeTruthy();
    expect(screen.getByText("FC_DECISIONS")).toBeTruthy();
    expect(screen.getByText("fresh (5m)")).toBeTruthy();
    expect(screen.getByText("stale (25h)")).toBeTruthy();
    expect(screen.getByText("Needs ingestion refresh.")).toBeTruthy();
    expect(screen.getAllByText("Open source").length).toBeGreaterThan(0);
  });

  it("renders an error state when the transparency request fails", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      jsonResponse({ error: { message: "backend unavailable" } }, 503)
    );

    render(<SourceTransparencyPage />);

    expect(await screen.findByText("Unable to load source transparency data.")).toBeTruthy();
  });
});
