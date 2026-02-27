import type {
  ApiErrorCode,
  ChatCitation,
  DocumentForum,
  FallbackUsed as ApiFallbackUsed,
  LawyerCaseSupport,
} from "@/lib/api-client";

export type MessageAuthor = "assistant" | "user";

export type ChatMessage = {
  id: string;
  author: MessageAuthor;
  content: string;
  disclaimer?: string;
  confidence?: "low" | "medium" | "high";
  traceId?: string | null;
  citations?: ChatCitation[];
  isPolicyRefusal?: boolean;
  fallbackUsed?: ApiFallbackUsed;
};

export type AgentActivityStage = "intake" | "retrieval" | "grounding" | "synthesis" | "delivery";
export type AgentActivityStatus = "running" | "success" | "warning" | "error" | "blocked";
export type AgentActivityMeta = Record<string, string | number | boolean | null>;
export type AgentActivityEvent = {
  id: string;
  turnId: string;
  stage: AgentActivityStage;
  status: AgentActivityStatus;
  label: string;
  startedAt: string;
  endedAt?: string;
  details?: string;
  meta?: AgentActivityMeta;
};

export type ChatShellProps = {
  apiBaseUrl: string;
  legalDisclaimer: string;
  showOperationalPanels?: boolean;
  enableAgentThinkingTimeline: boolean;
};

export type SubmissionPhase = "idle" | "chat" | "cases" | "export";
export type FrontendLocale = "en-CA" | "fr-CA";
export type CaseRetrievalMode = "auto" | "manual" | null;
export type ResearchConfidence = "low" | "medium" | "high" | null;
export type IntakeCompleteness = "low" | "medium" | "high" | null;
export type ResearchSourceStatus = Record<string, string> | null;
export type ResearchObjective =
  | "support_precedent"
  | "distinguish_precedent"
  | "background_research"
  | "";
export type ResearchPosture = "judicial_review" | "appeal" | "motion" | "application" | "";
export type DocumentUploadStatus = "pending" | "uploaded" | "needs_review" | "failed";
export type DocumentUploadIssueDetail = {
  code: string;
  message: string;
  severity: "blocking" | "warning" | "info" | string;
  remediation: string | null;
};
export type DocumentUploadItem = {
  fileId: string;
  filename: string;
  classification: string | null;
  status: DocumentUploadStatus;
  issues: string[];
  issueDetails: DocumentUploadIssueDetail[];
};
export type DocumentCompilationTocEntry = {
  position: number;
  documentType: string;
  filename: string;
  startPage: number | null;
  endPage: number | null;
};
export type DocumentCompilationRuleViolation = {
  severity: "blocking" | "warning" | string;
  code: string;
  sourceUrl: string | null;
  remediation: string | null;
};
export type DocumentCompilationProfile = {
  id: string;
  version: string;
};
export type DocumentCompiledArtifact = {
  filename: string;
  byteSize: number;
  sha256: string;
  pageCount: number;
};
export type DocumentCompilationPaginationSummary =
  | string
  | {
      total_documents?: number;
      total_pages?: number;
      last_assigned_page?: number;
      totalDocuments?: number;
      totalPages?: number;
      lastAssignedPage?: number;
    };
export type DocumentCompilationSectionSlotStatus = {
  documentType: string;
  status: "present" | "missing" | "warning" | string;
  ruleScope: "base" | "conditional";
  reason: string | null;
};
export type DocumentCompilationRecordSection = {
  sectionId: string;
  title: string;
  instructions: string;
  documentTypes: string[];
  sectionStatus: "present" | "missing" | "warning" | string;
  slotStatuses: DocumentCompilationSectionSlotStatus[];
  missingDocumentTypes: string[];
  missingReasons: string[];
};
export type DocumentCompilationState = {
  tocEntries: DocumentCompilationTocEntry[];
  paginationSummary: DocumentCompilationPaginationSummary | null;
  ruleViolations: DocumentCompilationRuleViolation[];
  compilationProfile: DocumentCompilationProfile | null;
  compilationOutputMode: "metadata_plan_only" | "compiled_pdf" | null;
  compiledArtifact: DocumentCompiledArtifact | null;
  recordSections: DocumentCompilationRecordSection[];
};
export type DocumentSupportMatrix = {
  supported_profiles_by_forum: Record<string, string[]>;
  unsupported_profile_families: string[];
};
export type DocumentReadinessState = {
  isReady: boolean;
  missingRequiredItems: string[];
  blockingIssues: string[];
  warnings: string[];
  requirementStatuses: {
    item: string;
    status: "present" | "missing" | "warning";
    ruleScope: "base" | "conditional";
    reason: string | null;
  }[];
  latestCompilation: DocumentCompilationState | null;
};

