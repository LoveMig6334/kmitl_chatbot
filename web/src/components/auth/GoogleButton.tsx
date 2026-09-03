"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { GoogleLogo } from "@/components/icons/GoogleLogo";
import { useTranslation } from "@/providers/LocaleProvider";
import { AFTER_LOGIN_PATH, signInWithGoogle, type AuthErrorCode } from "@/lib/auth";

export function GoogleButton({
  next,
  onError,
  disabled,
}: {
  next?: string;
  onError: (code: AuthErrorCode) => void;
  disabled?: boolean;
}) {
  const t = useTranslation();
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  async function handle() {
    setLoading(true);
    const result = await signInWithGoogle(next);
    if (!result.ok) {
      setLoading(false);
      onError(result.code);
      return;
    }
    if (result.demo) {
      router.replace(next ?? AFTER_LOGIN_PATH);
      return;
    }
    // Real OAuth: the browser is navigating to Google — keep the spinner.
  }

  return (
    <Button
      type="button"
      variant="outline"
      size="lg"
      className="w-full"
      onClick={handle}
      loading={loading}
      disabled={disabled}
    >
      <GoogleLogo className="size-4.5" />
      {t("auth.continueWithGoogle")}
    </Button>
  );
}
