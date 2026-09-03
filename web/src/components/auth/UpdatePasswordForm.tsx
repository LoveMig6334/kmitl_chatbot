"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { KeyRound } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { PasswordInput } from "@/components/ui/PasswordInput";
import { Skeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/components/ui/Toast";
import { useTranslation } from "@/providers/LocaleProvider";
import { useFormState } from "@/hooks/useFormState";
import { usePageTitle } from "@/hooks/usePageTitle";
import {
  AFTER_LOGIN_PATH,
  hasSession,
  updatePassword,
  validateUpdatePassword,
  type AuthErrorCode,
} from "@/lib/auth";
import { AuthLayout } from "./AuthLayout";
import { AuthErrorAlert } from "./AuthErrorAlert";
import { PasswordRequirements } from "./PasswordRequirements";

type Stage = "checking" | "form" | "no-session" | "done";

export function UpdatePasswordForm() {
  const t = useTranslation();
  const router = useRouter();
  const { toast } = useToast();
  usePageTitle("auth.update.pageTitle");

  const [stage, setStage] = useState<Stage>("checking");
  const redirectTimer = useRef<number | undefined>(undefined);
  const [formError, setFormError] = useState<AuthErrorCode | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const form = useFormState({ password: "", confirm: "" }, validateUpdatePassword);

  useEffect(() => {
    let cancelled = false;
    hasSession().then((ok) => {
      if (!cancelled) setStage(ok ? "form" : "no-session");
    });
    return () => {
      cancelled = true;
      window.clearTimeout(redirectTimer.current);
    };
  }, []);

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (submitting) return;
    setFormError(null);
    if (!form.check(event.currentTarget as HTMLFormElement)) return;
    setSubmitting(true);
    const result = await updatePassword(form.values.password);
    if (!result.ok) {
      setFormError(result.code);
      setSubmitting(false);
      return;
    }
    toast({ title: t("toast.passwordUpdated"), variant: "success" });
    setStage("done");
    redirectTimer.current = window.setTimeout(() => {
      router.replace(AFTER_LOGIN_PATH);
      router.refresh();
    }, 1200);
  }

  if (stage === "checking") {
    return (
      <AuthLayout title={t("auth.update.title")} subtitle={t("auth.update.subtitle")}>
        <div className="flex flex-col gap-4" aria-busy="true" aria-label={t("common.loading")}>
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-11 w-full" />
        </div>
      </AuthLayout>
    );
  }

  if (stage === "no-session") {
    return (
      <AuthLayout title={t("auth.update.noSessionTitle")}>
        <div className="flex flex-col gap-4 text-center" role="alert">
          <p className="text-sm text-fg-muted">{t("auth.update.noSessionBody")}</p>
          <Button asChild className="w-full">
            <Link href="/forgot-password">{t("auth.update.requestAgain")}</Link>
          </Button>
        </div>
      </AuthLayout>
    );
  }

  if (stage === "done") {
    return (
      <AuthLayout title={t("auth.update.successTitle")}>
        <div className="flex flex-col items-center gap-4 text-center" role="status">
          <span className="inline-flex size-14 items-center justify-center rounded-full bg-success-soft text-success">
            <KeyRound className="size-7" aria-hidden="true" />
          </span>
          <p className="text-sm text-fg-muted">{t("auth.update.successBody")}</p>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout title={t("auth.update.title")} subtitle={t("auth.update.subtitle")}>
      <form onSubmit={onSubmit} noValidate className="flex flex-col gap-4" aria-busy={submitting}>
        <AuthErrorAlert code={formError} />
        <div className="flex flex-col gap-2">
          <PasswordInput
            label={t("auth.update.newPassword")}
            name="password"
            autoComplete="new-password"
            autoFocus
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
          {submitting ? t("auth.update.submitting") : t("auth.update.submit")}
        </Button>
      </form>
    </AuthLayout>
  );
}
