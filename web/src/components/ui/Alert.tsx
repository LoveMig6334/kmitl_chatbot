import { AlertCircle, CheckCircle2, Info } from "lucide-react";
import { cn } from "@/lib/cn";

type Variant = "danger" | "success" | "info";

const styles: Record<Variant, string> = {
  danger: "border-danger/30 bg-danger-soft text-danger-hover",
  success: "border-success/30 bg-success-soft text-success",
  info: "border-border bg-bg-subtle text-fg-muted",
};

const icons: Record<Variant, typeof Info> = {
  danger: AlertCircle,
  success: CheckCircle2,
  info: Info,
};

export function Alert({
  variant = "info",
  title,
  children,
  className,
}: {
  variant?: Variant;
  title?: string;
  children?: React.ReactNode;
  className?: string;
}) {
  const Icon = icons[variant];
  return (
    <div
      role={variant === "danger" ? "alert" : "status"}
      className={cn(
        "flex items-start gap-2.5 rounded-md border px-3 py-2.5 text-sm",
        styles[variant],
        className,
      )}
    >
      <Icon className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
      <div className="min-w-0 flex-1">
        {title && <p className="font-medium">{title}</p>}
        {children && <div className={cn(title && "mt-0.5 text-fg-muted")}>{children}</div>}
      </div>
    </div>
  );
}
