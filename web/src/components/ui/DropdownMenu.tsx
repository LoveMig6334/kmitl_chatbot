"use client";

import { Check } from "lucide-react";
import { DropdownMenu as Radix } from "radix-ui";
import { cn } from "@/lib/cn";

export const DropdownMenu = Radix.Root;
export const DropdownMenuTrigger = Radix.Trigger;
export const DropdownMenuGroup = Radix.Group;
export const DropdownMenuRadioGroup = Radix.RadioGroup;

const itemBase =
  "relative flex cursor-default select-none items-center gap-2 rounded-sm px-2 py-1.5 text-sm text-fg outline-none transition-colors data-[highlighted]:bg-surface-hover data-[disabled]:pointer-events-none data-[disabled]:opacity-50";

export function DropdownMenuContent({
  className,
  sideOffset = 6,
  ...props
}: React.ComponentProps<typeof Radix.Content>) {
  return (
    <Radix.Portal>
      <Radix.Content
        sideOffset={sideOffset}
        collisionPadding={8}
        className={cn(
          "z-50 min-w-[12rem] overflow-hidden rounded-lg border border-border bg-surface p-1 text-fg shadow-lg",
          className,
        )}
        {...props}
      />
    </Radix.Portal>
  );
}

export function DropdownMenuItem({
  className,
  destructive,
  ...props
}: React.ComponentProps<typeof Radix.Item> & { destructive?: boolean }) {
  return (
    <Radix.Item
      className={cn(itemBase, destructive && "text-danger data-[highlighted]:bg-danger-soft", className)}
      {...props}
    />
  );
}

export function DropdownMenuRadioItem({
  className,
  children,
  ...props
}: React.ComponentProps<typeof Radix.RadioItem>) {
  return (
    <Radix.RadioItem className={cn(itemBase, "pr-8", className)} {...props}>
      {children}
      <Radix.ItemIndicator className="absolute right-2 inline-flex items-center">
        <Check className="size-4" aria-hidden="true" />
      </Radix.ItemIndicator>
    </Radix.RadioItem>
  );
}

export function DropdownMenuLabel({ className, ...props }: React.ComponentProps<typeof Radix.Label>) {
  return (
    <Radix.Label
      className={cn("px-2 py-1.5 text-xs font-medium text-fg-muted", className)}
      {...props}
    />
  );
}

export function DropdownMenuSeparator({ className, ...props }: React.ComponentProps<typeof Radix.Separator>) {
  return <Radix.Separator className={cn("-mx-1 my-1 h-px bg-border", className)} {...props} />;
}
