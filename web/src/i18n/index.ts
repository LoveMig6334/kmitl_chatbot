import { th, type Dictionary, type MessageKey } from "./th";
import { en } from "./en";

export type { Dictionary, MessageKey };
export type Locale = "th" | "en";

export const LOCALES: readonly Locale[] = ["th", "en"];
export const DEFAULT_LOCALE: Locale = "th";
/** Cookie mirrored from localStorage so the server can render <html lang> and the tab title. */
export const LOCALE_COOKIE = "kmitl.locale";

export const dictionaries: Record<Locale, Dictionary> = { th, en };

export function isLocale(value: unknown): value is Locale {
  return value === "th" || value === "en";
}

export type TranslateParams = Record<string, string | number>;

/** Look a key up in `dict` and substitute `{name}` placeholders. */
export function translate(
  dict: Dictionary,
  key: MessageKey,
  params?: TranslateParams,
): string {
  const template = dict[key] ?? key;
  if (!params) return template;
  return template.replace(/\{(\w+)\}/g, (match, name: string) =>
    name in params ? String(params[name]) : match,
  );
}

export type TFunction = (key: MessageKey, params?: TranslateParams) => string;

export function makeT(locale: Locale): TFunction {
  const dict = dictionaries[locale];
  return (key, params) => translate(dict, key, params);
}
