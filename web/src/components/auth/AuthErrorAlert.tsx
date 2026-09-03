"use client";

import { useEffect, useRef } from "react";
import { Alert } from "@/components/ui/Alert";
import { useTranslation } from "@/providers/LocaleProvider";
import { authErrorKey, type AuthErrorCode } from "@/lib/auth/errors";

/** Form-level error; moves focus to itself when a new error appears so screen readers announce it. */
export function AuthErrorAlert({ code }: { code: AuthErrorCode | null }) {
  const t = useTranslation();
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (code) ref.current?.focus();
  }, [code]);
  if (!code) return null;
  return (
    <div ref={ref} tabIndex={-1} className="focus-ring rounded-md">
      <Alert variant="danger">{t(authErrorKey(code))}</Alert>
    </div>
  );
}
