"use client";

import { useCallback, useEffect, useState } from "react";
import type { Assembly } from "@/lib/types";
import { useAssembly } from "@/context/AssemblyContext";
import { useExecution } from "@/context/ExecutionContext";
import { useConnectionStatus } from "@/lib/hooks";
import { useWebSocket } from "@/context/WebSocketContext";
import { RunControls } from "./RunControls";
import { UploadDialog } from "./UploadDialog";

function formatTime(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

function ConnectionDot() {
  const { isConnected } = useConnectionStatus();
  const { connectionState } = useWebSocket();

  const isReconnecting = connectionState === "connecting" && !isConnected;

  let dotClass = "bg-status-error";
  let label = "Offline";
  if (isConnected && connectionState === "connected") {
    dotClass = "bg-status-success";
    label = "Connected";
  } else if (isReconnecting) {
    dotClass = "bg-amber-400";
    label = "Reconnecting\u2026";
  }

  return (
    <div className="group relative flex items-center">
      <div className={`h-1.5 w-1.5 rounded-full ${dotClass}`} />
      <span className="pointer-events-none absolute left-4 hidden whitespace-nowrap text-[10px] text-text-tertiary group-hover:block">
        {label}
      </span>
    </div>
  );
}

export function TopBar() {
  const { assemblies, assembly, selectAssembly, refreshAssemblies } = useAssembly();
  const { executionState } = useExecution();
  const [uploadOpen, setUploadOpen] = useState(false);

  const showTime = executionState.phase !== "idle";
  const timeDisplay = showTime ? formatTime(executionState.elapsedMs) : "--:--";

  // Listen for upload trigger from StepList
  useEffect(() => {
    const handler = () => setUploadOpen(true);
    window.addEventListener("open-upload", handler);
    return () => window.removeEventListener("open-upload", handler);
  }, []);

  const handleUploadSuccess = useCallback(
    (newAssembly: Assembly) => {
      setUploadOpen(false);
      refreshAssemblies();
      selectAssembly(newAssembly.id);
    },
    [refreshAssemblies, selectAssembly],
  );

  return (
    <>
      <header className="flex h-12 shrink-0 items-center justify-between border-b border-bg-tertiary px-6">
        {/* Left: wordmark + assembly selector + connection */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-0.5">
            <span className="text-[16px] font-bold tracking-[0.2em] text-text-primary">
              AURA
            </span>
            <span className="text-[16px] text-text-tertiary">&middot;</span>
          </div>
          <select
            value={assembly?.id ?? ""}
            onChange={(e) => selectAssembly(e.target.value)}
            className="appearance-none rounded bg-transparent px-2 py-1 text-[13px] text-text-primary outline-none transition-colors hover:bg-bg-secondary"
          >
            {assemblies.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </select>
          <ConnectionDot />
        </div>

        {/* Center: cycle time */}
        <div className="absolute left-1/2 -translate-x-1/2 flex flex-col items-center">
          <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-text-tertiary">
            Cycle
          </span>
          <span className="font-mono text-[36px] font-medium leading-none tabular-nums text-text-primary">
            {timeDisplay}
          </span>
        </div>

        {/* Right: run controls */}
        <RunControls />
      </header>

      <UploadDialog
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        onSuccess={handleUploadSuccess}
      />
    </>
  );
}
