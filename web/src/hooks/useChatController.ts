"use client";

import { useCallback, useEffect, useMemo, useRef } from "react";
import { useRouter } from "next/navigation";
import { uid } from "@/lib/cn";
import type { ProgramId } from "@/lib/constants";
import {
  autoTitle,
  buildChatPayload,
  getChatRepository,
  initialStreamState,
  parseChatLine,
  readSseJson,
  streamReducer,
  type Chat,
  type ChatMessage,
  type ChatRepository,
  type StreamAction,
  type StreamState,
} from "@/lib/chat";
import { abortChat, clearAborter, registerAborter, useChatStore } from "@/lib/chat/store";
import { useUser } from "./useUser";

export const CHAT_ENDPOINT = "/api/chat";

function newId() {
  return typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : uid("m");
}

/**
 * Everything the chat page does with data: hydrate, send (stream + stop), edit-and-resend
 * (replace semantics), regenerate, rename/delete, per-chat scope. Persists through the
 * ChatRepository; the zustand store is the UI's view of it.
 */
export function useChatController(chatId: string | null) {
  const { user, loading: userLoading } = useUser();
  const router = useRouter();
  const store = useChatStore();
  const repoRef = useRef<ChatRepository | null>(null);

  const repo = useMemo(() => (userLoading ? null : getChatRepository(user?.id ?? null)), [user?.id, userLoading]);
  useEffect(() => {
    repoRef.current = repo;
  }, [repo]);

  // hydrate the chat list once the repository is known
  useEffect(() => {
    if (!repo) return;
    let cancelled = false;
    repo
      .listChats()
      .then((chats) => !cancelled && useChatStore.getState().setHydrated(chats))
      .catch(() => !cancelled && useChatStore.getState().setHydrated([], true));
    return () => {
      cancelled = true;
    };
  }, [repo]);

  // track the active chat and load its messages
  useEffect(() => {
    useChatStore.getState().setActive(chatId);
    if (!repo || !chatId) return;
    if (useChatStore.getState().loadedChats[chatId]) return;
    let cancelled = false;
    repo
      .listMessages(chatId)
      .then((messages) => !cancelled && useChatStore.getState().setMessages(chatId, messages))
      .catch(() => !cancelled && useChatStore.getState().setMessages(chatId, []));
    return () => {
      cancelled = true;
    };
  }, [repo, chatId]);

  const activeChat = chatId ? store.chats.find((c) => c.id === chatId) ?? null : null;
  const messages = chatId ? store.messages[chatId] ?? [] : [];
  const scope = activeChat?.scope ?? store.draftScope;
  const generating = store.generating?.chatId === chatId ? store.generating : null;

  const setScope = useCallback(
    (next: ProgramId[]) => {
      if (activeChat) {
        useChatStore.getState().patchChat(activeChat.id, { scope: next });
        void repoRef.current?.updateScope(activeChat.id, next);
      } else {
        useChatStore.getState().setDraftScope(next);
      }
    },
    [activeChat],
  );

  /** Stream the answer to the last user message of `targetChat`. */
  const run = useCallback(async (targetChat: Chat, userMessage: ChatMessage) => {
    const s = useChatStore.getState();
    const repository = repoRef.current;
    const assistant: ChatMessage = {
      id: newId(),
      chatId: targetChat.id,
      role: "assistant",
      content: "",
      sources: [],
      status: "streaming",
      error: null,
      parentId: userMessage.id,
      createdAt: Date.now(),
    };
    s.upsertMessage(assistant);
    s.setGenerating({ chatId: targetChat.id, messageId: assistant.id });

    const controller = new AbortController();
    registerAborter(targetChat.id, controller);
    let state: StreamState = initialStreamState;
    const apply = (action: StreamAction) => {
      state = streamReducer(state, action);
      useChatStore.getState().upsertMessage({
        ...assistant,
        content: state.content,
        sources: state.sources,
        status: state.status,
        error: state.error,
      });
    };

    try {
      const history = useChatStore.getState().messages[targetChat.id] ?? [];
      const payload = buildChatPayload(history, targetChat.scope, targetChat.id);
      const res = await fetch(CHAT_ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });
      if (!res.ok || !res.body) {
        let message = `HTTP ${res.status}`;
        try {
          const body = await res.json();
          if (typeof body?.error === "string") message = body.error;
        } catch {
          /* no body */
        }
        apply({ type: "error", code: res.status === 429 ? "rate_limited" : `http_${res.status}`, message });
      } else {
        for await (const payloadLine of readSseJson(res.body, controller.signal)) {
          const action = parseChatLine(payloadLine);
          if (action) apply(action);
          if (state.status !== "streaming") break;
        }
        if (state.status === "streaming") {
          apply(controller.signal.aborted ? { type: "stop" } : { type: "done", partial: true });
        }
      }
    } catch (err) {
      if (controller.signal.aborted) apply({ type: "stop" });
      else apply({ type: "error", code: "network", message: err instanceof Error ? err.message : String(err) });
    } finally {
      clearAborter(targetChat.id);
      const final = useChatStore.getState().messages[targetChat.id]?.find((m) => m.id === assistant.id);
      const stillExists = useChatStore.getState().chats.some((c) => c.id === targetChat.id);
      useChatStore.getState().setGenerating(null);
      if (final && repository && stillExists) {
        void repository.saveMessage(final).catch(() => undefined);
        const now = Date.now();
        useChatStore.getState().patchChat(targetChat.id, { updatedAt: now });
        void repository.touchChat(targetChat.id, now).catch(() => undefined);
      }
    }
  }, []);

  const send = useCallback(
    async (text: string) => {
      const content = text.trim();
      if (!content || useChatStore.getState().generating) return;
      const repository = repoRef.current;
      let chat = activeChat;
      if (!chat) {
        const now = Date.now();
        chat = { id: newId(), title: autoTitle(content), scope: useChatStore.getState().draftScope, createdAt: now, updatedAt: now };
        useChatStore.getState().upsertChat(chat);
        useChatStore.getState().setMessages(chat.id, []);
        // The chat row must exist before its first message (FK + RLS on Supabase).
        await repository?.createChat(chat).catch(() => undefined);
        // same page segment for /chat and /chat/<id>, so nothing remounts
        router.replace(`/chat/${chat.id}`);
      }
      const list = useChatStore.getState().messages[chat.id] ?? [];
      const userMessage: ChatMessage = {
        id: newId(),
        chatId: chat.id,
        role: "user",
        content,
        sources: [],
        status: "done",
        error: null,
        parentId: list[list.length - 1]?.id ?? null,
        createdAt: Date.now(),
      };
      useChatStore.getState().upsertMessage(userMessage);
      void repository?.saveMessage(userMessage).catch(() => undefined);
      await run(chat, userMessage);
    },
    [activeChat, router, run],
  );

  const stop = useCallback(() => {
    if (chatId) abortChat(chatId);
    else {
      const g = useChatStore.getState().generating;
      if (g) abortChat(g.chatId);
    }
  }, [chatId]);

  /** Replace semantics: drop the edited message and everything after it, then resend. */
  const editAndResend = useCallback(
    async (messageId: string, text: string) => {
      const content = text.trim();
      if (!activeChat || !content || useChatStore.getState().generating) return;
      const list = useChatStore.getState().messages[activeChat.id] ?? [];
      const original = list.find((m) => m.id === messageId && m.role === "user");
      if (!original) return;
      useChatStore.getState().truncateFrom(activeChat.id, messageId);
      await repoRef.current?.deleteMessagesFrom(activeChat.id, messageId).catch(() => undefined);
      const edited: ChatMessage = { ...original, id: newId(), content, createdAt: Date.now() };
      useChatStore.getState().upsertMessage(edited);
      void repoRef.current?.saveMessage(edited).catch(() => undefined);
      if (list[0]?.id === messageId) {
        const title = autoTitle(content);
        useChatStore.getState().patchChat(activeChat.id, { title });
        void repoRef.current?.renameChat(activeChat.id, title).catch(() => undefined);
      }
      await run({ ...activeChat, title: list[0]?.id === messageId ? autoTitle(content) : activeChat.title }, edited);
    },
    [activeChat, run],
  );

  /** Re-answer the last user message (also used as "retry" after an error). */
  const regenerate = useCallback(async () => {
    if (!activeChat || useChatStore.getState().generating) return;
    const list = useChatStore.getState().messages[activeChat.id] ?? [];
    const lastUserIdx = list.map((m) => m.role).lastIndexOf("user");
    if (lastUserIdx === -1) return;
    const after = list[lastUserIdx + 1];
    if (after) {
      useChatStore.getState().truncateFrom(activeChat.id, after.id);
      await repoRef.current?.deleteMessagesFrom(activeChat.id, after.id).catch(() => undefined);
    }
    await run(activeChat, list[lastUserIdx]);
  }, [activeChat, run]);

  const renameChat = useCallback((id: string, title: string) => {
    const clean = title.trim();
    if (!clean) return;
    useChatStore.getState().patchChat(id, { title: clean });
    void repoRef.current?.renameChat(id, clean).catch(() => undefined);
  }, []);

  const deleteChat = useCallback(
    async (id: string) => {
      if (useChatStore.getState().generating?.chatId === id) abortChat(id);
      useChatStore.getState().removeChat(id);
      await repoRef.current?.deleteChat(id).catch(() => undefined);
      if (id === chatId) router.push("/chat");
    },
    [chatId, router],
  );

  return {
    ready: store.hydrated,
    loadError: store.loadError,
    chats: store.chats,
    activeChat,
    messages,
    scope,
    setScope,
    generating,
    send,
    stop,
    editAndResend,
    regenerate,
    renameChat,
    deleteChat,
  };
}
