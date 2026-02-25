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
      {prompts.map((prompt) => (
        <button
          className="min-h-[44px] min-w-[44px] rounded-full border border-[rgba(176,174,165,0.8)] bg-[rgba(250,249,245,0.92)] px-3 py-1.5 text-xs font-medium text-ink transition duration-200 ease-out hover:border-[rgba(217,119,87,0.5)] hover:bg-[#f6ede8] disabled:cursor-not-allowed disabled:opacity-60"
          disabled={isSubmitting}
          key={prompt}
          onClick={() => onPromptClick(prompt)}
          type="button"
        >
          {prompt}
        </button>
      ))}
    </div>
  );
}
