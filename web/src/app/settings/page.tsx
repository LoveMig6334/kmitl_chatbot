import { SettingsPanel } from "@/components/settings/SettingsPanel";
import { ThemeSync } from "@/components/ThemeSync";

export const metadata = { title: "Settings" };

export default async function SettingsPage({
  searchParams,
}: {
  searchParams: Promise<{ section?: string }>;
}) {
  const { section } = await searchParams;
  const valid = section === "language" || section === "settings" ? section : "profile";

  return (
    <>
      <ThemeSync />
      <SettingsPanel initialSection={valid} />
    </>
  );
}
