"use client";

import { forwardRef, useState } from "react";
import { Eye, EyeOff } from "lucide-react";
import { useTranslation } from "@/providers/LocaleProvider";
import { Input, type InputProps } from "./Input";
import { Button } from "./Button";

export const PasswordInput = forwardRef<HTMLInputElement, Omit<InputProps, "type" | "trailing">>(
  function PasswordInput(props, ref) {
    const t = useTranslation();
    const [visible, setVisible] = useState(false);
    return (
      <Input
        ref={ref}
        type={visible ? "text" : "password"}
        autoComplete={props.autoComplete ?? "current-password"}
        trailing={
          <Button
            variant="ghost"
            size="icon"
            className="size-8 text-fg-subtle"
            aria-label={visible ? t("common.hidePassword") : t("common.showPassword")}
            onClick={() => setVisible((v) => !v)}
          >
            {visible ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
          </Button>
        }
        {...props}
      />
    );
  },
);
