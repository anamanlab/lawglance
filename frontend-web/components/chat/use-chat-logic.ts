import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { createApiClient } from "@/lib/api-client";
import type {
  DocumentForum,
  DocumentIntakeResult,
  LawyerCaseSupport,
  LawyerResearchIntakePayload,
  MatterReadinessResponsePayload,
} from "@/lib/api-client";
import { isLowSpecificityCaseQuery } from "@/components/chat/case-query-specificity";
import { ASSISTANT_BOOTSTRAP_TEXT, ERROR_COPY } from "@/components/chat/constants";
import type {
  CaseRetrievalMode,
  ChatErrorState,
  ChatMessage,
  DocumentReadinessState,
  DocumentUploadItem,
  IntakeCompleteness,
  ResearchConfidence,
  ResearchObjective,
  ResearchPosture,
  ResearchSourceStatus,
  SubmissionPhase,
  SupportContext,
} from "@/components/chat/types";
import { buildMessage, buildSessionId, nextMessageId } from "@/components/chat/utils";

function buildCaseExportUnavailableMessage(policyReason?: string | null): string {
  switch (policyReason) {
    case "source_export_blocked_by_policy":
      return "Case export is unavailable for this source under current policy.";
    case "export_url_not_allowed_for_source":
    case "export_redirect_url_not_allowed_for_source":
      return "Case export is unavailable because the document URL is not trusted for this source.";
    case "source_not_in_registry_for_export":
      return "Case export is unavailable because the source is not registered for export.";
    case "source_export_metadata_missing":
      return "Case export is unavailable because source metadata is missing for this result.";
    default:
      return "Case export is unavailable for this case result.";
  }
}

function buildCaseSearchErrorStatusMessage(params: {
  code: string;
  message: string;
  policyReason: string | null;
  traceId: string | null;
  showOperationalPanels: boolean;
}): string {
  const { code, message, policyReason, traceId, showOperationalPanels } = params;
  if (code === "VALIDATION_ERROR" && policyReason === "case_search_query_too_broad") {
    return "Case-law query is too broad. Add specific terms such as program, issue, court, or citation.";
  }
  if (showOperationalPanels) {
    return `Unable to search related case law: ${message}${policyReason ? ` (Policy: ${policyReason})` : ""} (Trace ID: ${traceId ?? "Unavailable"})`;
  }
  if (code === "SOURCE_UNAVAILABLE") {
    return "Case-law sources are temporarily unavailable. Please try again shortly.";
  }
  if (code === "RATE_LIMITED") {
    return "Case-law search is temporarily rate limited. Please wait a moment and try again.";
  }
  return "Case-law search is temporarily unavailable. Please try again shortly.";
}

function parseCommaSeparatedValues(value: string, maxItems = 8): string[] {
  const normalized = value
    .split(/[,;\n]/)
    .map((item) => item.trim())
    .filter(Boolean);
  const deduped = Array.from(new Set(normalized.map((item) => item.toLowerCase()))).map(
    (key) => normalized.find((item) => item.toLowerCase() === key) ?? key
  );
  return deduped.slice(0, maxItems);
}

function normalizeIssueTag(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
}

function splitAnchorReferences(value: string): { citations: string[]; dockets: string[] } {
  const entries = parseCommaSeparatedValues(value, 10);
  const citations = entries.filter((entry) =>
    /\b\d{4}\s+(?:fc|fca|caf|scc|irb)\s+\d+\b/i.test(entry)
  );
  const dockets = entries
    .filter((entry) => /^[A-Za-z]{1,5}\s*-\s*\d{1,8}\s*-\s*\d{2,4}$/.test(entry))
    .map((entry) => entry.replace(/\s*-\s*/g, "-"));
  return { citations, dockets };
}

const BROAD_QUERY_INTAKE_GATE_MESSAGE =
  "Add at least two intake details (objective, target court, issue tags, or citation/docket anchor) before running broad case-law research queries.";
const INVALID_DECISION_DATE_RANGE_MESSAGE =
  "Decision date range is invalid. 'From' date must be earlier than or equal to 'to' date.";
const DOCUMENT_UPLOAD_DEFAULT_STATUS =
  "Upload documents to evaluate filing readiness and package generation.";

function toDocumentUploadStatus(
  qualityStatus: string
): DocumentUploadItem["status"] {
  const normalizedStatus = qualityStatus.trim().toLowerCase();
  if (normalizedStatus === "needs_review") {
    return "needs_review";
  }
  if (normalizedStatus === "failed" || normalizedStatus === "error") {
    return "failed";
  }
  if (normalizedStatus === "pending") {
    return "pending";
  }
  return "uploaded";
}

