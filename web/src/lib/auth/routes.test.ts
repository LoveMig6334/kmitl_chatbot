import { describe, expect, it } from "vitest";
import { decideRedirect, safeNextPath } from "./routes";

describe("decideRedirect", () => {
  it("lets signed-out users into the chat (guest mode)", () => {
    expect(decideRedirect("/chat", false)).toBeNull();
    expect(decideRedirect("/chat/abc", false)).toBeNull();
  });
  it("sends signed-in users on auth pages to the chat", () => {
    for (const p of ["/login", "/register", "/signup", "/forgot-password"]) {
      expect(decideRedirect(p, true)).toBe("/chat");
    }
  });
  it("lets everything else through", () => {
    expect(decideRedirect("/", false)).toBeNull(); // public landing page
    expect(decideRedirect("/", true)).toBeNull();
    expect(decideRedirect("/login", false)).toBeNull();
    expect(decideRedirect("/register", false)).toBeNull();
    expect(decideRedirect("/chat", true)).toBeNull();
    expect(decideRedirect("/update-password", false)).toBeNull(); // page shows its own no-session state
    expect(decideRedirect("/update-password", true)).toBeNull();
    expect(decideRedirect("/chatter", false)).toBeNull(); // prefix match is path-segment aware
  });
});

describe("safeNextPath", () => {
  it("accepts same-origin paths only", () => {
    expect(safeNextPath("/chat")).toBe("/chat");
    expect(safeNextPath("/chat/abc?x=1")).toBe("/chat/abc?x=1");
    expect(safeNextPath("//evil.com")).toBe("/chat");
    expect(safeNextPath("https://evil.com")).toBe("/chat");
    expect(safeNextPath("/\\evil.com")).toBe("/chat");
    expect(safeNextPath("/\t/evil.com")).toBe("/chat"); // tab is stripped by URL parsers → "//evil.com"
    expect(safeNextPath("/\n/evil.com")).toBe("/chat");
    expect(safeNextPath("/%09/evil.com")).toBe("/%09/evil.com"); // still same-origin once resolved
    expect(new URL(safeNextPath("/%09/evil.com"), "http://app.test").origin).toBe("http://app.test");
    expect(safeNextPath("/chat/../login")).toBe("/chat"); // normalises to an auth page
    expect(safeNextPath(null)).toBe("/chat");
  });
  it("never bounces back to an auth page", () => {
    expect(safeNextPath("/login")).toBe("/chat");
  });
});
