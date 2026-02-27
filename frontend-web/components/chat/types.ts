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

export type ChatShellProps = {
  apiBaseUrl: string;
  legalDisclaimer: string;
  showOperationalPanels?: boolean;
};

export type SubmissionPhase = "idle" | "chat" | "cases" | "export";
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
export type DocumentUploadItem = {
  fileId: string;
  filename: string;
  classification: string | null;
  status: DocumentUploadStatus;
  issues: string[];
};
export type DocumentReadinessState = {
  isReady: boolean;
  missingRequiredItems: string[];
  blockingIssues: string[];
  warnings: string[];
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
    | "/api/documents/matters/{matter_id}/package";
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
