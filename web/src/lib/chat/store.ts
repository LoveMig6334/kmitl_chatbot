import { create } from "zustand";
import type { ProgramId } from "@/lib/constants";
import { DEFAULT_SCOPE } from "./payload";
import type { Chat, ChatMessage } from "./types";

/**
 * In-memory chat state (hydrated from the ChatRepository by useChatController).
 * A brand-new chat lives only as `draftScope` until the first message creates it —
 * so the sidebar never lists empty chats.
 */
export interface ChatStore {
  hydrated: boolean;
  loadError: boolean;
  chats: Chat[];
  messages: Record<string, ChatMessage[]>;
  loadedChats: Record<string, true>;
  activeChatId: string | null;
  draftScope: ProgramId[];
  generating: { chatId: string; messageId: string } | null;

  setHydrated: (chats: Chat[], error?: boolean) => void;
  upsertChat: (chat: Chat) => void;
  patchChat: (id: string, patch: Partial<Chat>) => void;
  removeChat: (id: string) => void;
  setMessages: (chatId: string, messages: ChatMessage[]) => void;
  upsertMessage: (message: ChatMessage) => void;
  truncateFrom: (chatId: string, messageId: string) => void;
  setActive: (id: string | null) => void;
  setDraftScope: (scope: ProgramId[]) => void;
  setGenerating: (g: ChatStore["generating"]) => void;
  reset: () => void;
}

const empty = {
  hydrated: false,
  loadError: false,
  chats: [] as Chat[],
  messages: {} as Record<string, ChatMessage[]>,
  loadedChats: {} as Record<string, true>,
  activeChatId: null as string | null,
  draftScope: DEFAULT_SCOPE,
  generating: null as ChatStore["generating"],
};

export const useChatStore = create<ChatStore>()((set) => ({
  ...empty,

  // Merge: a chat created a moment ago may not be in the persisted list yet (Supabase round trip).
  setHydrated: (chats, error = false) =>
    set((s) => ({ hydrated: true, loadError: error, chats: sortChats(mergeById(s.chats, chats)) })),
  upsertChat: (chat) =>
    set((s) => ({ chats: sortChats([chat, ...s.chats.filter((c) => c.id !== chat.id)]) })),
  patchChat: (id, patch) =>
    set((s) => ({ chats: sortChats(s.chats.map((c) => (c.id === id ? { ...c, ...patch } : c))) })),
  removeChat: (id) =>
    set((s) => {
      const messages = { ...s.messages };
      delete messages[id];
      return {
        chats: s.chats.filter((c) => c.id !== id),
        messages,
        activeChatId: s.activeChatId === id ? null : s.activeChatId,
      };
    }),
  setMessages: (chatId, messages) =>
    set((s) => ({
      messages: { ...s.messages, [chatId]: messages },
      loadedChats: { ...s.loadedChats, [chatId]: true },
    })),
  upsertMessage: (message) =>
    set((s) => {
      const list = s.messages[message.chatId] ?? [];
      const idx = list.findIndex((m) => m.id === message.id);
      const next = idx === -1 ? [...list, message] : list.map((m, i) => (i === idx ? message : m));
      return { messages: { ...s.messages, [message.chatId]: next } };
    }),
  truncateFrom: (chatId, messageId) =>
    set((s) => {
      const list = s.messages[chatId] ?? [];
      const idx = list.findIndex((m) => m.id === messageId);
      return idx === -1 ? {} : { messages: { ...s.messages, [chatId]: list.slice(0, idx) } };
    }),
  setActive: (id) => set({ activeChatId: id }),
  setDraftScope: (scope) => set({ draftScope: scope }),
  setGenerating: (generating) => set({ generating }),
  reset: () => set({ ...empty }),
}));

function mergeById(local: Chat[], remote: Chat[]): Chat[] {
  const byId = new Map<string, Chat>();
  for (const c of remote) byId.set(c.id, c);
  for (const c of local) {
    const r = byId.get(c.id);
    if (!r || c.updatedAt >= r.updatedAt) byId.set(c.id, c);
  }
  return [...byId.values()];
}

/** In-flight answer per chat; kept out of React state so Stop survives route changes. */
const aborters = new Map<string, AbortController>();
export function registerAborter(chatId: string, controller: AbortController) {
  aborters.set(chatId, controller);
}
export function abortChat(chatId: string) {
  aborters.get(chatId)?.abort();
  aborters.delete(chatId);
}
export function clearAborter(chatId: string) {
  aborters.delete(chatId);
}

function sortChats(chats: Chat[]): Chat[] {
  return [...chats].sort((a, b) => b.updatedAt - a.updatedAt);
}
