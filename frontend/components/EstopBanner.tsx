"use client";

import { useEffect } from "react";

interface EstopBannerProps {
  visible: boolean;
  onDismiss: () => void;
}

export function EstopBanner({ visible, onDismiss }: EstopBannerProps) {
  useEffect(() => {
    if (!visible) return;
    const timer = setTimeout(onDismiss, 1500);
    return () => clearTimeout(timer);
  }, [visible, onDismiss]);

  if (!visible) return null;

  return (
    <div className="fixed inset-x-0 top-0 z-50 flex items-center justify-between bg-status-error px-6 py-3 text-white shadow-lg">
      <span className="text-sm font-bold tracking-wide">
        EMERGENCY STOP ACTIVATED
      </span>
      <button
        onClick={onDismiss}
        className="text-sm text-white/80 hover:text-white"
      >
        Dismiss
      </button>
    </div>
  );
}
