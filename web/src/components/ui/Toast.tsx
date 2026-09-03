"use client";

import { createContext, useCallback, useContext, useMemo, useState } from "react";
import { AlertCircle, CheckCircle2, Info, X } from "lucide-react";
import { Toast as Radix } from "radix-ui";
import { cn, uid } from "@/lib/cn";
import { useTranslation } from "@/providers/LocaleProvider";

export type ToastVariant = "info" | "success" | "danger";

export interface ToastOptions {
  title: string;
  description?: string;
  variant?: ToastVariant;
  durationMs?: number;
}

interface ToastItem extends ToastOptions {
  id: string;
}

interface ToastContextValue {
  toast: (options: ToastOptions) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

const icons: Record<ToastVariant, typeof Info> = {
  info: Info,
  success: CheckCircle2,
  danger: AlertCircle,
};

const iconColor: Record<ToastVariant, string> = {
  info: "text-fg-muted",
  success: "text-success",
  danger: "text-danger",
};

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const t = useTranslation();

  const toast = useCallback((options: ToastOptions) => {
    setItems((list) => [...list.slice(-3), { id: uid("toast"), ...options }]);
  }, []);

  const remove = useCallback((id: string) => {
    setItems((list) => list.filter((item) => item.id !== id));
  }, []);

  const value = useMemo(() => ({ toast }), [toast]);

  return (
    <ToastContext.Provider value={value}>
      <Radix.Provider swipeDirection="right" duration={4000}>
        {children}
        {items.map((item) => {
          const variant = item.variant ?? "info";
          const Icon = icons[variant];
          return (
            <Radix.Root
              key={item.id}
              duration={item.durationMs}
              onOpenChange={(open) => !open && remove(item.id)}
              className={cn(
                "relative flex items-start gap-3 rounded-lg border border-border bg-surface p-4 pr-10 text-fg shadow-lg",
                "data-[swipe=move]:translate-x-[var(--radix-toast-swipe-move-x)] data-[swipe=end]:translate-x-full data-[swipe=end]:opacity-0",
              )}
            >
              <Icon className={cn("mt-0.5 size-4 shrink-0", iconColor[variant])} aria-hidden="true" />
              <div className="min-w-0 flex-1">
                <Radix.Title className="text-sm font-medium">{item.title}</Radix.Title>
                {item.description && (
                  <Radix.Description className="mt-0.5 text-sm text-fg-muted">
                    {item.description}
                  </Radix.Description>
                )}
              </div>
              <Radix.Close
                className="focus-ring absolute right-2 top-2 inline-flex size-7 items-center justify-center rounded-md text-fg-subtle transition-colors hover:bg-surface-hover hover:text-fg"
                aria-label={t("common.close")}
              >
                <X className="size-3.5" />
              </Radix.Close>
            </Radix.Root>
          );
        })}
        <Radix.Viewport label={t("toast.region")} className="fixed bottom-0 right-0 z-[100] flex w-full max-w-sm flex-col gap-2 p-4 outline-none" />
      </Radix.Provider>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used inside <ToastProvider>");
  return ctx;
}
