"use client";

import { useEffect } from "react";
import { useAppStore } from "@/lib/store";
import { useLocale } from "./LocaleProvider";
import { useTheme } from "./ThemeProvider";

/**
 * Phase 1 shim: mirrors the provider-owned locale/theme into the zustand store so the
 * untouched chat components (which still read `useAppStore(s => s.locale)`) follow along.
 * Removed in Phase 2 when the chat page moves onto the providers.
 */
export function LegacyStoreBridge() {
  const { locale } = useLocale();
  const { resolvedTheme } = useTheme();
  useEffect(() => {
    useAppStore.getState().setLocale(locale);
  }, [locale]);
  useEffect(() => {
    useAppStore.getState().setTheme(resolvedTheme);
  }, [resolvedTheme]);
  return null;
}
