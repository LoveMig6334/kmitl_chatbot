// @vitest-environment node
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

const supabase = vi.hoisted(() => ({ user: null as null | { id: string } }));
vi.mock("@supabase/ssr", () => ({
  createServerClient: () => ({
    auth: { getUser: async () => ({ data: { user: supabase.user } }) },
  }),
}));

import { config, proxy } from "./proxy";

const ENV = { ...process.env };
const req = (path: string) => new NextRequest(`http://localhost:3000${path}`);

describe("proxy (route protection)", () => {
  beforeEach(() => {
    process.env.NEXT_PUBLIC_SUPABASE_URL = "https://x.supabase.co";
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = "anon";
    supabase.user = null;
  });
  afterEach(() => {
    process.env = { ...ENV };
  });

  it("lets a signed-out visitor use /chat as a guest", async () => {
    const res = await proxy(req("/chat"));
    expect(res.status).toBe(200);
  });

  it("redirects a signed-in user away from /login and /register to /chat", async () => {
    supabase.user = { id: "u1" };
    for (const p of ["/login", "/register"]) {
      const res = await proxy(req(p));
      expect(res.status).toBe(307);
      expect(res.headers.get("location")).toBe("http://localhost:3000/chat");
    }
  });

  it("lets signed-in users reach the chat and signed-out users reach /login", async () => {
    expect((await proxy(req("/login"))).status).toBe(200);
    supabase.user = { id: "u1" };
    expect((await proxy(req("/chat"))).status).toBe(200);
  });

  it("is a no-op in demo mode (no Supabase keys)", async () => {
    delete process.env.NEXT_PUBLIC_SUPABASE_URL;
    delete process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
    expect((await proxy(req("/chat"))).status).toBe(200);
  });

  it("mirrors ?lang= into the locale cookie (also in demo mode)", async () => {
    delete process.env.NEXT_PUBLIC_SUPABASE_URL;
    const res = await proxy(req("/login?lang=en"));
    expect(res.status).toBe(200);
    expect(res.cookies.get("kmitl.locale")?.value).toBe("en");
    expect((await proxy(req("/login?lang=xx"))).cookies.get("kmitl.locale")).toBeUndefined();
  });

  it("keeps the locale cookie on an auth redirect", async () => {
    supabase.user = { id: "u1" }; // signed-in users are bounced off /login
    const res = await proxy(req("/login?lang=en"));
    expect(res.status).toBe(307);
    expect(res.cookies.get("kmitl.locale")?.value).toBe("en");
  });

  it("matcher skips API routes, the OAuth callback and static assets", () => {
    const re = new RegExp(`^${config.matcher[0].replace(/\\\\/g, "\\")}$`);
    expect(re.test("/chat")).toBe(true);
    expect(re.test("/login")).toBe(true);
    expect(re.test("/api/chat")).toBe(false);
    expect(re.test("/auth/callback")).toBe(false);
    expect(re.test("/_next/static/x.js")).toBe(false);
    expect(re.test("/favicon.ico")).toBe(false);
    expect(re.test("/logo.svg")).toBe(false);
  });
});
