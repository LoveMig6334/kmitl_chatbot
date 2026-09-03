import { describe, expect, it } from "vitest";
import { dictionaries, LOCALES, makeT, translate } from "@/i18n";
import { th, type MessageKey } from "@/i18n/th";
import { en } from "@/i18n/en";
import { AUTH_ERROR_CODES, authErrorKey } from "@/lib/auth/errors";

describe("dictionaries", () => {
  it("th and en define exactly the same keys", () => {
    expect(Object.keys(en).sort()).toEqual(Object.keys(th).sort());
  });

  it("no value is empty and placeholders match between locales", () => {
    for (const key of Object.keys(th) as MessageKey[]) {
      expect(th[key].trim(), key).not.toBe("");
      expect(en[key].trim(), key).not.toBe("");
      const params = (s: string) => (s.match(/\{\w+\}/g) ?? []).sort();
      expect(params(en[key]), key).toEqual(params(th[key]));
    }
  });

  it("every auth error code has a message in every locale", () => {
    for (const code of AUTH_ERROR_CODES) {
      for (const locale of LOCALES) {
        expect(dictionaries[locale][authErrorKey(code)]).toBeTruthy();
      }
    }
  });

  it("translate substitutes params and leaves unknown placeholders alone", () => {
    expect(translate(en, "auth.register.checkEmailBody", { email: "a@b.co" })).toContain("a@b.co");
    expect(translate({ ...en, "app.name": "{x} {y}" }, "app.name", { x: 1 })).toBe("1 {y}");
    expect(makeT("th")("theme.dark")).toBe(th["theme.dark"]);
  });
});
