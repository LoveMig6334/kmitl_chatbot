"use client";

import Link from "next/link";
import { BrandMark } from "@/components/auth/BrandMark";
import { LanguageToggle } from "@/components/LanguageToggle";
import { ThemeToggle } from "@/components/ThemeToggle";
import { Button } from "@/components/ui/Button";
import { useTranslation } from "@/providers/LocaleProvider";
import { AFTER_LOGIN_PATH, LOGIN_PATH } from "@/lib/auth/routes";

/** Top bar: brand, language/theme, and one button that always leads to the chat. */
export function LandingHeader({ signedIn }: { signedIn: boolean }) {
  const t = useTranslation();
  return (
    <header className="border-b border-border">
      <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between gap-3 px-5 sm:px-8">
        <BrandMark label={t("app.name")} />
        <nav className="flex items-center gap-2" aria-label={t("app.name")}>
          <LanguageToggle className="hidden sm:inline-flex" />
          <ThemeToggle />
          <Button asChild size="sm" variant={signedIn ? "primary" : "outline"} className="ml-1">
            <Link href={signedIn ? AFTER_LOGIN_PATH : LOGIN_PATH}>
              {signedIn ? t("landing.nav.openChat") : t("landing.nav.signIn")}
            </Link>
          </Button>
        </nav>
      </div>
    </header>
  );
}
