// @vitest-environment node
import { describe, expect, it, vi } from "vitest";

const jar = vi.hoisted(() => ({ value: undefined as string | undefined }));
vi.mock("server-only", () => ({}));
vi.mock("next/headers", () => ({
  cookies: async () => ({ get: () => (jar.value ? { value: jar.value } : undefined) }),
}));

import { pageMetadata, serverLocale } from "./server";
import { th } from "./th";
import { en } from "./en";

describe("serverLocale / pageMetadata", () => {
  it("defaults to Thai and follows the cookie", async () => {
    jar.value = undefined;
    expect(await serverLocale()).toBe("th");
    expect(await pageMetadata("auth.login.pageTitle")).toEqual({ title: th["auth.login.pageTitle"] });
    jar.value = "en";
    expect(await serverLocale()).toBe("en");
    expect(await pageMetadata("auth.login.pageTitle")).toEqual({ title: en["auth.login.pageTitle"] });
    jar.value = "xx";
    expect(await serverLocale()).toBe("th");
  });
});
