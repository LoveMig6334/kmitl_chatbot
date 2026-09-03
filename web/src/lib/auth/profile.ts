"use client";

/**
 * Legacy `profiles` upsert used by the Phase-1-untouched profile/settings pages.
 * Phase 1 stores the display name in `user_metadata`; this stays until Phase 2 decides
 * whether a profiles table survives.
 */
import { createSupabaseBrowserClient, supabaseConfigured } from "@/lib/supabase/client";
import type { Profile } from "@/lib/store";

export async function saveProfile(profile: Profile) {
  if (!supabaseConfigured) return; // demo — persisted via zustand/localStorage
  const supabase = createSupabaseBrowserClient();
  if (!supabase) return;
  const { data } = await supabase.auth.getUser();
  await supabase.from("profiles").upsert({
    id: data.user?.id,
    full_name: profile.fullName,
    user_name: profile.userName,
    degree: profile.degree,
    faculty: profile.faculty,
    email: profile.email,
  });
}
