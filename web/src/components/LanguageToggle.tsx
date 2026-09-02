"use client";

import { Languages } from "lucide-react";
import { useAppStore } from "@/lib/store";
import type { Locale } from "@/lib/constants";

const options: { value: Locale; label: string }[] = [
  { value: "th", label: "ไทย" },
  { value: "en", label: "EN" },
];

export function LanguageToggle() {
  const locale = useAppStore((s) => s.locale);
  const setLocale = useAppStore((s) => s.setLocale);

  return (
    <div className="flex items-center gap-1 rounded-full border border-border bg-surface p-1">
      <Languages className="ml-2 h-4 w-4 text-muted" />
      {options.map((o) => (
        <button
          key={o.value}
          onClick={() => setLocale(o.value)}
          className={`rounded-full px-2.5 py-1 text-xs font-medium transition-colors ${
            locale === o.value
              ? "bg-accent text-accent-foreground"
              : "text-muted hover:text-foreground"
          }`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}
