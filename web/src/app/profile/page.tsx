import { ProfileForm } from "@/components/auth/ProfileForm";
import { AuthShell } from "@/components/auth/AuthShell";

export const metadata = { title: "Profile" };

export default function ProfilePage() {
  return (
    <AuthShell>
      <ProfileForm />
    </AuthShell>
  );
}
