import { useEffect, useState } from "react";

import { isLowSpecificityCaseQuery } from "@/components/chat/case-query-specificity";
import { RelatedCasePanelResearchResults } from "@/components/chat/related-case-panel-research-results";
import {
  buildRefinementSuggestions,
  DEFAULT_QUERY_HINT,
  LOW_SPECIFICITY_HINT,
} from "@/components/chat/related-case-panel-utils";
import type { RelatedCasePanelProps } from "@/components/chat/types";

type ResearchWorkflowPanelProps = Pick<
  RelatedCasePanelProps,
  | "isChatSubmitting"
  | "isCaseSearchSubmitting"
  | "isExportSubmitting"
  | "submissionPhase"
  | "caseSearchQuery"
  | "lastCaseSearchQuery"
  | "relatedCasesRetrievalMode"
  | "sourceStatus"
  | "prioritySourceStatus"
  | "onCaseSearchQueryChange"
  | "researchConfidence"
  | "confidenceReasons"
  | "intakeCompleteness"
  | "intakeHints"
  | "relatedCases"
  | "matterProfile"
  | "intakeObjective"
  | "intakeTargetCourt"
  | "intakeProceduralPosture"
  | "intakeIssueTags"
  | "intakeAnchorReference"
  | "intakeDateFrom"
  | "intakeDateTo"
  | "onIntakeObjectiveChange"
  | "onIntakeTargetCourtChange"
  | "onIntakeProceduralPostureChange"
  | "onIntakeIssueTagsChange"
  | "onIntakeAnchorReferenceChange"
  | "onIntakeDateFromChange"
  | "onIntakeDateToChange"
  | "onSearch"
  | "onExportCase"
  | "exportingCaseId"
>;

