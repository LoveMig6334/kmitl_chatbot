/** Fake `/api/chat` responses for tests: a `data:` line per payload, streamed in small chunks. */
export function sseResponse(payloads: unknown[], opts: { delayMs?: number; status?: number; signal?: AbortSignal } = {}) {
  const enc = new TextEncoder();
  let cancelled = false;
  const body = new ReadableStream<Uint8Array>({
    async start(controller) {
      // like fetch: an aborted request makes the body read reject with AbortError
      opts.signal?.addEventListener("abort", () => {
        cancelled = true;
        try {
          controller.error(new DOMException("The operation was aborted", "AbortError"));
        } catch {
          /* already closed */
        }
      });
      for (const p of payloads) {
        if (cancelled) return;
        if (opts.delayMs) await new Promise((r) => setTimeout(r, opts.delayMs));
        if (cancelled) return;
        controller.enqueue(enc.encode(`data: ${JSON.stringify(p)}\n\n`));
      }
      if (!cancelled) controller.close();
    },
    cancel() {
      cancelled = true;
    },
  });
  return new Response(body, { status: opts.status ?? 200, headers: { "Content-Type": "text/event-stream" } });
}

export function answerPayloads(text: string, sources: unknown[] = []) {
  return [
    { meta: { category: "in_scope", language: "th", programs: [], question_kind: null } },
    ...text.split(" ").map((w, i) => ({ delta: (i ? " " : "") + w })),
    { citations: sources },
    { done: true, partial: false, model_used: null },
  ];
}
