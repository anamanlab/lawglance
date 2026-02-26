type QuickPromptsProps = {
  prompts: string[];
  isSubmitting: boolean;
  onPromptClick: (prompt: string) => void;
};

export function QuickPrompts({
  prompts,
  isSubmitting,
  onPromptClick,
}: QuickPromptsProps): JSX.Element {
  return (
    <div aria-label="Quick prompts" className="flex flex-wrap gap-2" role="group">
      {prompts.map((prompt, index) => (
        <button
          className="group imm-fade-up min-h-[44px] w-full min-w-[44px] rounded-md border border-[rgba(176,174,165,0.72)] bg-[var(--imm-surface-soft)] px-3 py-1.5 text-left text-xs font-semibold leading-5 text-ink transition duration-200 ease-out hover:-translate-y-0.5 hover:border-[rgba(217,119,87,0.42)] hover:bg-[var(--imm-primary-soft)] disabled:cursor-not-allowed disabled:opacity-60 sm:w-auto sm:text-[11px]"
          disabled={isSubmitting}
          key={prompt}
          onClick={() => onPromptClick(prompt)}
          style={{ animationDelay: `${140 + index * 30}ms` }}
          type="button"
        >
          <span
            aria-hidden="true"
            className="block border-b border-[rgba(176,174,165,0.28)] pb-1 text-[10px] uppercase tracking-[0.14em] text-muted group-hover:text-[var(--imm-warning-ink)]"
          >
            Prompt {index + 1}
          </span>
          <span className="mt-1 block">{prompt}</span>
        </button>
      ))}
    </div>
  );
}
