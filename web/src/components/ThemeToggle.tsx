"use client";

import { Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { useTheme } from "@/providers/ThemeProvider";
import { useTranslation } from "@/providers/LocaleProvider";

/** One-click light/dark flip (the user menu offers the full light/dark/system choice). */
export function ThemeToggle({ className }: { className?: string }) {
  const { resolvedTheme, setTheme } = useTheme();
  const t = useTranslation();
  const next = resolvedTheme === "dark" ? "light" : "dark";
  return (
    <Button
      variant="outline"
      size="icon"
      className={className}
      onClick={() => setTheme(next)}
      aria-label={t("theme.toggle")}
      title={next === "dark" ? t("theme.dark") : t("theme.light")}
    >
      {resolvedTheme === "dark" ? <Sun className="size-4" /> : <Moon className="size-4" />}
    </Button>
  );
}
