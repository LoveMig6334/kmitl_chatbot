"use client";

import { useCallback, useMemo, useState } from "react";
import { Dialog as RadixDialog } from "radix-ui";
import { PanelLeftOpen, SquarePen } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Tooltip } from "@/components/ui/Tooltip";
import { Alert } from "@/components/ui/Alert";
import { useLocale } from "@/providers/LocaleProvider";
import { useChatController } from "@/hooks/useChatController";
import { usePageTitle } from "@/hooks/usePageTitle";
import { useSpeechSynthesis } from "@/hooks/useSpeechSynthesis";
import { useSidebarLayout } from "@/hooks/useSidebarLayout";
import type { ChatMessage } from "@/lib/chat";
import { cn } from "@/lib/cn";
import { ChatSidebar } from "./ChatSidebar";
import { Composer } from "./Composer";
import { EmptyState } from "./EmptyState";
import { MessageList } from "./MessageList";
import { SettingsDialog } from "./SettingsDialog";
import { SourcePanel } from "./SourcePanel";

export function ChatApp({ chatId }: { chatId: string | null }) {
  const { locale, t } = useLocale();
  usePageTitle("chat.pageTitle");
  const chat = useChatController(chatId);
  const layout = useSidebarLayout();
  const tts = useSpeechSynthesis();

  const [drawerOpen, setDrawerOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [seed, setSeed] = useState<{ text: string; nonce: number } | null>(null);
  const [sourceState, setSourceState] = useState<{ chatId: string | null; messageId: string; index: number } | null>(null);
  // The panel only applies to the chat it was opened in and while its message still exists.
  const source = sourceState && sourceState.chatId === chatId ? sourceState : null;
  const sourceMessage = source ? chat.messages.find((m) => m.id === source.messageId) ?? null : null;
  const setSource = useCallback(
    (next: { messageId: string; index: number } | null) => setSourceState(next ? { ...next, chatId } : null),
    [chatId],
  );

  const pastQuestions = useMemo(
    () => chat.messages.filter((m) => m.role === "user").map((m) => m.content),
    [chat.messages],
  );

  const readAloud = useCallback(
    (m: ChatMessage) => {
      if (tts.speakingId === m.id) tts.cancel();
      else tts.speak(m.id, m.content, locale === "th" ? "th-TH" : "en-US");
    },
    [tts, locale],
  );

  const sidebar = (
    <ChatSidebar
      chats={chat.chats}
      activeId={chatId}
      ready={chat.ready}
      loadError={chat.loadError}
      onRename={chat.renameChat}
      onDelete={(id) => void chat.deleteChat(id)}
      onCollapse={layout.collapse}
      onNavigate={() => setDrawerOpen(false)}
      onOpenSettings={() => setSettingsOpen(true)}
    />
  );

  const panel = sourceMessage && source && sourceMessage.sources.length > 0 && (
    <SourcePanel
      sources={sourceMessage.sources}
      activeIndex={source.index}
      onSelect={(index) => setSource({ messageId: sourceMessage.id, index })}
      onClose={() => setSource(null)}
    />
  );

  return (
    <div className="flex h-dvh w-full overflow-hidden bg-bg text-fg">
      {/* desktop sidebar: resizable, collapsible */}
      <aside
        className={cn("relative hidden shrink-0 md:block", layout.collapsed && "md:hidden")}
        style={{ width: layout.width }}
      >
        {sidebar}
        <div
          role="separator"
          aria-orientation="vertical"
          aria-label={t("chat.resizeSidebar")}
          aria-valuenow={layout.width}
          aria-valuemin={layout.min}
          aria-valuemax={layout.max}
          tabIndex={0}
          onPointerDown={layout.startResize}
          onKeyDown={layout.onResizeKey}
          className="focus-ring absolute inset-y-0 -right-1 z-10 w-2 cursor-col-resize hover:bg-accent/30 active:bg-accent/40"
        />
      </aside>

      {/* mobile drawer */}
      <RadixDialog.Root open={drawerOpen} onOpenChange={setDrawerOpen}>
        <RadixDialog.Portal>
          <RadixDialog.Overlay className="fixed inset-0 z-40 bg-overlay md:hidden" />
          <RadixDialog.Content className="fixed inset-y-0 left-0 z-50 w-[85vw] max-w-xs border-r border-border shadow-lg outline-none md:hidden">
            <RadixDialog.Title className="sr-only">{t("chat.history")}</RadixDialog.Title>
            {sidebar}
          </RadixDialog.Content>
        </RadixDialog.Portal>
      </RadixDialog.Root>

      <main className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-12 shrink-0 items-center gap-1 border-b border-border px-2">
          <Tooltip content={t("chat.openSidebar")}>
            <Button
              variant="ghost"
              size="icon"
              className={cn("size-8", !layout.collapsed && "md:hidden")}
              aria-label={t("chat.openSidebar")}
              onClick={() => {
                if (window.matchMedia("(min-width: 768px)").matches) layout.expand();
                else setDrawerOpen(true);
              }}
            >
              <PanelLeftOpen className="size-4" />
            </Button>
          </Tooltip>
          <Tooltip content={t("chat.newChat")}>
            <Button asChild variant="ghost" size="icon" className={cn("size-8", !layout.collapsed && "md:hidden")} aria-label={t("chat.newChat")}>
              <Link href="/chat">
                <SquarePen className="size-4" />
              </Link>
            </Button>
          </Tooltip>
          <h1 className="min-w-0 flex-1 truncate px-2 text-sm font-medium">
            {chat.activeChat?.title || t("chat.newChat")}
          </h1>
        </header>

        <div className="flex min-h-0 flex-1">
          <div className="flex min-w-0 flex-1 flex-col">
            {chatId && !chat.ready ? (
              <div className="flex-1" />
            ) : chat.messages.length === 0 ? (
              <div className="flex-1 overflow-y-auto">
                <EmptyState onPick={(text) => setSeed({ text, nonce: Date.now() })} />
              </div>
            ) : (
              <MessageList
                messages={chat.messages}
                generating={chat.generating !== null}
                activeSource={source}
                onOpenSource={(messageId, index) => setSource({ messageId, index })}
                onEdit={(id, text) => void chat.editAndResend(id, text)}
                onRegenerate={() => void chat.regenerate()}
                onReadAloud={readAloud}
                readingId={tts.speakingId}
              />
            )}
            <div className="shrink-0 px-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] pt-1">
              <div className="mx-auto w-full max-w-3xl">
                {chat.messages.some((m) => m.status === "streaming") && chat.generating === null && (
                  <Alert variant="info" className="mb-2">{t("chat.partial")}</Alert>
                )}
                <Composer
                  onSend={(text) => void chat.send(text)}
                  onStop={chat.stop}
                  generating={chat.generating !== null}
                  scope={chat.scope}
                  onScopeChange={chat.setScope}
                  pastQuestions={pastQuestions}
                  seed={seed}
                />
              </div>
            </div>
          </div>

          {panel && (
            <>
              <aside className="hidden w-[26rem] shrink-0 border-l border-border lg:block">{panel}</aside>
              <RadixDialog.Root open onOpenChange={(o) => !o && setSource(null)}>
                <RadixDialog.Portal>
                  <RadixDialog.Overlay className="fixed inset-0 z-40 bg-overlay lg:hidden" />
                  <RadixDialog.Content className="fixed inset-y-0 right-0 z-50 w-full max-w-md border-l border-border shadow-lg outline-none lg:hidden">
                    <RadixDialog.Title className="sr-only">{t("chat.sourcesTitle")}</RadixDialog.Title>
                    {panel}
                  </RadixDialog.Content>
                </RadixDialog.Portal>
              </RadixDialog.Root>
            </>
          )}
        </div>
      </main>

      <SettingsDialog open={settingsOpen} onOpenChange={setSettingsOpen} />
    </div>
  );
}
