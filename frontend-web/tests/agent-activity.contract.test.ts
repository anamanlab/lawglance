import { describe, expect, it } from "vitest";

import {
  buildInitialTurnEvents,
  upsertTurnStageEvent,
} from "@/components/chat/agent-activity";
import type { AgentActivityEvent } from "@/components/chat/types";

describe("agent activity timeline contract", () => {
  it("builds initial running timeline for a new assistant turn", () => {
    const events = buildInitialTurnEvents("turn-1", "2026-02-27T00:00:00.000Z");

    expect(events).toEqual([
      {
        id: "turn-1-intake",
        turnId: "turn-1",
        stage: "intake",
        status: "running",
        label: "Understanding question",
        startedAt: "2026-02-27T00:00:00.000Z",
      },
    ]);
  });

  it("appends a new stage event for the same turn", () => {
    const initialEvents = buildInitialTurnEvents("turn-1", "2026-02-27T00:00:00.000Z");

    const nextEvents = upsertTurnStageEvent(initialEvents, {
      turnId: "turn-1",
      stage: "retrieval",
      status: "running",
      label: "Searching case law",
      startedAt: "2026-02-27T00:00:01.000Z",
    });

    expect(initialEvents).toHaveLength(1);
    expect(nextEvents).toHaveLength(2);
    expect(nextEvents[1]).toMatchObject({
      id: "turn-1-retrieval",
      turnId: "turn-1",
      stage: "retrieval",
      status: "running",
      label: "Searching case law",
      startedAt: "2026-02-27T00:00:01.000Z",
    });
  });

  it("updates an existing stage event without mutating the original event", () => {
    const events: AgentActivityEvent[] = [
      {
        id: "turn-1-retrieval",
        turnId: "turn-1",
        stage: "retrieval",
        status: "running",
        label: "Searching case law",
        startedAt: "2026-02-27T00:00:01.000Z",
      },
    ];

    const nextEvents = upsertTurnStageEvent(events, {
      turnId: "turn-1",
      stage: "retrieval",
      status: "success",
      label: "Sources retrieved",
      endedAt: "2026-02-27T00:00:02.000Z",
      details: "Retrieved 3 relevant authorities.",
      meta: {
        sourceCount: 3,
        traceId: "trace-123",
      },
    });

    expect(events[0]?.status).toBe("running");
    expect(nextEvents).toEqual([
      {
        id: "turn-1-retrieval",
        turnId: "turn-1",
        stage: "retrieval",
        status: "success",
        label: "Sources retrieved",
        startedAt: "2026-02-27T00:00:01.000Z",
        endedAt: "2026-02-27T00:00:02.000Z",
        details: "Retrieved 3 relevant authorities.",
        meta: {
          sourceCount: 3,
          traceId: "trace-123",
        },
      },
    ]);
  });
});
