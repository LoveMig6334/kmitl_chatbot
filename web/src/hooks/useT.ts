"use client";

import { useLocale } from "@/providers/LocaleProvider";
import { t } from "@/lib/i18n";

/** Legacy object-style strings for the Phase-1-untouched chat components (removed in Phase 2). */
export function useT() {
  const { locale } = useLocale();
  return t(locale);
}
