import { describe, expect, it } from "vitest";
import { buildChatPayload, normaliseScope } from "./payload";
import type { ChatMessage } from "./types";

const m = (id: string, role: ChatMessage["role"], content: string, status: ChatMessage["status"] = "done"): ChatMessage => ({
  id,
  chatId: "c1",
  role,
  content,
  sources: [],
  status,
  parentId: null,
  createdAt: Number(id.replace(/\D/g, "")) || 0,
});

describe("normaliseScope", () => {
  it("keeps valid ids in canonical order, case-insensitively; empty means all", () => {
    expect(normaliseScope(["it", "AIT", "AIT", "XX"])).toEqual(["AIT", "IT"]);
    expect(normaliseScope([])).toEqual(["AIT", "DSBA", "BIT", "IT"]);
    expect(normaliseScope(null)).toEqual(["AIT", "DSBA", "BIT", "IT"]);
  });
});

describe("buildChatPayload", () => {
  it("sends the turns up to the last user message with the scope field the route expects", () => {
    const payload = buildChatPayload(
      [m("1", "user", "hi"), m("2", "assistant", "hello"), m("3", "user", "AIT?"), m("4", "assistant", "", "streaming")],
      ["DSBA", "AIT"],
      "c1",
    );
    expect(payload).toEqual({
      messages: [
        { role: "user", content: "hi" },
        { role: "assistant", content: "hello" },
        { role: "user", content: "AIT?" },
      ],
      facultyScope: ["AIT", "DSBA"],
      conversationId: "c1",
    });
  });
  it("drops errored assistant turns and empty ones, keeps stopped partial answers", () => {
    const payload = buildChatPayload(
      [m("1", "user", "a"), m("2", "assistant", "", "error"), m("3", "user", "b"), m("4", "assistant", "half", "stopped"), m("5", "user", "c")],
      [],
      null,
    );
    expect(payload.messages.map((t) => t.content)).toEqual(["a", "b", "half", "c"]);
    expect(payload.conversationId).toBeNull();
    expect(payload.facultyScope).toHaveLength(4);
  });
});
