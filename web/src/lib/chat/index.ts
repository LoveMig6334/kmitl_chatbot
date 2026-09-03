import { createSupabaseBrowserClient, supabaseConfigured } from "@/lib/supabase/client";
import { LocalChatRepository, type ChatRepository } from "./repository";
import { SupabaseChatRepository } from "./supabase";

export type { ChatRepository } from "./repository";
export * from "./types";
export * from "./title";
export * from "./stream";
export * from "./payload";

let local: LocalChatRepository | null = null;

/** Repository for the current user: Supabase when configured (needs a user id), else localStorage. */
export function getChatRepository(userId: string | null): ChatRepository {
  if (supabaseConfigured && userId) {
    const supabase = createSupabaseBrowserClient();
    if (supabase) return new SupabaseChatRepository(supabase, userId);
  }
  local ??= new LocalChatRepository();
  return local;
}
