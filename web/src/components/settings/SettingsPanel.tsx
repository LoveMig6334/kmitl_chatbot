"use client";

import { useState } from "react";
import Link from "next/link";
import { ChevronRight, MessageSquare, Settings, User } from "lucide-react";
import { useT } from "@/hooks/useT";
import { ThemeToggle } from "@/components/ThemeToggle";
import { LanguageToggle } from "@/components/LanguageToggle";
import { EditableProfile } from "./EditableProfile";

type Section = "profile" | "language" | "settings";

export function SettingsPanel({ initialSection }: { initialSection: Section }) {
  const t = useT();
  const [section, setSection] = useState<Section>(initialSection);

  const menu = [
    { id: "profile" as const, label: t.profile, icon: <User className="h-4 w-4" /> },
    { id: "language" as const, label: t.language, icon: <MessageSquare className="h-4 w-4" /> },
    { id: "settings" as const, label: t.settings, icon: <Settings className="h-4 w-4" /> },
  ];

  return (
    <div className="min-h-dvh bg-background px-4 py-6">
      <div className="mx-auto w-full max-w-md">
        <Link
          href="/chat"
          className="mb-4 inline-flex items-center gap-1 text-sm text-muted hover:text-foreground"
        >
          <ChevronRight className="h-4 w-4 rotate-180" />
          {t.newChat}
        </Link>

        <div className="rounded-2xl border border-border bg-surface p-2 shadow-sm">
          {menu.map((item) => (
            <button
              key={item.id}
              onClick={() => setSection(item.id)}
              className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors ${
                section === item.id
                  ? "bg-surface-muted text-foreground"
                  : "text-foreground hover:bg-surface-muted"
              }`}
            >
              {item.icon}
              <span className="flex-1 text-left">{item.label}</span>
              <ChevronRight className="h-4 w-4 text-muted" />
            </button>
          ))}
        </div>

        <div className="mt-4 rounded-2xl border border-border bg-surface p-6 shadow-sm">
          {section === "profile" && <EditableProfile />}
          {section === "language" && (
            <div className="flex flex-col gap-3">
              <h2 className="text-lg font-semibold">{t.language}</h2>
              <LanguageToggle />
            </div>
          )}
          {section === "settings" && (
            <div className="flex flex-col gap-3">
              <h2 className="text-lg font-semibold">{t.settings}</h2>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted">{t.themeLight}</span>
                <ThemeToggle />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
