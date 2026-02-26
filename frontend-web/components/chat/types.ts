import type {
  ApiErrorCode,
  ChatCitation,
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

export type SupportContext = {
  endpoint:
    | "/api/chat"
    | "/api/search/cases"
    | "/api/research/lawyer-cases"
    | "/api/export/cases"
    | "/api/export/cases/approval";
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
