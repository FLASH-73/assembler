"use client";

import { useCallback, useState } from "react";
import type { AssemblyStep, PlanAnalysis, PlanSuggestion } from "@/lib/types";
import { useAssembly } from "@/context/AssemblyContext";
import { api } from "@/lib/api";
import { MOCK_PLAN_ANALYSIS } from "@/lib/mock-data";
import { ActionButton } from "./ActionButton";

function difficultyColor(score: number): string {
  if (score <= 3) return "bg-status-success text-white";
  if (score <= 6) return "bg-status-warning text-white";
  return "bg-status-error text-white";
}

interface SuggestionRowProps {
  suggestion: PlanSuggestion;
  onApply: (s: PlanSuggestion) => void;
  onDismiss: (s: PlanSuggestion) => void;
}

function SuggestionRow({ suggestion, onApply, onDismiss }: SuggestionRowProps) {
  return (
    <div className="flex flex-col gap-1 rounded-md border border-bg-tertiary p-2">
      <div className="flex items-center justify-between">
        <span className="font-mono text-[11px] text-text-secondary">
          {suggestion.stepId}.{suggestion.field}
        </span>
        <div className="flex gap-1">
          <button
            className="rounded px-1.5 py-0.5 text-[10px] font-medium text-status-success hover:bg-status-success-bg"
            onClick={() => onApply(suggestion)}
          >
            Apply
          </button>
          <button
            className="rounded px-1.5 py-0.5 text-[10px] font-medium text-text-tertiary hover:bg-bg-secondary"
            onClick={() => onDismiss(suggestion)}
          >
            Dismiss
          </button>
        </div>
      </div>
      <div className="flex items-center gap-2 text-[11px]">
        <span className="text-text-tertiary line-through">{suggestion.oldValue}</span>
        <span className="text-text-tertiary">&rarr;</span>
        <span className="font-medium text-text-primary">{suggestion.newValue}</span>
      </div>
      <p className="text-[11px] text-text-secondary">{suggestion.reason}</p>
    </div>
  );
}

export function AnalysisPanel() {
  const { assembly } = useAssembly();
  const [analysis, setAnalysis] = useState<PlanAnalysis | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isExpanded, setIsExpanded] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dismissedIds, setDismissedIds] = useState<Set<string>>(new Set());

  const handleAnalyze = useCallback(async () => {
    if (!assembly) return;
    setIsLoading(true);
    setError(null);
    setDismissedIds(new Set());
    try {
      const result = await api.analyzeAssembly(assembly.id);
      setAnalysis(result);
      setIsExpanded(true);
    } catch (err) {
      if (err instanceof TypeError) {
        setAnalysis(MOCK_PLAN_ANALYSIS);
        setIsExpanded(true);
      } else {
        setError(err instanceof Error ? err.message : "Analysis failed");
      }
    } finally {
      setIsLoading(false);
    }
  }, [assembly]);

  const handleApply = useCallback(
    async (suggestion: PlanSuggestion) => {
      if (!assembly) return;
      try {
        await api.updateStep(assembly.id, suggestion.stepId, {
          [suggestion.field]: suggestion.newValue,
        } as Partial<AssemblyStep>);
        setDismissedIds((prev) => new Set(prev).add(suggestion.stepId + suggestion.field));
      } catch {
        // Keep suggestion visible on error
      }
    },
    [assembly],
  );

  const handleDismiss = useCallback((suggestion: PlanSuggestion) => {
    setDismissedIds((prev) => new Set(prev).add(suggestion.stepId + suggestion.field));
  }, []);

  if (!assembly) return null;

  const visibleSuggestions = analysis?.suggestions.filter(
    (s) => !dismissedIds.has(s.stepId + s.field),
  );

  return (
    <div className="mb-3 flex flex-col gap-2">
      {!analysis ? (
        <ActionButton
          variant="secondary"
          disabled={isLoading}
          onClick={() => void handleAnalyze()}
        >
          {isLoading ? "Analyzing..." : "Analyze with AI"}
        </ActionButton>
      ) : (
        <button
          className="flex w-full items-center justify-between rounded-md bg-bg-secondary px-3 py-2 text-left text-[12px] font-medium text-text-primary hover:bg-bg-tertiary"
          onClick={() => setIsExpanded((prev) => !prev)}
        >
          <span>AI Analysis</span>
          <span className="text-text-tertiary">{isExpanded ? "\u25B2" : "\u25BC"}</span>
        </button>
      )}

      {error && <p className="text-[11px] text-status-error">{error}</p>}

      {analysis && isExpanded && (
        <div className="flex flex-col gap-2 rounded-md border border-bg-tertiary bg-bg-secondary/50 p-3">
          {/* Summary + difficulty + teaching time */}
          <div className="flex items-start gap-2">
            <span
              className={`inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[11px] font-bold ${difficultyColor(analysis.difficultyScore)}`}
            >
              {analysis.difficultyScore}
            </span>
            <div className="flex-1">
              <p className="text-[12px] leading-relaxed text-text-primary">
                {analysis.summary}
              </p>
              <p className="mt-0.5 text-[11px] text-text-tertiary">
                ~{analysis.estimatedTeachingMinutes} min teaching time
              </p>
            </div>
          </div>

          {/* Warnings */}
          {analysis.warnings.length > 0 && (
            <div className="rounded-md bg-status-warning-bg px-3 py-2">
              {analysis.warnings.map((w, i) => (
                <p key={i} className="text-[11px] text-status-warning">
                  {w}
                </p>
              ))}
            </div>
          )}

          {/* Suggestions */}
          {visibleSuggestions && visibleSuggestions.length > 0 && (
            <div className="flex flex-col gap-1.5">
              <span className="text-[11px] font-medium uppercase tracking-wider text-text-tertiary">
                Suggestions ({visibleSuggestions.length})
              </span>
              {visibleSuggestions.map((s) => (
                <SuggestionRow
                  key={s.stepId + s.field}
                  suggestion={s}
                  onApply={handleApply}
                  onDismiss={handleDismiss}
                />
              ))}
            </div>
          )}

          {/* Re-analyze */}
          <ActionButton
            variant="secondary"
            disabled={isLoading}
            onClick={() => void handleAnalyze()}
          >
            {isLoading ? "Analyzing..." : "Re-analyze"}
          </ActionButton>
        </div>
      )}
    </div>
  );
}
