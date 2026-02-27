import { useRef, type FormEvent, type RefObject } from "react";

import { MAX_MESSAGE_LENGTH, QUICK_PROMPTS } from "@/components/chat/constants";
import { QuickPrompts } from "@/components/chat/quick-prompts";
import { phaseLabel } from "@/components/chat/utils";
import type { SubmissionPhase } from "@/components/chat/types";

type MessageComposerProps = {
  draft: string;
  isFirstRun: boolean;
  isSubmitting: boolean;
  sendDisabled: boolean;
  remainingCharacters: number;
  submissionPhase: SubmissionPhase;
  textareaRef: RefObject<HTMLTextAreaElement>;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onDraftChange: (value: string) => void;
  onQuickPromptClick: (prompt: string) => void;
};

export function MessageComposer({
  draft,
  isFirstRun,
  isSubmitting,
  sendDisabled,
  remainingCharacters,
  submissionPhase,
  textareaRef,
  onSubmit,
  onDraftChange,
  onQuickPromptClick,
}: MessageComposerProps): JSX.Element {
  const countId = "chat-input-count";
  const hintId = "chat-input-hint";
  const statusId = "chat-input-status";
  const formRef = useRef<HTMLFormElement | null>(null);
  const countToneClass =
    remainingCharacters <= 200 ? "text-warning" : "text-muted";

  return (
    <section className="imm-paper-card imm-fade-up rounded-2xl p-4 md:p-5" style={{ animationDelay: "180ms" }}>
      <form className="relative z-10 space-y-4" onSubmit={onSubmit} ref={formRef}>
        {isFirstRun ? (
          <div className="rounded-xl border border-[rgba(95,132,171,0.35)] bg-[rgba(231,237,245,0.8)] p-3">
            <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--imm-accent-ink)]">
              Guided Start - Step 1 of 3
            </p>
            <p className="mt-1 text-xs leading-6 text-muted">
              Recommended next action: load a starter question, then send and review grounded sources.
            </p>
            <button
              className="imm-btn-secondary mt-2 px-2.5 py-1 text-[11px]"
              disabled={isSubmitting}
              onClick={() => onQuickPromptClick(QUICK_PROMPTS[0] ?? "")}
              type="button"
            >
              Load starter question
            </button>
          </div>
        ) : null}

        <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="imm-kicker">Question Draft</p>
            <label className="mt-2 block text-base font-semibold text-ink" htmlFor="chat-input">
              Ask a Canadian immigration question
            </label>
          </div>
          <p className="hidden text-[11px] uppercase tracking-[0.12em] text-muted sm:block">
            Structured prompts available below
          </p>
        </div>

        <div className="rounded-xl border border-[var(--imm-border-soft)] bg-[var(--imm-surface-warm)] p-3">
          <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">
            Quick prompts
          </p>
          <QuickPrompts
            isSubmitting={isSubmitting}
            onPromptClick={onQuickPromptClick}
            prompts={QUICK_PROMPTS}
          />
        </div>

        <div className="rounded-xl border border-[var(--imm-border-soft)] bg-[var(--imm-surface-soft)] p-2">
          <textarea
            aria-describedby={`${hintId} ${countId}${isSubmitting ? ` ${statusId}` : ""}`}
            className="imm-ledger-textarea h-32 w-full resize-y rounded-lg border border-[var(--imm-border-soft)] bg-[var(--imm-surface)] px-3 py-2 text-base leading-7 text-ink shadow-sm transition duration-200 ease-out focus:border-accent-blue focus:ring-2 focus:ring-[rgba(95,132,171,0.2)]"
            disabled={isSubmitting}
            id="chat-input"
            maxLength={MAX_MESSAGE_LENGTH}
            name="chat-input"
            onChange={(event) => onDraftChange(event.target.value)}
            onKeyDown={(event) => {
              if (
                event.key === "Enter" &&
                (event.ctrlKey || event.metaKey) &&
                !isSubmitting &&
                !sendDisabled
              ) {
                event.preventDefault();
                formRef.current?.requestSubmit();
              }
            }}
            placeholder="Example: What are the eligibility basics for Express Entry?"
            ref={textareaRef}
            value={draft}
          />
        </div>

        <div className="flex flex-col gap-3 border-t border-[var(--imm-border-soft)] pt-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="space-y-1">
            <p aria-live="polite" className={`text-[11px] font-medium ${countToneClass}`} id={countId}>
              {remainingCharacters} characters remaining
            </p>
            <p className="text-[11px] text-muted" id={hintId}>
              Tip: Press Ctrl/Cmd+Enter to send.
            </p>
            {isSubmitting ? (
              <p aria-live="polite" className="font-mono text-[11px] text-muted" id={statusId}>
                {phaseLabel(submissionPhase)}
              </p>
            ) : null}
          </div>

          <div className="flex w-full items-center gap-2 self-start sm:w-auto sm:self-auto">
            <span className="imm-pill imm-pill-neutral hidden md:inline-flex">
              Research mode
            </span>
            <button
              className="imm-btn-primary w-full min-w-[132px] px-4 py-2 text-sm sm:w-auto"
              disabled={sendDisabled}
              type="submit"
            >
              {isSubmitting
                ? submissionPhase === "cases" || submissionPhase === "export"
                  ? "Loading..."
                  : "Sending..."
                : "Send"}
            </button>
          </div>
        </div>
      </form>
    </section>
  );
}
