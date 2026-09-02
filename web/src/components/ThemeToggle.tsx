"use client";

import { Moon, Sun } from "lucide-react";
import { useAppStore } from "@/lib/store";
import { useT } from "@/hooks/useT";

export function ThemeToggle() {
  const theme = useAppStore((s) => s.theme);
  const toggle = useAppStore((s) => s.toggleTheme);
  const t = useT();

  return (
    <button
      onClick={toggle}
      title={theme === "dark" ? t.themeLight : t.themeDark}
      className="flex h-9 w-9 items-center justify-center rounded-full border border-border bg-surface text-muted transition-colors hover:bg-surface-muted hover:text-foreground"
    >
      {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
    </button>
  );
}
