"use client";

import { supabaseConfigured } from "./supabase/client";
import { createSupabaseBrowserClient } from "./supabase/client";
import type { Profile } from "./store";

export async function signInWithGoogle() {
  if (!supabaseConfigured) {
    // Demo: simulate a Google sign-in
    return { ok: true, demo: true };
  }
  const supabase = createSupabaseBrowserClient();
  if (!supabase) return { ok: false };
  const { data, error } = await supabase.auth.signInWithOAuth({
    provider: "google",
    options: { redirectTo: `${window.location.origin}/auth/callback` },
  });
  if (error) return { ok: false };
  return { ok: true, demo: false, data };
}

export async function registerWithEmail(email: string, password: string) {
  if (!supabaseConfigured) {
    return { ok: true, demo: true };
  }
  const supabase = createSupabaseBrowserClient();
  if (!supabase) return { ok: false };
  const { error } = await supabase.auth.signUp({ email, password });
  return { ok: !error };
}

export async function signInWithEmail(email: string, password: string) {
  if (!supabaseConfigured) {
    return { ok: true, demo: true };
  }
  const supabase = createSupabaseBrowserClient();
  if (!supabase) return { ok: false };
  const { error } = await supabase.auth.signInWithPassword({ email, password });
  return { ok: !error };
}

export async function saveProfile(profile: Profile) {
  if (!supabaseConfigured) {
    return; // demo — persisted via zustand/localStorage
  }
  const supabase = createSupabaseBrowserClient();
  if (!supabase) return;
  await supabase.from("profiles").upsert({
    id: (await supabase.auth.getUser()).data.user?.id,
    full_name: profile.fullName,
    user_name: profile.userName,
    degree: profile.degree,
    faculty: profile.faculty,
    email: profile.email,
  });
}
