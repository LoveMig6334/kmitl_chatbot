import { NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import { mapAuthError, type AuthErrorCode } from "@/lib/auth/errors";
import { safeNextPath } from "@/lib/auth/routes";

type Flow = "oauth" | "confirm" | "reset";

/** Which friendly error to show when a link/flow fails, by the flow that started it. */
export function callbackErrorCode(flow: string | null, providerCode: string | null): AuthErrorCode {
  const f: Flow = flow === "confirm" || flow === "reset" ? flow : "oauth";
  if (f === "reset") return "link_invalid";
  if (f === "confirm") return "confirm_link_used";
  const mapped = providerCode ? mapAuthError({ code: providerCode }) : "unknown";
  return mapped === "unknown" ? "oauth_failed" : mapped;
}

/**
 * Supabase redirects here after Google OAuth (`flow=oauth`), email confirmation
 * (`flow=confirm`) and password-reset links (`flow=reset`). Exchanges the PKCE code
 * for a session cookie and forwards to `next` (same-origin paths only).
 */
export async function GET(req: Request) {
  const url = new URL(req.url);
  const code = url.searchParams.get("code");
  const flow = url.searchParams.get("flow");
  const next = safeNextPath(url.searchParams.get("next"));
  const providerError = url.searchParams.get("error_code") ?? url.searchParams.get("error");
  const toLogin = (reason: AuthErrorCode) =>
    NextResponse.redirect(new URL(`/login?error=${reason}`, url.origin));

  if (providerError) return toLogin(callbackErrorCode(flow, providerError));

  const supabase = await createSupabaseServerClient();
  if (supabase && code) {
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (error) return toLogin(callbackErrorCode(flow, error.code ?? null));
  }

  const target = new URL(next, url.origin);
  if (target.origin !== url.origin) return NextResponse.redirect(new URL("/chat", url.origin));
  return NextResponse.redirect(target);
}