export function RelatedCasePanelResearch({
  isChatSubmitting,
  isCaseSearchSubmitting,
  isExportSubmitting,
  submissionPhase,
  caseSearchQuery,
  lastCaseSearchQuery,
  relatedCasesRetrievalMode,
  sourceStatus,
  prioritySourceStatus,
  onCaseSearchQueryChange,
  researchConfidence,
  confidenceReasons,
  intakeCompleteness,
  intakeHints,
  relatedCases,
  matterProfile,
  intakeObjective,
  intakeTargetCourt,
  intakeProceduralPosture,
  intakeIssueTags,
  intakeAnchorReference,
  intakeDateFrom,
  intakeDateTo,
  onIntakeObjectiveChange,
  onIntakeTargetCourtChange,
  onIntakeProceduralPostureChange,
  onIntakeIssueTagsChange,
  onIntakeAnchorReferenceChange,
  onIntakeDateFromChange,
  onIntakeDateToChange,
  onSearch,
  onExportCase,
  exportingCaseId,
}: ResearchWorkflowPanelProps): JSX.Element {
  const caseSearchInputId = "related-case-query";
  const caseSearchHintId = "related-case-query-hint";
  const [showAdvancedIntake, setShowAdvancedIntake] = useState(false);

  const normalizedCurrentQuery = caseSearchQuery.trim().toLowerCase();
  const normalizedLastSearchQuery = (lastCaseSearchQuery ?? "").trim().toLowerCase();
  const hasResults = relatedCases.length > 0;
  const hasCaseSearchQuery = caseSearchQuery.trim().length >= 2;
  const lowSpecificityQuery = isLowSpecificityCaseQuery(caseSearchQuery);
  const queryChangedSinceLastSearch =
    hasResults &&
    Boolean(normalizedCurrentQuery) &&
    Boolean(normalizedLastSearchQuery) &&
    normalizedCurrentQuery !== normalizedLastSearchQuery;
  const queryHint = queryChangedSinceLastSearch
    ? "Current query differs from the query used for the listed results."
    : lowSpecificityQuery
      ? LOW_SPECIFICITY_HINT
      : DEFAULT_QUERY_HINT;
  const refinementSuggestions = buildRefinementSuggestions({
    query: caseSearchQuery,
    matterProfile,
  });

  const disableCaseSearchControls = isChatSubmitting || isCaseSearchSubmitting;
  const disableExportControls = isChatSubmitting || isCaseSearchSubmitting || isExportSubmitting;

  useEffect(() => {
    if (
      intakeProceduralPosture ||
      intakeIssueTags.trim() ||
      intakeAnchorReference.trim() ||
      intakeDateFrom ||
      intakeDateTo
    ) {
      setShowAdvancedIntake(true);
    }
  }, [
    intakeAnchorReference,
    intakeDateFrom,
    intakeDateTo,
    intakeIssueTags,
    intakeProceduralPosture,
  ]);

  return (
    <>
      <div className="mt-4 rounded-xl border border-[var(--imm-border-soft)] bg-[var(--imm-surface-warm)] p-3">
        <label
          className="mb-1 block min-h-[24px] py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-muted"
          htmlFor={caseSearchInputId}
        >
          Case search query
        </label>
        <input
          className="min-h-[44px] w-full rounded-lg border border-[var(--imm-border-soft)] bg-[var(--imm-surface-soft)] px-3 py-2 text-xs leading-6 text-ink shadow-sm outline-none transition duration-150 focus:border-accent-blue focus:ring-2 focus:ring-[rgba(95,132,171,0.2)] disabled:cursor-not-allowed disabled:opacity-70"
          disabled={disableCaseSearchControls}
          id={caseSearchInputId}
          aria-describedby={caseSearchHintId}
          maxLength={300}
          onChange={(event) => {
            onCaseSearchQueryChange(event.target.value);
          }}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !disableCaseSearchControls && hasCaseSearchQuery) {
              event.preventDefault();
              onSearch();
            }
          }}
          placeholder="Example: Express Entry refusal Federal Court"
          type="text"
          value={caseSearchQuery}
        />
        <p
          className={`mt-2 text-[11px] leading-5 ${queryChangedSinceLastSearch || lowSpecificityQuery ? "text-warning" : "text-muted"}`}
          id={caseSearchHintId}
        >
          {queryHint}
        </p>

        <div className="mt-3 rounded-lg border border-[var(--imm-border-soft)] bg-[var(--imm-surface-warm)] p-3">
          <p className="text-[10px] uppercase tracking-[0.12em] text-muted">
            Research intake (recommended)
          </p>
          <p className="mt-1 text-[11px] leading-5 text-muted">
            Add context so ranking and confidence are grounded in your litigation objective.
          </p>
          <div className="mt-2 grid gap-2 sm:grid-cols-2">
            <label className="text-[11px] text-muted">
              Research objective
              <select
                aria-label="Research objective"
                className="mt-1 min-h-[38px] w-full rounded-md border border-[var(--imm-border-soft)] bg-[var(--imm-surface)] px-2 text-xs text-ink"
                disabled={disableCaseSearchControls}
                onChange={(event) => onIntakeObjectiveChange(event.target.value as typeof intakeObjective)}
                value={intakeObjective}
              >
                <option value="">Not specified</option>
                <option value="support_precedent">Support precedent</option>
                <option value="distinguish_precedent">Distinguish precedent</option>
                <option value="background_research">Background research</option>
              </select>
            </label>
            <label className="text-[11px] text-muted">
              Target court
              <select
                aria-label="Target court"
                className="mt-1 min-h-[38px] w-full rounded-md border border-[var(--imm-border-soft)] bg-[var(--imm-surface)] px-2 text-xs text-ink"
                disabled={disableCaseSearchControls}
                onChange={(event) => onIntakeTargetCourtChange(event.target.value)}
                value={intakeTargetCourt}
              >
                <option value="">Not specified</option>
                <option value="fc">Federal Court (FC)</option>
                <option value="fca">Federal Court of Appeal (FCA)</option>
                <option value="scc">Supreme Court (SCC)</option>
              </select>
            </label>
          </div>
          <button
            aria-expanded={showAdvancedIntake}
            className="imm-btn-secondary mt-2 px-2.5 py-1 text-[11px]"
            disabled={disableCaseSearchControls}
            onClick={() => setShowAdvancedIntake((currentValue) => !currentValue)}
            type="button"
          >
            {showAdvancedIntake ? "Hide advanced filters" : "Show advanced filters"}
          </button>
          {showAdvancedIntake ? (
            <div className="mt-2 grid gap-2 sm:grid-cols-2">
              <label className="text-[11px] text-muted">
                Procedural posture
                <select
                  aria-label="Procedural posture"
                  className="mt-1 min-h-[38px] w-full rounded-md border border-[var(--imm-border-soft)] bg-[var(--imm-surface)] px-2 text-xs text-ink"
                  disabled={disableCaseSearchControls}
                  onChange={(event) =>
                    onIntakeProceduralPostureChange(event.target.value as typeof intakeProceduralPosture)
                  }
                  value={intakeProceduralPosture}
                >
                  <option value="">Not specified</option>
                  <option value="judicial_review">Judicial review</option>
                  <option value="appeal">Appeal</option>
                  <option value="motion">Motion</option>
                  <option value="application">Application</option>
                </select>
              </label>
              <label className="text-[11px] text-muted">
                Issue tags
                <input
                  aria-label="Issue tags"
                  className="mt-1 min-h-[38px] w-full rounded-md border border-[var(--imm-border-soft)] bg-[var(--imm-surface)] px-2 text-xs text-ink"
                  disabled={disableCaseSearchControls}
                  onChange={(event) => onIntakeIssueTagsChange(event.target.value)}
                  placeholder="procedural_fairness, inadmissibility"
                  type="text"
                  value={intakeIssueTags}
                />
              </label>
              <label className="text-[11px] text-muted sm:col-span-2">
                Citation or docket anchor
                <input
                  aria-label="Citation or docket anchor"
                  className="mt-1 min-h-[38px] w-full rounded-md border border-[var(--imm-border-soft)] bg-[var(--imm-surface)] px-2 text-xs text-ink"
                  disabled={disableCaseSearchControls}
                  onChange={(event) => onIntakeAnchorReferenceChange(event.target.value)}
                  placeholder="2024 FCA 77 or A-77-23"
                  type="text"
                  value={intakeAnchorReference}
                />
              </label>
              <label className="text-[11px] text-muted">
                Decision date from
                <input
                  aria-label="Decision date from"
                  className="mt-1 min-h-[38px] w-full rounded-md border border-[var(--imm-border-soft)] bg-[var(--imm-surface)] px-2 text-xs text-ink"
                  disabled={disableCaseSearchControls}
                  onChange={(event) => onIntakeDateFromChange(event.target.value)}
                  type="date"
                  value={intakeDateFrom}
                />
              </label>
              <label className="text-[11px] text-muted">
                Decision date to
                <input
                  aria-label="Decision date to"
                  className="mt-1 min-h-[38px] w-full rounded-md border border-[var(--imm-border-soft)] bg-[var(--imm-surface)] px-2 text-xs text-ink"
                  disabled={disableCaseSearchControls}
                  onChange={(event) => onIntakeDateToChange(event.target.value)}
                  type="date"
                  value={intakeDateTo}
                />
              </label>
            </div>
          ) : null}
        </div>

        {refinementSuggestions.length ? (
          <div className="mt-3">
            <p className="text-[10px] uppercase tracking-[0.12em] text-muted">
              Query refinements
            </p>
            <div className="mt-2 flex flex-wrap gap-2">
              {refinementSuggestions.map((suggestion) => (
                <button
                  className="imm-btn-secondary px-2.5 py-1 text-[11px]"
                  disabled={disableCaseSearchControls}
                  key={suggestion}
                  onClick={() => {
                    onCaseSearchQueryChange(suggestion);
                  }}
                  type="button"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        ) : null}

        <div className="mt-3 flex flex-col items-stretch gap-2 sm:flex-row sm:flex-wrap sm:items-center">
          <button
            aria-controls="related-case-results"
            aria-expanded={hasResults}
            className="imm-btn-secondary px-3 py-1.5 text-xs"
            disabled={disableCaseSearchControls || !hasCaseSearchQuery}
            onClick={onSearch}
            type="button"
          >
            {isCaseSearchSubmitting && submissionPhase === "cases" ? "Searching..." : "Find related cases"}
          </button>
          <span className="self-start text-[10px] uppercase tracking-[0.12em] text-muted sm:self-auto">
            Grounded lawyer research
          </span>
        </div>
      </div>

      {isCaseSearchSubmitting && submissionPhase === "cases" ? (
        <div aria-live="polite" className="mt-3 min-h-[20px]" role="status">
          <div className="flex animate-pulse flex-col gap-2.5 py-1">
            <div className="h-2.5 w-3/4 rounded-full bg-[rgba(159,154,142,0.25)]" />
            <div className="h-2.5 w-1/2 rounded-full bg-[rgba(159,154,142,0.25)]" />
            <span className="sr-only">Running grounded lawyer case research...</span>
          </div>
        </div>
      ) : null}

      <RelatedCasePanelResearchResults
        relatedCases={relatedCases}
        lastCaseSearchQuery={lastCaseSearchQuery}
        relatedCasesRetrievalMode={relatedCasesRetrievalMode}
        sourceStatus={sourceStatus}
        prioritySourceStatus={prioritySourceStatus}
        researchConfidence={researchConfidence}
        confidenceReasons={confidenceReasons}
        intakeCompleteness={intakeCompleteness}
        intakeHints={intakeHints}
        onExportCase={onExportCase}
        exportingCaseId={exportingCaseId}
        isExportSubmitting={isExportSubmitting}
        submissionPhase={submissionPhase}
        disableExportControls={disableExportControls}
      />
    </>
  );
}

