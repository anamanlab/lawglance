import { describe, expect, it } from "vitest";

import { DOCUMENT_UPLOAD_DEFAULT_STATUS } from "@/components/chat/constants";
import { buildWorkflowStatusContract } from "@/components/chat/workflow-status-contract";

describe("workflow status contract", () => {
  it("returns idle rails and no banner when workflows are idle", () => {
    const status = buildWorkflowStatusContract({
      relatedCasesStatus: "",
      documentStatusMessage: DOCUMENT_UPLOAD_DEFAULT_STATUS,
      isCaseSearchSubmitting: false,
      isDocumentIntakeSubmitting: false,
      isDocumentReadinessSubmitting: false,
      isDocumentPackageSubmitting: false,
      isDocumentDownloadSubmitting: false,
    });

    expect(status.research.label).toBe("Idle");
    expect(status.documents.label).toBe("Idle");
    expect(status.overall).toBeNull();
  });

  it("surfaces research warnings in the overall banner", () => {
    const status = buildWorkflowStatusContract({
      relatedCasesStatus: "Case search unavailable: provider failed",
      documentStatusMessage: DOCUMENT_UPLOAD_DEFAULT_STATUS,
      isCaseSearchSubmitting: false,
      isDocumentIntakeSubmitting: false,
      isDocumentReadinessSubmitting: false,
      isDocumentPackageSubmitting: false,
      isDocumentDownloadSubmitting: false,
    });

    expect(status.research.label).toBe("Needs attention");
    expect(status.research.tone).toBe("warning");
    expect(status.overall).toEqual({
      title: "Research workflow",
      message: "Case search unavailable: provider failed",
      tone: "warning",
    });
  });

  it("keeps document success states out of overall banner to avoid duplicate guidance", () => {
    const status = buildWorkflowStatusContract({
      relatedCasesStatus: "",
      documentStatusMessage: "Document package ready for download",
      isCaseSearchSubmitting: false,
      isDocumentIntakeSubmitting: false,
      isDocumentReadinessSubmitting: false,
      isDocumentPackageSubmitting: false,
      isDocumentDownloadSubmitting: false,
    });

    expect(status.documents.label).toBe("Ready");
    expect(status.documents.tone).toBe("success");
    expect(status.overall).toBeNull();
  });

  it("promotes document warning states when research is quiet", () => {
    const status = buildWorkflowStatusContract({
      relatedCasesStatus: "",
      documentStatusMessage: "Document package generation failed",
      isCaseSearchSubmitting: false,
      isDocumentIntakeSubmitting: false,
      isDocumentReadinessSubmitting: false,
      isDocumentPackageSubmitting: false,
      isDocumentDownloadSubmitting: false,
    });

    expect(status.documents.label).toBe("Needs attention");
    expect(status.documents.tone).toBe("warning");
    expect(status.overall?.title).toBe("Document workflow");
    expect(status.overall?.tone).toBe("warning");
  });

  it("marks active workflows as searching/working", () => {
    const status = buildWorkflowStatusContract({
      relatedCasesStatus: "",
      documentStatusMessage: DOCUMENT_UPLOAD_DEFAULT_STATUS,
      isCaseSearchSubmitting: true,
      isDocumentIntakeSubmitting: true,
      isDocumentReadinessSubmitting: false,
      isDocumentPackageSubmitting: false,
      isDocumentDownloadSubmitting: false,
    });

    expect(status.research.label).toBe("Searching");
    expect(status.documents.label).toBe("Working");
    expect(status.research.tone).toBe("info");
    expect(status.documents.tone).toBe("info");
  });
});

