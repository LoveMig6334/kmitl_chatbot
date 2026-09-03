import { describe, expect, it } from "vitest";
import { initialStreamState, parseChatLine, parseCitations, readSseJson, streamReducer } from "./stream";

describe("parseChatLine", () => {
  it("decodes every line shape the route emits", () => {
    expect(parseChatLine({ delta: "สวัส" })).toEqual({ type: "delta", text: "สวัส" });
    expect(parseChatLine({ citations: [] })).toEqual({ type: "citations", citations: [] });
    expect(parseChatLine({ done: true, partial: false, model_used: null })).toEqual({ type: "done", partial: false });
    expect(parseChatLine({ done: true, partial: true })).toEqual({ type: "done", partial: true });
    expect(parseChatLine({ error: { code: "upstream_timeout", message: "slow" } })).toEqual({
      type: "error",
      code: "upstream_timeout",
      message: "slow",
    });
    expect(parseChatLine({ error: "boom" })).toEqual({ type: "error", code: "unknown", message: "boom" });
    expect(parseChatLine({ meta: { category: "in_scope" } })?.type).toBe("meta");
    expect(parseChatLine({ something: 1 })).toBeNull();
    expect(parseChatLine("nope")).toBeNull();
  });
});

describe("parseCitations", () => {
  it("keeps well-formed citations only and fills defaults", () => {
    const out = parseCitations([
      { faculty: "IT", program: "AIT", page: 12, chunk_id: "AIT::gen::0012", snippet: "…" },
      { program: "IT", page: "3", chunk_id: "bad-page" },
      { page: 4, chunk_id: "no-program" },
      null,
      "x",
    ]);
    expect(out).toEqual([
      { faculty: "IT", program: "AIT", page: 12, chunk_id: "AIT::gen::0012", snippet: "…" },
      { faculty: "IT", program: null, page: 4, chunk_id: "no-program", snippet: null },
    ]);
    expect(parseCitations(undefined)).toEqual([]);
  });
});

describe("streamReducer", () => {
  it("appends deltas, records citations and finishes on done", () => {
    let s = initialStreamState;
    s = streamReducer(s, { type: "meta", meta: { category: "in_scope", language: "th", programs: [], question_kind: null } });
    s = streamReducer(s, { type: "delta", text: "AIT " });
    s = streamReducer(s, { type: "delta", text: "129 หน่วยกิต" });
    s = streamReducer(s, { type: "citations", citations: [{ faculty: "IT", program: "AIT", page: 9, chunk_id: "c1", snippet: null }] });
    s = streamReducer(s, { type: "done", partial: false });
    expect(s).toMatchObject({ content: "AIT 129 หน่วยกิต", status: "done", partial: false, error: null });
    expect(s.sources).toHaveLength(1);
    expect(s.meta?.category).toBe("in_scope");
  });
  it("stop keeps the partial text; later events are ignored", () => {
    let s = streamReducer(initialStreamState, { type: "delta", text: "half" });
    s = streamReducer(s, { type: "stop" });
    s = streamReducer(s, { type: "delta", text: " more" });
    s = streamReducer(s, { type: "done", partial: false });
    expect(s).toMatchObject({ content: "half", status: "stopped" });
  });
  it("error is terminal and keeps the message", () => {
    let s = streamReducer(initialStreamState, { type: "delta", text: "x" });
    s = streamReducer(s, { type: "error", code: "answerer_failed", message: "nope" });
    expect(s).toMatchObject({ content: "x", status: "error", error: "nope" });
  });
  it("a cut stream is done + partial", () => {
    expect(streamReducer(initialStreamState, { type: "done", partial: true })).toMatchObject({ status: "done", partial: true });
  });
});

function sse(lines: string[]): ReadableStream<Uint8Array> {
  const enc = new TextEncoder();
  return new ReadableStream({
    start(c) {
      // split across chunk boundaries on purpose
      const text = lines.map((l) => `data: ${l}\n\n`).join("");
      for (let i = 0; i < text.length; i += 7) c.enqueue(enc.encode(text.slice(i, i + 7)));
      c.close();
    },
  });
}

describe("readSseJson", () => {
  it("reassembles payloads split across chunks and skips junk", async () => {
    const out: unknown[] = [];
    for await (const p of readSseJson(sse(['{"delta":"a"}', "not json", '{"done":true}']))) out.push(p);
    expect(out).toEqual([{ delta: "a" }, { done: true }]);
  });
});
