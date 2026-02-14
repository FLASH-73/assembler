"use client";

import useSWR from "swr";
import { api } from "@/lib/api";

interface DemoListProps {
  assemblyId: string;
  stepId: string;
}

function formatTimestamp(ts: number): string {
  return new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export function DemoList({ assemblyId, stepId }: DemoListProps) {
  const swrKey = `/recording/demos/${assemblyId}/${stepId}`;
  const { data: demos = [], mutate } = useSWR(swrKey, () => api.getDemos(assemblyId, stepId));

  if (demos.length === 0) {
    return (
      <p className="text-[11px] text-text-tertiary">No demos recorded yet</p>
    );
  }

  const handleDelete = async (demoId: string) => {
    try {
      await api.deleteDemo(assemblyId, stepId, demoId);
    } catch {
      // Backend may be unavailable
    }
    void mutate();
  };

  return (
    <div className="max-h-36 overflow-y-auto">
      <span className="text-[11px] font-medium uppercase tracking-[0.02em] text-text-tertiary">
        Demonstrations
      </span>
      <div className="mt-1 flex flex-col gap-1">
        {demos.map((demo) => (
          <div
            key={demo.id}
            className="group flex items-center justify-between rounded bg-bg-secondary px-2 py-1"
          >
            <div className="flex items-center gap-3 text-[12px]">
              <span className="font-mono text-text-secondary">
                {formatTimestamp(demo.timestamp)}
              </span>
              <span className="text-text-tertiary">
                {formatDuration(demo.durationMs)}
              </span>
            </div>
            <button
              title="Delete demo"
              className="flex-shrink-0 opacity-0 transition-opacity group-hover:opacity-100 text-text-tertiary hover:text-status-error"
              onClick={() => void handleDelete(demo.id)}
            >
              <svg
                width="12"
                height="12"
                viewBox="0 0 14 14"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
              >
                <path d="M2.5 3.5h9M5.5 3.5V2.5h3v1M5.5 5.5v5M8.5 5.5v5M3.5 3.5h7v8.5a1 1 0 0 1-1 1h-5a1 1 0 0 1-1-1z" />
              </svg>
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
