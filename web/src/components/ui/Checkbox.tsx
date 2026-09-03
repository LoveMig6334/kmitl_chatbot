"use client";

import { useId } from "react";
import { Check } from "lucide-react";
import { Checkbox as RadixCheckbox } from "radix-ui";
import { cn } from "@/lib/cn";

export interface CheckboxProps extends React.ComponentProps<typeof RadixCheckbox.Root> {
  label?: React.ReactNode;
}

export function Checkbox({ label, className, id, ...props }: CheckboxProps) {
  const autoId = useId();
  const boxId = id ?? autoId;
  const control = (
    <RadixCheckbox.Root
      id={boxId}
      className={cn(
        "focus-ring flex size-4.5 shrink-0 items-center justify-center rounded-sm border border-border-strong bg-surface transition-colors",
        "data-[state=checked]:border-accent data-[state=checked]:bg-accent data-[state=checked]:text-accent-fg",
        "disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      {...props}
    >
      <RadixCheckbox.Indicator>
        <Check className="size-3.5" strokeWidth={3} aria-hidden="true" />
      </RadixCheckbox.Indicator>
    </RadixCheckbox.Root>
  );
  if (!label) return control;
  return (
    <label
      htmlFor={boxId}
      className="flex cursor-pointer select-none items-center gap-2.5 rounded-md px-2 py-1.5 text-sm text-fg transition-colors hover:bg-surface-hover"
    >
      {control}
      <span className="leading-tight">{label}</span>
    </label>
  );
}
