import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { createApiClient, type SupportMatrixResponsePayload } from "@/lib/api-client";
import type {
  DocumentForum,
  DocumentIntakeResult,
  LawyerCaseSupport,
  LawyerResearchIntakePayload,
  MatterPackageResponsePayload,
  MatterReadinessResponsePayload,
} from "@/lib/api-client";
import {
  buildInitialTurnEvents,
  upsertTurnStageEvent,
} from "@/components/chat/agent-activity";
import { isLowSpecificityCaseQuery } from "@/components/chat/case-query-specificity";
import {
  ASSISTANT_BOOTSTRAP_TEXT,
  DOCUMENT_UPLOAD_DEFAULT_STATUS,
  ERROR_COPY,
} from "@/components/chat/constants";
import type {
  AgentActivityByTurn,
  AgentActivityMeta,
  AgentActivityStage,
  AgentActivityStatus,
  CaseRetrievalMode,
  ChatErrorState,
  DocumentCompilationState,
  FrontendLocale,
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

function toDocumentUploadIssueDetails(
  result: DocumentIntakeResult
): DocumentUploadItem["issueDetails"] {
  const normalizedDetails: DocumentUploadItem["issueDetails"] = [];
  const seenDetails = new Set<string>();
  for (const issueDetail of result.issue_details ?? []) {
    const normalizedCode = issueDetail.code?.trim();
    const normalizedMessage = issueDetail.message?.trim();
    if (!normalizedCode || !normalizedMessage) {
      continue;
    }
    const normalizedRemediation =
      typeof issueDetail.remediation === "string" && issueDetail.remediation.trim().length > 0
        ? issueDetail.remediation.trim()
        : null;
    const dedupeKey = [
      normalizedCode.toLowerCase(),
      normalizedMessage.toLowerCase(),
      issueDetail.severity.trim().toLowerCase(),
      normalizedRemediation?.toLowerCase() ?? "",
    ].join("|");
    if (seenDetails.has(dedupeKey)) {
      continue;
    }
    seenDetails.add(dedupeKey);
    normalizedDetails.push({
      code: normalizedCode,
      message: normalizedMessage,
      severity: issueDetail.severity,
      remediation: normalizedRemediation,
    });
  }
  return normalizedDetails;
}

function toDocumentUploadIssueCodes(
  result: DocumentIntakeResult,
  issueDetails: DocumentUploadItem["issueDetails"]
): string[] {
  const issueCodes = result.issues.length > 0 ? result.issues : issueDetails.map((detail) => detail.code);
  const normalizedIssueCodes: string[] = [];
  const seenIssueCodes = new Set<string>();
  for (const issueCode of issueCodes) {
    const normalizedIssueCode = issueCode.trim();
    if (!normalizedIssueCode) {
      continue;
    }
    const dedupeKey = normalizedIssueCode.toLowerCase();
    if (seenIssueCodes.has(dedupeKey)) {
      continue;
    }
    seenIssueCodes.add(dedupeKey);
    normalizedIssueCodes.push(normalizedIssueCode);
  }
  return normalizedIssueCodes;
}

const DEFAULT_DOCUMENT_SUPPORT_MATRIX: SupportMatrixResponsePayload = {
  supported_profiles_by_forum: {
    federal_court_jr: ["federal_court_jr_leave", "federal_court_jr_hearing"],
    rpd: ["rpd"],
    rad: ["rad"],
    id: ["id"],
    iad: ["iad", "iad_sponsorship", "iad_residency", "iad_admissibility"],
    ircc_application: ["ircc_pr_card_renewal"],
  },
  unsupported_profile_families: [
    "humanitarian_and_compassionate",
    "prra",
    "work_permit",
    "study_permit",
    "citizenship_proof",
  ],
};

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
    latestCompilation: null,
  };
}

