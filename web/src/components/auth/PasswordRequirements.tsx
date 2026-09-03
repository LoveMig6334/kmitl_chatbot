"use client";

import { Check, Circle } from "lucide-react";
import { cn } from "@/lib/cn";
import { useTranslation } from "@/providers/LocaleProvider";
import { passwordChecks, passwordStrength, type PasswordStrength } from "@/lib/auth/validation";

const meter: Record<PasswordStrength, { width: string; color: string; key: `auth.pw.strength.${PasswordStrength}` }> = {
  weak: { width: "w-1/3", color: "bg-danger", key: "auth.pw.strength.weak" },
  fair: { width: "w-2/3", color: "bg-warning", key: "auth.pw.strength.fair" },
  strong: { width: "w-full", color: "bg-success", key: "auth.pw.strength.strong" },
};

/** Live checklist + strength bar under the password field. */
export function PasswordRequirements({ password, id }: { password: string; id?: string }) {
  const t = useTranslation();
  const checks = passwordChecks(password);
  const strength = passwordStrength(password);
  const items: { key: keyof typeof checks; label: string; required: boolean }[] = [
    { key: "minLength", label: t("auth.pw.minLength"), required: true },
    { key: "letter", label: t("auth.pw.letter"), required: false },
    { key: "number", label: t("auth.pw.number"), required: false },
  ];
  const show = password.length > 0;

  return (
    <div id={id} className="flex flex-col gap-2 text-xs">
      {show && (
        <div className="flex items-center gap-2">
          <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-border">
            <div className={cn("h-full rounded-full transition-all", meter[strength].width, meter[strength].color)} />
          </div>
          <span className="w-16 text-right text-fg-muted" aria-live="polite">
            {t(meter[strength].key)}
          </span>
        </div>
      )}
      <p className="text-fg-muted">{t("auth.pw.title")}</p>
      <ul aria-label={t("auth.pw.title")} className="flex flex-col gap-1">
        {items.map((item) => {
          const ok = checks[item.key];
          return (
            <li
              key={item.key}
              data-ok={ok}
              className={cn("flex items-center gap-2", ok ? "text-success" : "text-fg-muted")}
            >
              {ok ? (
                <Check className="size-3.5" aria-hidden="true" />
              ) : (
                <Circle className="size-3.5" aria-hidden="true" />
              )}
              <span>
                {item.label}
                {!item.required && <span className="text-fg-muted"> · {t("common.optional")}</span>}
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
