"use client";

import type { StepStatus } from "@/lib/types";

const STATUS_CONFIG: Record<StepStatus, { label: string; dot: string }> = {
  pending: { label: "PENDING", dot: "bg-status-pending" },
  running: { label: "RUNNING", dot: "bg-status-running" },
  success: { label: "DONE", dot: "bg-status-success" },
  failed: { label: "FAILED", dot: "bg-status-error" },
  human: { label: "HUMAN", dot: "bg-status-human" },
  retrying: { label: "RETRY", dot: "bg-status-warning" },
};

interface StatusBadgeProps {
  status: StepStatus;
  retryInfo?: string;
}

export function StatusBadge({ status, retryInfo }: StatusBadgeProps) {
  const config = STATUS_CONFIG[status];
  const label =
    status === "retrying" && retryInfo ? `RETRY ${retryInfo}` : config.label;

  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={`h-1.5 w-1.5 rounded-full ${config.dot}`} />
      <span className="text-[10px] font-semibold uppercase tracking-[0.04em] text-text-secondary">
        {label}
      </span>
    </span>
  );
}
