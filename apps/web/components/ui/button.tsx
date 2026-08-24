"use client";

import { type ButtonHTMLAttributes, forwardRef } from "react";

import { cn } from "@/lib/utils";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md";

const variantClasses: Record<Variant, string> = {
  primary: "bg-accent text-accent-ink shadow-sm hover:bg-accent-hover hover:shadow-md",
  secondary:
    "bg-surface-raised text-ink border border-border hover:border-accent/50 hover:text-accent hover:shadow-sm",
  ghost: "text-ink-muted hover:text-accent hover:bg-accent/10",
  danger: "bg-danger/10 text-danger hover:bg-danger hover:text-white hover:shadow-sm",
};

const sizeClasses: Record<Size, string> = {
  sm: "h-7 px-2.5 text-xs gap-1.5",
  md: "h-9 px-3.5 text-sm gap-2",
};

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "secondary", size = "md", ...props }, ref) => (
    <button
      ref={ref}
      className={cn(
        "inline-flex items-center justify-center rounded-md font-medium",
        "transition-[color,background-color,border-color,box-shadow,transform] duration-150 ease-out",
        "active:scale-[0.96]",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/50 focus-visible:ring-offset-1 focus-visible:ring-offset-surface",
        "disabled:opacity-40 disabled:pointer-events-none disabled:active:scale-100",
        variantClasses[variant],
        sizeClasses[size],
        className
      )}
      {...props}
    />
  )
);
Button.displayName = "Button";
