import Link from "next/link";
import { GraduationCap } from "lucide-react";
import { cn } from "@/lib/cn";

export function BrandMark({ label, className }: { label: string; className?: string }) {
  return (
    <Link
      href="/"
      className={cn("focus-ring inline-flex items-center gap-2.5 rounded-md text-fg", className)}
    >
      <span className="inline-flex size-8 items-center justify-center rounded-lg bg-accent text-accent-fg">
        <GraduationCap className="size-4.5" aria-hidden="true" />
      </span>
      <span className="text-sm font-semibold tracking-tight">{label}</span>
    </Link>
  );
}
