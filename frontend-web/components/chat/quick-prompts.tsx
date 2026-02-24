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
          className="min-h-[44px] min-w-[44px] rounded-full border border-slate-300 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-800 transition duration-200 ease-out hover:border-blue-300 hover:bg-blue-50 disabled:cursor-not-allowed disabled:opacity-60"
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
