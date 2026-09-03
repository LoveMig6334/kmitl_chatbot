"use client";

import { ToggleGroup } from "radix-ui";
import { isLocale, LOCALES } from "@/i18n";
import { useLocale } from "@/providers/LocaleProvider";
import { cn } from "@/lib/cn";

/** Segmented th/en switch: one tab stop, arrow keys move between options. */
export function LanguageToggle({ className }: { className?: string }) {
  const { locale, setLocale, t } = useLocale();
  return (
    <ToggleGroup.Root
      type="single"
      value={locale}
      onValueChange={(value) => isLocale(value) && setLocale(value)}
      aria-label={t("locale.label")}
      className={cn("inline-flex h-9 items-center rounded-md border border-border bg-surface p-0.5", className)}
    >
      {LOCALES.map((value) => (
        <ToggleGroup.Item
          key={value}
          value={value}
          className={cn(
            "focus-ring h-full rounded-sm px-2.5 text-xs font-medium text-fg-muted transition-colors hover:text-fg",
            "data-[state=on]:bg-bg-subtle data-[state=on]:text-fg data-[state=on]:shadow-sm",
          )}
        >
          {t(`locale.${value}`)}
        </ToggleGroup.Item>
      ))}
    </ToggleGroup.Root>
  );
}
