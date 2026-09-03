import type { ProgramId } from "@/lib/constants";

/** One retrieved passage the answer cited (shape from docs/api-contract.md). */
export interface Citation {
  faculty: string;
  program: string | null;
  page: number;
  chunk_id: string;
  snippet: string | null;
}

export type MessageRole = "user" | "assistant";

/** Lifecycle of an assistant message; user messages are always "done". */
export type MessageStatus = "streaming" | "done" | "stopped" | "error";

export interface ChatMessage {
  id: string;
  chatId: string;
  role: MessageRole;
  content: string;
  sources: Citation[];
  status: MessageStatus;
  /** Backend error text (status === "error"); never shown raw when a dictionary message exists. */
  error?: string | null;
  /** Reserved for branching; Phase 2 uses replace semantics so it is always the previous message. */
  parentId: string | null;
  createdAt: number;
}

export interface Chat {
  id: string;
  title: string;
  scope: ProgramId[];
  createdAt: number;
  updatedAt: number;
}

/** Gate decision echoed by the backend before the first token. */
export interface ChatMeta {
  category:
    | "in_scope"
    | "off_topic_general"
    | "off_topic_other_university"
    | "out_of_scope_kmitl"
    | "injection_or_abuse"
    | "greeting_smalltalk";
  language: "th" | "en" | "zh" | "other";
  programs: string[];
  question_kind: "fact_lookup" | "descriptive" | "comparison" | null;
  mock?: boolean;
}
