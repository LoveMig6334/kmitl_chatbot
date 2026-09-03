"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { MailCheck } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { PasswordInput } from "@/components/ui/PasswordInput";
import { useToast } from "@/components/ui/Toast";
import { useTranslation } from "@/providers/LocaleProvider";
import { useFormState } from "@/hooks/useFormState";
import { usePageTitle } from "@/hooks/usePageTitle";
import {
  AFTER_LOGIN_PATH,
  DISPLAY_NAME_MAX,
  signUpWithEmail,
  validateRegister,
  type AuthErrorCode,
} from "@/lib/auth";
import { AuthLayout } from "./AuthLayout";
import { GoogleButton } from "./GoogleButton";
import { OrDivider } from "./OrDivider";
import { AuthErrorAlert } from "./AuthErrorAlert";
import { PasswordRequirements } from "./PasswordRequirements";

export function RegisterForm() {
  const t = useTranslation();
  const router = useRouter();
  const { toast } = useToast();
  usePageTitle("auth.register.pageTitle");

  const [formError, setFormError] = useState<AuthErrorCode | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [confirmationEmail, setConfirmationEmail] = useState<string | null>(null);
  const form = useFormState({ displayName: "", email: "", password: "", confirm: "" }, validateRegister);

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (submitting) return;
    setFormError(null);
    if (!form.check(event.currentTarget as HTMLFormElement)) return;
    setSubmitting(true);
    const { displayName, email, password } = form.values;
    const result = await signUpWithEmail(displayName, email, password);
    if (!result.ok) {
      setFormError(result.code);
      setSubmitting(false);
      return;
    }
    if (result.needsConfirmation) {
      setConfirmationEmail(email.trim());
      setSubmitting(false);
      return;
    }
    toast({ title: t("toast.accountCreated"), variant: "success" });
    router.replace(AFTER_LOGIN_PATH);
    router.refresh();
  }

  if (confirmationEmail) {
    return (
      <AuthLayout title={t("auth.register.checkEmailTitle")}>
        <div className="flex flex-col items-center gap-4 text-center" role="status">
          <span className="inline-flex size-14 items-center justify-center rounded-full bg-accent-soft text-accent">
            <MailCheck className="size-7" aria-hidden="true" />
          </span>
          <p className="break-words text-sm text-fg-muted">
            {t("auth.register.checkEmailBody", { email: confirmationEmail })}
          </p>
          <Button asChild variant="secondary" className="mt-2 w-full">
            <Link href="/login">{t("auth.register.goToLogin")}</Link>
          </Button>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout
      title={t("auth.register.title")}
      subtitle={t("auth.register.subtitle")}
      footer={
        <>
          {t("auth.register.haveAccount")}{" "}
          <Link href="/login" className="focus-ring rounded-sm font-medium text-fg underline-offset-4 hover:underline">
            {t("auth.register.loginLink")}
          </Link>
        </>
      }
    >
      <GoogleButton onError={setFormError} disabled={submitting} />
      <OrDivider />
      <form onSubmit={onSubmit} noValidate className="flex flex-col gap-4" aria-busy={submitting}>
        <AuthErrorAlert code={formError} />
        <Input
          label={t("auth.displayName")}
          name="displayName"
          autoComplete="nickname"
          autoFocus
          maxLength={DISPLAY_NAME_MAX}
          placeholder={t("auth.displayNamePlaceholder")}
          value={form.values.displayName}
          onChange={form.set("displayName")}
          error={form.errors.displayName && t(form.errors.displayName)}
        />
        <Input
          label={t("auth.email")}
          name="email"
          type="email"
          inputMode="email"
          autoComplete="email"
          placeholder={t("auth.emailPlaceholder")}
          value={form.values.email}
          onChange={form.set("email")}
          error={form.errors.email && t(form.errors.email)}
        />
        <div className="flex flex-col gap-2">
          <PasswordInput
            label={t("auth.password")}
            name="password"
            autoComplete="new-password"
            placeholder={t("auth.passwordPlaceholder")}
            value={form.values.password}
            onChange={form.set("password")}
            error={form.errors.password && t(form.errors.password)}
            aria-describedby="password-requirements"
          />
          <PasswordRequirements id="password-requirements" password={form.values.password} />
        </div>
        <PasswordInput
          label={t("auth.confirmPassword")}
          name="confirm"
          autoComplete="new-password"
          placeholder={t("auth.confirmPasswordPlaceholder")}
          value={form.values.confirm}
          onChange={form.set("confirm")}
          error={form.errors.confirm && t(form.errors.confirm)}
        />
        <Button type="submit" size="lg" className="w-full" loading={submitting}>
          {submitting ? t("auth.register.submitting") : t("auth.register.submit")}
        </Button>
      </form>
    </AuthLayout>
  );
}
