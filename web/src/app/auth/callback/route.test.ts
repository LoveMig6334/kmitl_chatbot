// @vitest-environment node
import { beforeEach, describe, expect, it, vi } from "vitest";

const supabase = vi.hoisted(() => ({
  client: null as null | { auth: { exchangeCodeForSession: (c: string) => Promise<{ error: null | { code?: string } }> } },
}));
vi.mock("@/lib/supabase/server", () => ({
  createSupabaseServerClient: async () => supabase.client,
}));

import { callbackErrorCode, GET } from "./route";

const call = (qs: string) => GET(new Request(`http://app.test/auth/callback${qs}`));
const location = async (qs: string) => (await call(qs)).headers.get("location");

beforeEach(() => {
  supabase.client = { auth: { exchangeCodeForSession: async () => ({ error: null }) } };
});

describe("/auth/callback", () => {
  it("exchanges the code and forwards to a safe next path", async () => {
    expect(await location("?code=abc&next=%2Fupdate-password")).toBe("http://app.test/update-password");
    expect(await location("?code=abc")).toBe("http://app.test/chat");
  });

  it("never redirects off-origin", async () => {
    expect(await location("?code=abc&next=%2F%2Fevil.com")).toBe("http://app.test/chat");
    expect(await location("?code=abc&next=%2F%09%2Fevil.com")).toBe("http://app.test/chat");
    expect(await location("?code=abc&next=https%3A%2F%2Fevil.com")).toBe("http://app.test/chat");
  });

  it("maps provider errors by flow", async () => {
    expect(await location("?flow=reset&error=access_denied&error_code=otp_expired")).toBe(
      "http://app.test/login?error=link_invalid",
    );
    expect(await location("?flow=confirm&error=access_denied&error_code=otp_expired")).toBe(
      "http://app.test/login?error=confirm_link_used",
    );
    expect(await location("?flow=oauth&error=access_denied")).toBe("http://app.test/login?error=oauth_failed");
    expect(await location("?error=server_error&error_code=provider_disabled")).toBe(
      "http://app.test/login?error=provider_disabled",
    );
  });

  it("maps a failed code exchange by flow", async () => {
    supabase.client = { auth: { exchangeCodeForSession: async () => ({ error: { code: "flow_state_not_found" } }) } };
    expect(await location("?flow=reset&code=x&next=%2Fupdate-password")).toBe("http://app.test/login?error=link_invalid");
    expect(await location("?flow=confirm&code=x")).toBe("http://app.test/login?error=confirm_link_used");
    expect(await location("?flow=oauth&code=x")).toBe("http://app.test/login?error=session_expired");
  });

  it("passes through in demo mode (no Supabase client)", async () => {
    supabase.client = null;
    expect(await location("?code=abc&next=%2Fchat")).toBe("http://app.test/chat");
  });

  it("callbackErrorCode defaults unknown flows to oauth", () => {
    expect(callbackErrorCode(null, null)).toBe("oauth_failed");
    expect(callbackErrorCode("weird", "otp_expired")).toBe("session_expired");
  });
});
