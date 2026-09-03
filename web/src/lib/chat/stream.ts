import type { ChatMeta, Citation, MessageStatus } from "./types";

/** Events after decoding one `data: {...}` line from /api/chat. */
export type StreamAction =
  | { type: "meta"; meta: ChatMeta }
  | { type: "delta"; text: string }
  | { type: "citations"; citations: Citation[] }
  | { type: "done"; partial: boolean }
  | { type: "error"; code: string; message: string }
  | { type: "stop" };

export interface StreamState {
  content: string;
  sources: Citation[];
  status: MessageStatus;
  /** The backend stream ended without `done` (cut answer). */
  partial: boolean;
  error: string | null;
  meta: ChatMeta | null;
}

export const initialStreamState: StreamState = {
  content: "",
  sources: [],
  status: "streaming",
  partial: false,
  error: null,
  meta: null,
};

export function streamReducer(state: StreamState, action: StreamAction): StreamState {
  if (state.status !== "streaming") return state; // terminal states ignore late events
  switch (action.type) {
    case "meta":
      return { ...state, meta: action.meta };
    case "delta":
      return { ...state, content: state.content + action.text };
    case "citations":
      return { ...state, sources: parseCitations(action.citations) };
    case "done":
      return { ...state, status: "done", partial: action.partial };
    case "stop":
      return { ...state, status: "stopped" };
    case "error":
      return { ...state, status: "error", error: action.message };
  }
}

/** Decode one JSON payload from the route's `data:` line; unknown shapes yield null. */
export function parseChatLine(payload: unknown): StreamAction | null {
  if (!payload || typeof payload !== "object") return null;
  const p = payload as Record<string, unknown>;
  if (typeof p.delta === "string") return { type: "delta", text: p.delta };
  if (p.citations !== undefined) {
    return { type: "citations", citations: Array.isArray(p.citations) ? (p.citations as Citation[]) : [] };
  }
  if (p.done) return { type: "done", partial: p.partial === true };
  if (p.error !== undefined) {
    const e = p.error as { code?: unknown; message?: unknown } | string;
    if (typeof e === "string") return { type: "error", code: "unknown", message: e };
    return {
      type: "error",
      code: typeof e?.code === "string" ? e.code : "unknown",
      message: typeof e?.message === "string" ? e.message : "unknown",
    };
  }
  if (p.meta && typeof p.meta === "object") return { type: "meta", meta: p.meta as ChatMeta };
  return null;
}

/** Keep only well-formed citations; the UI relies on `page` being a number. */
export function parseCitations(raw: unknown): Citation[] {
  if (!Array.isArray(raw)) return [];
  const out: Citation[] = [];
  for (const c of raw) {
    if (!c || typeof c !== "object") continue;
    const r = c as Record<string, unknown>;
    if (typeof r.chunk_id !== "string" || typeof r.page !== "number") continue;
    out.push({
      faculty: typeof r.faculty === "string" ? r.faculty : "IT",
      program: typeof r.program === "string" ? r.program : null,
      page: r.page,
      chunk_id: r.chunk_id,
      snippet: typeof r.snippet === "string" ? r.snippet : null,
    });
  }
  return out;
}

/** Split an SSE body into the JSON payloads of its `data:` lines. */
export async function* readSseJson(
  body: ReadableStream<Uint8Array>,
  signal?: AbortSignal,
): AsyncGenerator<unknown> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let idx: number;
      while ((idx = buffer.indexOf("\n\n")) !== -1) {
        const block = buffer.slice(0, idx);
        buffer = buffer.slice(idx + 2);
        yield* blockPayloads(block);
      }
    }
    yield* blockPayloads(buffer);
  } catch (err) {
    if (signal?.aborted) return;
    throw err;
  } finally {
    reader.releaseLock();
  }
}

function* blockPayloads(block: string): Generator<unknown> {
  for (const raw of block.split("\n")) {
    const line = raw.endsWith("\r") ? raw.slice(0, -1) : raw;
    if (!line.startsWith("data:")) continue;
    try {
      yield JSON.parse(line.slice(5).trim());
    } catch {
      /* malformed line — skip */
    }
  }
}
