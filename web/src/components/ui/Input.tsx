"use client";

import { forwardRef, useId } from "react";
import { cn } from "@/lib/cn";
import { Label } from "./Label";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  /** Small text under the field; replaced by `error` when present. */
  helper?: string;
  /** Error message; sets aria-invalid and the danger border. */
  error?: string;
  /** Element rendered inside the field on the right (e.g. a show/hide button). */
  trailing?: React.ReactNode;
  /** Small text next to the label, e.g. "optional". */
  labelHint?: string;
  containerClassName?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  {
    label,
    helper,
    error,
    trailing,
    labelHint,
    className,
    containerClassName,
    id,
    "aria-describedby": ariaDescribedBy,
    ...props
  },
  ref,
) {
  const autoId = useId();
  const inputId = id ?? autoId;
  const helperId = `${inputId}-helper`;
  const errorId = `${inputId}-error`;
  // Error/helper ids are appended to any caller-provided description (e.g. the password checklist).
  const describedBy =
    [ariaDescribedBy, error ? errorId : helper ? helperId : undefined].filter(Boolean).join(" ") ||
    undefined;

  return (
    <div className={cn("flex flex-col gap-1.5", containerClassName)}>
      {label && (
        <div className="flex items-baseline justify-between gap-2">
          <Label htmlFor={inputId}>{label}</Label>
          {labelHint && <span className="text-xs text-fg-muted">{labelHint}</span>}
        </div>
      )}
      <div className="relative">
        <input
          ref={ref}
          id={inputId}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
          className={cn(
            "focus-ring h-10 w-full rounded-md border border-border bg-surface px-3 text-sm text-fg shadow-sm transition-colors",
            "hover:border-border-strong focus-visible:border-border-strong",
            "disabled:cursor-not-allowed disabled:opacity-60",
            error && "border-danger hover:border-danger focus-visible:ring-danger",
            trailing && "pr-11",
            className,
          )}
          {...props}
        />
        {trailing && (
          <div className="absolute inset-y-0 right-1 flex items-center">{trailing}</div>
        )}
      </div>
      {error ? (
        <p id={errorId} role="alert" className="text-xs text-danger">
          {error}
        </p>
      ) : helper ? (
        <p id={helperId} className="text-xs text-fg-muted">
          {helper}
        </p>
      ) : null}
    </div>
  );
});
