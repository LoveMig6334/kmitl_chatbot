import type { Chat, ChatMessage } from "./types";
import type { ProgramId } from "@/lib/constants";

/**
 * Persistence seam. `LocalChatRepository` (localStorage) backs demo mode and tests;
 * `SupabaseChatRepository` (supabase.ts) is used when NEXT_PUBLIC_SUPABASE_* are set.
 * Everything is keyed by the signed-in user on the Supabase side via RLS.
 */
export interface ChatRepository {
  listChats(): Promise<Chat[]>;
  createChat(chat: Chat): Promise<void>;
  renameChat(id: string, title: string): Promise<void>;
  updateScope(id: string, scope: ProgramId[]): Promise<void>;
  touchChat(id: string, updatedAt: number): Promise<void>;
  deleteChat(id: string): Promise<void>;
  listMessages(chatId: string): Promise<ChatMessage[]>;
  /** Insert or replace by id. */
  saveMessage(message: ChatMessage): Promise<void>;
  /** Remove `messageId` and everything after it in the chat (replace-edit semantics). */
  deleteMessagesFrom(chatId: string, messageId: string): Promise<void>;
}

export const LOCAL_CHATS_KEY = "kmitl.chats.v2";

interface LocalShape {
  chats: Chat[];
  messages: Record<string, ChatMessage[]>;
}

export class LocalChatRepository implements ChatRepository {
  constructor(private readonly storage: Storage = window.localStorage) {}

  private read(): LocalShape {
    try {
      const raw = this.storage.getItem(LOCAL_CHATS_KEY);
      if (!raw) return { chats: [], messages: {} };
      const parsed = JSON.parse(raw) as Partial<LocalShape>;
      return { chats: parsed.chats ?? [], messages: parsed.messages ?? {} };
    } catch {
      return { chats: [], messages: {} };
    }
  }

  private write(data: LocalShape) {
    try {
      this.storage.setItem(LOCAL_CHATS_KEY, JSON.stringify(data));
    } catch {
      /* quota / private mode — state stays in memory for this page */
    }
  }

  async listChats() {
    return [...this.read().chats].sort((a, b) => b.updatedAt - a.updatedAt);
  }
  async createChat(chat: Chat) {
    const d = this.read();
    d.chats = [chat, ...d.chats.filter((c) => c.id !== chat.id)];
    d.messages[chat.id] ??= [];
    this.write(d);
  }
  async renameChat(id: string, title: string) {
    const d = this.read();
    d.chats = d.chats.map((c) => (c.id === id ? { ...c, title, updatedAt: Date.now() } : c));
    this.write(d);
  }
  async updateScope(id: string, scope: ProgramId[]) {
    const d = this.read();
    d.chats = d.chats.map((c) => (c.id === id ? { ...c, scope } : c));
    this.write(d);
  }
  async touchChat(id: string, updatedAt: number) {
    const d = this.read();
    d.chats = d.chats.map((c) => (c.id === id ? { ...c, updatedAt } : c));
    this.write(d);
  }
  async deleteChat(id: string) {
    const d = this.read();
    d.chats = d.chats.filter((c) => c.id !== id);
    delete d.messages[id];
    this.write(d);
  }
  async listMessages(chatId: string) {
    return [...(this.read().messages[chatId] ?? [])].sort((a, b) => a.createdAt - b.createdAt);
  }
  async saveMessage(message: ChatMessage) {
    const d = this.read();
    const list = d.messages[message.chatId] ?? [];
    const idx = list.findIndex((m) => m.id === message.id);
    if (idx === -1) list.push(message);
    else list[idx] = message;
    d.messages[message.chatId] = list;
    this.write(d);
  }
  async deleteMessagesFrom(chatId: string, messageId: string) {
    const d = this.read();
    const list = d.messages[chatId] ?? [];
    const idx = list.findIndex((m) => m.id === messageId);
    if (idx !== -1) d.messages[chatId] = list.slice(0, idx);
    this.write(d);
  }
}
