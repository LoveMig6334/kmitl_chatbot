import { describe, expect, it } from "vitest";
import { dictionaries } from "@/i18n";
import { AUTH_ERROR_CODES, authErrorKey, isAuthErrorCode, mapAuthError } from "./errors";

describe("mapAuthError", () => {
  it.each([
    [{ code: "invalid_credentials", status: 400 }, "invalid_credentials"],
    [{ code: "email_not_confirmed", status: 400 }, "email_not_confirmed"],
    [{ code: "over_request_rate_limit", status: 429 }, "rate_limited"],
    [{ code: "over_email_send_rate_limit" }, "rate_limited"],
    [{ status: 429, message: "whatever" }, "rate_limited"],
    [{ code: "user_already_exists" }, "user_exists"],
    [{ code: "email_exists" }, "user_exists"],
    [{ code: "weak_password" }, "weak_password"],
    [{ code: "same_password" }, "same_password"],
    [{ code: "session_expired" }, "session_expired"],
    [{ code: "otp_expired" }, "session_expired"],
    [{ code: "bad_oauth_state" }, "oauth_failed"],
    [{ code: "provider_disabled" }, "provider_disabled"],
    [{ name: "AuthRetryableFetchError", message: "Failed to fetch" }, "network"],
    [new TypeError("Failed to fetch"), "network"],
    [{ status: 503 }, "network"],
    [{ code: "something_new", message: "???" }, "unknown"],
    [null, "unknown"],
    ["boom", "unknown"],
  ])("%o → %s", (input, expected) => {
    expect(mapAuthError(input)).toBe(expected);
  });

  it("falls back to well-known GoTrue messages when no code is sent", () => {
    expect(mapAuthError({ message: "Invalid login credentials" })).toBe("invalid_credentials");
    expect(mapAuthError({ message: "Email not confirmed" })).toBe("email_not_confirmed");
    expect(mapAuthError({ message: "User already registered" })).toBe("user_exists");
    expect(mapAuthError({ message: "Password should be at least 6 characters" })).toBe("weak_password");
  });
});

describe("error → message mapping", () => {
  it("maps every code to a distinct, non-raw message in both locales", () => {
    for (const locale of ["th", "en"] as const) {
      const messages = AUTH_ERROR_CODES.map((c) => dictionaries[locale][authErrorKey(c)]);
      expect(new Set(messages).size).toBe(messages.length);
      for (const m of messages) {
        expect(m).not.toMatch(/invalid login credentials|AuthApiError|gotrue/i);
      }
    }
  });
  it("Thai messages are Thai and English messages are English", () => {
    for (const code of AUTH_ERROR_CODES) {
      expect(dictionaries.th[authErrorKey(code)]).toMatch(/[฀-๿]/);
      expect(dictionaries.en[authErrorKey(code)]).not.toMatch(/[฀-๿]/);
    }
  });
  it("isAuthErrorCode guards query-string input", () => {
    expect(isAuthErrorCode("oauth_failed")).toBe(true);
    expect(isAuthErrorCode("<script>")).toBe(false);
    expect(isAuthErrorCode(null)).toBe(false);
  });
});
