import { ProfileForm } from "@/components/auth/ProfileForm";
import { LanguageToggle } from "@/components/LanguageToggle";
import { ThemeToggle } from "@/components/ThemeToggle";

export const metadata = { title: "Profile" };

/** Legacy profile step (no longer part of sign-up); revisited in Phase 2. */
export default function ProfilePage() {
  return (
    <div className="flex min-h-dvh flex-col items-center justify-center gap-6 bg-bg-subtle px-4">
      <div className="flex w-full max-w-sm items-center justify-end gap-2">
        <LanguageToggle />
        <ThemeToggle />
      </div>
      <ProfileForm />
    </div>
  );
}
