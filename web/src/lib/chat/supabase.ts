import type { SupabaseClient } from "@supabase/supabase-js";
import type { ProgramId } from "@/lib/constants";
import { normaliseScope } from "./payload";
import type { ChatRepository } from "./repository";
import type { Chat, ChatMessage, MessageStatus } from "./types";

/** Row shapes of web/supabase/migrations/0001_chats.sql. */
interface ChatRow {
  id: string;
  title: string;
  scope: string[] | null;
  created_at: string;
  updated_at: string;
}
interface MessageRow {
  id: string;
  chat_id: string;
  role: "user" | "assistant";
  content: string;
  sources: unknown;
  status: string;
  error: string | null;
  parent_id: string | null;
  created_at: string;
}

const STATUSES: MessageStatus[] = ["streaming", "done", "stopped", "error"];

function toChat(r: ChatRow): Chat {
  return {
    id: r.id,
    title: r.title,
    scope: normaliseScope(r.scope),
    createdAt: Date.parse(r.created_at),
    updatedAt: Date.parse(r.updated_at),
  };
}

function toMessage(r: MessageRow): ChatMessage {
  const status = STATUSES.includes(r.status as MessageStatus) ? (r.status as MessageStatus) : "done";
  return {
    id: r.id,
    chatId: r.chat_id,
    role: r.role,
    content: r.content,
    sources: Array.isArray(r.sources) ? (r.sources as ChatMessage["sources"]) : [],
    // a message left "streaming" (tab closed mid-answer) is shown as stopped
    status: status === "streaming" ? "stopped" : status,
    error: r.error,
    parentId: r.parent_id,
    createdAt: Date.parse(r.created_at),
  };
}

export class SupabaseChatRepository implements ChatRepository {
  constructor(
    private readonly supabase: SupabaseClient,
    private readonly userId: string,
  ) {}

  private async must<T>(q: PromiseLike<{ data: T | null; error: { message: string } | null }>): Promise<T | null> {
    const { data, error } = await q;
    if (error) throw new Error(error.message);
    return data;
  }

  async listChats() {
    const rows = await this.must<ChatRow[]>(
      this.supabase.from("chats").select("id,title,scope,created_at,updated_at").order("updated_at", { ascending: false }),
    );
    return (rows ?? []).map(toChat);
  }
  async createChat(chat: Chat) {
    await this.must(
      this.supabase.from("chats").upsert({
        id: chat.id,
        user_id: this.userId,
        title: chat.title,
        scope: chat.scope,
        created_at: new Date(chat.createdAt).toISOString(),
        updated_at: new Date(chat.updatedAt).toISOString(),
      }),
    );
  }
  async renameChat(id: string, title: string) {
    await this.must(this.supabase.from("chats").update({ title, updated_at: new Date().toISOString() }).eq("id", id));
  }
  async updateScope(id: string, scope: ProgramId[]) {
    await this.must(this.supabase.from("chats").update({ scope }).eq("id", id));
  }
  async touchChat(id: string, updatedAt: number) {
    await this.must(this.supabase.from("chats").update({ updated_at: new Date(updatedAt).toISOString() }).eq("id", id));
  }
  async deleteChat(id: string) {
    await this.must(this.supabase.from("chats").delete().eq("id", id)); // messages cascade
  }
  async listMessages(chatId: string) {
    const rows = await this.must<MessageRow[]>(
      this.supabase
        .from("messages")
        .select("id,chat_id,role,content,sources,status,error,parent_id,created_at")
        .eq("chat_id", chatId)
        .order("created_at", { ascending: true }),
    );
    return (rows ?? []).map(toMessage);
  }
  async saveMessage(m: ChatMessage) {
    await this.must(
      this.supabase.from("messages").upsert({
        id: m.id,
        chat_id: m.chatId,
        user_id: this.userId,
        role: m.role,
        content: m.content,
        sources: m.sources,
        status: m.status,
        error: m.error ?? null,
        parent_id: m.parentId,
        created_at: new Date(m.createdAt).toISOString(),
      }),
    );
  }
  async deleteMessagesFrom(chatId: string, messageId: string) {
    const row = await this.must<{ created_at: string }>(
      this.supabase.from("messages").select("created_at").eq("id", messageId).single(),
    );
    if (!row) return;
    await this.must(this.supabase.from("messages").delete().eq("chat_id", chatId).gte("created_at", row.created_at));
  }
}
