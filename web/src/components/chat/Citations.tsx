"use client";

import { useState } from "react";
import { FileText } from "lucide-react";
import { useT } from "@/hooks/useT";
import type { Citation } from "@/lib/store";

/**
 * Compact source chips under an assistant message: `{program} หน้า {page}`.
 * Hover shows the snippet as a tooltip; click expands it inline.
 */
export function Citations({ citations }: { citations: Citation[] }) {
  const t = useT();
  const [open, setOpen] = useState<string | null>(null);
  if (citations.length === 0) return null;
  const openCitation = citations.find((c) => c.chunk_id === open) ?? null;

  return (
    <div className="flex w-full flex-col gap-1.5 px-1">
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="flex items-center gap-1 text-[11px] text-muted">
          <FileText className="h-3 w-3" />
          {t.sources}
        </span>
        {citations.map((c) => {
          const active = open === c.chunk_id;
          return (
            <button
              key={c.chunk_id}
              type="button"
              title={c.snippet ?? undefined}
              onClick={() => setOpen(active ? null : c.chunk_id)}
              className={`rounded-full border px-2 py-0.5 text-[11px] font-medium transition-colors ${
                active
                  ? "border-accent bg-accent/25 text-foreground"
                  : "border-border bg-surface-muted text-muted hover:text-foreground"
              }`}
            >
              {c.program ?? "IT"} หน้า {c.page}
            </button>
          );
        })}
      </div>
      {openCitation && openCitation.snippet && (
        <p className="rounded-xl border border-border bg-surface-muted px-3 py-2 text-xs leading-relaxed text-muted">
          {openCitation.snippet}
        </p>
      )}
    </div>
  );
}
