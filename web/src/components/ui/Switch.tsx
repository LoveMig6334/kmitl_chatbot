"use client";

import { useId } from "react";
import { Switch as RadixSwitch } from "radix-ui";
import { cn } from "@/lib/cn";
import { Label } from "./Label";

export interface SwitchProps extends React.ComponentProps<typeof RadixSwitch.Root> {
  label?: string;
  description?: string;
}

export function Switch({ label, description, className, id, ...props }: SwitchProps) {
  const autoId = useId();
  const switchId = id ?? autoId;
  const control = (
    <RadixSwitch.Root
      id={switchId}
      className={cn(
        "focus-ring relative inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full border border-transparent bg-border-strong transition-colors",
        "data-[state=checked]:bg-accent disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      {...props}
    >
      <RadixSwitch.Thumb className="block size-5 translate-x-0.5 rounded-full bg-surface shadow-sm transition-transform data-[state=checked]:translate-x-5" />
    </RadixSwitch.Root>
  );
  if (!label) return control;
  return (
    <div className="flex items-center justify-between gap-4">
      <div className="flex flex-col">
        <Label htmlFor={switchId}>{label}</Label>
        {description && <span className="text-xs text-fg-muted">{description}</span>}
      </div>
      {control}
    </div>
  );
}
