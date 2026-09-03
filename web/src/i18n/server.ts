import "server-only";
import { cookies } from "next/headers";
import type { Metadata } from "next";
import { DEFAULT_LOCALE, dictionaries, isLocale, LOCALE_COOKIE, translate, type Locale, type MessageKey } from "./index";

/** Locale chosen by the browser (cookie mirrored from localStorage by LocaleProvider). */
export async function serverLocale(): Promise<Locale> {
  const value = (await cookies()).get(LOCALE_COOKIE)?.value;
  return isLocale(value) ? value : DEFAULT_LOCALE;
}

/** `generateMetadata` helper: localised tab title for a page. */
export async function pageMetadata(titleKey: MessageKey): Promise<Metadata> {
  const dict = dictionaries[await serverLocale()];
  return { title: translate(dict, titleKey) };
}
