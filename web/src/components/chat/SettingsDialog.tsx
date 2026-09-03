"use client";

import { useState } from "react";
import Link from "next/link";
import { Monitor, Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/Dialog";
import { useToast } from "@/components/ui/Toast";
import { LanguageToggle } from "@/components/LanguageToggle";
import { useUser } from "@/hooks/useUser";
import { useLocale } from "@/providers/LocaleProvider";
import { useTheme, type ThemeMode } from "@/providers/ThemeProvider";
import { LOGIN_PATH, updateDisplayName, validateDisplayName } from "@/lib/auth";
import { authErrorKey } from "@/lib/auth/errors";
import { cn } from "@/lib/cn";

const THEMES: { mode: ThemeMode; Icon: typeof Sun }[] = [
  { mode: "light", Icon: Sun },
  { mode: "dark", Icon: Moon },
  { mode: "system", Icon: Monitor },
];

/** Profile (display name) + appearance (theme, language), opened from the sidebar footer. */
export function SettingsDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const { t } = useLocale();
  const { theme, setTheme } = useTheme();
  const { user, demo } = useUser();

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{t("settings.title")}</DialogTitle>
        </DialogHeader>

        <section className="flex flex-col gap-3">
          <h3 className="text-xs font-medium uppercase tracking-wide text-fg-muted">{t("settings.profile")}</h3>
          {user ? (
            <ProfileForm key={`${open}:${user.displayName}`} initialName={user.displayName} email={user.email ?? ""} demo={demo} />
          ) : (
            <div className="flex flex-col gap-3">
              <p className="text-sm text-fg-muted">{t("settings.guestProfile")}</p>
              <Button asChild variant="outline" className="w-fit">
                <Link href={LOGIN_PATH}>{t("user.signIn")}</Link>
              </Button>
            </div>
          )}
        </section>

        <section className="flex flex-col gap-3 border-t border-border pt-4">
          <h3 className="text-xs font-medium uppercase tracking-wide text-fg-muted">{t("settings.appearance")}</h3>
          <div className="flex items-center justify-between gap-4">
            <span className="text-sm">{t("theme.label")}</span>
            <div role="radiogroup" aria-label={t("theme.label")} className="inline-flex h-9 items-center rounded-md border border-border bg-surface p-0.5">
              {THEMES.map(({ mode, Icon }) => (
                <button
                  key={mode}
                  type="button"
                  role="radio"
                  aria-checked={theme === mode}
                  onClick={() => setTheme(mode)}
                  className={cn(
                    "focus-ring inline-flex h-full items-center gap-1.5 rounded-sm px-2.5 text-xs font-medium transition-colors",
                    theme === mode ? "bg-bg-subtle text-fg shadow-sm" : "text-fg-muted hover:text-fg",
                  )}
                >
                  <Icon className="size-3.5" aria-hidden="true" />
                  {t(`theme.${mode}`)}
                </button>
              ))}
            </div>
          </div>
          <div className="flex items-center justify-between gap-4">
            <span className="text-sm">{t("locale.label")}</span>
            <LanguageToggle />
          </div>
        </section>
      </DialogContent>
    </Dialog>
  );
}

function ProfileForm({ initialName, email, demo }: { initialName: string; email: string; demo: boolean }) {
  const { t } = useLocale();
  const { toast } = useToast();
  const [name, setName] = useState(initialName);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    const problem = validateDisplayName(name);
    if (problem) {
      setError(t(problem));
      return;
    }
    setError(null);
    setSaving(true);
    const result = await updateDisplayName(name.trim());
    setSaving(false);
    if (!result.ok) {
      setError(t(authErrorKey(result.code)));
      return;
    }
    toast({ title: t("settings.profileSaved"), variant: "success" });
  }

  return (
    <form onSubmit={save} className="flex flex-col gap-3">
      <Input
        label={t("settings.displayName")}
        value={name}
        onChange={(e) => setName(e.target.value)}
        error={error ?? undefined}
        maxLength={40}
        autoComplete="nickname"
      />
      <Input label={t("settings.email")} value={email} readOnly disabled />
      {demo && <p className="text-xs text-fg-muted">{t("settings.profileDemo")}</p>}
      <div className="flex justify-end">
        <Button type="submit" size="sm" loading={saving} disabled={name.trim() === initialName}>
          {t("settings.saveProfile")}
        </Button>
      </div>
    </form>
  );
}
