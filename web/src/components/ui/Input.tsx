import { cn } from "@/lib/cn";

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
}

export function Input({ label, className, id, ...props }: InputProps) {
  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label htmlFor={id} className="text-xs font-medium text-muted">
          {label}
        </label>
      )}
      <input
        id={id}
        className={cn(
          "w-full rounded-lg bg-surface-muted px-3.5 py-2.5 text-sm text-foreground placeholder:text-muted/70 outline-none transition focus:ring-2 focus:ring-accent/60",
          className,
        )}
        {...props}
      />
    </div>
  );
}
