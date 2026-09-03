import { PROGRAM_IDS, type ProgramId } from "@/lib/constants";
import type { ChatMessage } from "./types";

/** Body of `POST /api/chat` (the Next route forwards it to FastAPI as message/scope/history). */
export interface ChatRequestPayload {
  messages: { role: "user" | "assistant"; content: string }[];
  facultyScope: ProgramId[];
  conversationId: string | null;
}

export const DEFAULT_SCOPE: ProgramId[] = [...PROGRAM_IDS];

/**
 * Turns the conversation up to (and including) the user message being answered into the
 * request body. Streaming / errored assistant turns are dropped; stopped ones keep their text.
 */
export function buildChatPayload(
  messages: ChatMessage[],
  scope: ProgramId[],
  chatId: string | null,
): ChatRequestPayload {
  const lastUser = [...messages].reverse().find((m) => m.role === "user");
  const cutoff = lastUser ? messages.indexOf(lastUser) : messages.length - 1;
  const turns = messages
    .slice(0, cutoff + 1)
    .filter((m) => m.role === "user" || m.status === "done" || m.status === "stopped")
    .filter((m) => m.content.trim().length > 0)
    .map((m) => ({ role: m.role, content: m.content }));
  return {
    messages: turns,
    facultyScope: normaliseScope(scope),
    conversationId: chatId,
  };
}

/** Valid, de-duplicated program ids in canonical order; empty → every program. */
export function normaliseScope(scope: readonly string[] | null | undefined): ProgramId[] {
  const set = new Set((scope ?? []).map((s) => s.toUpperCase()));
  const picked = PROGRAM_IDS.filter((id) => set.has(id));
  return picked.length === 0 ? [...PROGRAM_IDS] : [...picked];
}
