import { describe, expect, it } from "vitest";
import { groupChats } from "./ChatSidebar";
import type { Chat } from "@/lib/chat";

const chat = (id: string, updatedAt: number): Chat => ({ id, title: id, scope: ["AIT"], createdAt: updatedAt, updatedAt });

describe("groupChats", () => {
  it("buckets by day relative to now and omits empty groups", () => {
    const now = new Date(2026, 8, 3, 15, 0).getTime();
    const day = 86_400_000;
    const groups = groupChats(
      [chat("today", now - 3600_000), chat("yesterday", now - day), chat("week", now - 4 * day), chat("old", now - 30 * day)],
      now,
    );
    expect(groups.map((g) => [g.key, g.chats.map((c) => c.id)])).toEqual([
      ["chat.today", ["today"]],
      ["chat.yesterday", ["yesterday"]],
      ["chat.thisWeek", ["week"]],
      ["chat.older", ["old"]],
    ]);
    expect(groupChats([chat("a", now)], now)).toHaveLength(1);
  });
});
