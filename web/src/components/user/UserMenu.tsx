"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ChevronDown, Languages, LogIn, LogOut, Monitor, Moon, Settings, Sun } from "lucide-react";
import { Avatar } from "@/components/ui/Avatar";
import { Skeleton } from "@/components/ui/Skeleton";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/DropdownMenu";
import { useToast } from "@/components/ui/Toast";
import { useUser } from "@/hooks/useUser";
import { useLocale } from "@/providers/LocaleProvider";
import { useTheme, type ThemeMode } from "@/providers/ThemeProvider";
import { isLocale, LOCALES } from "@/i18n";
import { authErrorKey, LOGIN_PATH, signOut } from "@/lib/auth";
import { cn } from "@/lib/cn";

const THEME_ICONS: Record<ThemeMode, typeof Sun> = { light: Sun, dark: Moon, system: Monitor };
const THEME_MODES: ThemeMode[] = ["light", "dark", "system"];

/** Avatar + name trigger with theme, language and sign-out. Reused by the chat page in Phase 2. */
export function UserMenu({
  className,
  showName = true,
  onOpenSettings,
  side = "bottom",
}: {
  className?: string;
  showName?: boolean;
  /** When given, adds a "Settings" item (profile + appearance dialog owned by the caller). */
  onOpenSettings?: () => void;
  side?: "top" | "bottom";
}) {
  const { user, loading, demo } = useUser();
  const { locale, setLocale, t } = useLocale();
  const { theme, setTheme } = useTheme();
  const { toast } = useToast();
  const router = useRouter();
  const [signingOut, setSigningOut] = useState(false);

  if (loading) {
    return <Skeleton className={cn("h-9 w-9 rounded-full", showName && "w-32", className)} />;
  }

  const name = user?.displayName || t("user.guest");

  async function onSignOut() {
    setSigningOut(true);
    const result = await signOut();
    if (!result.ok) {
      setSigningOut(false);
      toast({ title: t(authErrorKey(result.code)), variant: "danger" });
      return;
    }
    toast({ title: t("toast.signedOut") });
    router.replace(LOGIN_PATH);
    router.refresh();
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        className={cn(
          "focus-ring inline-flex h-10 max-w-full items-center gap-2 rounded-full border border-transparent pl-0.5 pr-2 text-sm text-fg transition-colors hover:bg-surface-hover data-[state=open]:bg-surface-hover",
          className,
        )}
        aria-label={t("user.menu")}
      >
        <Avatar name={name} src={user?.avatarUrl} size="md" />
        {showName && <span className="min-w-0 flex-1 truncate text-left font-medium">{name}</span>}
        <ChevronDown className="size-4 shrink-0 text-fg-subtle" aria-hidden="true" />
      </DropdownMenuTrigger>

      <DropdownMenuContent align={side === "top" ? "start" : "end"} side={side} className="w-64">
        <DropdownMenuLabel className="flex flex-col gap-0.5">
          {user && <span className="text-xs">{t("user.signedInAs")}</span>}
          <span className="truncate text-sm font-medium text-fg">{name}</span>
          {user?.email && <span className="truncate text-xs">{user.email}</span>}
          {!user && <span className="text-xs">{t("user.guestHint")}</span>}
          {demo && (
            <span className="mt-1 w-fit rounded-sm bg-accent-soft px-1.5 py-0.5 text-xs font-medium text-accent">
              {t("user.demoBadge")}
            </span>
          )}
        </DropdownMenuLabel>
        <DropdownMenuSeparator />

        <DropdownMenuLabel>{t("theme.label")}</DropdownMenuLabel>
        <DropdownMenuRadioGroup value={theme} onValueChange={(v) => setTheme(v as ThemeMode)}>
          {THEME_MODES.map((mode) => {
            const Icon = THEME_ICONS[mode];
            return (
              <DropdownMenuRadioItem key={mode} value={mode}>
                <Icon className="size-4 text-fg-muted" aria-hidden="true" />
                {t(`theme.${mode}`)}
              </DropdownMenuRadioItem>
            );
          })}
        </DropdownMenuRadioGroup>
        <DropdownMenuSeparator />

        <DropdownMenuLabel>{t("locale.label")}</DropdownMenuLabel>
        <DropdownMenuRadioGroup value={locale} onValueChange={(v) => isLocale(v) && setLocale(v)}>
          {LOCALES.map((value) => (
            <DropdownMenuRadioItem key={value} value={value}>
              <Languages className="size-4 text-fg-muted" aria-hidden="true" />
              {t(`locale.${value}`)}
            </DropdownMenuRadioItem>
          ))}
        </DropdownMenuRadioGroup>
        <DropdownMenuSeparator />

        {onOpenSettings && (
          <DropdownMenuItem onSelect={onOpenSettings}>
            <Settings className="size-4 text-fg-muted" aria-hidden="true" />
            {t("user.settings")}
          </DropdownMenuItem>
        )}
        {user ? (
          <DropdownMenuItem destructive disabled={signingOut} onSelect={onSignOut}>
            <LogOut className="size-4" aria-hidden="true" />
            {t("user.signOut")}
          </DropdownMenuItem>
        ) : (
          <DropdownMenuItem onSelect={() => router.push(LOGIN_PATH)}>
            <LogIn className="size-4 text-fg-muted" aria-hidden="true" />
            {t("user.signIn")}
          </DropdownMenuItem>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
