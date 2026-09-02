export function Avatar({ name, size = 32 }: { name: string; size?: number }) {
  const initial = name?.trim()?.charAt(0)?.toUpperCase() || "?";
  return (
    <span
      className="inline-flex shrink-0 items-center justify-center rounded-full bg-accent text-accent-foreground font-semibold"
      style={{ width: size, height: size, fontSize: size * 0.45 }}
    >
      {initial}
    </span>
  );
}
