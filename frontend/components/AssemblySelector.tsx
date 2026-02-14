"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useAssembly } from "@/context/AssemblyContext";
import type { AssemblySummary } from "@/lib/types";
import { ActionButton } from "./ActionButton";

export function AssemblySelector() {
  const { assemblies, assembly, selectAssembly, deleteAssembly } =
    useAssembly();
  const [open, setOpen] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<AssemblySummary | null>(
    null,
  );
  const containerRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    if (!open) return;
    function onClick(e: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [open]);

  // Close dropdown on Escape
  useEffect(() => {
    if (!open && !pendingDelete) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        if (pendingDelete) {
          setPendingDelete(null);
        } else {
          setOpen(false);
        }
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, pendingDelete]);

  const handleSelect = useCallback(
    (id: string) => {
      selectAssembly(id);
      setOpen(false);
    },
    [selectAssembly],
  );

  const handleDelete = useCallback(async () => {
    if (!pendingDelete) return;
    await deleteAssembly(pendingDelete.id);
    setPendingDelete(null);
    setOpen(false);
  }, [pendingDelete, deleteAssembly]);

  const openUpload = useCallback(() => {
    setOpen(false);
    window.dispatchEvent(new Event("open-upload"));
  }, []);

  return (
    <>
      <div ref={containerRef} className="relative">
        {/* Trigger */}
        <button
          onClick={() => setOpen((prev) => !prev)}
          className="flex items-center gap-1 rounded px-2 py-1 text-[13px] text-text-primary outline-none transition-colors hover:bg-bg-secondary"
        >
          <span>{assembly?.name ?? "Select assembly"}</span>
          <svg
            width="12"
            height="12"
            viewBox="0 0 12 12"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            className="text-text-tertiary"
          >
            <path d="M3 4.5 6 7.5 9 4.5" />
          </svg>
        </button>

        {/* Dropdown panel */}
        {open && (
          <div className="absolute left-0 top-full z-40 mt-1 w-64 max-h-60 overflow-y-auto rounded-md border border-bg-tertiary bg-bg-elevated shadow-lg">
            {assemblies.length === 0 ? (
              <div className="px-3 py-4 text-center">
                <p className="text-[12px] text-text-tertiary">No assemblies</p>
                <button
                  onClick={openUpload}
                  className="mt-1 text-[12px] text-signal hover:underline"
                >
                  Upload STEP file
                </button>
              </div>
            ) : (
              assemblies.map((a) => (
                <div
                  key={a.id}
                  className={`group flex items-center justify-between px-3 py-2 transition-colors hover:bg-bg-secondary ${
                    a.id === assembly?.id ? "bg-bg-secondary" : ""
                  }`}
                >
                  <button
                    className="flex-1 text-left text-[13px] text-text-primary truncate"
                    onClick={() => handleSelect(a.id)}
                  >
                    {a.name}
                  </button>
                  <button
                    title={`Delete ${a.name}`}
                    className="ml-2 flex-shrink-0 opacity-0 transition-opacity group-hover:opacity-100 text-text-tertiary hover:text-status-error"
                    onClick={(e) => {
                      e.stopPropagation();
                      setPendingDelete(a);
                    }}
                  >
                    <svg
                      width="14"
                      height="14"
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
              ))
            )}
          </div>
        )}
      </div>

      {/* Delete confirmation dialog */}
      {pendingDelete && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/30"
          onClick={() => setPendingDelete(null)}
        >
          <div
            className="w-full max-w-sm rounded-lg bg-bg-primary p-6 shadow-lg"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-[14px] font-semibold text-text-primary">
              Delete assembly
            </h2>
            <p className="mt-2 text-[13px] text-text-secondary">
              Delete &ldquo;{pendingDelete.name}&rdquo;? This cannot be undone.
            </p>
            <div className="mt-4 flex justify-end gap-2">
              <ActionButton
                variant="secondary"
                onClick={() => setPendingDelete(null)}
              >
                Cancel
              </ActionButton>
              <ActionButton variant="danger" onClick={handleDelete}>
                Delete
              </ActionButton>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
