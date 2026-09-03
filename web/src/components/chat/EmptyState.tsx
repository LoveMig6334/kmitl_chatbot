"use client";

import { GraduationCap } from "lucide-react";
import { useTranslation } from "@/providers/LocaleProvider";
import type { MessageKey } from "@/i18n";

export const EXAMPLE_KEYS: MessageKey[] = [
  "chat.example1",
  "chat.example2",
  "chat.example3",
  "chat.example4",
  "chat.example5",
  "chat.example6",
];

export function EmptyState({ onPick }: { onPick: (text: string) => void }) {
  const t = useTranslation();
  return (
    <div className="flex h-full flex-col items-center justify-center gap-6 px-4 py-10 text-center">
      <span className="inline-flex size-12 items-center justify-center rounded-2xl bg-accent-soft text-accent">
        <GraduationCap className="size-6" aria-hidden="true" />
      </span>
      <div className="flex flex-col gap-1.5">
        <h1 className="text-2xl font-semibold tracking-tight">{t("chat.emptyTitle")}</h1>
        <p className="max-w-md text-sm text-fg-muted">{t("chat.emptySubtitle")}</p>
      </div>
      <ul className="grid w-full max-w-2xl grid-cols-1 gap-2 sm:grid-cols-2">
        {EXAMPLE_KEYS.map((key) => (
          <li key={key}>
            <button
              type="button"
              onClick={() => onPick(t(key))}
              className="focus-ring w-full rounded-xl border border-border bg-surface px-4 py-3 text-left text-sm text-fg transition-colors hover:border-border-strong hover:bg-surface-hover"
            >
              {t(key)}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
