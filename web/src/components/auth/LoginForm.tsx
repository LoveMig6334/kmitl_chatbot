"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { GoogleButton } from "./GoogleButton";
import { useT } from "@/hooks/useT";
import { useAppStore } from "@/lib/store";
import { signInWithEmail } from "@/lib/auth";

export function LoginForm() {
  const t = useT();
  const router = useRouter();
  const setProfile = useAppStore((s) => s.setProfile);
  const profile = useAppStore((s) => s.profile);

  const [cred, setCred] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function submit() {
    if (!cred || !password) {
      setError(t.login);
      return;
    }
    setError("");
    const res = await signInWithEmail(cred, password);
    if (!res.ok) {
      setError(t.login);
      return;
    }
    setProfile({
      email: cred.includes("@") ? cred : profile.email,
      userName: profile.userName,
      authed: true,
    });
    router.push("/chat");
  }

  return (
    <div className="w-full max-w-sm rounded-2xl border border-border bg-surface p-8 shadow-sm">
      <h1 className="mb-6 text-center text-3xl font-semibold tracking-tight">
        {t.login}
      </h1>
      <div className="flex flex-col gap-3.5">
        <Input
          label={t.userName}
          id="cred"
          value={cred}
          onChange={(e) => setCred(e.target.value)}
          placeholder={t.userName}
        />
        <Input
          label={t.password}
          id="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder={t.passwordPlaceholder}
        />
        {error && <p className="text-xs text-red-500">{error}</p>}
        <Button className="mt-1 w-full" onClick={submit}>
          {t.login}
        </Button>
        <GoogleButton />
        <p className="mt-2 text-center text-xs text-muted">
          {t.noAccount}{" "}
          <Link href="/signup" className="font-medium text-foreground underline-offset-2 hover:underline">
            {t.signUp}
          </Link>
        </p>
      </div>
    </div>
  );
}
