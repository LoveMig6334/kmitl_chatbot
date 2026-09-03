"use client";

import { Tooltip } from "radix-ui";
import type { Locale } from "@/i18n";
import { ThemeProvider } from "./ThemeProvider";
import { LocaleProvider } from "./LocaleProvider";
import { ToastProvider } from "@/components/ui/Toast";
import { LegacyStoreBridge } from "./LegacyStoreBridge";

export function AppProviders({
  children,
  initialLocale,
}: {
  children: React.ReactNode;
  initialLocale?: Locale;
}) {
  return (
    <ThemeProvider>
      <LocaleProvider initialLocale={initialLocale}>
        <Tooltip.Provider delayDuration={300}>
          <ToastProvider>
            <LegacyStoreBridge />
            {children}
          </ToastProvider>
        </Tooltip.Provider>
      </LocaleProvider>
    </ThemeProvider>
  );
}
