"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { useT } from "@/hooks/useT";
import { useAppStore } from "@/lib/store";
import { DEGREES, FACULTIES } from "@/lib/constants";
import { saveProfile } from "@/lib/auth";

export function EditableProfile() {
  const t = useT();
  const locale = useAppStore((s) => s.locale);
  const profile = useAppStore((s) => s.profile);
  const setProfile = useAppStore((s) => s.setProfile);

  const [fullName, setFullName] = useState(profile.fullName);
  const [userName, setUserName] = useState(profile.userName);
  const [email, setEmail] = useState(profile.email);
  const [degree, setDegree] = useState(profile.degree);
  const [faculty, setFaculty] = useState(profile.faculty);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);

  const degreeOptions = DEGREES.map((d) => ({
    value: d.id,
    label: locale === "th" ? d.th : d.en,
  }));
  const facultyOptions = FACULTIES.map((f) => ({
    value: f.id,
    label: locale === "th" ? f.th : f.en,
  }));

  async function submit() {
    if (!fullName || !userName) {
      setError(t.fullName);
      return;
    }
    setError("");
    const next = { ...profile, fullName, userName, email, degree, faculty, authed: true };
    setProfile(next);
    await saveProfile(next);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  return (
    <div className="flex flex-col gap-3.5">
      <Input
        label={t.fullName}
        id="edit-fullName"
        value={fullName}
        onChange={(e) => setFullName(e.target.value)}
        placeholder={t.namePlaceholder}
      />
      <Input
        label={t.userName}
        id="edit-userName"
        value={userName}
        onChange={(e) => setUserName(e.target.value)}
        placeholder={t.userName}
      />
      <Input
        label={t.email}
        id="edit-email"
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder={t.emailPlaceholder}
      />
      <Select
        label={t.degree}
        id="edit-degree"
        value={degree}
        onChange={(e) => setDegree(e.target.value)}
        options={degreeOptions}
        placeholder={t.degree}
      />
      <Select
        label={t.faculty}
        id="edit-faculty"
        value={faculty}
        onChange={(e) => setFaculty(e.target.value)}
        options={facultyOptions}
        placeholder={t.faculty}
      />
      {error && <p className="text-xs text-red-500">{error}</p>}
      <div className="flex items-center gap-3">
        <Button onClick={submit}>{t.saveChanges}</Button>
        {saved && <span className="text-xs font-medium text-accent">{t.saved}</span>}
      </div>
    </div>
  );
}
