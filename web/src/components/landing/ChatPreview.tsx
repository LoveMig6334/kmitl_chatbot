"use client";

import { useCallback, useRef, useState } from "react";
import { GraduationCap } from "lucide-react";
import { useTranslation } from "@/providers/LocaleProvider";
import { SourceReference } from "./SourceReference";

const MAX_TILT_DEG = 10;

/**
 * One real exchange, as the chat renders it. The card slowly tilts around on its own
 * and follows the pointer on hover; the source chip reveals the cited passage.
 */
export function ChatPreview() {
  const t = useTranslation();
  const ref = useRef<HTMLDivElement>(null);
  const [hovering, setHovering] = useState(false);

  const onPointerMove = useCallback((e: React.PointerEvent<HTMLDivElement>) => {
    const el = ref.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const px = (e.clientX - rect.left) / rect.width - 0.5; // -0.5 … 0.5
    const py = (e.clientY - rect.top) / rect.height - 0.5;
    el.style.setProperty("--tilt-y", `${(px * MAX_TILT_DEG * 2).toFixed(2)}deg`);
    el.style.setProperty("--tilt-x", `${(-py * MAX_TILT_DEG * 2).toFixed(2)}deg`);
    el.style.setProperty("--lift", "-10px");
  }, []);

  const reset = useCallback(() => {
    const el = ref.current;
    if (!el) return;
    el.style.removeProperty("--tilt-x");
    el.style.removeProperty("--tilt-y");
    el.style.removeProperty("--lift");
    setHovering(false);
  }, []);

  return (
    <div
      ref={ref}
      data-hovering={hovering || undefined}
      onPointerMove={onPointerMove}
      onPointerEnter={() => setHovering(true)}
      onPointerLeave={reset}
      className="tilt-card w-full max-w-md rounded-2xl border border-border bg-surface p-5 shadow-md data-[hovering=true]:shadow-lg"
    >
      <div className="flex flex-col gap-5 text-sm">
        <div className="flex justify-end">
          <div className="max-w-[85%] rounded-2xl rounded-tr-md bg-bg-subtle px-4 py-2.5 text-fg">
            <span className="sr-only">{t("landing.preview.you")}: </span>
            {t("landing.preview.question")}
          </div>
        </div>
        <div className="flex items-start gap-3">
          <span
            className="mt-0.5 inline-flex size-7 shrink-0 items-center justify-center rounded-lg bg-accent-soft text-accent"
            aria-hidden="true"
          >
            <GraduationCap className="size-4" />
          </span>
          <div className="flex min-w-0 flex-col gap-3">
            <p className="leading-relaxed text-fg">
              <span className="sr-only">{t("landing.preview.assistant")}: </span>
              {t("landing.preview.answer")}
            </p>
            <SourceReference variant="chip" />
          </div>
        </div>
      </div>
    </div>
  );
}
