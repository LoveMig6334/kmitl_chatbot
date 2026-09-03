"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useSyncExternalStore,
} from "react";
import { DEFAULT_LOCALE, isLocale, LOCALE_COOKIE, makeT, type Locale, type TFunction } from "@/i18n";

export const LOCALE_STORAGE_KEY = "kmitl.locale";
const CHANGE_EVENT = "kmitl:locale";

function readCookie(name: string): string | undefined {
  return document.cookie
    .split("; ")
    .find((c) => c.startsWith(`${name}=`))
    ?.slice(name.length + 1);
}

/** Cookie first (what the server rendered with), localStorage as the fallback copy. */
export function readStoredLocale(): Locale {
  try {
    const fromCookie = readCookie(LOCALE_COOKIE);
    if (isLocale(fromCookie)) return fromCookie;
    const raw = window.localStorage.getItem(LOCALE_STORAGE_KEY);
    return isLocale(raw) ? raw : DEFAULT_LOCALE;
  } catch {
    return DEFAULT_LOCALE;
  }
}

function persist(locale: Locale) {
  try {
    const secure = window.location.protocol === "https:" ? "; secure" : "";
    document.cookie = `${LOCALE_COOKIE}=${locale}; path=/; max-age=31536000; samesite=lax${secure}`;
    window.localStorage.setItem(LOCALE_STORAGE_KEY, locale);
  } catch {
    /* storage unavailable — the change still applies for this page */
  }
  window.dispatchEvent(new Event(CHANGE_EVENT));
}

function subscribe(callback: () => void) {
  window.addEventListener("storage", callback);
  window.addEventListener(CHANGE_EVENT, callback);
  return () => {
    window.removeEventListener("storage", callback);
    window.removeEventListener(CHANGE_EVENT, callback);
  };
}

interface LocaleContextValue {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: TFunction;
}

const LocaleContext = createContext<LocaleContextValue | null>(null);

export function LocaleProvider({
  children,
  initialLocale = DEFAULT_LOCALE,
}: {
  children: React.ReactNode;
  /** Locale the server rendered with (from the cookie) so SSR and hydration match. */
  initialLocale?: Locale;
}) {
  const locale = useSyncExternalStore(subscribe, readStoredLocale, () => initialLocale);

  useEffect(() => {
    // `?lang=en` on any page switches (and persists) the locale — handy for sharing links.
    const fromQuery = new URLSearchParams(window.location.search).get("lang");
    if (isLocale(fromQuery) && fromQuery !== readStoredLocale()) persist(fromQuery);
  }, []);

  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

  const setLocale = useCallback((next: Locale) => persist(next), []);

  const value = useMemo(
    () => ({ locale, setLocale, t: makeT(locale) }),
    [locale, setLocale],
  );

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useLocale(): LocaleContextValue {
  const ctx = useContext(LocaleContext);
  if (!ctx) throw new Error("useLocale must be used inside <LocaleProvider>");
  return ctx;
}

/** The typed translation function: `t("auth.login.title")`, `t("x.y", { email })`. */
export function useTranslation(): TFunction {
  return useLocale().t;
}
