import { beforeEach, describe, expect, it } from "vitest";
import { LocalChatRepository } from "./repository";
import type { Chat, ChatMessage } from "./types";

const chat = (id: string, updatedAt: number): Chat => ({ id, title: id, scope: ["AIT"], createdAt: updatedAt, updatedAt });
const msg = (id: string, chatId: string, createdAt: number): ChatMessage => ({
  id,
  chatId,
  role: "user",
  content: id,
  sources: [],
  status: "done",
  parentId: null,
  createdAt,
});

describe("LocalChatRepository", () => {
  let repo: LocalChatRepository;
  beforeEach(() => {
    repo = new LocalChatRepository();
  });

  it("stores chats newest-first and survives a fresh instance", async () => {
    await repo.createChat(chat("a", 1));
    await repo.createChat(chat("b", 2));
    expect((await new LocalChatRepository().listChats()).map((c) => c.id)).toEqual(["b", "a"]);
    await repo.renameChat("a", "renamed");
    expect((await repo.listChats()).find((c) => c.id === "a")?.title).toBe("renamed");
    await repo.deleteChat("b");
    expect((await repo.listChats()).map((c) => c.id)).toEqual(["a"]);
  });

  it("upserts messages and truncates from a message (replace-edit)", async () => {
    await repo.createChat(chat("a", 1));
    await repo.saveMessage(msg("m1", "a", 1));
    await repo.saveMessage(msg("m2", "a", 2));
    await repo.saveMessage(msg("m3", "a", 3));
    await repo.saveMessage({ ...msg("m2", "a", 2), content: "edited" });
    expect((await repo.listMessages("a")).map((m) => m.content)).toEqual(["m1", "edited", "m3"]);
    await repo.deleteMessagesFrom("a", "m2");
    expect((await repo.listMessages("a")).map((m) => m.id)).toEqual(["m1"]);
    await repo.deleteChat("a");
    expect(await repo.listMessages("a")).toEqual([]);
  });
});
