"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { PasswordInput } from "@/components/ui/PasswordInput";
import { useToast } from "@/components/ui/Toast";
import { useTranslation } from "@/providers/LocaleProvider";
import { useFormState } from "@/hooks/useFormState";
import { usePageTitle } from "@/hooks/usePageTitle";
import {
  isAuthErrorCode,
  safeNextPath,
  signInWithEmail,
  validateLogin,
  type AuthErrorCode,
} from "@/lib/auth";
import { AuthLayout } from "./AuthLayout";
import { GoogleButton } from "./GoogleButton";
import { OrDivider } from "./OrDivider";
import { AuthErrorAlert } from "./AuthErrorAlert";

export function LoginForm() {
  const t = useTranslation();
  const router = useRouter();
  const params = useSearchParams();
  const { toast } = useToast();
  usePageTitle("auth.login.pageTitle");

  const next = safeNextPath(params.get("next"));
  const initialError = params.get("error");
  const [formError, setFormError] = useState<AuthErrorCode | null>(
    isAuthErrorCode(initialError) ? initialError : null,
  );
  const [submitting, setSubmitting] = useState(false);
  const form = useFormState({ email: "", password: "" }, validateLogin);

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (submitting) return;
    setFormError(null);
    if (!form.check(event.currentTarget as HTMLFormElement)) return;
    setSubmitting(true);
    const result = await signInWithEmail(form.values.email, form.values.password);
    if (!result.ok) {
      setFormError(result.code);
      setSubmitting(false);
      return;
    }
    toast({ title: t("toast.signedIn"), variant: "success" });
    router.replace(next);
    router.refresh();
  }

  return (
    <AuthLayout
      title={t("auth.login.title")}
      subtitle={t("auth.login.subtitle")}
      footer={
        <>
          {t("auth.login.noAccount")}{" "}
          <Link href="/register" className="focus-ring rounded-sm font-medium text-fg underline-offset-4 hover:underline">
            {t("auth.login.registerLink")}
          </Link>
        </>
      }
    >
      <GoogleButton next={next} onError={setFormError} disabled={submitting} />
      <OrDivider />
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
        <div className="flex flex-col gap-1.5">
          <PasswordInput
            label={t("auth.password")}
            name="password"
            autoComplete="current-password"
            placeholder={t("auth.passwordPlaceholder")}
            value={form.values.password}
            onChange={form.set("password")}
            error={form.errors.password && t(form.errors.password)}
          />
          <Link
            href="/forgot-password"
            className="focus-ring self-end rounded-sm text-xs font-medium text-fg-muted underline-offset-4 hover:text-fg hover:underline"
          >
            {t("auth.login.forgot")}
          </Link>
        </div>
        <Button type="submit" size="lg" className="w-full" loading={submitting}>
          {submitting ? t("auth.login.submitting") : t("auth.login.submit")}
        </Button>
      </form>
    </AuthLayout>
  );
}
