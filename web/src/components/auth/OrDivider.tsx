"use client";

import { useTranslation } from "@/providers/LocaleProvider";

export function OrDivider() {
  const t = useTranslation();
  return (
    <div className="flex items-center gap-3 text-xs uppercase text-fg-muted" aria-hidden="true">
      <span className="h-px flex-1 bg-border" />
      {t("common.or")}
      <span className="h-px flex-1 bg-border" />
    </div>
  );
}
