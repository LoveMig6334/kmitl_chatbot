"use client";

import { useRouter } from "next/navigation";
import { signInWithGoogle } from "@/lib/auth";
import { useAppStore } from "@/lib/store";
import { useT } from "@/hooks/useT";

export function GoogleButton() {
  const t = useT();
  const router = useRouter();
  const setProfile = useAppStore((s) => s.setProfile);

  async function handle() {
    const result = await signInWithGoogle();
    if (!result.ok) return;
    if (result.demo) {
      setProfile({ fullName: "Student", userName: "student", authed: true });
      router.push("/profile");
      return;
    }
    router.push("/auth/callback");
  }

  return (
    <button
      type="button"
      onClick={handle}
      className="flex w-full items-center justify-center gap-3 rounded-full border border-border bg-surface px-5 py-2.5 text-sm font-medium text-foreground transition-colors hover:bg-surface-muted"
    >
      <svg className="h-4 w-4" viewBox="0 0 24 24">
        <path
          fill="#4285F4"
          d="M23.5 12.27c0-.85-.08-1.66-.22-2.45H12v4.64h6.46a5.53 5.53 0 0 1-2.4 3.62v3.01h3.89c2.27-2.09 3.55-5.17 3.55-8.82z"
        />
        <path
          fill="#34A853"
          d="M12 24c3.24 0 5.96-1.07 7.95-2.91l-3.89-3.01c-1.08.72-2.45 1.15-4.06 1.15-3.13 0-5.78-2.11-6.73-4.95H1.29v3.11A12 12 0 0 0 12 24z"
        />
        <path
          fill="#FBBC05"
          d="M5.27 14.28a7.2 7.2 0 0 1 0-4.56V6.61H1.29a12 12 0 0 0 0 10.78l3.98-3.11z"
        />
        <path
          fill="#EA4335"
          d="M12 4.77c1.76 0 3.34.61 4.59 1.8l3.44-3.44C17.96 1.19 15.24 0 12 0A12 12 0 0 0 1.29 6.61l3.98 3.11C6.22 6.88 8.87 4.77 12 4.77z"
        />
      </svg>
      {t.continueWithGoogle}
    </button>
  );
}
