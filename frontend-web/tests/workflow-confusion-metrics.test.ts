import { describe, expect, it, vi } from "vitest";

import {
  emitWorkflowMetric,
  WORKFLOW_METRIC_EVENT_NAME,
} from "@/lib/workflow-confusion-metrics";

describe("workflow confusion metrics", () => {
  it("dispatches browser events with metric payload", () => {
    const dispatchSpy = vi.spyOn(window, "dispatchEvent");

    emitWorkflowMetric("workflow_mode_switch", {
      from_mode: "research",
      to_mode: "documents",
    });

    expect(dispatchSpy).toHaveBeenCalledTimes(1);
    const firstCallArgument = dispatchSpy.mock.calls[0]?.[0];
    expect(firstCallArgument).toBeInstanceOf(CustomEvent);

    const event = firstCallArgument as CustomEvent;
    expect(event.type).toBe(WORKFLOW_METRIC_EVENT_NAME);
    expect(event.detail).toEqual(
      expect.objectContaining({
        name: "workflow_mode_switch",
        details: {
          from_mode: "research",
          to_mode: "documents",
        },
      })
    );
  });
});