function toDocumentReadinessState(
  payload: MatterReadinessResponsePayload
): DocumentReadinessState {
  return {
    isReady: payload.is_ready,
    missingRequiredItems: payload.missing_required_items ?? [],
    blockingIssues: payload.blocking_issues ?? [],
    warnings: payload.warnings ?? [],
    requirementStatuses: (payload.requirement_statuses ?? []).map((status) => ({
      item: status.item,
      status: status.status,
      ruleScope: status.rule_scope ?? "base",
      reason: status.reason ?? null,
    })),
  };
}

function buildDocumentUploadItem(
  result: DocumentIntakeResult,
  fallbackFilename: string
): DocumentUploadItem {
  return {
    fileId: result.file_id || `${fallbackFilename}-${Date.now()}`,
    filename: result.original_filename || fallbackFilename,
    classification: result.classification ?? null,
    status: toDocumentUploadStatus(result.quality_status),
    issues: result.issues ?? [],
  };
}

export interface UseChatLogicProps {
  apiBaseUrl: string;
  legalDisclaimer: string;
  showOperationalPanels: boolean;
}

export function useChatLogic({ apiBaseUrl, legalDisclaimer, showOperationalPanels }: UseChatLogicProps) {
  const sessionIdRef = useRef(buildSessionId());
  const messageCounterRef = useRef(0);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const endOfThreadRef = useRef<HTMLDivElement | null>(null);

  const [draft, setDraft] = useState("");
  const [isChatSubmitting, setIsChatSubmitting] = useState(false);
  const [isCaseSearchSubmitting, setIsCaseSearchSubmitting] = useState(false);
  const [isExportSubmitting, setIsExportSubmitting] = useState(false);
  const [chatError, setChatError] = useState<ChatErrorState | null>(null);
  const [retryPrompt, setRetryPrompt] = useState<string | null>(null);
  const [supportContext, setSupportContext] = useState<SupportContext | null>(null);
  const [relatedCases, setRelatedCases] = useState<LawyerCaseSupport[]>([]);
  const [relatedCasesStatus, setRelatedCasesStatus] = useState("");
  const [matterProfile, setMatterProfile] = useState<Record<string, string | string[] | null> | undefined>();
  const [caseSearchQuery, setCaseSearchQuery] = useState("");
  const [lastCaseSearchQuery, setLastCaseSearchQuery] = useState<string | null>(null);
  const [relatedCasesRetrievalMode, setRelatedCasesRetrievalMode] = useState<CaseRetrievalMode>(null);
  const [sourceStatus, setSourceStatus] = useState<ResearchSourceStatus>(null);
  const [researchConfidence, setResearchConfidence] = useState<ResearchConfidence>(null);
  const [confidenceReasons, setConfidenceReasons] = useState<string[]>([]);
  const [intakeCompleteness, setIntakeCompleteness] = useState<IntakeCompleteness>(null);
  const [intakeHints, setIntakeHints] = useState<string[]>([]);
  const [intakeObjective, setIntakeObjective] = useState<ResearchObjective>("");
  const [intakeTargetCourt, setIntakeTargetCourt] = useState("");
  const [intakeProceduralPosture, setIntakeProceduralPosture] = useState<ResearchPosture>("");
  const [intakeIssueTags, setIntakeIssueTags] = useState("");
  const [intakeAnchorReference, setIntakeAnchorReference] = useState("");
  const [intakeDateFrom, setIntakeDateFrom] = useState("");
  const [intakeDateTo, setIntakeDateTo] = useState("");
  const [documentForum, setDocumentForum] = useState<DocumentForum>("federal_court_jr");
  const [documentMatterId, setDocumentMatterId] = useState("");
  const [documentStatusMessage, setDocumentStatusMessage] = useState(
    DOCUMENT_UPLOAD_DEFAULT_STATUS
  );
  const [documentUploads, setDocumentUploads] = useState<DocumentUploadItem[]>([]);
  const [documentReadiness, setDocumentReadiness] = useState<DocumentReadinessState | null>(
    null
  );
  const [isDocumentIntakeSubmitting, setIsDocumentIntakeSubmitting] = useState(false);
  const [isDocumentReadinessSubmitting, setIsDocumentReadinessSubmitting] = useState(false);
  const [isDocumentPackageSubmitting, setIsDocumentPackageSubmitting] = useState(false);
  const [exportingCaseId, setExportingCaseId] = useState<string | null>(null);
  const [submissionPhase, setSubmissionPhase] = useState<SubmissionPhase>("idle");
  const [chatPendingElapsedSeconds, setChatPendingElapsedSeconds] = useState(0);

  const isSubmitting = isChatSubmitting || isCaseSearchSubmitting || isExportSubmitting;
  const isSlowChatResponse = isChatSubmitting && chatPendingElapsedSeconds >= 8;

  const apiClient = useMemo(() => createApiClient({ apiBaseUrl }), [apiBaseUrl]);

  const [messages, setMessages] = useState<ChatMessage[]>([
    buildMessage("assistant-bootstrap", "assistant", ASSISTANT_BOOTSTRAP_TEXT, {
      disclaimer: legalDisclaimer,
    }),
  ]);

  useEffect(() => {
    if (typeof endOfThreadRef.current?.scrollIntoView === "function") {
      endOfThreadRef.current.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }, [messages, isSubmitting]);

  useEffect(() => {
    if (!isChatSubmitting) {
      setChatPendingElapsedSeconds(0);
      return;
    }

    const intervalId = window.setInterval(() => {
      setChatPendingElapsedSeconds((elapsed) => elapsed + 1);
    }, 1000);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [isChatSubmitting]);

  const submitPrompt = useCallback(
    async (prompt: string, options?: { isRetry?: boolean }): Promise<void> => {
      if (isSubmitting) {
        return;
      }

      const promptToSubmit = prompt.trim();
      if (!promptToSubmit) {
        return;
      }

      if (!options?.isRetry) {
        const userMessageId = nextMessageId("user", messageCounterRef);
        setMessages((currentMessages) => [
          ...currentMessages,
          buildMessage(userMessageId, "user", promptToSubmit),
        ]);
        setDraft("");
      }

      setChatError(null);
      setRetryPrompt(null);
      setRelatedCases([]);
      setMatterProfile(undefined);
      setRelatedCasesStatus("");
      setLastCaseSearchQuery(null);
      setRelatedCasesRetrievalMode(null);
      setSourceStatus(null);
      setResearchConfidence(null);
      setConfidenceReasons([]);
      setIntakeCompleteness(null);
      setIntakeHints([]);
      setExportingCaseId(null);
      setChatPendingElapsedSeconds(0);
      setIsChatSubmitting(true);
      setSubmissionPhase("chat");

      try {
        const chatResult = await apiClient.sendChatMessage({
          session_id: sessionIdRef.current,
          message: promptToSubmit,
          locale: "en-CA",
          mode: "standard",
        });

        if (!chatResult.ok) {
          const errorCopy = ERROR_COPY[chatResult.error.code];
          setChatError({
            title: errorCopy.title,
            detail: chatResult.error.message || errorCopy.detail,
            action: errorCopy.action,
            retryable: errorCopy.retryable,
            traceId: chatResult.traceId,
          });
          setRetryPrompt(errorCopy.retryable ? promptToSubmit : null);
          setSupportContext({
            endpoint: "/api/chat",
            status: "error",
            traceId: chatResult.traceId,
            code: chatResult.error.code,
            traceIdMismatch: chatResult.traceIdMismatch,
          });
          return;
        }

        const chatResponse = chatResult.data;
        const isPolicyRefusal = chatResponse.fallback_used.reason === "policy_block";
        const assistantMessageId = nextMessageId("assistant", messageCounterRef);

        setMessages((currentMessages) => [
          ...currentMessages,
          buildMessage(assistantMessageId, "assistant", chatResponse.answer, {
            disclaimer: chatResponse.disclaimer || legalDisclaimer,
            traceId: chatResult.traceId,
            citations: chatResponse.citations,
            isPolicyRefusal,
            confidence: chatResponse.confidence,
            fallbackUsed: chatResponse.fallback_used,
          }),
        ]);

        setSupportContext({
          endpoint: "/api/chat",
          status: "success",
          traceId: chatResult.traceId,
          traceIdMismatch: false,
        });

        if (isPolicyRefusal) {
          setRelatedCasesStatus(
            "This chat request was blocked by policy. You can still run case-law search with a specific Canadian immigration query."
          );
          return;
        }

        const researchPreview = chatResponse.research_preview;
        if (researchPreview) {
          const previewQuery = researchPreview.query.trim() || promptToSubmit;
          setCaseSearchQuery(previewQuery);
          setLastCaseSearchQuery(previewQuery);
          setRelatedCasesRetrievalMode(researchPreview.retrieval_mode ?? "auto");
          setSourceStatus(researchPreview.source_status ?? null);
          setResearchConfidence(null);
          setConfidenceReasons([]);
          setIntakeCompleteness(null);
          setIntakeHints([]);

          if (researchPreview.cases.length > 0) {
            setRelatedCases(researchPreview.cases);
            setRelatedCasesStatus(
              "Auto-retrieved case-law precedents are shown below. Refine the query and run manual search if needed."
            );
            return;
          }

          const noPreviewMatchMessage =
            researchPreview.source_status.official === "unavailable"
              ? "Official case-law sources are temporarily unavailable. Please retry shortly."
              : "No matching case-law records were auto-retrieved for this answer. You can run a manual search.";
          setRelatedCasesStatus(noPreviewMatchMessage);
          return;
        }

        setCaseSearchQuery(promptToSubmit);
        setSourceStatus(null);
        setRelatedCasesStatus("Ready to find related Canadian case law.");
      } finally {
        setIsChatSubmitting(false);
        setSubmissionPhase("idle");
        textareaRef.current?.focus();
      }
    },
    [apiClient, isSubmitting, legalDisclaimer]
  );

  const runRelatedCaseSearch = useCallback(async (): Promise<void> => {
    const query = caseSearchQuery.trim();
    if (isSubmitting || query.length < 2) {
      return;
    }

    const issueTags = parseCommaSeparatedValues(intakeIssueTags, 8)
      .map(normalizeIssueTag)
      .filter(Boolean);
    const { citations: anchorCitations, dockets: anchorDockets } =
      splitAnchorReferences(intakeAnchorReference);
    const normalizedDateFrom = intakeDateFrom.trim();
    const normalizedDateTo = intakeDateTo.trim();
    if (normalizedDateFrom && normalizedDateTo && normalizedDateFrom > normalizedDateTo) {
      setRelatedCasesStatus(INVALID_DECISION_DATE_RANGE_MESSAGE);
      return;
    }
    const intakeSignalCount = [
      intakeObjective ? 1 : 0,
      intakeTargetCourt.trim() ? 1 : 0,
      intakeProceduralPosture ? 1 : 0,
      issueTags.length > 0 ? 1 : 0,
      anchorCitations.length > 0 || anchorDockets.length > 0 ? 1 : 0,
      normalizedDateFrom || normalizedDateTo ? 1 : 0,
    ].reduce((total, next) => total + next, 0);
    const lowSpecificityQuery = isLowSpecificityCaseQuery(query);
    if (lowSpecificityQuery && intakeSignalCount < 2) {
      setRelatedCasesStatus(BROAD_QUERY_INTAKE_GATE_MESSAGE);
      return;
    }

    const intakePayload: LawyerResearchIntakePayload | undefined =
      intakeObjective ||
      intakeTargetCourt.trim() ||
      intakeProceduralPosture ||
      issueTags.length > 0 ||
      anchorCitations.length > 0 ||
      anchorDockets.length > 0 ||
      normalizedDateFrom ||
      normalizedDateTo
        ? {
            objective: intakeObjective || undefined,
            target_court: intakeTargetCourt.trim() || undefined,
            procedural_posture: intakeProceduralPosture || undefined,
            issue_tags: issueTags.length ? issueTags : undefined,
            anchor_citations: anchorCitations.length ? anchorCitations : undefined,
            anchor_dockets: anchorDockets.length ? anchorDockets : undefined,
            date_from: normalizedDateFrom || undefined,
            date_to: normalizedDateTo || undefined,
          }
        : undefined;

    const shouldPromptForIntake = lowSpecificityQuery && intakeSignalCount < 3;

    setIsCaseSearchSubmitting(true);
    setSubmissionPhase("cases");
    setExportingCaseId(null);
    setSourceStatus(null);
    setResearchConfidence(null);
    setConfidenceReasons([]);
    setIntakeCompleteness(null);
    setIntakeHints([]);
    setRelatedCasesStatus(
      shouldPromptForIntake
        ? "Running grounded lawyer case research... Add intake details next to improve confidence."
        : "Running grounded lawyer case research..."
    );

    try {
      const caseSearchResult = await apiClient.researchLawyerCases({
        session_id: sessionIdRef.current,
        matter_summary: query,
        jurisdiction: "ca",
        court: intakeTargetCourt.trim() || undefined,
        intake: intakePayload,
        limit: 5,
      });

      if (!caseSearchResult.ok) {
        const statusMessage = buildCaseSearchErrorStatusMessage({
          code: caseSearchResult.error.code,
          message: caseSearchResult.error.message,
          policyReason: caseSearchResult.policyReason,
          traceId: caseSearchResult.traceId,
          showOperationalPanels,
        });
        setRelatedCasesStatus(statusMessage);
        setSupportContext({
          endpoint: "/api/research/lawyer-cases",
          status: "error",
          traceId: caseSearchResult.traceId,
          code: caseSearchResult.error.code,
          traceIdMismatch: caseSearchResult.traceIdMismatch,
        });
        return;
      }

      setRelatedCases(caseSearchResult.data.cases);
      setMatterProfile(caseSearchResult.data.matter_profile);
      setLastCaseSearchQuery(query);
      setRelatedCasesRetrievalMode("manual");
      setSourceStatus(caseSearchResult.data.source_status ?? null);
      setResearchConfidence(caseSearchResult.data.research_confidence);
      setConfidenceReasons(caseSearchResult.data.confidence_reasons ?? []);
      setIntakeCompleteness(caseSearchResult.data.intake_completeness);
      setIntakeHints(caseSearchResult.data.intake_hints ?? []);
      const noMatchMessage =
        caseSearchResult.data.source_status.official === "unavailable"
          ? "Official case-law sources are temporarily unavailable. Please retry shortly."
          : "No matching case-law records were found for this query.";
      setRelatedCasesStatus(caseSearchResult.data.cases.length ? "" : noMatchMessage);
      setSupportContext({
        endpoint: "/api/research/lawyer-cases",
        status: "success",
        traceId: caseSearchResult.traceId,
        traceIdMismatch: false,
      });
    } finally {
      setIsCaseSearchSubmitting(false);
      setSubmissionPhase("idle");
    }
  }, [
    apiClient,
    caseSearchQuery,
    intakeAnchorReference,
    intakeDateFrom,
    intakeDateTo,
    intakeIssueTags,
    intakeObjective,
    intakeProceduralPosture,
    intakeTargetCourt,
    isSubmitting,
    showOperationalPanels,
  ]);

  const runCaseExport = useCallback(
    async (caseResult: LawyerCaseSupport): Promise<void> => {
      if (isSubmitting) {
        return;
      }

      if (caseResult.export_allowed === false) {
        setRelatedCasesStatus(
          buildCaseExportUnavailableMessage(caseResult.export_policy_reason)
        );
        return;
      }

      if (!caseResult.source_id || !caseResult.document_url) {
        setRelatedCasesStatus(
          buildCaseExportUnavailableMessage("source_export_metadata_missing")
        );
        return;
      }

      const userApproved =
        typeof window !== "undefined"
          ? window.confirm(
              "Export this case PDF now? This will download the document from the official source."
            )
          : false;
      if (!userApproved) {
        setRelatedCasesStatus("Case export cancelled. No file was downloaded.");
        return;
      }

      setIsExportSubmitting(true);
      setSubmissionPhase("export");
      setExportingCaseId(caseResult.case_id);
      setRelatedCasesStatus("Preparing case PDF export...");

      try {
        const approvalResult = await apiClient.requestCaseExportApproval({
          source_id: caseResult.source_id,
          case_id: caseResult.case_id,
          document_url: caseResult.document_url,
          user_approved: true,
        });

        if (!approvalResult.ok) {
          const errorCopy = ERROR_COPY[approvalResult.error.code];
          const errorDetail = approvalResult.error.message || errorCopy.detail;
          const policyReason = approvalResult.policyReason;
          const statusMessage = showOperationalPanels
            ? `${errorCopy.title}: ${errorDetail}${
                policyReason ? ` (Policy: ${policyReason})` : ""
              } (Trace ID: ${approvalResult.traceId ?? "Unavailable"})`
            : "Case export approval is temporarily unavailable. Please try again shortly.";
          setRelatedCasesStatus(statusMessage);
          setSupportContext({
            endpoint: "/api/export/cases/approval",
            status: "error",
            traceId: approvalResult.traceId,
            code: approvalResult.error.code,
            policyReason,
            traceIdMismatch: approvalResult.traceIdMismatch,
          });
          return;
        }

        const exportResult = await apiClient.exportCasePdf({
          source_id: caseResult.source_id,
          case_id: caseResult.case_id,
          document_url: caseResult.document_url,
          format: "pdf",
          user_approved: true,
          approval_token: approvalResult.data.approval_token,
        });

        if (!exportResult.ok) {
          const errorCopy = ERROR_COPY[exportResult.error.code];
          const errorDetail = exportResult.error.message || errorCopy.detail;
          const policyReason = exportResult.policyReason;
          const isPolicyBlocked = exportResult.error.code === "POLICY_BLOCKED";
          const policyBlockedMessage =
            policyReason === "source_export_user_approval_required"
              ? "Case export requires explicit user approval before download."
              : "Case export was blocked by source policy for this source.";
          const statusMessage = showOperationalPanels
            ? `${errorCopy.title}: ${errorDetail}${
                policyReason ? ` (Policy: ${policyReason})` : ""
              } (Trace ID: ${exportResult.traceId ?? "Unavailable"})`
            : isPolicyBlocked
              ? policyBlockedMessage
              : "Case export is temporarily unavailable. Please try again shortly.";
          setRelatedCasesStatus(statusMessage);
          setSupportContext({
            endpoint: "/api/export/cases",
            status: "error",
            traceId: exportResult.traceId,
            code: exportResult.error.code,
            policyReason,
            traceIdMismatch: exportResult.traceIdMismatch,
          });
          return;
        }

        const fallbackFilename = `${caseResult.case_id}.pdf`;
        const downloadFilename = exportResult.data.filename || fallbackFilename;
        if (typeof window.URL.createObjectURL !== "function") {
          setRelatedCasesStatus(
            `Case export completed, but automatic download is unavailable in this browser (${downloadFilename}).`
          );
          return;
        }
        const objectUrl = window.URL.createObjectURL(exportResult.data.blob);
        const downloadLink = document.createElement("a");
        downloadLink.href = objectUrl;
        downloadLink.download = downloadFilename;
        downloadLink.rel = "noopener";
        document.body.append(downloadLink);
        downloadLink.click();
        downloadLink.remove();
        if (typeof window.URL.revokeObjectURL === "function") {
          window.URL.revokeObjectURL(objectUrl);
        }

        setRelatedCasesStatus(`Download started: ${downloadFilename}`);
        setSupportContext({
          endpoint: "/api/export/cases",
          status: "success",
          traceId: exportResult.traceId,
          policyReason: exportResult.data.policyReason,
          traceIdMismatch: false,
        });
      } finally {
        setExportingCaseId(null);
        setIsExportSubmitting(false);
        setSubmissionPhase("idle");
      }
    },
    [apiClient, isSubmitting, showOperationalPanels]
  );

  const fetchDocumentReadinessForMatter = useCallback(
    async (
      matterId: string,
      options?: { suppressStatusMessage?: boolean }
    ): Promise<boolean> => {
      const normalizedMatterId = matterId.trim();
      if (!normalizedMatterId) {
        if (!options?.suppressStatusMessage) {
          setDocumentStatusMessage("Enter a matter ID or upload documents first.");
        }
        return false;
      }

      setIsDocumentReadinessSubmitting(true);
      if (!options?.suppressStatusMessage) {
        setDocumentStatusMessage("Checking readiness...");
      }
      try {
        const readinessResult = await apiClient.getMatterReadiness(normalizedMatterId);
        if (!readinessResult.ok) {
          const statusMessage = showOperationalPanels
            ? `Unable to fetch readiness: ${readinessResult.error.message} (Trace ID: ${readinessResult.traceId ?? "Unavailable"})`
            : `Readiness check failed. ${readinessResult.error.message}`;
          setDocumentStatusMessage(statusMessage);
          setSupportContext({
            endpoint: "/api/documents/matters/{matter_id}/readiness",
            status: "error",
            traceId: readinessResult.traceId,
            code: readinessResult.error.code,
            policyReason: readinessResult.policyReason,
            traceIdMismatch: readinessResult.traceIdMismatch,
          });
          return false;
        }

        setDocumentMatterId(readinessResult.data.matter_id || normalizedMatterId);
        setDocumentReadiness(toDocumentReadinessState(readinessResult.data));
        if (!options?.suppressStatusMessage) {
          setDocumentStatusMessage(
            readinessResult.data.is_ready
              ? "Matter is ready for package generation."
              : "Matter not ready. Resolve missing or blocking items."
          );
        }
        setSupportContext({
          endpoint: "/api/documents/matters/{matter_id}/readiness",
          status: "success",
          traceId: readinessResult.traceId,
          traceIdMismatch: false,
        });
        return true;
      } finally {
        setIsDocumentReadinessSubmitting(false);
      }
    },
    [apiClient, showOperationalPanels]
  );

  const onDocumentUpload = useCallback(
    async (files: File[]): Promise<void> => {
      if (isDocumentIntakeSubmitting) {
        return;
      }

      const selectedFiles = files.filter(Boolean);
      if (selectedFiles.length === 0) {
        return;
      }

      setIsDocumentIntakeSubmitting(true);
      setDocumentStatusMessage(
        `Uploading ${selectedFiles.length} document${selectedFiles.length === 1 ? "" : "s"}...`
      );
      setDocumentReadiness(null);
      setDocumentUploads(
        selectedFiles.map((file, index) => ({
          fileId: `pending-${Date.now()}-${index}`,
          filename: file.name,
          classification: null,
          status: "pending",
          issues: [],
        }))
      );

      try {
        const intakeResult = await apiClient.uploadMatterDocuments({
          forum: documentForum,
          matter_id: documentMatterId.trim() || undefined,
          files: selectedFiles,
        });

        if (!intakeResult.ok) {
          setDocumentUploads(
            selectedFiles.map((file, index) => ({
              fileId: `failed-${Date.now()}-${index}`,
              filename: file.name,
              classification: null,
              status: "failed",
              issues: [],
            }))
          );
          setDocumentStatusMessage(`Upload failed. ${intakeResult.error.message}`);
          setSupportContext({
            endpoint: "/api/documents/intake",
            status: "error",
            traceId: intakeResult.traceId,
            code: intakeResult.error.code,
            policyReason: intakeResult.policyReason,
            traceIdMismatch: intakeResult.traceIdMismatch,
          });
          return;
        }

        const intakeResults = intakeResult.data.results ?? [];
        const uploadItems = selectedFiles.map((file, index) => {
          const matchedResult = intakeResults[index];
          if (!matchedResult) {
            return {
              fileId: `missing-${Date.now()}-${index}`,
              filename: file.name,
              classification: null,
              status: "failed" as const,
              issues: ["missing_result"],
            };
          }
          return buildDocumentUploadItem(matchedResult, file.name);
        });
        setDocumentUploads(uploadItems);

        const normalizedMatterId = intakeResult.data.matter_id?.trim();
        if (normalizedMatterId) {
          setDocumentMatterId(normalizedMatterId);
        }

        const failedCount = uploadItems.filter((item) => item.status === "failed").length;
        const reviewCount = uploadItems.filter((item) => item.status === "needs_review").length;
        const processedCount = uploadItems.length - failedCount;
        let nextStatusMessage = `Upload complete. ${processedCount}/${uploadItems.length} processed.`;
        if (reviewCount > 0) {
          nextStatusMessage += ` ${reviewCount} need review.`;
        }
        setDocumentStatusMessage(nextStatusMessage);
        setSupportContext({
          endpoint: "/api/documents/intake",
          status: "success",
          traceId: intakeResult.traceId,
          traceIdMismatch: false,
        });

        if (normalizedMatterId) {
          await fetchDocumentReadinessForMatter(normalizedMatterId, {
            suppressStatusMessage: true,
          });
        }
      } finally {
        setIsDocumentIntakeSubmitting(false);
      }
    },
    [
      apiClient,
      documentForum,
      documentMatterId,
      fetchDocumentReadinessForMatter,
      isDocumentIntakeSubmitting,
    ]
  );

  const onRefreshDocumentReadiness = useCallback((): void => {
    const matterId = documentMatterId.trim();
    if (!matterId || isDocumentReadinessSubmitting) {
      if (!matterId) {
        setDocumentStatusMessage("Enter a matter ID or upload documents first.");
      }
      return;
    }
    void fetchDocumentReadinessForMatter(matterId);
  }, [documentMatterId, fetchDocumentReadinessForMatter, isDocumentReadinessSubmitting]);

  const onBuildDocumentPackage = useCallback(async (): Promise<void> => {
    if (isDocumentPackageSubmitting || isDocumentIntakeSubmitting || isDocumentReadinessSubmitting) {
      return;
    }

    const matterId = documentMatterId.trim();
    if (!matterId) {
      setDocumentStatusMessage("Enter a matter ID or upload documents first.");
      return;
    }

    setIsDocumentPackageSubmitting(true);
    setDocumentStatusMessage("Generating package...");
    try {
      const packageResult = await apiClient.buildMatterPackage(matterId);
      if (!packageResult.ok) {
        const policyBlockedMessage =
          packageResult.policyReason === "document_package_not_ready"
            ? "Package blocked. Resolve missing or blocking items first."
            : null;
        const statusMessage = showOperationalPanels
          ? `Unable to generate package: ${packageResult.error.message}${
              packageResult.policyReason ? ` (Policy: ${packageResult.policyReason})` : ""
            } (Trace ID: ${packageResult.traceId ?? "Unavailable"})`
          : policyBlockedMessage ?? `Package generation failed. ${packageResult.error.message}`;
        setDocumentStatusMessage(statusMessage);
        setSupportContext({
          endpoint: "/api/documents/matters/{matter_id}/package",
          status: "error",
          traceId: packageResult.traceId,
          code: packageResult.error.code,
          policyReason: packageResult.policyReason,
          traceIdMismatch: packageResult.traceIdMismatch,
        });
        return;
      }

      setDocumentStatusMessage(
        `Package generated. TOC items: ${packageResult.data.table_of_contents.length}.`
      );
      setDocumentReadiness((currentReadiness) =>
        currentReadiness
          ? { ...currentReadiness, isReady: packageResult.data.is_ready }
          : {
              isReady: packageResult.data.is_ready,
              missingRequiredItems: [],
              blockingIssues: [],
              warnings: [],
              requirementStatuses: [],
            }
      );
      setSupportContext({
        endpoint: "/api/documents/matters/{matter_id}/package",
        status: "success",
        traceId: packageResult.traceId,
        traceIdMismatch: false,
      });
    } finally {
      setIsDocumentPackageSubmitting(false);
    }
  }, [
    apiClient,
    documentMatterId,
    isDocumentIntakeSubmitting,
    isDocumentPackageSubmitting,
    isDocumentReadinessSubmitting,
    showOperationalPanels,
  ]);

  const onDocumentForumChange = useCallback((value: DocumentForum): void => {
    setDocumentForum(value);
  }, []);

  const onDocumentMatterIdChange = useCallback((value: string): void => {
    setDocumentMatterId(value);
  }, []);

  const onSubmit = useCallback(
    (event: FormEvent<HTMLFormElement>): void => {
      event.preventDefault();
      void submitPrompt(draft);
    },
    [draft, submitPrompt]
  );

  const onRetryLastRequest = useCallback((): void => {
    if (!retryPrompt || isSubmitting) {
      return;
    }
    void submitPrompt(retryPrompt, { isRetry: true });
  }, [isSubmitting, retryPrompt, submitPrompt]);

  const onQuickPromptClick = useCallback(
    (prompt: string): void => {
      if (isChatSubmitting) {
        return;
      }
      setDraft(prompt);
      textareaRef.current?.focus();
    },
    [isChatSubmitting]
  );

  const onCaseSearchQueryChange = useCallback(
    (value: string): void => {
      setCaseSearchQuery(value);
      const nextQuery = value.trim().toLowerCase();
      const previousQuery = (lastCaseSearchQuery ?? "").trim().toLowerCase();
      if (!nextQuery || !previousQuery || relatedCases.length === 0) {
        return;
      }
      if (nextQuery !== previousQuery) {
        setRelatedCasesStatus(
          "Case-search query updated. Click Find related cases to refresh results."
        );
      }
    },
    [lastCaseSearchQuery, relatedCases.length]
  );

  const onIntakeObjectiveChange = useCallback((value: ResearchObjective): void => {
    setIntakeObjective(value);
  }, []);

  const onIntakeTargetCourtChange = useCallback((value: string): void => {
    setIntakeTargetCourt(value);
  }, []);

  const onIntakeProceduralPostureChange = useCallback((value: ResearchPosture): void => {
    setIntakeProceduralPosture(value);
  }, []);

  const onIntakeIssueTagsChange = useCallback((value: string): void => {
    setIntakeIssueTags(value);
  }, []);

  const onIntakeAnchorReferenceChange = useCallback((value: string): void => {
    setIntakeAnchorReference(value);
  }, []);

  const onIntakeDateFromChange = useCallback((value: string): void => {
    setIntakeDateFrom(value);
  }, []);

  const onIntakeDateToChange = useCallback((value: string): void => {
    setIntakeDateTo(value);
  }, []);

  return {
    sessionId: sessionIdRef.current,
    textareaRef,
    endOfThreadRef,
    draft,
    setDraft,
    isSubmitting,
    isChatSubmitting,
    isCaseSearchSubmitting,
    isExportSubmitting,
    chatError,
    retryPrompt,
    supportContext,
    relatedCases,
    matterProfile,
    relatedCasesStatus,
    caseSearchQuery,
    lastCaseSearchQuery,
    relatedCasesRetrievalMode,
    sourceStatus,
    researchConfidence,
    confidenceReasons,
    intakeCompleteness,
    intakeHints,
    intakeObjective,
    intakeTargetCourt,
    intakeProceduralPosture,
    intakeIssueTags,
    intakeAnchorReference,
    intakeDateFrom,
    intakeDateTo,
    documentForum,
    documentMatterId,
    documentStatusMessage,
    documentUploads,
    documentReadiness,
    isDocumentIntakeSubmitting,
    isDocumentReadinessSubmitting,
    isDocumentPackageSubmitting,
    exportingCaseId,
    submissionPhase,
    chatPendingElapsedSeconds,
    isSlowChatResponse,
    messages,
    submitPrompt,
    runRelatedCaseSearch,
    runCaseExport,
    onSubmit,
    onRetryLastRequest,
    onQuickPromptClick,
    onCaseSearchQueryChange,
    onIntakeObjectiveChange,
    onIntakeTargetCourtChange,
    onIntakeProceduralPostureChange,
    onIntakeIssueTagsChange,
    onIntakeAnchorReferenceChange,
    onIntakeDateFromChange,
    onIntakeDateToChange,
    onDocumentForumChange,
    onDocumentMatterIdChange,
    onDocumentUpload,
    onRefreshDocumentReadiness,
    onBuildDocumentPackage,
  };
}
