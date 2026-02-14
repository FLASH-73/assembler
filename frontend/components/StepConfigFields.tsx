"use client";

import { useCallback, useRef, useState } from "react";
import { useAssembly } from "@/context/AssemblyContext";
import type { AssemblyStep, SuccessCriteria } from "@/lib/types";

const PRIMITIVE_TYPES = [
  "pick", "place", "move_to", "guarded_move", "linear_insert", "screw", "press_fit",
] as const;

const CRITERIA_TYPES: SuccessCriteria["type"][] = [
  "force_threshold", "classifier", "force_signature", "position",
];

interface StepConfigFieldsProps {
  step: AssemblyStep;
}

export function StepConfigFields({ step }: StepConfigFieldsProps) {
  const { updateStep } = useAssembly();
  const [saveState, setSaveState] = useState<"idle" | "saved" | "error">("idle");
  const [localRetries, setLocalRetries] = useState(step.maxRetries);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Sync local retries when step changes (e.g. switching selected step)
  const prevStepId = useRef(step.id);
  if (prevStepId.current !== step.id) {
    prevStepId.current = step.id;
    setLocalRetries(step.maxRetries);
  }

  const handleUpdate = useCallback(
    async (data: Partial<AssemblyStep>) => {
      if (timerRef.current) clearTimeout(timerRef.current);
      setSaveState("idle");
      try {
        await updateStep(step.id, data);
        setSaveState("saved");
        timerRef.current = setTimeout(() => setSaveState("idle"), 1000);
      } catch {
        setSaveState("error");
        timerRef.current = setTimeout(() => setSaveState("idle"), 2000);
      }
    },
    [step.id, updateStep],
  );

  const handleHandlerChange = useCallback(
    (handler: "primitive" | "policy") => {
      if (handler === step.handler) return;
      if (handler === "primitive") {
        void handleUpdate({ handler: "primitive", primitiveType: "pick" });
      } else {
        void handleUpdate({ handler: "policy", primitiveType: null, primitiveParams: null });
      }
    },
    [step.handler, handleUpdate],
  );

  const flushRetries = useCallback(() => {
    const val = Math.max(1, Math.min(10, localRetries));
    setLocalRetries(val);
    if (val !== step.maxRetries) {
      void handleUpdate({ maxRetries: val });
    }
  }, [localRetries, step.maxRetries, handleUpdate]);

  const labelClass =
    "text-[10px] font-semibold uppercase tracking-[0.06em] text-text-tertiary";
  const inputClass =
    "appearance-none rounded bg-bg-tertiary px-2 py-1 text-[12px] text-text-primary outline-none";

  return (
    <div className="rounded-lg bg-bg-secondary p-2.5">
      {/* Section header + save indicator */}
      <div className="flex items-center justify-between">
        <span className={labelClass}>Configuration</span>
        {saveState === "saved" && (
          <span className="flex items-center gap-1 text-[11px] text-status-success animate-fade-out">
            <svg className="h-3 w-3" viewBox="0 0 12 12" fill="none">
              <path
                d="M2 6l3 3 5-5"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            Saved
          </span>
        )}
        {saveState === "error" && (
          <span className="text-[11px] text-status-error">Save failed</span>
        )}
      </div>

      <div className="mt-2 flex flex-col gap-3">
        {/* Handler toggle */}
        <div>
          <span className={labelClass}>Handler</span>
          <div className="mt-1 flex">
            <button
              className={`rounded-l-md px-3 py-1 text-[12px] font-medium transition-colors ${
                step.handler === "primitive"
                  ? "bg-text-primary text-bg-primary"
                  : "bg-bg-tertiary text-text-secondary"
              }`}
              onClick={() => handleHandlerChange("primitive")}
            >
              Primitive
            </button>
            <button
              className={`rounded-r-md px-3 py-1 text-[12px] font-medium transition-colors ${
                step.handler === "policy"
                  ? "bg-text-primary text-bg-primary"
                  : "bg-bg-tertiary text-text-secondary"
              }`}
              onClick={() => handleHandlerChange("policy")}
            >
              Policy
            </button>
          </div>
        </div>

        {/* Primitive type dropdown */}
        {step.handler === "primitive" && (
          <div>
            <span className={labelClass}>Primitive Type</span>
            <select
              className={`mt-1 block w-full ${inputClass}`}
              value={step.primitiveType ?? ""}
              onChange={(e) =>
                void handleUpdate({ primitiveType: e.target.value || null })
              }
            >
              {PRIMITIVE_TYPES.map((pt) => (
                <option key={pt} value={pt}>
                  {pt.replace(/_/g, " ")}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Policy ID (read-only) */}
        {step.handler === "policy" && (
          <div>
            <span className={labelClass}>Policy</span>
            <p className="mt-1 text-[12px] text-text-tertiary">
              {step.policyId ?? "no policy trained"}
            </p>
          </div>
        )}

        {/* Max Retries + Success Criteria side by side */}
        <div className="flex gap-3">
          <div>
            <span className={labelClass}>Max Retries</span>
            <input
              type="number"
              min={1}
              max={10}
              className={`mt-1 block w-16 ${inputClass}`}
              value={localRetries}
              onChange={(e) => setLocalRetries(parseInt(e.target.value, 10) || 1)}
              onBlur={flushRetries}
              onKeyDown={(e) => {
                if (e.key === "Enter") flushRetries();
              }}
            />
          </div>
          <div className="flex-1">
            <span className={labelClass}>Success Criteria</span>
            <select
              className={`mt-1 block w-full ${inputClass}`}
              value={step.successCriteria.type}
              onChange={(e) =>
                void handleUpdate({
                  successCriteria: {
                    ...step.successCriteria,
                    type: e.target.value as SuccessCriteria["type"],
                  },
                })
              }
            >
              {CRITERIA_TYPES.map((ct) => (
                <option key={ct} value={ct}>
                  {ct.replace(/_/g, " ")}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>
    </div>
  );
}
