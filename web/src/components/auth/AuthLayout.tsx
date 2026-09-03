"use client";

import { useTranslation } from "@/providers/LocaleProvider";
import { LanguageToggle } from "@/components/LanguageToggle";
import { ThemeToggle } from "@/components/ThemeToggle";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { BrandMark } from "./BrandMark";
import { DemoNotice } from "./DemoNotice";

/** Shared frame for /login, /register, /forgot-password, /update-password. */
export function AuthLayout({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
}) {
  const t = useTranslation();
  return (
    <div className="flex min-h-dvh flex-col bg-bg-subtle">
      <header className="flex items-center justify-between gap-3 px-4 py-3 sm:px-6">
        <BrandMark label={t("app.name")} />
        <div className="flex items-center gap-2">
          <LanguageToggle />
          <ThemeToggle />
        </div>
      </header>

      <main className="flex flex-1 flex-col items-center justify-center px-4 py-6 sm:py-10">
        <Card className="w-full max-w-[26rem] border-0 bg-transparent shadow-none sm:border sm:bg-surface sm:shadow-sm">
          <CardHeader className="p-0 pb-6 sm:p-8 sm:pb-2">
            <CardTitle>{title}</CardTitle>
            {subtitle && <CardDescription>{subtitle}</CardDescription>}
          </CardHeader>
          <CardContent className="flex flex-col gap-5 p-0 sm:p-8">
            <DemoNotice />
            {children}
          </CardContent>
        </Card>
        {footer && <div className="mt-6 text-center text-sm text-fg-muted">{footer}</div>}
      </main>

      <footer className="px-4 pb-6 text-center text-xs text-fg-muted">{t("auth.legal")}</footer>
    </div>
  );
}
