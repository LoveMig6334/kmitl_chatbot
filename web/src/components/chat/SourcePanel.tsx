"use client";

import { useEffect, useState } from "react";
import { ArrowLeft, ExternalLink, FileText, X } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { useTranslation } from "@/providers/LocaleProvider";
import type { Citation } from "@/lib/chat";
import { PROGRAMS } from "@/lib/constants";
import { cn } from "@/lib/cn";

export interface SourcePanelProps {
  sources: Citation[];
  activeIndex: number;
  onSelect: (index: number) => void;
  onClose: () => void;
}

export function pdfUrl(program: string, page: number) {
  return `/api/pdf/${encodeURIComponent(program)}#page=${page}&view=FitH`;
}

/** Right-hand panel: the cited passages of one answer, and the PDF page they come from. */
export function SourcePanel({ sources, activeIndex, onSelect, onClose }: SourcePanelProps) {
  const t = useTranslation();
  const [viewing, setViewing] = useState(false);
  const active = sources[activeIndex] ?? sources[0];
  const program = active?.program ?? "IT";
  const programName = PROGRAMS.find((p) => p.id === program);
  const available = usePdfAvailable(viewing ? program : null);

  return (
    <div className="flex h-full flex-col bg-surface">
      <div className="flex items-center gap-2 border-b border-border px-3 py-2.5">
        {viewing ? (
          <Button variant="ghost" size="sm" onClick={() => setViewing(false)} className="-ml-1">
            <ArrowLeft className="size-4" /> {t("chat.backToSources")}
          </Button>
        ) : (
          <h2 className="inline-flex items-center gap-2 text-sm font-semibold">
            <FileText className="size-4 text-fg-muted" aria-hidden="true" />
            {t("chat.sourcesTitle")}
          </h2>
        )}
        <div className="ml-auto flex items-center gap-1">
          {viewing && active && (
            <Button asChild variant="ghost" size="icon" className="size-8" aria-label={t("chat.pdfOpenNewTab")}>
              <a href={pdfUrl(program, active.page)} target="_blank" rel="noreferrer noopener">
                <ExternalLink className="size-4" />
              </a>
            </Button>
          )}
          <Button variant="ghost" size="icon" className="size-8" onClick={onClose} aria-label={t("chat.closePanel")}>
            <X className="size-4" />
          </Button>
        </div>
      </div>

      {viewing && active ? (
        <div className="flex min-h-0 flex-1 flex-col">
          <p className="border-b border-border px-3 py-1.5 text-xs text-fg-muted">
            {t("chat.pdfTitle", { program })} · {t("chat.sourcePage", { page: active.page })}
          </p>
          {available === false ? (
            <div className="flex flex-1 items-center justify-center p-6 text-center text-sm text-fg-muted">
              {t("chat.pdfUnavailable")}
            </div>
          ) : (
            <iframe
              key={`${program}-${active.page}`}
              src={pdfUrl(program, active.page)}
              title={t("chat.pdfTitle", { program })}
              className="min-h-0 w-full flex-1 bg-bg-subtle"
            />
          )}
        </div>
      ) : (
        <ol className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto p-3">
          {sources.map((c, i) => {
            const isActive = i === activeIndex;
            return (
              <li key={c.chunk_id}>
                <button
                  type="button"
                  onClick={() => onSelect(i)}
                  aria-pressed={isActive}
                  className={cn(
                    "focus-ring flex w-full flex-col gap-1.5 rounded-lg border p-3 text-left transition-colors",
                    isActive ? "border-accent bg-accent-soft/40" : "border-border hover:bg-surface-hover",
                  )}
                >
                  <span className="flex items-center gap-2 text-sm font-medium">
                    <span className="inline-flex size-5 items-center justify-center rounded-full bg-bg-subtle text-xs text-fg-muted">{i + 1}</span>
                    {c.program ?? c.faculty}
                    <span className="text-fg-muted">· {t("chat.sourcePage", { page: c.page })}</span>
                  </span>
                  {programName && <span className="text-xs text-fg-muted">{programName.th}</span>}
                  {c.snippet && <p className="text-sm text-fg-muted">{c.snippet}</p>}
                </button>
                {isActive && (
                  <Button
                    variant="secondary"
                    size="sm"
                    className="mt-2 w-full"
                    onClick={() => setViewing(true)}
                  >
                    <FileText className="size-3.5" /> {t("chat.openPdf")}
                  </Button>
                )}
              </li>
            );
          })}
        </ol>
      )}
    </div>
  );
}

const availability = new Map<string, boolean>();

/** HEAD-probes /api/pdf/<program> once per program; null while unknown. */
function usePdfAvailable(program: string | null): boolean | null {
  const [state, setState] = useState<Record<string, boolean>>({});
  useEffect(() => {
    if (!program || availability.has(program)) return;
    let cancelled = false;
    fetch(`/api/pdf/${encodeURIComponent(program)}`, { method: "HEAD" })
      .then((res) => {
        availability.set(program, res.ok);
        if (!cancelled) setState((s) => ({ ...s, [program]: res.ok }));
      })
      .catch(() => {
        availability.set(program, false);
        if (!cancelled) setState((s) => ({ ...s, [program]: false }));
      });
    return () => {
      cancelled = true;
    };
  }, [program]);
  if (!program) return null;
  return availability.get(program) ?? state[program] ?? null;
}
