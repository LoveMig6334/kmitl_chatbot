import { createSupabaseBrowserClient, supabaseConfigured } from "@/lib/supabase/client";
import { mapAuthError, type AuthErrorCode } from "./errors";
import { AFTER_LOGIN_PATH } from "./routes";
import { clearDemoUser, setDemoUser } from "./demo";

export { mapAuthError, authErrorKey, isAuthErrorCode, type AuthErrorCode } from "./errors";
export * from "./validation";
export * from "./routes";
export * from "./demo";

export type AuthResult =
  | { ok: true; demo?: boolean; needsConfirmation?: boolean }
  | { ok: false; code: AuthErrorCode };

function fail(error: unknown): AuthResult {
  return { ok: false, code: mapAuthError(error) };
}

function client() {
  const supabase = createSupabaseBrowserClient();
  if (!supabase) throw new Error("Supabase is not configured");
  return supabase;
}

function origin() {
  return window.location.origin;
}

export async function signInWithGoogle(next: string = AFTER_LOGIN_PATH): Promise<AuthResult> {
  if (!supabaseConfigured) {
    setDemoUser({ email: "student@example.com", displayName: "Demo Student" });
    return { ok: true, demo: true };
  }
  try {
    const { error } = await client().auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${origin()}/auth/callback?flow=oauth&next=${encodeURIComponent(next)}`,
        queryParams: { prompt: "select_account" },
      },
    });
    if (error) return fail(error);
    return { ok: true }; // the browser is being redirected to Google
  } catch (error) {
    return fail(error);
  }
}

export async function signInWithEmail(email: string, password: string): Promise<AuthResult> {
  if (!supabaseConfigured) {
    setDemoUser({ email, displayName: email.split("@")[0] });
    return { ok: true, demo: true };
  }
  try {
    const { error } = await client().auth.signInWithPassword({ email: email.trim(), password });
    if (error) return fail(error);
    return { ok: true };
  } catch (error) {
    return fail(error);
  }
}

export async function signUpWithEmail(
  displayName: string,
  email: string,
  password: string,
): Promise<AuthResult> {
  if (!supabaseConfigured) {
    setDemoUser({ email, displayName });
    return { ok: true, demo: true };
  }
  try {
    const { data, error } = await client().auth.signUp({
      email: email.trim(),
      password,
      options: {
        data: { display_name: displayName.trim(), full_name: displayName.trim() },
        emailRedirectTo: `${origin()}/auth/callback?flow=confirm&next=${encodeURIComponent(AFTER_LOGIN_PATH)}`,
      },
    });
    if (error) return fail(error);
    // With email confirmation on, Supabase returns a user with no identities for an
    // address that already exists (to avoid leaking whether it is registered).
    if (data.user && data.user.identities && data.user.identities.length === 0) {
      return { ok: false, code: "user_exists" };
    }
    return { ok: true, needsConfirmation: !data.session };
  } catch (error) {
    return fail(error);
  }
}

export async function requestPasswordReset(email: string): Promise<AuthResult> {
  if (!supabaseConfigured) return { ok: true, demo: true };
  try {
    const { error } = await client().auth.resetPasswordForEmail(email.trim(), {
      redirectTo: `${origin()}/auth/callback?flow=reset&next=${encodeURIComponent("/update-password")}`,
    });
    if (error) return fail(error);
    return { ok: true };
  } catch (error) {
    return fail(error);
  }
}

export async function updatePassword(password: string): Promise<AuthResult> {
  if (!supabaseConfigured) return { ok: true, demo: true };
  try {
    const { error } = await client().auth.updateUser({ password });
    if (error) return fail(error);
    return { ok: true };
  } catch (error) {
    return fail(error);
  }
}

/** True when the browser holds a session (used by /update-password to accept the recovery link). */
export async function hasSession(): Promise<boolean> {
  if (!supabaseConfigured) return true;
  try {
    const { data } = await client().auth.getSession();
    return Boolean(data.session);
  } catch {
    return false;
  }
}

export async function signOut(): Promise<AuthResult> {
  if (!supabaseConfigured) {
    clearDemoUser();
    return { ok: true, demo: true };
  }
  try {
    const { error } = await client().auth.signOut();
    if (error) return fail(error);
    return { ok: true };
  } catch (error) {
    return fail(error);
  }
}
