export const WORKFLOW_METRIC_EVENT_NAME = "immcad:workflow-metric";

export type WorkflowMetricName =
  | "workflow_mode_switch"
  | "workflow_switch_churn"
  | "workflow_abandonment"
  | "workflow_warning"
  | "research_retry_after_failure";

export type WorkflowMetricPayload = {
  details: Record<string, string | number | boolean | null>;
  name: WorkflowMetricName;
  timestamp: string;
};

export function emitWorkflowMetric(
  name: WorkflowMetricName,
  details: Record<string, string | number | boolean | null> = {}
): void {
  if (typeof window === "undefined") {
    return;
  }

  const payload: WorkflowMetricPayload = {
    details,
    name,
    timestamp: new Date().toISOString(),
  };

  window.dispatchEvent(
    new CustomEvent<WorkflowMetricPayload>(WORKFLOW_METRIC_EVENT_NAME, {
      detail: payload,
    })
  );
}

