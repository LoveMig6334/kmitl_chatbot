"use client";

import { useState } from "react";
import { AlertTriangle, Check, Copy, Pencil, RotateCcw, Sparkles, Square, Volume2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Tooltip } from "@/components/ui/Tooltip";
import { Alert } from "@/components/ui/Alert";
import { useLocale } from "@/providers/LocaleProvider";
import type { MessageKey } from "@/i18n";
import type { ChatMessage } from "@/lib/chat";
import { cn } from "@/lib/cn";
import { Markdown } from "./Markdown";
import { SourceChips } from "./SourceChips";

export interface MessageItemProps {
  message: ChatMessage;
  isLast: boolean;
  generating: boolean;
  activeSourceIndex: number | null;
  onOpenSource: (index: number) => void;
  onEdit: (text: string) => void;
  onRegenerate: () => void;
  onReadAloud?: () => void;
  reading?: boolean;
}

function errorKey(error: string | null | undefined): MessageKey {
  const e = (error ?? "").toLowerCase();
  if (/rate|429/.test(e)) return "chat.error.rateLimited";
  if (/timeout/.test(e)) return "chat.error.timeout";
  if (/fetch|network|http 5/.test(e)) return "chat.error.network";
  return "chat.error.generic";
}

export function MessageItem({
  message,
  isLast,
  generating,
  activeSourceIndex,
  onOpenSource,
  onEdit,
  onRegenerate,
  onReadAloud,
  reading,
}: MessageItemProps) {
  const { t } = useLocale();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(message.content);
  const [copied, setCopied] = useState(false);
  const isUser = message.role === "user";
  const streaming = message.status === "streaming";

  async function copy() {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard unavailable */
    }
  }

  function startEdit() {
    setDraft(message.content);
    setEditing(true);
  }

  function saveEdit() {
    const text = draft.trim();
    if (!text) return;
    setEditing(false);
    if (text !== message.content) onEdit(text);
  }

  const actionBtn = "size-7 text-fg-subtle hover:text-fg";

  if (isUser) {
    return (
      <div className="group flex flex-col items-end gap-1" data-role="user">
        {editing ? (
          <form
            className="w-full max-w-[85%] rounded-xl border border-border-strong bg-surface p-2 shadow-sm"
            onSubmit={(e) => {
              e.preventDefault();
              saveEdit();
            }}
          >
            <textarea
              autoFocus
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Escape") setEditing(false);
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  saveEdit();
                }
              }}
              rows={Math.min(8, Math.max(2, draft.split("\n").length))}
              aria-label={t("chat.edit")}
              className="focus-ring w-full resize-none rounded-md bg-transparent px-2 py-1 text-sm"
            />
            <div className="mt-1 flex justify-end gap-2">
              <Button variant="ghost" size="sm" onClick={() => setEditing(false)}>
                {t("common.cancel")}
              </Button>
              <Button type="submit" size="sm" disabled={!draft.trim()}>
                {t("chat.editSave")}
              </Button>
            </div>
          </form>
        ) : (
          <div className="max-w-[85%] whitespace-pre-wrap break-words rounded-2xl rounded-br-md bg-bg-subtle px-4 py-2.5 text-sm text-fg">
            {message.content}
          </div>
        )}
        {!editing && (
          <div className="flex items-center gap-0.5 opacity-100 transition-opacity sm:opacity-0 sm:group-hover:opacity-100 sm:group-focus-within:opacity-100">
            <Tooltip content={t("chat.edit")}>
              <Button variant="ghost" size="icon" className={actionBtn} onClick={startEdit} disabled={generating} aria-label={t("chat.edit")}>
                <Pencil className="size-3.5" />
              </Button>
            </Tooltip>
            <Tooltip content={copied ? t("chat.copied") : t("chat.copy")}>
              <Button variant="ghost" size="icon" className={actionBtn} onClick={copy} aria-label={t("chat.copy")}>
                {copied ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
              </Button>
            </Tooltip>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="group flex gap-3" data-role="assistant">
      <span className="mt-0.5 inline-flex size-7 shrink-0 items-center justify-center rounded-full bg-accent-soft text-accent">
        <Sparkles className="size-3.5" aria-hidden="true" />
      </span>
      <div className="flex min-w-0 flex-1 flex-col gap-2">
        {message.content ? (
          <Markdown text={message.content} className={cn(streaming && "streaming")} />
        ) : streaming ? (
          <p className="text-sm text-fg-muted" aria-live="polite">
            <span className="inline-flex items-center gap-2">
              <span className="size-2 animate-pulse rounded-full bg-accent" />
              {t("chat.thinking")}
            </span>
          </p>
        ) : null}

        {message.status === "error" && (
          <Alert variant="danger">
            <div className="flex flex-wrap items-center gap-2">
              <span>{t(errorKey(message.error))}</span>
              <Button variant="outline" size="sm" onClick={onRegenerate} disabled={generating}>
                <RotateCcw className="size-3.5" /> {t("chat.retry")}
              </Button>
            </div>
          </Alert>
        )}
        {message.status === "stopped" && (
          <p className="inline-flex items-center gap-1.5 text-xs text-fg-muted">
            <Square className="size-3" aria-hidden="true" /> {t("chat.stopped")}
          </p>
        )}
        {message.status === "done" && message.error === "partial" && (
          <p className="inline-flex items-center gap-1.5 text-xs text-warning">
            <AlertTriangle className="size-3" aria-hidden="true" /> {t("chat.partial")}
          </p>
        )}

        {!streaming && <SourceChips sources={message.sources} activeIndex={activeSourceIndex} onOpen={onOpenSource} />}

        {!streaming && message.content && (
          <div className="flex items-center gap-0.5 opacity-100 transition-opacity sm:opacity-0 sm:group-hover:opacity-100 sm:group-focus-within:opacity-100">
            <Tooltip content={copied ? t("chat.copied") : t("chat.copy")}>
              <Button variant="ghost" size="icon" className={actionBtn} onClick={copy} aria-label={t("chat.copy")}>
                {copied ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
              </Button>
            </Tooltip>
            {isLast && (
              <Tooltip content={t("chat.regenerate")}>
                <Button variant="ghost" size="icon" className={actionBtn} onClick={onRegenerate} disabled={generating} aria-label={t("chat.regenerate")}>
                  <RotateCcw className="size-3.5" />
                </Button>
              </Tooltip>
            )}
            {onReadAloud && (
              <Tooltip content={reading ? t("chat.stopReading") : t("chat.readAloud")}>
                <Button
                  variant="ghost"
                  size="icon"
                  className={cn(actionBtn, reading && "text-accent")}
                  onClick={onReadAloud}
                  aria-label={reading ? t("chat.stopReading") : t("chat.readAloud")}
                  aria-pressed={reading}
                >
                  {reading ? <Square className="size-3.5" /> : <Volume2 className="size-3.5" />}
                </Button>
              </Tooltip>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
