/**
 * Demo mode — when NEXT_PUBLIC_SUPABASE_* are unset the app still runs (local dev,
 * judges without keys): sign-in is simulated by storing a fake user in localStorage.
 */
export const DEMO_USER_KEY = "kmitl.demoUser";

export interface DemoUser {
  email: string;
  displayName: string;
}

export function readDemoUser(): DemoUser | null {
  try {
    const raw = window.localStorage.getItem(DEMO_USER_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<DemoUser>;
    if (typeof parsed.email !== "string") return null;
    return { email: parsed.email, displayName: parsed.displayName || parsed.email };
  } catch {
    return null;
  }
}

export function setDemoUser(user: DemoUser) {
  try {
    window.localStorage.setItem(DEMO_USER_KEY, JSON.stringify(user));
    window.dispatchEvent(new Event("kmitl:demo-auth"));
  } catch {
    /* ignore */
  }
}

export function clearDemoUser() {
  try {
    window.localStorage.removeItem(DEMO_USER_KEY);
    window.dispatchEvent(new Event("kmitl:demo-auth"));
  } catch {
    /* ignore */
  }
}
