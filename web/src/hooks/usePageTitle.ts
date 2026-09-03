"use client";

import { useEffect } from "react";
import { useLocale } from "@/providers/LocaleProvider";
import type { MessageKey } from "@/i18n";

/** Localised <title> for client pages (server metadata only knows the default locale). */
export function usePageTitle(key: MessageKey) {
  const { t } = useLocale();
  useEffect(() => {
    document.title = `${t(key)} · ${t("app.name")}`;
  }, [key, t]);
}