function toDocumentCompilationState(
  payload: MatterPackageResponsePayload
): DocumentCompilationState {
  const rawTocEntries =
    payload.toc_entries && payload.toc_entries.length > 0
      ? payload.toc_entries
      : payload.table_of_contents ?? [];
  return {
    tocEntries: rawTocEntries.map((entry) => ({
      position: entry.position,
      documentType: entry.document_type,
      filename: entry.filename,
      startPage: typeof entry.start_page === "number" ? entry.start_page : null,
      endPage: typeof entry.end_page === "number" ? entry.end_page : null,
    })),
    paginationSummary: payload.pagination_summary ?? null,
    ruleViolations: (payload.rule_violations ?? []).map((violation) => ({
      severity: violation.severity,
      code: violation.violation_code ?? violation.code ?? "UNKNOWN_RULE_VIOLATION",
      sourceUrl: violation.rule_source_url ?? violation.source_url ?? null,
      remediation: violation.remediation ?? null,
    })),
    compilationProfile: payload.compilation_profile
      ? {
          id: payload.compilation_profile.id,
          version: payload.compilation_profile.version,
        }
      : null,
    compilationOutputMode:
      payload.compilation_output_mode === "compiled_pdf"
        ? "compiled_pdf"
        : payload.compilation_output_mode === "metadata_plan_only"
          ? "metadata_plan_only"
          : null,
    compiledArtifact: payload.compiled_artifact
      ? {
          filename: payload.compiled_artifact.filename,
          byteSize: payload.compiled_artifact.byte_size,
          sha256: payload.compiled_artifact.sha256,
          pageCount: payload.compiled_artifact.page_count,
        }
      : null,
    recordSections: (payload.record_sections ?? []).map((section) => ({
      sectionId: section.section_id,
      title: section.title,
      instructions: section.instructions,
      documentTypes: section.document_types ?? [],
      sectionStatus: section.section_status ?? "present",
      slotStatuses: (section.slot_statuses ?? []).map((slotStatus) => ({
        documentType: slotStatus.document_type,
        status: slotStatus.status,
        ruleScope: slotStatus.rule_scope ?? "base",
        reason: slotStatus.reason ?? null,
      })),
      missingDocumentTypes: section.missing_document_types ?? [],
      missingReasons: section.missing_reasons ?? [],
    })),
  };
}

function buildDocumentUploadItem(
  result: DocumentIntakeResult,
  fallbackFilename: string
): DocumentUploadItem {
  const issueDetails = toDocumentUploadIssueDetails(result);
  return {
    fileId: result.file_id || `${fallbackFilename}-${Date.now()}`,
    filename: result.original_filename || fallbackFilename,
    classification: result.classification ?? null,
    status: toDocumentUploadStatus(result.quality_status),
    issues: toDocumentUploadIssueCodes(result, issueDetails),
    issueDetails,
  };
}

function startBrowserDownload(blob: Blob, filename: string): boolean {
  if (
    typeof window === "undefined" ||
    typeof window.URL.createObjectURL !== "function"
  ) {
    return false;
  }
  const objectUrl = window.URL.createObjectURL(blob);
  const downloadLink = document.createElement("a");
  downloadLink.href = objectUrl;
  downloadLink.download = filename;
  downloadLink.rel = "noopener";
  document.body.append(downloadLink);
  downloadLink.click();
  downloadLink.remove();
  if (typeof window.URL.revokeObjectURL === "function") {
    window.URL.revokeObjectURL(objectUrl);
  }
  return true;
}

export interface UseChatLogicProps {
  apiBaseUrl: string;
  legalDisclaimer: string;
  showOperationalPanels: boolean;
}

