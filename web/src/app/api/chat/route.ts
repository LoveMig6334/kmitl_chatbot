import { streamChat } from "@/lib/ai";
import type { ChatEvent, ChatTurn } from "@/lib/ai";
import { PROGRAM_IDS as KNOWN_PROGRAMS } from "@/lib/constants";

/**
 * Browser → this route → FastAPI `/chat` (see docs/api-contract.md).
 *
 * Request body (from ChatApp): `{ messages, facultyScope, conversationId }`.
 * Response: SSE where every line is `data: <json>` with exactly one of
 *   {meta}                       gate decision (category, language, programs, …)
 *   {delta}                      answer text chunk (unchanged from the old shape)
 *   {citations}                  list of {program, page, chunk_id, snippet}; in-scope only
 *   {done, partial, model_used}  end of answer; partial=true when the backend stream was cut
 *   {error: {code, message}}     terminal
 * Aborting the browser request aborts the upstream FastAPI request too.
 */

const PROGRAM_IDS = new Set<string>(KNOWN_PROGRAMS);
const MAX_HISTORY = 50; // backend validation limit
const MAX_TURN_CHARS = 8000;
const MAX_MESSAGE_CHARS = 4000;

// RAG answers (gate + retrieval + a ThaiLLM stream) can take up to a minute; Vercel's default is 60 s.
export const maxDuration = 300;

interface IncomingMessage {
  role?: unknown;
  content?: unknown;
}

function toLine(ev: ChatEvent): string {
  switch (ev.type) {
    case "meta":
      return JSON.stringify({ meta: ev.meta });
    case "token":
      return JSON.stringify({ delta: ev.text });
    case "citations":
      return JSON.stringify({ citations: ev.citations });
    case "done":
      return JSON.stringify({
        done: true,
        partial: ev.partial,
        model_used: ev.model_used ?? null,
        latency_ms: ev.latency_ms ?? null,
      });
    case "error":
      return JSON.stringify({ error: { code: ev.code, message: ev.message } });
  }
}

export async function POST(req: Request) {
  const body = await req.json().catch(() => ({}));
  const rawMessages: IncomingMessage[] = Array.isArray(body?.messages) ? body.messages : [];
  const turns: ChatTurn[] = rawMessages
    .filter(
      (m): m is { role: "user" | "assistant"; content: string } =>
        (m.role === "user" || m.role === "assistant") && typeof m.content === "string",
    )
    .map((m) => ({ role: m.role, content: m.content.slice(0, MAX_TURN_CHARS) }));

  const lastUserIdx = turns.map((t) => t.role).lastIndexOf("user");
  if (lastUserIdx === -1 || !turns[lastUserIdx].content.trim()) {
    return Response.json({ error: "messages must contain a user turn" }, { status: 400 });
  }
  const message = turns[lastUserIdx].content.slice(0, MAX_MESSAGE_CHARS);
  const history = turns.slice(0, lastUserIdx).slice(-MAX_HISTORY);

  const scopeIn: unknown[] = Array.isArray(body?.facultyScope) ? body.facultyScope : [];
  const scope = scopeIn
    .filter((s): s is string => typeof s === "string")
    .map((s) => s.toUpperCase())
    .filter((s) => PROGRAM_IDS.has(s));
  const conversationId = typeof body?.conversationId === "string" ? body.conversationId : null;

  // One abort controller fed by both disconnect signals Next.js can give us:
  // the request's own signal and the response stream being cancelled.
  const upstream = new AbortController();
  const onAbort = () => upstream.abort();
  if (req.signal.aborted) onAbort();
  else req.signal.addEventListener("abort", onAbort, { once: true });

  const encoder = new TextEncoder();
  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      const send = (line: string) => {
        if (upstream.signal.aborted) return;
        try {
          controller.enqueue(encoder.encode(`data: ${line}\n\n`));
        } catch {
          // stream already closed by the client
        }
      };
      try {
        const events = streamChat(
          { message, conversationId, scope: scope.length ? scope : null, history },
          upstream.signal,
        );
        for await (const ev of events) {
          if (upstream.signal.aborted) break;
          send(toLine(ev));
        }
      } catch (err) {
        if (!upstream.signal.aborted) {
          send(toLine({ type: "error", code: "proxy_failed", message: String(err) }));
        }
      } finally {
        req.signal.removeEventListener("abort", onAbort);
        try {
          controller.close();
        } catch {
          // already closed
        }
      }
    },
    cancel() {
      onAbort();
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}
