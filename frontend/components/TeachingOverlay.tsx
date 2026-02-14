"use client";

import { useState } from "react";
import { useTeaching } from "@/context/TeachingContext";
import { ActionButton } from "./ActionButton";

function formatElapsed(ms: number): string {
  const s = Math.floor(ms / 1000);
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
}

function RecIndicator() {
  return (
    <div className="flex items-center gap-1.5">
      <div className="h-2.5 w-2.5 animate-pulse rounded-full bg-status-error" />
      <span className="text-[13px] font-semibold text-status-error">REC</span>
    </div>
  );
}

function TeleopBadge({ active }: { active: boolean }) {
  if (!active) return null;
  return (
    <div className="flex items-center gap-1.5">
      <div className="h-1.5 w-1.5 animate-pulse-subtle rounded-full bg-status-success" />
      <span className="text-[9px] font-medium uppercase tracking-[0.06em] text-text-tertiary">
        Teleop Active
      </span>
    </div>
  );
}

export function TeachingOverlay() {
  const {
    isTeaching,
    elapsed,
    demoCount,
    stepName,
    stepNumber,
    teleopActive,
    stopTeaching,
    discardTeaching,
  } = useTeaching();
  const [saving, setSaving] = useState(false);

  if (!isTeaching) return null;

  const handleSave = async () => {
    setSaving(true);
    try {
      await stopTeaching();
    } finally {
      setSaving(false);
    }
  };

  const handleDiscard = async () => {
    setSaving(true);
    try {
      await discardTeaching();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      className="animate-slide-up absolute inset-x-0 bottom-0 z-40 flex max-h-[60%] flex-col gap-4 overflow-y-auto rounded-t-xl bg-bg-elevated/95 px-6 py-5 shadow-xl backdrop-blur-sm md:max-h-[40%]"
    >
      {/* Header: REC indicator + timer | Teleop status */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <RecIndicator />
          <span className="font-mono text-[13px] tabular-nums text-text-secondary">
            {formatElapsed(elapsed)}
          </span>
        </div>
        <TeleopBadge active={teleopActive} />
      </div>

      {/* Step info */}
      {stepName && (
        <div>
          <span className="text-[11px] font-medium uppercase tracking-[0.02em] text-text-tertiary">
            Step {stepNumber}
          </span>
          <p className="text-[16px] font-semibold text-text-primary">
            {stepName}
          </p>
        </div>
      )}

      {/* Camera placeholder */}
      <div className="flex h-32 w-full items-center justify-center rounded-lg bg-bg-tertiary">
        <span className="text-[13px] text-text-tertiary">
          Live camera feed during teleoperation
        </span>
      </div>

      {/* Footer: demo count + action buttons */}
      <div className="flex items-center justify-between">
        <span className="text-[12px] text-text-tertiary">
          {demoCount} demo{demoCount !== 1 ? "s" : ""} recorded
        </span>
        <div className="flex gap-2">
          <ActionButton
            variant="primary"
            onClick={() => void handleSave()}
            disabled={saving}
          >
            Save Demo
          </ActionButton>
          <ActionButton
            variant="danger"
            onClick={() => void handleDiscard()}
            disabled={saving}
          >
            Discard
          </ActionButton>
        </div>
      </div>
    </div>
  );
}