export function useChatLogic({ apiBaseUrl, legalDisclaimer, showOperationalPanels }: UseChatLogicProps) {
  const sessionIdRef = useRef(buildSessionId());
  const messageCounterRef = useRef(0);
  const activityTurnCounterRef = useRef(0);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const endOfThreadRef = useRef<HTMLDivElement | null>(null);
  const localeStorageKey = "immcad.locale";

  const [draft, setDraft] = useState("");
  const [activeLocale, setActiveLocale] = useState<FrontendLocale>("en-CA");
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
  const [isDocumentDownloadSubmitting, setIsDocumentDownloadSubmitting] = useState(false);
  const [exportingCaseId, setExportingCaseId] = useState<string | null>(null);
  const [submissionPhase, setSubmissionPhase] = useState<SubmissionPhase>("idle");
  const [chatPendingElapsedSeconds, setChatPendingElapsedSeconds] = useState(0);

  const isSubmitting = isChatSubmitting || isCaseSearchSubmitting || isExportSubmitting;
  const isSlowChatResponse = isChatSubmitting && chatPendingElapsedSeconds >= 8;

  const apiClient = useMemo(() => createApiClient({ apiBaseUrl }), [apiBaseUrl]);
  const [supportMatrix, setSupportMatrix] = useState<SupportMatrixResponsePayload | null>(
    null
  );
  const supportMatrixRequestInFlightRef = useRef(false);

  const loadDocumentSupportMatrix = useCallback(async (): Promise<void> => {
    if (supportMatrixRequestInFlightRef.current || supportMatrix !== null) {
      return;
    }
    supportMatrixRequestInFlightRef.current = true;
    try {
      const result = await apiClient.getDocumentSupportMatrix();
      if (result.ok) {
        setSupportMatrix(result.data);
      }
    } finally {
      supportMatrixRequestInFlightRef.current = false;
    }
  }, [apiClient, supportMatrix]);

  const [messages, setMessages] = useState<ChatMessage[]>([
    buildMessage("assistant-bootstrap", "assistant", ASSISTANT_BOOTSTRAP_TEXT, {
      disclaimer: legalDisclaimer,
    }),
  ]);
  const [activityByTurn, setActivityByTurn] = useState<AgentActivityByTurn>({});
  const [activeActivityTurnId, setActiveActivityTurnId] = useState<string | null>(null);

  const nextActivityTurnId = useCallback((): string => {
    const turnId = `turn-${activityTurnCounterRef.current}`;
    activityTurnCounterRef.current += 1;
    return turnId;
  }, []);

  const applyTurnActivityEvents = useCallback(
    (
      turnId: string,
      updates: Array<{
        stage: AgentActivityStage;
        status: AgentActivityStatus;
        label: string;
        endedAt?: string;
        details?: string;
        meta?: AgentActivityMeta;
      }>
    ): void => {
      setActivityByTurn((currentActivityByTurn) => {
        let nextTurnEvents = currentActivityByTurn[turnId] ?? buildInitialTurnEvents(turnId);
        for (const update of updates) {
          nextTurnEvents = upsertTurnStageEvent(nextTurnEvents, {
            turnId,
            stage: update.stage,
            status: update.status,
            label: update.label,
            endedAt: update.endedAt,
            details: update.details,
            meta: update.meta,
          });
        }
        return {
          ...currentActivityByTurn,
          [turnId]: nextTurnEvents,
        };
      });
    },
    []
  );

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const storedLocale = window.localStorage.getItem(localeStorageKey);
    if (storedLocale === "en-CA" || storedLocale === "fr-CA") {
      setActiveLocale(storedLocale);
    }
  }, [localeStorageKey]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    window.localStorage.setItem(localeStorageKey, activeLocale);
  }, [activeLocale, localeStorageKey]);

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

  useEffect(() => {
    if (supportMatrix) {
      return;
    }
    if (documentReadiness || documentUploads.length > 0) {
      void loadDocumentSupportMatrix();
    }
  }, [documentReadiness, documentUploads.length, loadDocumentSupportMatrix, supportMatrix]);

  const submitPrompt = useCallback(
    async (prompt: string, options?: { isRetry?: boolean }): Promise<void> => {
      if (isSubmitting) {
        return;
      }

      const promptToSubmit = prompt.trim();
      if (!promptToSubmit) {
        return;
      }
      const activityTurnId = nextActivityTurnId();

      if (!options?.isRetry) {
        const userMessageId = nextMessageId("user", messageCounterRef);
        setMessages((currentMessages) => [
          ...currentMessages,
          buildMessage(userMessageId, "user", promptToSubmit),
        ]);
        setDraft("");
      }
      setActiveActivityTurnId(activityTurnId);
      setActivityByTurn((currentActivityByTurn) => {
        let initialEvents = buildInitialTurnEvents(activityTurnId);
        initialEvents = upsertTurnStageEvent(initialEvents, {
          turnId: activityTurnId,
          stage: "retrieval",
          status: "running",
          label: "Searching case law",
        });
        return {
          ...currentActivityByTurn,
          [activityTurnId]: initialEvents,
        };
      });

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
          locale: activeLocale,
          mode: "standard",
        });

        if (!chatResult.ok) {
          const completedAt = new Date().toISOString();
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
          applyTurnActivityEvents(activityTurnId, [
            {
              stage: "retrieval",
              status: "error",
              label: "Searching case law",
              endedAt: completedAt,
              meta: {
                code: chatResult.error.code,
              },
            },
            {
              stage: "delivery",
              status: "error",
              label: "Delivering response",
              endedAt: completedAt,
              meta: {
                code: chatResult.error.code,
                traceId: chatResult.traceId ?? null,
              },
            },
          ]);
          return;
        }

        const chatResponse = chatResult.data;
        const isPolicyRefusal = chatResponse.fallback_used.reason === "policy_block";
        const completedAt = new Date().toISOString();
        const synthesisStatus =
          chatResponse.fallback_used.used && !isPolicyRefusal ? "warning" : "success";
        const synthesisMeta: AgentActivityMeta | undefined =
          chatResponse.fallback_used.used
            ? {
                fallbackUsed: chatResponse.fallback_used.used,
                fallbackReason: chatResponse.fallback_used.reason ?? null,
                fallbackProvider: chatResponse.fallback_used.provider ?? null,
              }
            : undefined;
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
            activityTurnId,
          }),
        ]);

        setSupportContext({
          endpoint: "/api/chat",
          status: "success",
          traceId: chatResult.traceId,
          traceIdMismatch: false,
        });
        applyTurnActivityEvents(activityTurnId, [
          {
            stage: "intake",
            status: "success",
            label: "Understanding question",
            endedAt: completedAt,
          },
          {
            stage: "retrieval",
            status: "success",
            label: "Searching case law",
            endedAt: completedAt,
          },
          {
            stage: "grounding",
            status: "success",
            label: "Evaluating sources",
            endedAt: completedAt,
            meta: {
              sourceCount: chatResponse.citations.length,
            },
          },
          {
            stage: "synthesis",
            status: synthesisStatus,
            label: "Drafting answer",
            endedAt: completedAt,
            meta: synthesisMeta,
          },
          {
            stage: "delivery",
            status: isPolicyRefusal ? "blocked" : "success",
            label: "Delivering response",
            endedAt: completedAt,
            meta: isPolicyRefusal
              ? {
                  fallbackReason: chatResponse.fallback_used.reason ?? "policy_block",
                }
              : {
                  traceId: chatResult.traceId ?? null,
                },
          },
        ]);

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
    [activeLocale, apiClient, applyTurnActivityEvents, isSubmitting, legalDisclaimer, nextActivityTurnId]
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
        if (caseSearchResult.error.code === "SOURCE_UNAVAILABLE") {
          setSourceStatus((currentStatus) =>
            currentStatus ?? {
              official: "unavailable",
              canlii: "unavailable",
            }
          );
        }
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

        const resolvedMatterId = readinessResult.data.matter_id || normalizedMatterId;
        const shouldPreserveCompilation = documentMatterId.trim() === resolvedMatterId;
        setDocumentMatterId(resolvedMatterId);
        setDocumentReadiness((currentReadiness) => {
          const nextReadiness = toDocumentReadinessState(readinessResult.data);
          if (shouldPreserveCompilation) {
            nextReadiness.latestCompilation = currentReadiness?.latestCompilation ?? null;
          }
          return nextReadiness;
        });
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
    [apiClient, documentMatterId, showOperationalPanels]
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
          issueDetails: [],
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
              issueDetails: [],
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
              issueDetails: [],
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

      const compilationState = toDocumentCompilationState(packageResult.data);
      setDocumentStatusMessage(
        `Package generated. TOC items: ${compilationState.tocEntries.length}.`
      );
      setDocumentReadiness((currentReadiness) =>
        currentReadiness
          ? {
              ...currentReadiness,
              isReady: packageResult.data.is_ready,
              latestCompilation: compilationState,
            }
          : {
              isReady: packageResult.data.is_ready,
              missingRequiredItems: [],
              blockingIssues: [],
              warnings: [],
              requirementStatuses: [],
              latestCompilation: compilationState,
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

  const onDownloadDocumentPackage = useCallback(async (): Promise<void> => {
    if (
      isDocumentDownloadSubmitting ||
      isDocumentPackageSubmitting ||
      isDocumentIntakeSubmitting ||
      isDocumentReadinessSubmitting
    ) {
      return;
    }

    const matterId = documentMatterId.trim();
    if (!matterId) {
      setDocumentStatusMessage("Enter a matter ID or upload documents first.");
      return;
    }

    const latestCompilation = documentReadiness?.latestCompilation ?? null;
    if (latestCompilation?.compilationOutputMode !== "compiled_pdf") {
      setDocumentStatusMessage("Compiled binder unavailable. Generate package in compiled mode.");
      return;
    }

    setIsDocumentDownloadSubmitting(true);
    setDocumentStatusMessage("Preparing binder download...");
    try {
      const downloadResult = await apiClient.downloadMatterPackagePdf(matterId);
      if (!downloadResult.ok) {
        const unavailableMessage =
          downloadResult.policyReason === "document_compiled_artifact_unavailable"
            ? "Compiled binder unavailable. Generate package again or verify compiled mode."
            : downloadResult.policyReason === "document_package_not_ready"
              ? "Package blocked. Resolve missing or blocking items first."
              : null;
        const statusMessage = showOperationalPanels
          ? `Unable to download binder: ${downloadResult.error.message}${
              downloadResult.policyReason ? ` (Policy: ${downloadResult.policyReason})` : ""
            } (Trace ID: ${downloadResult.traceId ?? "Unavailable"})`
          : unavailableMessage ?? `Binder download failed. ${downloadResult.error.message}`;
        setDocumentStatusMessage(statusMessage);
        setSupportContext({
          endpoint: "/api/documents/matters/{matter_id}/package/download",
          status: "error",
          traceId: downloadResult.traceId,
          code: downloadResult.error.code,
          policyReason: downloadResult.policyReason,
          traceIdMismatch: downloadResult.traceIdMismatch,
        });
        return;
      }

      const fallbackFilename =
        latestCompilation.compiledArtifact?.filename || `${matterId}-compiled-binder.pdf`;
      const downloadFilename = downloadResult.data.filename || fallbackFilename;
      if (!startBrowserDownload(downloadResult.data.blob, downloadFilename)) {
        setDocumentStatusMessage(
          `Binder download is ready, but automatic download is unavailable in this browser (${downloadFilename}).`
        );
      } else {
        setDocumentStatusMessage(`Download started: ${downloadFilename}`);
      }
      setSupportContext({
        endpoint: "/api/documents/matters/{matter_id}/package/download",
        status: "success",
        traceId: downloadResult.traceId,
        traceIdMismatch: false,
      });
    } finally {
      setIsDocumentDownloadSubmitting(false);
    }
  }, [
    apiClient,
    documentMatterId,
    documentReadiness,
    isDocumentDownloadSubmitting,
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

  const onLocaleChange = useCallback((value: FrontendLocale): void => {
    setActiveLocale(value);
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
    activeLocale,
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
    isDocumentDownloadSubmitting,
    exportingCaseId,
    submissionPhase,
    chatPendingElapsedSeconds,
    isSlowChatResponse,
    activityByTurn,
    activeActivityTurnId,
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
    onLocaleChange,
    onDocumentUpload,
    onRefreshDocumentReadiness,
    onBuildDocumentPackage,
    onDownloadDocumentPackage,
    documentSupportMatrix: supportMatrix ?? DEFAULT_DOCUMENT_SUPPORT_MATRIX,
  };
}
