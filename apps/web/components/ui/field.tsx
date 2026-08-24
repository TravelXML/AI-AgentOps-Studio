"use client";

import { forwardRef, type InputHTMLAttributes, type SelectHTMLAttributes, type TextareaHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

const fieldClasses =
  "w-full rounded-md border border-border bg-surface px-2.5 py-1.5 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:ring-2 focus:ring-accent/40 focus:border-accent";

export function Label({ children }: { children: React.ReactNode }) {
  return <label className="mb-1 block text-xs font-medium text-ink-muted">{children}</label>;
}

export const TextInput = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  (props, ref) => <input ref={ref} {...props} className={cn(fieldClasses, props.className)} />
);
TextInput.displayName = "TextInput";

export const TextArea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(
  (props, ref) => (
    <textarea ref={ref} {...props} className={cn(fieldClasses, "min-h-[72px] resize-y", props.className)} />
  )
);
TextArea.displayName = "TextArea";

export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(
  (props, ref) => <select ref={ref} {...props} className={cn(fieldClasses, props.className)} />
);
Select.displayName = "Select";

export function FieldGroup({ children }: { children: React.ReactNode }) {
  return <div className="space-y-3">{children}</div>;
}
