import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, renderHook, waitFor } from "@testing-library/react";
import { useChatStore } from "@/lib/chat/store";
import { LocalChatRepository } from "@/lib/chat/repository";
import { answerPayloads, sseResponse } from "@/test/sse";
import { setDemoUser } from "@/lib/auth/demo";
import { useChatController } from "./useChatController";

const router = { replace: vi.fn(), push: vi.fn(), refresh: vi.fn() };
vi.mock("next/navigation", () => ({ useRouter: () => router }));

const fetchMock = vi.fn();

beforeEach(() => {
  vi.clearAllMocks();
  useChatStore.getState().reset();
  setDemoUser({ email: "a@b.co", displayName: "A" });
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => vi.unstubAllGlobals());

function lastRequestBody() {
  const [, init] = fetchMock.mock.calls[fetchMock.mock.calls.length - 1] as [string, RequestInit];
  return JSON.parse(String(init.body));
}

describe("useChatController", () => {
  it("does not list a chat until the first message is sent; then auto-titles and streams", async () => {
    fetchMock.mockImplementation(() =>
      Promise.resolve(sseResponse(answerPayloads("AIT มี 129 หน่วยกิต", [{ faculty: "IT", program: "AIT", page: 9, chunk_id: "c1", snippet: "…" }]))),
    );
    const { result } = renderHook(() => useChatController(null));
    await waitFor(() => expect(result.current.ready).toBe(true));
    expect(result.current.chats).toEqual([]);

    await act(async () => {
      await result.current.send("  AIT เรียนกี่หน่วยกิต  ");
    });

    const chats = useChatStore.getState().chats;
    expect(chats).toHaveLength(1);
    expect(chats[0].title).toBe("AIT เรียนกี่หน่วยกิต");
    expect(chats[0].scope).toEqual(["AIT", "DSBA", "BIT", "IT"]);
    expect(router.replace).toHaveBeenCalledWith(`/chat/${chats[0].id}`);

    const messages = useChatStore.getState().messages[chats[0].id];
    expect(messages.map((m) => m.role)).toEqual(["user", "assistant"]);
    expect(messages[1]).toMatchObject({ content: "AIT มี 129 หน่วยกิต", status: "done" });
    expect(messages[1].sources[0]).toMatchObject({ program: "AIT", page: 9 });

    // payload shape the Next route expects
    expect(lastRequestBody()).toEqual({
      messages: [{ role: "user", content: "AIT เรียนกี่หน่วยกิต" }],
      facultyScope: ["AIT", "DSBA", "BIT", "IT"],
      conversationId: chats[0].id,
    });

    // persisted
    const repo = new LocalChatRepository();
    expect((await repo.listChats()).map((c) => c.id)).toEqual([chats[0].id]);
    expect(await repo.listMessages(chats[0].id)).toHaveLength(2);
  });

  it("stop keeps the partial answer with status stopped", async () => {
    fetchMock.mockImplementation((_url: string, init: RequestInit) =>
      Promise.resolve(sseResponse(answerPayloads("one two three four five six"), { delayMs: 20, signal: init.signal ?? undefined })),
    );
    const { result } = renderHook(() => useChatController(null));
    await waitFor(() => expect(result.current.ready).toBe(true));
    let sending!: Promise<void>;
    act(() => {
      sending = result.current.send("hello");
    });
    await waitFor(() => {
      const chat = useChatStore.getState().chats[0];
      const msgs = chat ? useChatStore.getState().messages[chat.id] : [];
      expect(msgs[1]?.content.length ?? 0).toBeGreaterThan(0);
    });
    act(() => result.current.stop());
    await act(async () => {
      await sending;
    });
    const chat = useChatStore.getState().chats[0];
    const assistant = useChatStore.getState().messages[chat.id][1];
    expect(assistant.status).toBe("stopped");
    expect(assistant.content.length).toBeGreaterThan(0);
    expect(assistant.content.length).toBeLessThan("one two three four five six".length);
    expect(useChatStore.getState().generating).toBeNull();
  });

  it("edit-and-resend replaces the message and everything after it", async () => {
    fetchMock.mockImplementation(() => Promise.resolve(sseResponse(answerPayloads("answer"))));
    const first = renderHook(() => useChatController(null));
    await waitFor(() => expect(first.result.current.ready).toBe(true));
    await act(async () => {
      await first.result.current.send("q1");
    });
    const chatId = useChatStore.getState().chats[0].id;
    const ctl = renderHook(() => useChatController(chatId));
    await waitFor(() => expect(ctl.result.current.messages).toHaveLength(2));
    await act(async () => {
      await ctl.result.current.send("q2");
    });
    expect(ctl.result.current.messages.map((m) => m.content)).toEqual(["q1", "answer", "q2", "answer"]);

    const q1 = ctl.result.current.messages[0];
    await act(async () => {
      await ctl.result.current.editAndResend(q1.id, "q1 edited");
    });
    const after = ctl.result.current.messages;
    expect(after.map((m) => m.content)).toEqual(["q1 edited", "answer"]);
    expect(after[0].id).not.toBe(q1.id);
    expect(lastRequestBody().messages).toEqual([{ role: "user", content: "q1 edited" }]);
    expect(useChatStore.getState().chats[0].title).toBe("q1 edited"); // first message renames the chat
    expect((await new LocalChatRepository().listMessages(chatId)).map((m) => m.content)).toEqual(["q1 edited", "answer"]);
  });

  it("regenerate re-answers the last question; an HTTP error becomes an error message", async () => {
    fetchMock.mockImplementationOnce(() => Promise.resolve(sseResponse(answerPayloads("first"))));
    const { result } = renderHook(() => useChatController(null));
    await waitFor(() => expect(result.current.ready).toBe(true));
    await act(async () => {
      await result.current.send("q");
    });
    const chatId = useChatStore.getState().chats[0].id;
    const ctl = renderHook(() => useChatController(chatId));
    await waitFor(() => expect(ctl.result.current.messages).toHaveLength(2));

    fetchMock.mockImplementationOnce(() => Promise.resolve(new Response(JSON.stringify({ error: "nope" }), { status: 429 })));
    await act(async () => {
      await ctl.result.current.regenerate();
    });
    const msgs = ctl.result.current.messages;
    expect(msgs).toHaveLength(2);
    expect(msgs[1]).toMatchObject({ status: "error", error: "nope", content: "" });
    expect(lastRequestBody().messages).toEqual([{ role: "user", content: "q" }]);
  });

  it("scope changes persist per chat and are sent with the next request", async () => {
    fetchMock.mockImplementation(() => Promise.resolve(sseResponse(answerPayloads("a"))));
    const { result } = renderHook(() => useChatController(null));
    await waitFor(() => expect(result.current.ready).toBe(true));
    act(() => result.current.setScope(["DSBA"]));
    await act(async () => {
      await result.current.send("q");
    });
    expect(lastRequestBody().facultyScope).toEqual(["DSBA"]);
    const chatId = useChatStore.getState().chats[0].id;
    expect((await new LocalChatRepository().listChats())[0].scope).toEqual(["DSBA"]);

    const ctl = renderHook(() => useChatController(chatId));
    await waitFor(() => expect(ctl.result.current.scope).toEqual(["DSBA"]));
    act(() => ctl.result.current.setScope(["AIT", "IT"]));
    await act(async () => {
      await ctl.result.current.send("q2");
    });
    expect(lastRequestBody().facultyScope).toEqual(["AIT", "IT"]);
  });

  it("rename and delete update the list and storage; deleting the open chat goes to /chat", async () => {
    fetchMock.mockImplementation(() => Promise.resolve(sseResponse(answerPayloads("a"))));
    const { result } = renderHook(() => useChatController(null));
    await waitFor(() => expect(result.current.ready).toBe(true));
    await act(async () => {
      await result.current.send("q");
    });
    const chatId = useChatStore.getState().chats[0].id;
    const ctl = renderHook(() => useChatController(chatId));
    await act(async () => {
      await new Promise((r) => setTimeout(r, 0)); // let its hydration settle
    });
    act(() => ctl.result.current.renameChat(chatId, "  My chat "));
    expect(useChatStore.getState().chats[0].title).toBe("My chat");
    await act(async () => {
      await ctl.result.current.deleteChat(chatId);
    });
    expect(useChatStore.getState().chats).toEqual([]);
    expect(await new LocalChatRepository().listChats()).toEqual([]);
    expect(router.push).toHaveBeenCalledWith("/chat");
  });
});
