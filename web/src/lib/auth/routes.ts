/** Route rules shared by the proxy (server) and the pages (client). Pure — no imports. */

export const AFTER_LOGIN_PATH = "/chat";
export const LOGIN_PATH = "/login";

/** Pages that require a session. `/` is included because it forwards to the chat. */
export const PROTECTED_PATHS = ["/", "/chat", "/settings", "/profile"] as const;

/** Pages for signed-out users; a signed-in user is bounced to the chat. */
export const AUTH_PATHS = ["/login", "/register", "/signup", "/forgot-password"] as const;

function matches(pathname: string, base: string): boolean {
  if (base === "/") return pathname === "/";
  return pathname === base || pathname.startsWith(`${base}/`);
}

export function isProtectedPath(pathname: string): boolean {
  return PROTECTED_PATHS.some((p) => matches(pathname, p));
}

export function isAuthPath(pathname: string): boolean {
  return AUTH_PATHS.some((p) => matches(pathname, p));
}

/**
 * Where to send a request, or null to let it through.
 * Signed-out + protected page → /login (with `next` so we can return the user afterwards).
 * Signed-in + auth page → the chat.
 */
export function decideRedirect(pathname: string, isAuthenticated: boolean): string | null {
  if (!isAuthenticated && isProtectedPath(pathname)) {
    return pathname === "/" || pathname === AFTER_LOGIN_PATH
      ? LOGIN_PATH
      : `${LOGIN_PATH}?next=${encodeURIComponent(pathname)}`;
  }
  if (isAuthenticated && isAuthPath(pathname)) {
    return AFTER_LOGIN_PATH;
  }
  return null;
}

/** Only allow same-origin relative paths as post-login targets (blocks open redirects). */
export function safeNextPath(value: string | null | undefined, fallback = AFTER_LOGIN_PATH): string {
  if (!value || !value.startsWith("/")) return fallback;
  // The URL parser strips tabs/newlines, so "/\t/evil" would become "//evil"; reject control chars and backslashes outright.
  if (/[\u0000-\u001f\u007f\\]/.test(value)) return fallback;
  let parsed: URL;
  try {
    parsed = new URL(value, "http://safe.invalid");
  } catch {
    return fallback;
  }
  if (parsed.origin !== "http://safe.invalid") return fallback;
  if (isAuthPath(parsed.pathname)) return fallback;
  return parsed.pathname + parsed.search + parsed.hash;
}
