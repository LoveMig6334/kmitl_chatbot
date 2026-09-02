import { ThemeToggle } from "@/components/ThemeToggle";
import { LanguageToggle } from "@/components/LanguageToggle";

export function AuthShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-dvh flex-col items-center justify-center gap-6 bg-background px-4">
      <div className="flex w-full max-w-sm items-center justify-end gap-2">
        <LanguageToggle />
        <ThemeToggle />
      </div>
      {children}
    </div>
  );
}
