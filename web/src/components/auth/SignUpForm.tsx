"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { GoogleButton } from "./GoogleButton";
import { useT } from "@/hooks/useT";
import { registerWithEmail } from "@/lib/auth";

export function SignUpForm() {
  const t = useT();
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");

  async function submit() {
    if (!email || !password) {
      setError(t.email);
      return;
    }
    if (password.length < 6) {
      setError(t.password);
      return;
    }
    if (password !== confirm) {
      setError(t.password);
      return;
    }
    setError("");
    const res = await registerWithEmail(email, password);
    if (!res.ok) {
      setError(t.email);
      return;
    }
    router.push("/profile");
  }

  return (
    <div className="w-full max-w-sm rounded-2xl border border-border bg-surface p-8 shadow-sm">
      <h1 className="mb-6 text-center text-3xl font-semibold tracking-tight">
        {t.signUp}
      </h1>
      <div className="flex flex-col gap-3.5">
        <Input
          label={t.email}
          id="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder={t.emailPlaceholder}
        />
        <Input
          label={t.password}
          id="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder={t.passwordPlaceholder}
        />
        <Input
          label={t.confirmPassword}
          id="confirm"
          type="password"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          placeholder={t.passwordPlaceholder}
        />
        {error && <p className="text-xs text-red-500">{error}</p>}
        <Button className="mt-1 w-full" onClick={submit}>
          {t.signUp}
        </Button>
        <GoogleButton />
        <p className="mt-2 text-center text-xs text-muted">
          {t.haveAccount}{" "}
          <Link href="/login" className="font-medium text-foreground underline-offset-2 hover:underline">
            {t.login}
          </Link>
        </p>
      </div>
    </div>
  );
}
