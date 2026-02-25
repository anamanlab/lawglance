import type {
  ApiErrorCode,
  CaseSearchResult,
  ChatCitation,
} from "@/lib/api-client";

export type MessageAuthor = "assistant" | "user";

export type ChatMessage = {
  id: string;
  author: MessageAuthor;
  content: string;
  disclaimer?: string;
  traceId?: string | null;
  citations?: ChatCitation[];
  isPolicyRefusal?: boolean;
};

export type ChatShellProps = {
  apiBaseUrl: string;
  legalDisclaimer: string;
  showOperationalPanels?: boolean;
};

export type SubmissionPhase = "idle" | "chat" | "cases";

export type SupportContext = {
  endpoint: "/api/chat" | "/api/search/cases";
  status: "success" | "error";
  traceId: string | null;
  code?: ApiErrorCode;
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
  isSubmitting: boolean;
  submissionPhase: SubmissionPhase;
  pendingCaseQuery: string | null;
  relatedCasesStatus: string;
  relatedCases: CaseSearchResult[];
  onSearch: () => void;
};
