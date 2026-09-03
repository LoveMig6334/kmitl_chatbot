import { describe, expect, it } from "vitest";
import {
  isValidEmail,
  passwordChecks,
  passwordStrength,
  validateForgot,
  validateLogin,
  validateRegister,
  validateUpdatePassword,
} from "./validation";

describe("isValidEmail", () => {
  it.each(["a@b.co", "first.last+tag@sub.example.org", " padded@x.io "])("accepts %s", (v) => {
    expect(isValidEmail(v)).toBe(true);
  });
  it.each(["", "plain", "a@b", "a@ b.co", "@x.io", "a@b."])("rejects %s", (v) => {
    expect(isValidEmail(v)).toBe(false);
  });
});

describe("passwordChecks / strength", () => {
  it("flags each requirement independently", () => {
    expect(passwordChecks("")).toEqual({ minLength: false, letter: false, number: false });
    expect(passwordChecks("abcdefgh")).toEqual({ minLength: true, letter: true, number: false });
    expect(passwordChecks("12345678")).toEqual({ minLength: true, letter: false, number: true });
    expect(passwordChecks("รหัสผ่าน1")).toEqual({ minLength: true, letter: true, number: true });
  });
  it("grades weak < fair < strong", () => {
    expect(passwordStrength("short1")).toBe("weak");
    expect(passwordStrength("abcdefgh")).toBe("fair");
    expect(passwordStrength("abcdefgh1234")).toBe("strong");
    expect(passwordStrength("abcdefghijkl")).toBe("fair"); // long but one class
  });
});

describe("validateLogin", () => {
  it("requires both fields", () => {
    expect(validateLogin({ email: "", password: "" })).toEqual({
      email: "validation.required",
      password: "validation.required",
    });
  });
  it("checks the email format but not the password length", () => {
    expect(validateLogin({ email: "nope", password: "x" })).toEqual({ email: "validation.emailInvalid" });
    expect(validateLogin({ email: "a@b.co", password: "x" })).toEqual({});
  });
});

describe("validateRegister", () => {
  const ok = { displayName: "Som", email: "a@b.co", password: "abcdefgh", confirm: "abcdefgh" };
  it("accepts a valid form", () => {
    expect(validateRegister(ok)).toEqual({});
  });
  it("enforces display-name bounds", () => {
    expect(validateRegister({ ...ok, displayName: " " }).displayName).toBe("validation.required");
    expect(validateRegister({ ...ok, displayName: "A" }).displayName).toBe("validation.displayNameTooShort");
    expect(validateRegister({ ...ok, displayName: "x".repeat(41) }).displayName).toBe(
      "validation.displayNameTooLong",
    );
  });
  it("enforces the 8-char minimum and the confirmation", () => {
    expect(validateRegister({ ...ok, password: "abc", confirm: "abc" }).password).toBe(
      "validation.passwordTooShort",
    );
    expect(validateRegister({ ...ok, confirm: "different" }).confirm).toBe("validation.passwordMismatch");
    expect(validateRegister({ ...ok, confirm: "" }).confirm).toBe("validation.required");
  });
});

describe("validateForgot / validateUpdatePassword", () => {
  it("forgot needs a valid email", () => {
    expect(validateForgot({ email: "" })).toEqual({ email: "validation.required" });
    expect(validateForgot({ email: "a@b.co" })).toEqual({});
  });
  it("update needs a long enough, matching password", () => {
    expect(validateUpdatePassword({ password: "abc", confirm: "abc" })).toEqual({
      password: "validation.passwordTooShort",
    });
    expect(validateUpdatePassword({ password: "abcdefgh", confirm: "abcdefgX" })).toEqual({
      confirm: "validation.passwordMismatch",
    });
    expect(validateUpdatePassword({ password: "abcdefgh", confirm: "abcdefgh" })).toEqual({});
  });
});
