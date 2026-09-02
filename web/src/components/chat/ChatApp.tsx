"use client";

import { useEffect, useRef, useState } from "react";
import { useAppStore } from "@/lib/store";
import type { Message } from "@/lib/store";
import { uid } from "@/lib/cn";
import { useT } from "@/hooks/useT";
import { Sidebar } from "./Sidebar";
import { Composer } from "./Composer";
import { MessageBubble } from "./MessageBubble";
import { ThemeToggle } from "@/components/ThemeToggle";

export function ChatApp() {
  const t = useT();
  const {
    profile,
    sessions,
    activeSessionId,
    facultyScope,
    newChat,
    selectSession,
    addMessage,
    updateMessage,
    deleteSession,
    setGenerating,
  } = useAppStore();

  const active = sessions.find((s) => s.id === activeSessionId) ?? sessions[0];
  const [generating, setGen] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const id = requestAnimationFrame(() => setMounted(true));
    return () => cancelAnimationFrame(id);
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [active?.messages.length, generating]);

  async function ensureSession(): Promise<string> {
    if (active) return active.id;
    return newChat();
  }

  async function onSend(text: string) {
    const sessionId = await ensureSession();
    const userMsg: Message = { id: uid("u"), role: "user", content: text };
    const asstMsg: Message = { id: uid("a"), role: "assistant", content: "" };
    addMessage(sessionId, userMsg);
    setGen(true);
    setGenerating(true);

    const controller = new AbortController();
    abortRef.current = controller;

    const history = [...(sessions.find((s) => s.id === sessionId)?.messages ?? []), userMsg];
    let acc = "";
    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: history.map((m) => ({ role: m.role, content: m.content })),
          facultyScope,
        }),
        signal: controller.signal,
      });

      if (!res.body) throw new Error("No stream");
      addMessage(sessionId, asstMsg);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split("\n\n");
        buffer = events.pop() ?? "";
        for (const ev of events) {
          const line = ev.split("\n").find((l) => l.startsWith("data:"));
          if (!line) continue;
          const payload = JSON.parse(line.slice(5).trim());
          if (payload.error) {
            acc += " [error]";
            continue;
          }
          if (payload.done) {
            continue;
          }
          if (payload.delta) {
            acc += payload.delta;
            updateMessage(sessionId, asstMsg.id, acc);
          }
        }
      }
    } catch {
      updateMessage(
        sessionId,
        asstMsg.id,
        acc === "" ? `⚠ ${t.stop}` : acc,
      );
    } finally {
      setGen(false);
      setGenerating(false);
      abortRef.current = null;
    }
  }

  function onStop() {
    abortRef.current?.abort();
    setGen(false);
    setGenerating(false);
  }

  function onSaveEdit(msgId: string, content: string) {
    if (!active) return;
    updateMessage(active.id, msgId, content);
    setEditingId(null);
  }

  const name = profile.fullName || t.student;

  if (!mounted) {
    return (
      <div className="flex h-dvh w-full items-center justify-center bg-background">
        <span className="text-sm text-muted">Loading…</span>
      </div>
    );
  }

  return (
    <div className="flex h-dvh w-full bg-background">
      <Sidebar
        onNewChat={() => newChat()}
        sessions={sessions}
        activeId={active?.id ?? null}
        onSelect={selectSession}
        onDelete={deleteSession}
      />

      <main className="flex flex-1 flex-col min-w-0 p-4">
        <div className="flex items-center justify-end gap-2">
          <ThemeToggle />
        </div>

        <div ref={scrollRef} className="flex-1 overflow-y-auto pb-4">
          {active && active.messages.length > 0 ? (
            <div className="mx-auto flex max-w-2xl flex-col gap-4">
              {active.messages.map((msg) => (
                <MessageBubble
                  key={msg.id}
                  msg={msg}
                  editing={editingId === msg.id}
                  onStartEdit={() => setEditingId(msg.id)}
                  onCancelEdit={() => setEditingId(null)}
                  onSaveEdit={(c) => onSaveEdit(msg.id, c)}
                />
              ))}
            </div>
          ) : (
            <div className="flex h-full items-center justify-center">
              <h1 className="text-center text-3xl font-semibold tracking-tight">
                {t.helloJumpIn}{" "}
                <span className="text-muted">{name}</span>
              </h1>
            </div>
          )}
        </div>

        <div className="mx-auto w-full max-w-2xl pb-2">
          <Composer onSend={onSend} onStop={onStop} generating={generating} />
        </div>
      </main>
    </div>
  );
}
