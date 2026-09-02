"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { useT } from "@/hooks/useT";
import { useAppStore } from "@/lib/store";
import { DEGREES, FACULTIES } from "@/lib/constants";
import { saveProfile } from "@/lib/auth";

export function ProfileForm() {
  const t = useT();
  const router = useRouter();
  const locale = useAppStore((s) => s.locale);
  const setProfile = useAppStore((s) => s.setProfile);
  const profile = useAppStore((s) => s.profile);

  const [fullName, setFullName] = useState(profile.fullName || "");
  const [userName, setUserName] = useState(profile.userName || "");
  const [degree, setDegree] = useState(profile.degree || "");
  const [faculty, setFaculty] = useState(profile.faculty || "");
  const [error, setError] = useState("");

  const degreeOptions = DEGREES.map((d) => ({
    value: d.id,
    label: locale === "th" ? d.th : d.en,
  }));
  const facultyOptions = FACULTIES.map((f) => ({
    value: f.id,
    label: locale === "th" ? f.th : f.en,
  }));

  async function submit() {
    if (!fullName || !userName || !degree || !faculty) {
      setError(t.fullName);
      return;
    }
    setError("");
    const next = { ...profile, fullName, userName, degree, faculty, authed: true };
    setProfile(next);
    await saveProfile(next);
    router.push("/chat");
  }

  return (
    <div className="w-full max-w-sm rounded-2xl border border-border bg-surface p-8 shadow-sm">
      <h1 className="mb-6 text-center text-3xl font-semibold tracking-tight">
        {t.createProfile}
      </h1>
      <div className="flex flex-col gap-3.5">
        <Input
          label={t.fullName}
          id="fullName"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          placeholder={t.namePlaceholder}
        />
        <Input
          label={t.userName}
          id="userName"
          value={userName}
          onChange={(e) => setUserName(e.target.value)}
          placeholder={t.userName}
        />
        <Select
          label={t.degree}
          id="degree"
          value={degree}
          onChange={(e) => setDegree(e.target.value)}
          options={degreeOptions}
          placeholder={t.degree}
        />
        <Select
          label={t.faculty}
          id="faculty"
          value={faculty}
          onChange={(e) => setFaculty(e.target.value)}
          options={facultyOptions}
          placeholder={t.faculty}
        />
        {error && <p className="text-xs text-red-500">{error}</p>}
        <Button className="mt-1 w-full" onClick={submit}>
          {t.continue}
        </Button>
      </div>
    </div>
  );
}
