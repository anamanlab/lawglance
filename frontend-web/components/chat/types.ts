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
  relatedCasesStatus: string;
  relatedCases: LawyerCaseSupport[];
  matterProfile?: Record<string, string | string[] | null>;
  onCaseSearchQueryChange: (value: string) => void;
  onSearch: () => void;
  onExportCase: (result: LawyerCaseSupport) => void;
  exportingCaseId: string | null;
};
