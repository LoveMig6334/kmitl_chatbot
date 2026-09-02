"use client";

import { useAppStore } from "@/lib/store";
import { useT } from "@/hooks/useT";
import { FACULTIES } from "@/lib/constants";

export function FacultyScope() {
  const t = useT();
  const locale = useAppStore((s) => s.locale);
  const scope = useAppStore((s) => s.facultyScope);
  const setScope = useAppStore((s) => s.setFacultyScope);

  function toggle(id: string) {
    setScope(
      scope.includes(id) ? scope.filter((s) => s !== id) : [...scope, id],
    );
  }

  return (
    <div className="flex flex-wrap gap-1.5">
      <button
        onClick={() => setScope([])}
        className={`rounded-full px-2.5 py-1 text-xs font-medium transition-colors ${
          scope.length === 0
            ? "bg-accent text-accent-foreground"
            : "bg-surface-muted text-muted hover:text-foreground"
        }`}
      >
        {t.selectAll}
      </button>
      {FACULTIES.map((f) => {
        const checked = scope.includes(f.id);
        const label = locale === "th" ? f.th : f.en;
        return (
          <button
            key={f.id}
            onClick={() => toggle(f.id)}
            className={`rounded-full px-2.5 py-1 text-xs font-medium transition-colors ${
              checked
                ? "bg-accent text-accent-foreground"
                : "bg-surface-muted text-muted hover:text-foreground"
            }`}
          >
            {label}
          </button>
        );
      })}
    </div>
  );
}
