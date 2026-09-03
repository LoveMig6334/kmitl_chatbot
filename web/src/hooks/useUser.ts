"use client";

import { useEffect, useState } from "react";
import type { User } from "@supabase/supabase-js";
import { createSupabaseBrowserClient, supabaseConfigured } from "@/lib/supabase/client";
import { readDemoUser } from "@/lib/auth/demo";

export interface AppUser {
  id: string;
  email: string | null;
  displayName: string;
  avatarUrl: string | null;
}

export function toAppUser(user: User): AppUser {
  const meta = (user.user_metadata ?? {}) as Record<string, unknown>;
  const pick = (key: string) => (typeof meta[key] === "string" ? (meta[key] as string) : "");
  const displayName =
    pick("display_name") || pick("full_name") || pick("name") || user.email?.split("@")[0] || "";
  return {
    id: user.id,
    email: user.email ?? null,
    displayName,
    avatarUrl: pick("avatar_url") || pick("picture") || null,
  };
}

interface UseUserState {
  user: AppUser | null;
  /** True until the first session lookup resolves. */
  loading: boolean;
  demo: boolean;
}

/** Current signed-in user (Supabase session, or the simulated demo user without keys). */
export function useUser(): UseUserState {
  const [state, setState] = useState<UseUserState>({
    user: null,
    loading: true,
    demo: !supabaseConfigured,
  });

  useEffect(() => {
    if (!supabaseConfigured) {
      const sync = () => {
        const demo = readDemoUser();
        setState({
          user: demo
            ? { id: "demo", email: demo.email, displayName: demo.displayName, avatarUrl: null }
            : null,
          loading: false,
          demo: true,
        });
      };
      sync();
      window.addEventListener("kmitl:demo-auth", sync);
      window.addEventListener("storage", sync);
      return () => {
        window.removeEventListener("kmitl:demo-auth", sync);
        window.removeEventListener("storage", sync);
      };
    }

    const supabase = createSupabaseBrowserClient();
    if (!supabase) return;
    let cancelled = false;
    supabase.auth.getUser().then(({ data }) => {
      if (!cancelled) setState({ user: data.user ? toAppUser(data.user) : null, loading: false, demo: false });
    });
    const { data: sub } = supabase.auth.onAuthStateChange((_event, session) => {
      setState({ user: session?.user ? toAppUser(session.user) : null, loading: false, demo: false });
    });
    return () => {
      cancelled = true;
      sub.subscription.unsubscribe();
    };
  }, []);

  return state;
}
