import { DOCUMENT_UPLOAD_DEFAULT_STATUS } from "@/components/chat/constants";

export type WorkflowStatusTone = "info" | "success" | "warning";

export type WorkflowRailStatus = {
  detail: string | null;
  label: string;
  tone: WorkflowStatusTone;
};

export type WorkflowBannerStatus = {
  message: string;
  title: string;
  tone: WorkflowStatusTone;
} | null;

export type WorkflowStatusContract = {
  documents: WorkflowRailStatus;
  overall: WorkflowBannerStatus;
  research: WorkflowRailStatus;
};

type BuildWorkflowStatusParams = {
  documentStatusMessage: string;
  isCaseSearchSubmitting: boolean;
  isDocumentDownloadSubmitting: boolean;
  isDocumentIntakeSubmitting: boolean;
  isDocumentPackageSubmitting: boolean;
  isDocumentReadinessSubmitting: boolean;
  relatedCasesStatus: string;
};

function classifyTone(message: string): WorkflowStatusTone {
  const normalizedMessage = message.toLowerCase();
  if (
    normalizedMessage.includes("failed") ||
    normalizedMessage.includes("error") ||
    normalizedMessage.includes("blocked") ||
    normalizedMessage.includes("not ready") ||
    normalizedMessage.includes("unavailable")
  ) {
    return "warning";
  }
  if (
    normalizedMessage.includes("complete") ||
    normalizedMessage.includes("ready") ||
    normalizedMessage.includes("generated") ||
    normalizedMessage.includes("available")
  ) {
    return "success";
  }
  return "info";
}

function normalizeDocumentStatus(message: string): string {
  const normalizedMessage = message.trim();
  if (!normalizedMessage || normalizedMessage === DOCUMENT_UPLOAD_DEFAULT_STATUS) {
    return "";
  }
  return normalizedMessage;
}

function buildRailStatus(params: {
  idleLabel: string;
  isRunning: boolean;
  runningLabel: string;
  statusMessage: string;
}): WorkflowRailStatus {
  const { idleLabel, isRunning, runningLabel, statusMessage } = params;
  if (isRunning) {
    return {
      detail: statusMessage || null,
      label: runningLabel,
      tone: "info",
    };
  }
  if (!statusMessage) {
    return {
      detail: null,
      label: idleLabel,
      tone: "info",
    };
  }
  const tone = classifyTone(statusMessage);
  return {
    detail: statusMessage,
    label: tone === "success" ? "Ready" : tone === "warning" ? "Needs attention" : "Updated",
    tone,
  };
}

export function buildWorkflowStatusContract(
  params: BuildWorkflowStatusParams
): WorkflowStatusContract {
  const researchMessage = params.relatedCasesStatus.trim();
  const documentMessage = normalizeDocumentStatus(params.documentStatusMessage);
  const isDocumentSubmitting =
    params.isDocumentIntakeSubmitting ||
    params.isDocumentReadinessSubmitting ||
    params.isDocumentPackageSubmitting ||
    params.isDocumentDownloadSubmitting;

  const research = buildRailStatus({
    idleLabel: "Idle",
    isRunning: params.isCaseSearchSubmitting,
    runningLabel: "Searching",
    statusMessage: researchMessage,
  });
  const documents = buildRailStatus({
    idleLabel: "Idle",
    isRunning: isDocumentSubmitting,
    runningLabel: "Working",
    statusMessage: documentMessage,
  });

  let overall: WorkflowBannerStatus = null;
  if (researchMessage) {
    overall = {
      message: researchMessage,
      title: "Research workflow",
      tone: research.tone,
    };
  } else if (documentMessage && documents.tone === "warning") {
    overall = {
      message: documentMessage,
      title: "Document workflow",
      tone: documents.tone,
    };
  }

  return {
    documents,
    overall,
    research,
  };
}

