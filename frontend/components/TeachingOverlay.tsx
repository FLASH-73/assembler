"use client";

import { useExecution } from "@/context/ExecutionContext";
import { useAssembly } from "@/context/AssemblyContext";
import { ActionButton } from "./ActionButton";

export function TeachingOverlay() {
  const { executionState, stopExecution } = useExecution();
  const { assembly } = useAssembly();

  if (executionState.phase !== "teaching") return null;

  const currentStep = executionState.currentStepId
    ? assembly?.steps[executionState.currentStepId]
    : null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-text-primary/60">
      <div className="flex w-full max-w-2xl flex-col items-center gap-6 rounded-xl bg-bg-primary p-8 shadow-xl">
        {/* Recording indicator */}
        <div className="flex items-center gap-2">
          <span className="h-3 w-3 animate-pulse rounded-full bg-status-error" />
          <span className="text-[14px] font-semibold text-status-error">
            REC
          </span>
        </div>

        {/* Step info */}
        {currentStep && (
          <div className="text-center">
            <p className="text-[11px] font-medium uppercase tracking-[0.02em] text-text-tertiary">
              Teaching Step
            </p>
            <p className="mt-1 text-[18px] font-semibold text-text-primary">
              {currentStep.name}
            </p>
          </div>
        )}

        {/* Camera placeholder */}
        <div className="flex h-64 w-full items-center justify-center rounded-lg bg-bg-tertiary">
          <span className="text-[13px] text-text-tertiary">
            Live camera feed during teleoperation
          </span>
        </div>

        {/* Controls */}
        <ActionButton variant="danger" onClick={stopExecution}>
          Stop Recording
        </ActionButton>
      </div>
    </div>
  );
}
