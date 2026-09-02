/**
 * Server-side client for the FastAPI backend (`POST /chat`, SSE).
 * Contract: docs/api-contract.md at the repo root.  Never imported by the browser.
 *
 * `streamChat` yields typed events; `app/api/chat/route.ts` turns them into the
 * `data: {...}` lines the client reads.  When FastAPI cannot be reached at all
 * (connection refused / DNS) it falls back to a mock stream in the same shape.
 */

export interface ChatTurn {
  role: "user" | "assistant";
  content: string;
}

export interface ChatInput {
  message: string;
  conversationId: string | null;
  scope: string[] | null;
  history: ChatTurn[];
}

export interface ChatMeta {
  category:
    | "in_scope"
    | "off_topic_general"
    | "off_topic_other_university"
    | "out_of_scope_kmitl"
    | "injection_or_abuse";
  language: "th" | "en" | "zh" | "other";
  faculty: string;
  programs: string[];
  question_kind: "fact_lookup" | "descriptive" | "comparison" | null;
  decided_by: "rule" | "llm" | "fallback";
  model_used: string | null;
  /** Set only by the local mock when FASTAPI_URL is unreachable. */
  mock?: true;
}

export interface Citation {
  faculty: string;
  program: string | null;
  page: number;
  chunk_id: string;
  snippet: string | null;
}

export type ChatEvent =
  | { type: "meta"; meta: ChatMeta }
  | { type: "token"; text: string }
  | { type: "citations"; citations: Citation[] }
  | {
      type: "done";
      /** true when the backend stream ended without a `done` event (cut answer). */
      partial: boolean;
      latency_ms?: number;
      model_used?: string | null;
    }
  | { type: "error"; code: string; message: string };

export const FASTAPI_URL = (process.env.FASTAPI_URL || "http://localhost:8000").replace(/\/+$/, "");

export async function* streamChat(
  input: ChatInput,
  signal?: AbortSignal,
): AsyncGenerator<ChatEvent> {
  let res: Response;
  try {
    res = await fetch(`${FASTAPI_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify({
        message: input.message,
        conversation_id: input.conversationId,
        scope: input.scope,
        history: input.history,
      }),
      signal,
    });
  } catch (err) {
    if (signal?.aborted) return; // client went away; nothing to report
    // Only a transport failure (backend down) gets the mock; everything else is surfaced.
    console.warn(`[ai] FastAPI unreachable at ${FASTAPI_URL}, using mock stream:`, err);
    yield* mockStream(input);
    return;
  }

  if (!res.ok || !res.body) {
    yield await httpError(res);
    return;
  }

  let sawDone = false;
  for await (const { event, data } of parseSse(res.body, signal)) {
    let json: Record<string, unknown>;
    try {
      json = JSON.parse(data);
    } catch {
      continue; // malformed line; keep going
    }
    switch (event) {
      case "meta":
        yield { type: "meta", meta: json as unknown as ChatMeta };
        break;
      case "token":
        yield { type: "token", text: typeof json.text === "string" ? json.text : "" };
        break;
      case "citations":
        yield { type: "citations", citations: (json.citations as Citation[] | undefined) ?? [] };
        break;
      case "done":
        sawDone = true;
        yield {
          type: "done",
          partial: false,
          latency_ms: typeof json.latency_ms === "number" ? json.latency_ms : undefined,
          model_used: (json.model_used as string | null | undefined) ?? null,
        };
        return;
      case "error":
        yield {
          type: "error",
          code: typeof json.code === "string" ? json.code : "unknown",
          message: typeof json.message === "string" ? json.message : "Unknown backend error",
        };
        return;
      default:
        break; // unknown event types are ignored (forward-compatible)
    }
  }
  if (!sawDone && !signal?.aborted) {
    yield { type: "done", partial: true };
  }
}

async function httpError(res: Response): Promise<ChatEvent> {
  let code = `http_${res.status}`;
  let message = `Backend returned HTTP ${res.status}`;
  try {
    const body = await res.json();
    if (body && typeof body === "object") {
      if (typeof body.code === "string") code = body.code;
      if (typeof body.message === "string") message = body.message;
      else if (typeof body.detail === "string") message = body.detail;
    }
  } catch {
    // no JSON body; keep the generic message
  }
  return { type: "error", code, message };
}

/** Minimal SSE parser: yields {event, data} per blank-line-terminated block. */
async function* parseSse(
  body: ReadableStream<Uint8Array>,
  signal?: AbortSignal,
): AsyncGenerator<{ event: string; data: string }> {
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
        const parsed = parseBlock(block);
        if (parsed) yield parsed;
      }
    }
    const tail = parseBlock(buffer);
    if (tail) yield tail;
  } catch (err) {
    if (signal?.aborted) return;
    throw err;
  } finally {
    reader.releaseLock();
  }
}

function parseBlock(block: string): { event: string; data: string } | null {
  let event = "message";
  const data: string[] = [];
  for (const raw of block.split("\n")) {
    const line = raw.endsWith("\r") ? raw.slice(0, -1) : raw;
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) data.push(line.slice(5).trimStart());
  }
  if (data.length === 0) return null;
  return { event, data: data.join("\n") };
}

// --- mock fallback (backend unreachable) ------------------------------------

async function* mockStream(input: ChatInput): AsyncGenerator<ChatEvent> {
  yield {
    type: "meta",
    meta: {
      category: "in_scope",
      language: "th",
      faculty: "IT",
      programs: [],
      question_kind: null,
      decided_by: "fallback",
      model_used: null,
      mock: true,
    },
  };
  const reply =
    `(โหมดสาธิต) ยังเชื่อมต่อ backend ไม่ได้ที่ ${FASTAPI_URL} — ` +
    `รันเซิร์ฟเวอร์ FastAPI แล้วตั้งค่า FASTAPI_URL ใน .env.local · คุณถามว่า: "${input.message}"`;
  for (const chunk of splitIntoChunks(reply)) {
    await sleep(24);
    yield { type: "token", text: chunk };
  }
  yield { type: "citations", citations: [] };
  yield { type: "done", partial: false, model_used: null };
}

function splitIntoChunks(text: string): string[] {
  const chunks: string[] = [];
  for (const w of text.split(/(\s+)/)) {
    if (w.length > 24) {
      for (let i = 0; i < w.length; i += 24) chunks.push(w.slice(i, i + 24));
    } else if (w) {
      chunks.push(w);
    }
  }
  return chunks;
}

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}
