"use client";

import { supabaseConfigured } from "@/lib/supabase/client";
import { useTranslation } from "@/providers/LocaleProvider";
import { Alert } from "@/components/ui/Alert";

export function DemoNotice() {
  const t = useTranslation();
  if (supabaseConfigured) return null;
  return <Alert variant="info">{t("auth.demoNotice")}</Alert>;
}
