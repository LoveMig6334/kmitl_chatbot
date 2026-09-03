import type { MessageKey } from "@/i18n";

/** Friendly, locale-independent error categories. Raw Supabase messages never reach the UI. */
export type AuthErrorCode =
  | "invalid_credentials"
  | "email_not_confirmed"
  | "rate_limited"
  | "network"
  | "user_exists"
  | "weak_password"
  | "same_password"
  | "session_expired"
  | "oauth_failed"
  | "link_invalid"
  | "confirm_link_used"
  | "provider_disabled"
  | "unknown";

export const AUTH_ERROR_CODES: readonly AuthErrorCode[] = [
  "invalid_credentials",
  "email_not_confirmed",
  "rate_limited",
  "network",
  "user_exists",
  "weak_password",
  "same_password",
  "session_expired",
  "oauth_failed",
  "link_invalid",
  "confirm_link_used",
  "provider_disabled",
  "unknown",
];

export function isAuthErrorCode(value: unknown): value is AuthErrorCode {
  return typeof value === "string" && (AUTH_ERROR_CODES as readonly string[]).includes(value);
}

/** Dictionary key for a code — every code has an entry in both locales (tested). */
export function authErrorKey(code: AuthErrorCode): MessageKey {
  return `authError.${code}`;
}

// Supabase GoTrue error codes (supabase-js `AuthError.code`) → our categories.
const BY_CODE: Record<string, AuthErrorCode> = {
  invalid_credentials: "invalid_credentials",
  email_not_confirmed: "email_not_confirmed",
  phone_not_confirmed: "email_not_confirmed",
  over_request_rate_limit: "rate_limited",
  over_email_send_rate_limit: "rate_limited",
  over_sms_send_rate_limit: "rate_limited",
  user_already_exists: "user_exists",
  email_exists: "user_exists",
  weak_password: "weak_password",
  same_password: "same_password",
  session_expired: "session_expired",
  session_not_found: "session_expired",
  refresh_token_not_found: "session_expired",
  refresh_token_already_used: "session_expired",
  otp_expired: "session_expired",
  flow_state_expired: "session_expired",
  flow_state_not_found: "session_expired",
  bad_oauth_state: "oauth_failed",
  bad_oauth_callback: "oauth_failed",
  oauth_provider_not_supported: "oauth_failed",
  provider_disabled: "provider_disabled",
  email_provider_disabled: "provider_disabled",
  signup_disabled: "provider_disabled",
};

// Older GoTrue versions only send a message; match the well-known phrases.
const BY_MESSAGE: [RegExp, AuthErrorCode][] = [
  [/invalid login credentials/i, "invalid_credentials"],
  [/email not confirmed/i, "email_not_confirmed"],
  [/already (registered|exists|been registered)/i, "user_exists"],
  [/password should be|password is too weak|weak password/i, "weak_password"],
  [/different from the old password/i, "same_password"],
  [/rate limit|too many requests/i, "rate_limited"],
  [/failed to fetch|network|fetch failed|load failed|ECONNREFUSED|ENOTFOUND/i, "network"],
  [/session.*(expired|missing|not found)|not authenticated|jwt expired/i, "session_expired"],
];

interface ErrorLike {
  name?: unknown;
  code?: unknown;
  status?: unknown;
  message?: unknown;
}

/** Map anything Supabase (or fetch) can throw/return into an {@link AuthErrorCode}. */
export function mapAuthError(error: unknown): AuthErrorCode {
  if (!error) return "unknown";
  const e = (typeof error === "object" ? error : { message: String(error) }) as ErrorLike;
  const name = typeof e.name === "string" ? e.name : "";
  const code = typeof e.code === "string" ? e.code : "";
  const status = typeof e.status === "number" ? e.status : undefined;
  const message = typeof e.message === "string" ? e.message : "";

  if (name === "AuthRetryableFetchError" || (name === "TypeError" && /fetch/i.test(message))) {
    return "network";
  }
  if (code && BY_CODE[code]) return BY_CODE[code];
  if (status === 429) return "rate_limited";
  for (const [pattern, mapped] of BY_MESSAGE) {
    if (pattern.test(message)) return mapped;
  }
  if (status === 0 || status === 502 || status === 503 || status === 504) return "network";
  return "unknown";
}
