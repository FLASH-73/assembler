"use client";

import { useEffect } from "react";

type KeyHandler = (e: KeyboardEvent) => void;

export function useKeyboardShortcuts(handlers: Record<string, KeyHandler>) {
  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      // Don't trigger shortcuts when typing in inputs
      const target = e.target as HTMLElement;
      if (target.tagName === "INPUT" || target.tagName === "SELECT" || target.tagName === "TEXTAREA") {
        return;
      }

      const handler = handlers[e.key];
      if (handler) {
        handler(e);
      }
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [handlers]);
}
