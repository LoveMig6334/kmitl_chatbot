"use client";

import { useAppStore } from "@/lib/store";
import { t } from "@/lib/i18n";

export function useT() {
  const locale = useAppStore((s) => s.locale);
  return t(locale);
}
