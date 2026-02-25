import { useRef, type FormEvent, type RefObject } from "react";

import { MAX_MESSAGE_LENGTH, QUICK_PROMPTS } from "@/components/chat/constants";
import { QuickPrompts } from "@/components/chat/quick-prompts";
import { phaseLabel } from "@/components/chat/utils";
import type { SubmissionPhase } from "@/components/chat/types";

type MessageComposerProps = {
  draft: string;
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
    remainingCharacters <= 200 ? "text-amber-700" : "text-slate-500";

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-3 shadow-[0_10px_28px_rgba(15,23,42,0.08)]">
      <form className="space-y-3" onSubmit={onSubmit} ref={formRef}>
        <label className="block text-sm font-semibold text-slate-700" htmlFor="chat-input">
          Ask a Canadian immigration question
        </label>

        <QuickPrompts
          isSubmitting={isSubmitting}
          onPromptClick={onQuickPromptClick}
          prompts={QUICK_PROMPTS}
        />

        <textarea
          aria-describedby={`${hintId} ${countId}${isSubmitting ? ` ${statusId}` : ""}`}
          className="h-28 w-full resize-y rounded-xl border border-slate-300 px-3 py-2 text-base leading-7 text-ink shadow-sm transition duration-200 ease-out focus:border-blue-600 focus:ring-2 focus:ring-blue-200"
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

        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p
              aria-live="polite"
              className={`text-[11px] ${countToneClass}`}
              id={countId}
            >
              {remainingCharacters} characters remaining
            </p>
            <p className="text-[11px] text-slate-500" id={hintId}>
              Tip: Press Ctrl/Cmd+Enter to send.
            </p>
            {isSubmitting ? (
              <p
                aria-live="polite"
                className="text-[11px] text-slate-500"
                id={statusId}
              >
                {phaseLabel(submissionPhase)}
              </p>
            ) : null}
          </div>

          <button
            className="min-h-[44px] min-w-[120px] rounded-lg bg-gradient-to-r from-blue-900 to-blue-700 px-4 py-2 text-sm font-semibold text-white transition duration-200 ease-out hover:from-blue-800 hover:to-blue-600 disabled:cursor-not-allowed disabled:from-slate-400 disabled:to-slate-400"
            disabled={sendDisabled}
            type="submit"
          >
            {isSubmitting
              ? submissionPhase === "cases"
                ? "Loading..."
                : "Sending..."
              : "Send"}
          </button>
        </div>
      </form>
    </section>
  );
}
