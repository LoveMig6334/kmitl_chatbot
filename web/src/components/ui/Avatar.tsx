"use client";

import { Avatar as RadixAvatar } from "radix-ui";
import { cn } from "@/lib/cn";

const sizes = {
  sm: "size-7 text-xs",
  md: "size-9 text-sm",
  lg: "size-12 text-base",
} as const;

export function initialsOf(name: string | null | undefined, fallback = "?") {
  const parts = (name ?? "").trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return fallback;
  const first = parts[0].charAt(0);
  const last = parts.length > 1 ? parts[parts.length - 1].charAt(0) : "";
  return (first + last).toUpperCase();
}

export function Avatar({
  name,
  src,
  size = "md",
  className,
}: {
  name?: string | null;
  src?: string | null;
  size?: keyof typeof sizes | number;
  className?: string;
}) {
  const sizeClass = typeof size === "number" ? undefined : sizes[size];
  const style = typeof size === "number" ? { width: size, height: size, fontSize: size * 0.4 } : undefined;
  return (
    <RadixAvatar.Root
      className={cn(
        "inline-flex shrink-0 select-none items-center justify-center overflow-hidden rounded-full bg-accent-soft font-semibold text-accent",
        sizeClass,
        className,
      )}
      style={style}
    >
      {src && (
        <RadixAvatar.Image
          src={src}
          alt=""
          referrerPolicy="no-referrer"
          className="size-full object-cover"
        />
      )}
      <RadixAvatar.Fallback delayMs={src ? 300 : 0}>{initialsOf(name)}</RadixAvatar.Fallback>
    </RadixAvatar.Root>
  );
}
