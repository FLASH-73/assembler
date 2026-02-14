"use client";

import { useCallback, useState } from "react";
import dynamic from "next/dynamic";
import type { Assembly } from "@/lib/types";
import { api } from "@/lib/api";
import { ActionButton } from "./ActionButton";

const UploadPreview = dynamic(
  () => import("./UploadPreview").then((m) => ({ default: m.UploadPreview })),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-[200px] items-center justify-center rounded-lg bg-bg-secondary">
        <span className="text-[12px] text-text-tertiary">Loading preview...</span>
      </div>
    ),
  },
);

interface UploadSummaryProps {
  assembly: Assembly;
  onConfirm: (assembly: Assembly) => void;
  onDelete: () => void;
}

const MAX_VISIBLE_STEPS = 5;

const HANDLER_LABEL: Record<string, string> = {
  primitive: "Primitive",
  policy: "Policy",
  rl_finetune: "RL",
};

export function UploadSummary({ assembly, onConfirm, onDelete }: UploadSummaryProps) {
  const [name, setName] = useState(assembly.name);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const partCount = Object.keys(assembly.parts).length;
  const stepCount = assembly.stepOrder.length;
  const estimatedMinutes = stepCount * 3;
  const visibleSteps = assembly.stepOrder.slice(0, MAX_VISIBLE_STEPS);
  const remainingSteps = stepCount - MAX_VISIBLE_STEPS;

  const handleConfirm = useCallback(async () => {
    setSaving(true);
    try {
      const trimmed = name.trim();
      if (trimmed && trimmed !== assembly.name) {
        await api.renameAssembly(assembly.id, trimmed);
        onConfirm({ ...assembly, name: trimmed });
      } else {
        onConfirm(assembly);
      }
    } catch {
      // If rename fails, still open with original name
      onConfirm(assembly);
    }
  }, [name, assembly, onConfirm]);

  const handleDelete = useCallback(async () => {
    setDeleting(true);
    try {
      await api.deleteAssembly(assembly.id);
    } catch {
      // Best-effort deletion
    }
    onDelete();
  }, [assembly.id, onDelete]);

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-[14px] font-semibold text-text-primary">Assembly Parsed</h2>
        <p className="mt-1 text-[12px] text-text-secondary">
          Review the parsed assembly before opening.
        </p>
      </div>

      {/* Editable name */}
      <input
        type="text"
        value={name}
        onChange={(e) => setName(e.target.value)}
        maxLength={100}
        className="w-full rounded-md border border-bg-tertiary bg-bg-secondary px-3 py-2 text-[13px] text-text-primary outline-none focus:border-signal"
      />

      {/* Mini 3D preview */}
      <UploadPreview assembly={assembly} />

      {/* Stats */}
      <div className="flex items-center gap-2 text-[12px] text-text-secondary">
        <span className="font-medium text-text-primary">{partCount}</span> parts
        <span className="text-text-tertiary">&middot;</span>
        <span className="font-medium text-text-primary">{stepCount}</span> steps
        <span className="text-text-tertiary">&middot;</span>
        ~{estimatedMinutes} min est.
      </div>

      {/* Step preview list */}
      {stepCount > 0 && (
        <div className="space-y-1">
          <span className="text-[11px] font-medium uppercase tracking-wider text-text-tertiary">
            Steps
          </span>
          <ul className="space-y-0.5">
            {visibleSteps.map((stepId, i) => {
              const step = assembly.steps[stepId];
              if (!step) return null;
              return (
                <li
                  key={stepId}
                  className="flex items-center justify-between rounded px-2 py-1 text-[12px]"
                >
                  <span className="text-text-primary">
                    <span className="text-text-tertiary">{i + 1}.</span> {step.name}
                  </span>
                  <span className="rounded bg-bg-secondary px-1.5 py-0.5 text-[10px] text-text-tertiary">
                    {HANDLER_LABEL[step.handler] ?? step.handler}
                  </span>
                </li>
              );
            })}
          </ul>
          {remainingSteps > 0 && (
            <p className="px-2 text-[11px] text-text-tertiary">
              + {remainingSteps} more
            </p>
          )}
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center justify-between pt-1">
        <ActionButton
          variant="danger"
          onClick={handleDelete}
          disabled={deleting || saving}
        >
          {deleting ? "Deleting..." : "Delete"}
        </ActionButton>
        <ActionButton
          variant="primary"
          onClick={handleConfirm}
          disabled={saving || deleting || !name.trim()}
        >
          {saving ? "Opening..." : "Open Assembly"}
        </ActionButton>
      </div>
    </div>
  );
}
