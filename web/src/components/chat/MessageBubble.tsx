"use client";

import { useState } from "react";
import { Check, Copy, Pencil } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { useT } from "@/hooks/useT";
import type { Message } from "@/lib/store";

interface Props {
  msg: Message;
  editing: boolean;
  onStartEdit: () => void;
  onCancelEdit: () => void;
  onSaveEdit: (content: string) => void;
}

export function MessageBubble({
  msg,
  editing,
  onStartEdit,
  onCancelEdit,
  onSaveEdit,
}: Props) {
  const t = useT();
  const [draft, setDraft] = useState(msg.content);
  const [copied, setCopied] = useState(false);
  const isUser = msg.role === "user";

  async function copy() {
    await navigator.clipboard.writeText(msg.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 1200);
  }

  return (
    <div className={`group flex w-full gap-3 ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser && (
        <span className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-accent text-sm text-accent-foreground">
          ✦
        </span>
      )}
      <div className={`flex max-w-[82%] flex-col gap-1 ${isUser ? "items-end" : "items-start"}`}>
        {editing ? (
          <div className="w-full rounded-2xl border border-accent bg-surface p-3">
            <textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              className="w-full resize-none bg-transparent text-sm outline-none"
              rows={Math.max(2, Math.ceil(draft.length / 60))}
            />
            <div className="mt-2 flex justify-end gap-2">
              <Button variant="ghost" onClick={onCancelEdit}>
                {t.cancel}
              </Button>
              <Button onClick={() => onSaveEdit(draft)}>{t.save}</Button>
            </div>
          </div>
        ) : (
          <div
            className={`whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
              isUser ? "bg-accent/25 text-foreground" : "text-foreground bg-surface"
            }`}
          >
            {msg.content}
          </div>
        )}

        <div className="hidden items-center gap-1 text-xs text-muted group-hover:flex">
          {isUser && !editing && (
            <IconBtn title={t.editing} onClick={onStartEdit}>
              <Pencil className="h-3.5 w-3.5" />
            </IconBtn>
          )}
          <IconBtn title={t.save} onClick={copy}>
            {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
          </IconBtn>
        </div>
      </div>
    </div>
  );
}

function IconBtn({
  children,
  title,
  onClick,
}: {
  children: React.ReactNode;
  title: string;
  onClick: () => void;
}) {
  return (
    <button
      title={title}
      onClick={onClick}
      className="grid h-6 w-6 place-items-center rounded-md text-muted transition-colors hover:bg-surface-muted hover:text-foreground"
    >
      {children}
    </button>
  );
}
