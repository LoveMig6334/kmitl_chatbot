"use client";

import { FileText } from "lucide-react";
import { useTranslation } from "@/providers/LocaleProvider";
import type { Citation } from "@/lib/chat";
import { cn } from "@/lib/cn";

/** Numbered source chips under an assistant answer; clicking opens the document panel. */
export function SourceChips({
  sources,
  activeIndex,
  onOpen,
}: {
  sources: Citation[];
  activeIndex: number | null;
  onOpen: (index: number) => void;
}) {
  const t = useTranslation();
  if (sources.length === 0) return null;
  return (
    <div className="flex flex-wrap items-center gap-1.5" aria-label={t("chat.sources")}>
      <span className="mr-0.5 inline-flex items-center gap-1 text-xs text-fg-muted">
        <FileText className="size-3.5" aria-hidden="true" />
        {t("chat.sources")}
      </span>
      {sources.map((c, i) => (
        <button
          key={c.chunk_id}
          type="button"
          onClick={() => onOpen(i)}
          aria-pressed={activeIndex === i}
          title={c.snippet ?? undefined}
          className={cn(
            "focus-ring inline-flex h-7 items-center gap-1.5 rounded-full border px-2.5 text-xs font-medium transition-colors",
            activeIndex === i
              ? "border-accent bg-accent-soft text-accent"
              : "border-border bg-surface text-fg-muted hover:border-border-strong hover:text-fg",
          )}
        >
          <span className="inline-flex size-4 items-center justify-center rounded-full bg-bg-subtle text-[length:inherit] text-fg-muted">
            {i + 1}
          </span>
          {t("chat.sourceChip", { program: c.program ?? c.faculty, page: c.page })}
        </button>
      ))}
    </div>
  );
}
