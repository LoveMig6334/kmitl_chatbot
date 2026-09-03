"use client";

import { useState } from "react";
import Link from "next/link";
import { MailCheck } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { useTranslation } from "@/providers/LocaleProvider";
import { useFormState } from "@/hooks/useFormState";
import { usePageTitle } from "@/hooks/usePageTitle";
import { requestPasswordReset, validateForgot, type AuthErrorCode } from "@/lib/auth";
import { AuthLayout } from "./AuthLayout";
import { AuthErrorAlert } from "./AuthErrorAlert";

export function ForgotPasswordForm() {
  const t = useTranslation();
  usePageTitle("auth.forgot.pageTitle");

  const [formError, setFormError] = useState<AuthErrorCode | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [sentTo, setSentTo] = useState<string | null>(null);
  const form = useFormState({ email: "" }, validateForgot);

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (submitting) return;
    setFormError(null);
    if (!form.check(event.currentTarget as HTMLFormElement)) return;
    setSubmitting(true);
    const result = await requestPasswordReset(form.values.email);
    setSubmitting(false);
    if (!result.ok) {
      setFormError(result.code);
      return;
    }
    setSentTo(form.values.email.trim());
  }

  const backLink = (
    <Link href="/login" className="focus-ring rounded-sm font-medium text-fg underline-offset-4 hover:underline">
      {t("auth.forgot.backToLogin")}
    </Link>
  );

  if (sentTo) {
    return (
      <AuthLayout title={t("auth.forgot.sentTitle")} footer={backLink}>
        <div className="flex flex-col items-center gap-4 text-center" role="status">
          <span className="inline-flex size-14 items-center justify-center rounded-full bg-accent-soft text-accent">
            <MailCheck className="size-7" aria-hidden="true" />
          </span>
          <p className="break-words text-sm text-fg-muted">{t("auth.forgot.sentBody", { email: sentTo })}</p>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout title={t("auth.forgot.title")} subtitle={t("auth.forgot.subtitle")} footer={backLink}>
      <form onSubmit={onSubmit} noValidate className="flex flex-col gap-4" aria-busy={submitting}>
        <AuthErrorAlert code={formError} />
        <Input
          label={t("auth.email")}
          name="email"
          type="email"
          inputMode="email"
          autoComplete="email"
          autoFocus
          placeholder={t("auth.emailPlaceholder")}
          value={form.values.email}
          onChange={form.set("email")}
          error={form.errors.email && t(form.errors.email)}
        />
        <Button type="submit" size="lg" className="w-full" loading={submitting}>
          {submitting ? t("auth.forgot.submitting") : t("auth.forgot.submit")}
        </Button>
      </form>
    </AuthLayout>
  );
}
