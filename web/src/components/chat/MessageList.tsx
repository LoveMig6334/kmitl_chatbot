"use client";

import { useRef } from "react";
import { ArrowDown } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { useTranslation } from "@/providers/LocaleProvider";
import { useAutoScroll } from "@/hooks/useAutoScroll";
import type { ChatMessage } from "@/lib/chat";
import { MessageItem } from "./MessageItem";

export interface MessageListProps {
  messages: ChatMessage[];
  generating: boolean;
  activeSource: { messageId: string; index: number } | null;
  onOpenSource: (messageId: string, index: number) => void;
  onEdit: (messageId: string, text: string) => void;
  onRegenerate: () => void;
  onReadAloud: (message: ChatMessage) => void;
  readingId: string | null;
  mockNotice?: boolean;
}

export function MessageList({
  messages,
  generating,
  activeSource,
  onOpenSource,
  onEdit,
  onRegenerate,
  onReadAloud,
  readingId,
}: MessageListProps) {
  const t = useTranslation();
  const ref = useRef<HTMLDivElement>(null);
  const last = messages[messages.length - 1];
  const { atBottom, scrollToBottom } = useAutoScroll(ref, `${messages.length}:${last?.content.length ?? 0}:${last?.status}`);
  const lastAssistant = [...messages].reverse().find((m) => m.role === "assistant");

  return (
    <div className="relative flex min-h-0 flex-1">
      <div ref={ref} className="flex-1 overflow-y-auto overscroll-contain px-4 py-6">
        <div className="mx-auto flex w-full max-w-3xl flex-col gap-6">
          {messages.map((m, i) => (
            <MessageItem
              key={m.id}
              message={m}
              isLast={i === messages.length - 1}
              generating={generating}
              activeSourceIndex={activeSource?.messageId === m.id ? activeSource.index : null}
              onOpenSource={(idx) => onOpenSource(m.id, idx)}
              onEdit={(text) => onEdit(m.id, text)}
              onRegenerate={onRegenerate}
              onReadAloud={m.role === "assistant" && m.content ? () => onReadAloud(m) : undefined}
              reading={readingId === m.id}
            />
          ))}
        </div>
        {/* screen readers: announce completed answers without re-reading every token */}
        <div className="sr-only" aria-live="polite" aria-atomic="true">
          {lastAssistant?.status === "done" ? lastAssistant.content : ""}
        </div>
      </div>
      {!atBottom && (
        <div className="pointer-events-none absolute inset-x-0 bottom-3 flex justify-center">
          <Button
            variant="outline"
            size="sm"
            className="pointer-events-auto rounded-full shadow-md"
            onClick={() => scrollToBottom()}
          >
            <ArrowDown className="size-3.5" />
            {generating ? t("chat.newAnswer") : t("chat.jumpToLatest")}
          </Button>
        </div>
      )}
    </div>
  );
}
