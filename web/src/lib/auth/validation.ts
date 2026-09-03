import type { MessageKey } from "@/i18n";

export const PASSWORD_MIN_LENGTH = 8;
export const DISPLAY_NAME_MIN = 2;
export const DISPLAY_NAME_MAX = 40;

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

export function isValidEmail(value: string): boolean {
  return EMAIL_RE.test(value.trim());
}

export interface PasswordChecks {
  minLength: boolean;
  letter: boolean;
  number: boolean;
}

/** Live requirement flags shown under the password field (only minLength is enforced). */
export function passwordChecks(password: string): PasswordChecks {
  return {
    minLength: password.length >= PASSWORD_MIN_LENGTH,
    letter: /\p{L}/u.test(password),
    number: /\d/.test(password),
  };
}

export type PasswordStrength = "weak" | "fair" | "strong";

export function passwordStrength(password: string): PasswordStrength {
  const c = passwordChecks(password);
  if (!c.minLength) return "weak";
  const classes = [c.letter, c.number, /[^\p{L}\d]/u.test(password)].filter(Boolean).length;
  if (password.length >= 12 && classes >= 2) return "strong";
  return "fair";
}

/** Field → dictionary key of the message to show. Absent key = valid. */
export type FieldErrors<F extends string> = Partial<Record<F, MessageKey>>;

export type LoginFields = "email" | "password";
export type RegisterFields = "displayName" | "email" | "password" | "confirm";
export type ForgotFields = "email";
export type UpdatePasswordFields = "password" | "confirm";

function emailError(email: string): MessageKey | undefined {
  if (!email.trim()) return "validation.required";
  if (!isValidEmail(email)) return "validation.emailInvalid";
  return undefined;
}

function passwordError(password: string): MessageKey | undefined {
  if (!password) return "validation.required";
  if (password.length < PASSWORD_MIN_LENGTH) return "validation.passwordTooShort";
  return undefined;
}

function confirmError(password: string, confirm: string): MessageKey | undefined {
  if (!confirm) return "validation.required";
  if (confirm !== password) return "validation.passwordMismatch";
  return undefined;
}

export function validateLogin(v: { email: string; password: string }): FieldErrors<LoginFields> {
  const errors: FieldErrors<LoginFields> = {};
  const email = emailError(v.email);
  if (email) errors.email = email;
  if (!v.password) errors.password = "validation.required";
  return errors;
}

export function validateRegister(v: {
  displayName: string;
  email: string;
  password: string;
  confirm: string;
}): FieldErrors<RegisterFields> {
  const errors: FieldErrors<RegisterFields> = {};
  const name = v.displayName.trim();
  if (!name) errors.displayName = "validation.required";
  else if (name.length < DISPLAY_NAME_MIN) errors.displayName = "validation.displayNameTooShort";
  else if (name.length > DISPLAY_NAME_MAX) errors.displayName = "validation.displayNameTooLong";
  const email = emailError(v.email);
  if (email) errors.email = email;
  const password = passwordError(v.password);
  if (password) errors.password = password;
  const confirm = confirmError(v.password, v.confirm);
  if (confirm) errors.confirm = confirm;
  return errors;
}

export function validateForgot(v: { email: string }): FieldErrors<ForgotFields> {
  const email = emailError(v.email);
  return email ? { email } : {};
}

export function validateUpdatePassword(v: {
  password: string;
  confirm: string;
}): FieldErrors<UpdatePasswordFields> {
  const errors: FieldErrors<UpdatePasswordFields> = {};
  const password = passwordError(v.password);
  if (password) errors.password = password;
  const confirm = confirmError(v.password, v.confirm);
  if (confirm) errors.confirm = confirm;
  return errors;
}

export function hasErrors(errors: FieldErrors<string>): boolean {
  return Object.keys(errors).length > 0;
}
