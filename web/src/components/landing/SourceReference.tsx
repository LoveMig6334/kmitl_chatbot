"use client";

import { HoverCard } from "radix-ui";
import { ExternalLink, FileText } from "lucide-react";
import { useTranslation } from "@/providers/LocaleProvider";
import { pdfUrl } from "@/components/chat/SourcePanel";
import { cn } from "@/lib/cn";

/** The one fact the landing page cites; it is real (fixture chunk AIT-p12-c1). */
export const PREVIEW_SOURCE = { program: "AIT", page: 12 } as const;

/**
 * A citation marker, rendered either as the inline `[1]` that real answers carry
 * (`variant="marker"`, hover/focus only — not a link) or as the source chip shown under
 * an answer (`variant="chip"`, which also opens the PDF page on click).
 * Hovering or focusing either one reveals the cited passage.
 */
export function SourceReference({
  variant = "chip",
  className,
}: {
  variant?: "chip" | "marker";
  className?: string;
}) {
  const t = useTranslation();
  const { program, page } = PREVIEW_SOURCE;
  const href = pdfUrl(program, page);
  const label = `${t("chat.openPdf")}: ${t("landing.preview.source")}`;

  return (
    <HoverCard.Root openDelay={120} closeDelay={200}>
      <HoverCard.Trigger asChild>
        {variant === "marker" ? (
          <span
            tabIndex={0}
            aria-label={t("landing.preview.source")}
            className={cn(
              "focus-ring inline-flex cursor-default items-center justify-center rounded-md bg-accent px-[0.3em] align-super text-[0.4em] font-semibold leading-[1.7] tracking-normal text-accent-fg",
              className,
            )}
          >
            1
          </span>
        ) : (
          <a
            href={href}
            target="_blank"
            rel="noreferrer noopener"
            aria-label={label}
            className={cn(
              "focus-ring inline-flex w-fit max-w-full items-center gap-2 rounded-lg border border-border bg-bg-subtle px-2.5 py-1.5 text-xs text-fg-muted transition-colors hover:border-border-strong hover:bg-surface-hover hover:text-fg",
              className,
            )}
          >
            <span className="inline-flex size-4 shrink-0 items-center justify-center rounded-sm bg-accent text-[0.625rem] font-semibold text-accent-fg">
              1
            </span>
            <FileText className="size-3.5 shrink-0" aria-hidden="true" />
            <span className="truncate">{t("landing.preview.source")}</span>
            <ExternalLink className="size-3 shrink-0 opacity-60" aria-hidden="true" />
          </a>
        )}
      </HoverCard.Trigger>
      <HoverCard.Portal>
        <HoverCard.Content
          side="top"
          align="start"
          sideOffset={12}
          collisionPadding={12}
          className="pop-in z-50 w-[min(20rem,calc(100vw-1.5rem))] rounded-xl border border-border bg-surface p-3 shadow-lg"
        >
          <SourcePeek />
          <HoverCard.Arrow className="fill-surface" />
        </HoverCard.Content>
      </HoverCard.Portal>
    </HoverCard.Root>
  );
}

/** Line widths (in %) of the stylised page; the highlighted passage sits between them. */
const LINES_ABOVE = [62, 90, 84];
const LINES_BELOW = [88, 76, 58];

/**
 * A stylised document page: skeleton lines draw in, the cited passage lands highlighted,
 * and the [1] badge snaps on — how a citation maps to the PDF, in one glance.
 */
function SourcePeek() {
  const t = useTranslation();
  const { program, page } = PREVIEW_SOURCE;
  let i = 0;
  const line = (w: number, key: string) => (
    <span
      key={key}
      className="doc-line block h-1.5 rounded-full bg-border-strong/70"
      style={{ width: `${w}%`, ["--i" as string]: `${i++ * 60}ms` }}
    />
  );

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-2 text-xs text-fg-muted">
        <FileText className="size-3.5 shrink-0" aria-hidden="true" />
        <span className="font-medium text-fg">{t("landing.preview.docName")}</span>
        <span>{t("chat.sourcePage", { page })}</span>
        <span className="ml-auto rounded-md bg-accent-soft px-1.5 py-0.5 text-[0.625rem] font-semibold text-accent">
          {program}
        </span>
      </div>

      <div className="relative rounded-lg border border-border bg-bg-subtle p-4 pt-5">
        <span
          aria-hidden="true"
          className="absolute right-0 top-0 size-4 rounded-bl-md border-b border-l border-border bg-surface"
        />
        <p className="doc-line mb-3 text-xs font-semibold text-fg" style={{ ["--i" as string]: "0ms" }}>
          {t("landing.preview.docHeading")}
        </p>
        <div className="flex flex-col gap-2">
          {LINES_ABOVE.map((w, n) => line(w, `a${n}`))}
          <div className="doc-highlight relative my-1 rounded-md border border-accent/40 bg-accent-soft px-3 py-2">
            <span className="doc-badge absolute -left-2 -top-2 inline-flex size-5 items-center justify-center rounded-md bg-accent text-[0.625rem] font-semibold text-accent-fg shadow-sm">
              1
            </span>
            <p className="text-xs leading-relaxed text-fg">{t("landing.preview.excerpt")}</p>
          </div>
          {LINES_BELOW.map((w, n) => line(w, `b${n}`))}
        </div>
      </div>

      <p className="text-xs text-fg-muted">
        <span className="font-medium text-fg">{t("landing.preview.excerptLabel")}</span>{" "}
        {t("landing.preview.source")}
      </p>
    </div>
  );
}
