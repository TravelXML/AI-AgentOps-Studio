"use client";

import { X } from "lucide-react";
import { useEffect } from "react";

import { cn } from "@/lib/utils";

export function Modal({
  open,
  onClose,
  title,
  children,
  className,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  className?: string;
}) {
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 animate-[modal-overlay-in_150ms_ease-out]"
      onClick={onClose}
    >
      <div
        className={cn(
          "max-h-[85vh] w-full max-w-2xl overflow-hidden rounded-lg border border-border bg-surface shadow-xl",
          "animate-[modal-panel-in_150ms_ease-out]",
          className
        )}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <span className="text-sm font-medium text-ink">{title}</span>
          <button
            onClick={onClose}
            className="rounded-md p-1 text-ink-faint transition-colors hover:bg-surface-raised hover:text-ink"
          >
            <X size={16} />
          </button>
        </div>
        <div className="scrollbar-thin max-h-[calc(85vh-52px)] overflow-y-auto p-4">{children}</div>
      </div>
    </div>
  );
}