export type SupportContext = {
  endpoint:
    | "/api/chat"
    | "/api/search/cases"
    | "/api/research/lawyer-cases"
    | "/api/export/cases"
    | "/api/export/cases/approval"
    | "/api/documents/intake"
    | "/api/documents/matters/{matter_id}/readiness"
    | "/api/documents/matters/{matter_id}/package"
    | "/api/documents/matters/{matter_id}/package/download";
  status: "success" | "error";
  traceId: string | null;
  code?: ApiErrorCode;
  policyReason?: string | null;
  traceIdMismatch: boolean;
};

export type ChatErrorState = {
  title: string;
  detail: string;
  action: string;
  retryable: boolean;
  traceId: string | null;
};

export type ErrorCopy = {
  title: string;
  detail: string;
  action: string;
  retryable: boolean;
};

export type RelatedCasePanelProps = {
  statusToneClass?: string;
  supportStatus?: SupportContext["status"] | null;
  showDiagnostics?: boolean;
  documentForum: DocumentForum;
  documentMatterId: string;
  documentStatusMessage: string;
  documentUploads: DocumentUploadItem[];
  documentReadiness: DocumentReadinessState | null;
  isDocumentIntakeSubmitting: boolean;
  isDocumentReadinessSubmitting: boolean;
  isDocumentPackageSubmitting: boolean;
  isDocumentDownloadSubmitting: boolean;
  isChatSubmitting: boolean;
  isCaseSearchSubmitting: boolean;
  isExportSubmitting: boolean;
  submissionPhase: SubmissionPhase;
  caseSearchQuery: string;
  lastCaseSearchQuery: string | null;
  relatedCasesRetrievalMode: CaseRetrievalMode;
  sourceStatus: ResearchSourceStatus;
  relatedCasesStatus: string;
  researchConfidence: ResearchConfidence;
  confidenceReasons: string[];
  intakeCompleteness: IntakeCompleteness;
  intakeHints: string[];
  relatedCases: LawyerCaseSupport[];
  matterProfile?: Record<string, string | string[] | null>;
  intakeObjective: ResearchObjective;
  intakeTargetCourt: string;
  intakeProceduralPosture: ResearchPosture;
  intakeIssueTags: string;
  intakeAnchorReference: string;
  intakeDateFrom: string;
  intakeDateTo: string;
  onDocumentForumChange: (value: DocumentForum) => void;
  onDocumentMatterIdChange: (value: string) => void;
  onDocumentUpload: (files: File[]) => void;
  onRefreshDocumentReadiness: () => void;
  onBuildDocumentPackage: () => void;
  onDownloadDocumentPackage: () => void;
  documentSupportMatrix: DocumentSupportMatrix;
  onCaseSearchQueryChange: (value: string) => void;
  onIntakeObjectiveChange: (value: ResearchObjective) => void;
  onIntakeTargetCourtChange: (value: string) => void;
  onIntakeProceduralPostureChange: (value: ResearchPosture) => void;
  onIntakeIssueTagsChange: (value: string) => void;
  onIntakeAnchorReferenceChange: (value: string) => void;
  onIntakeDateFromChange: (value: string) => void;
  onIntakeDateToChange: (value: string) => void;
  onSearch: () => void;
  onExportCase: (result: LawyerCaseSupport) => void;
  exportingCaseId: string | null;
};
