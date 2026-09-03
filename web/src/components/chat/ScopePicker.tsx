"use client";

import { ChevronDown, SlidersHorizontal } from "lucide-react";
import { Popover } from "radix-ui";
import { Checkbox } from "@/components/ui/Checkbox";
import { useLocale } from "@/providers/LocaleProvider";
import { PROGRAMS, PROGRAM_IDS, type ProgramId } from "@/lib/constants";
import { cn } from "@/lib/cn";

/** Program checkboxes (AIT / DSBA / BIT / IT) in a popover; at least one stays selected. */
export function ScopePicker({ scope, onChange, className }: { scope: ProgramId[]; onChange: (s: ProgramId[]) => void; className?: string }) {
  const { locale, t } = useLocale();
  const all = scope.length === PROGRAM_IDS.length;

  function toggle(id: ProgramId, checked: boolean) {
    const next = checked ? [...scope, id] : scope.filter((s) => s !== id);
    if (next.length === 0) return; // never send an empty scope from the UI
    onChange(PROGRAM_IDS.filter((p) => next.includes(p)));
  }

  return (
    <Popover.Root>
      <Popover.Trigger
        className={cn(
          "focus-ring inline-flex h-8 items-center gap-1.5 rounded-full border border-border bg-surface px-2.5 text-xs font-medium text-fg-muted transition-colors hover:text-fg data-[state=open]:bg-surface-hover",
          className,
        )}
        aria-label={t("chat.scope")}
      >
        <SlidersHorizontal className="size-3.5" aria-hidden="true" />
        <span>{all ? t("chat.scopeAll") : scope.join(" · ")}</span>
        <ChevronDown className="size-3.5" aria-hidden="true" />
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          align="start"
          sideOffset={6}
          collisionPadding={8}
          className="z-50 w-72 rounded-lg border border-border bg-surface p-2 text-fg shadow-lg"
        >
          <p className="px-2 pb-1.5 text-xs text-fg-muted">{t("chat.scopeHint")}</p>
          <div className="flex flex-col">
            {PROGRAMS.map((p) => (
              <Checkbox
                key={p.id}
                checked={scope.includes(p.id)}
                onCheckedChange={(v) => toggle(p.id, v === true)}
                label={
                  <span className="flex flex-col">
                    <span className="font-medium">{p.id}</span>
                    <span className="text-xs text-fg-muted">{locale === "th" ? p.th : p.en}</span>
                  </span>
                }
              />
            ))}
          </div>
          {!all && (
            <button
              type="button"
              onClick={() => onChange([...PROGRAM_IDS])}
              className="focus-ring mt-1 w-full rounded-md px-2 py-1.5 text-left text-xs font-medium text-accent hover:bg-surface-hover"
            >
              {t("chat.scopeSelectAll")}
            </button>
          )}
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}
