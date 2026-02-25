import type { ChatErrorState } from "@/components/chat/types";

type StatusBannerProps = {
  chatError: ChatErrorState | null;
  isSubmitting: boolean;
  retryPrompt: string | null;
  showDiagnostics?: boolean;
  onRetryLastRequest: () => void;
};

export function StatusBanner({
  chatError,
  isSubmitting,
  retryPrompt,
  showDiagnostics = false,
  onRetryLastRequest,
}: StatusBannerProps): JSX.Element | null {
  if (!chatError) {
    return null;
  }

  return (
    <div
      aria-live="assertive"
      className="rounded-xl border border-red-300 bg-red-50 p-3 text-sm text-red-900"
    >
      <p className="font-semibold">{chatError.title}</p>
      <p className="mt-1">{chatError.detail}</p>
      <p className="mt-2 text-xs">{chatError.action}</p>
      {showDiagnostics ? (
        <p className="mt-1 text-xs">Trace ID: {chatError.traceId ?? "Unavailable"}</p>
      ) : null}
      {chatError.retryable && retryPrompt ? (
        <button
          className="mt-2 min-h-[44px] min-w-[44px] rounded-md bg-red-700 px-3 py-1.5 text-xs font-semibold text-white transition duration-200 ease-out hover:bg-red-800 disabled:cursor-not-allowed disabled:bg-red-500"
          disabled={isSubmitting}
          onClick={onRetryLastRequest}
          type="button"
        >
          Retry last request
        </button>
      ) : null}
    </div>
  );
}
