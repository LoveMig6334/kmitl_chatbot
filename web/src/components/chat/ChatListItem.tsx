"use client";

import { useState } from "react";
import Link from "next/link";
import { MoreHorizontal, Pencil, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/Dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/DropdownMenu";
import { useTranslation } from "@/providers/LocaleProvider";
import type { Chat } from "@/lib/chat";
import { cn } from "@/lib/cn";

export function ChatListItem({
  chat,
  active,
  onRename,
  onDelete,
  onNavigate,
}: {
  chat: Chat;
  active: boolean;
  onRename: (title: string) => void;
  onDelete: () => void;
  onNavigate?: () => void;
}) {
  const t = useTranslation();
  const [dialog, setDialog] = useState<"rename" | "delete" | null>(null);
  const [title, setTitle] = useState(chat.title);
  const label = chat.title || t("chat.untitled");

  return (
    <li className={cn("group relative flex items-center rounded-md", active ? "bg-surface-hover" : "hover:bg-surface-hover")}>
      <Link
        href={`/chat/${chat.id}`}
        onClick={onNavigate}
        aria-current={active ? "page" : undefined}
        className="focus-ring min-w-0 flex-1 truncate rounded-md py-2 pl-3 pr-9 text-sm text-fg"
        title={label}
      >
        {label}
      </Link>
      <DropdownMenu>
        <DropdownMenuTrigger
          aria-label={t("chat.menu")}
          className={cn(
            "focus-ring absolute right-1 top-1/2 inline-flex size-7 -translate-y-1/2 items-center justify-center rounded-sm text-fg-muted transition-opacity hover:bg-border hover:text-fg",
            "opacity-100 sm:opacity-0 sm:group-hover:opacity-100 sm:focus-visible:opacity-100 sm:data-[state=open]:opacity-100",
            active && "sm:opacity-100",
          )}
        >
          <MoreHorizontal className="size-4" />
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-44">
          <DropdownMenuItem
            onSelect={() => {
              setTitle(chat.title);
              setDialog("rename");
            }}
          >
            <Pencil className="size-4 text-fg-muted" /> {t("chat.rename")}
          </DropdownMenuItem>
          <DropdownMenuItem destructive onSelect={() => setDialog("delete")}>
            <Trash2 className="size-4" /> {t("chat.delete")}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <Dialog open={dialog === "rename"} onOpenChange={(o) => !o && setDialog(null)}>
        <DialogContent>
          <form
            className="flex flex-col gap-4"
            onSubmit={(e) => {
              e.preventDefault();
              if (title.trim()) onRename(title.trim());
              setDialog(null);
            }}
          >
            <DialogHeader>
              <DialogTitle>{t("chat.renameTitle")}</DialogTitle>
            </DialogHeader>
            <Input label={t("chat.renameLabel")} value={title} onChange={(e) => setTitle(e.target.value)} autoFocus maxLength={120} />
            <DialogFooter>
              <Button variant="ghost" onClick={() => setDialog(null)}>
                {t("common.cancel")}
              </Button>
              <Button type="submit" disabled={!title.trim()}>
                {t("chat.save")}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={dialog === "delete"} onOpenChange={(o) => !o && setDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("chat.deleteTitle")}</DialogTitle>
            <DialogDescription>{t("chat.deleteBody", { title: label })}</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setDialog(null)}>
              {t("common.cancel")}
            </Button>
            <Button
              variant="destructive"
              onClick={() => {
                setDialog(null);
                onDelete();
              }}
            >
              {t("chat.deleteConfirm")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </li>
  );
}
