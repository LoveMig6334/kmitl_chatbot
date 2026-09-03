import { describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "@/test/render";
import { dictionaries } from "@/i18n";
import type { ChatMessage } from "@/lib/chat";
import { MessageItem } from "./MessageItem";

const th = dictionaries.th;
const base: ChatMessage = {
  id: "a1",
  chatId: "c",
  role: "assistant",
  content: "",
  sources: [],
  status: "done",
  error: null,
  parentId: null,
  createdAt: 1,
};

function render(message: Partial<ChatMessage>, props: Partial<React.ComponentProps<typeof MessageItem>> = {}) {
  const onEdit = vi.fn();
  const onRegenerate = vi.fn();
  const onOpenSource = vi.fn();
  renderWithProviders(
    <MessageItem
      message={{ ...base, ...message }}
      isLast
      generating={false}
      activeSourceIndex={null}
      onOpenSource={onOpenSource}
      onEdit={onEdit}
      onRegenerate={onRegenerate}
      {...props}
    />,
  );
  return { onEdit, onRegenerate, onOpenSource };
}

describe("MessageItem", () => {
  it("renders markdown (table, code) and numbered source chips that open the panel", async () => {
    const { onOpenSource } = render({
      content: "**AIT** 120 หน่วยกิต [1]\n\n| ปี | หน่วยกิต |\n|---|---|\n| 1 | 30 |\n\n```js\nconst x = 1;\n```",
      sources: [
        { faculty: "IT", program: "AIT", page: 2, chunk_id: "a", snippet: "…" },
        { faculty: "IT", program: "AIT", page: 12, chunk_id: "b", snippet: null },
      ],
    });
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByText("AIT").tagName).toBe("STRONG");
    expect(screen.getByRole("button", { name: th["chat.copyCode"] })).toBeInTheDocument();
    const chips = screen.getAllByRole("button", { name: /AIT หน้า/ });
    expect(chips.map((c) => c.textContent)).toEqual(["1AIT หน้า 2", "2AIT หน้า 12"]);
    await userEvent.click(chips[1]);
    expect(onOpenSource).toHaveBeenCalledWith(1);
  });

  it("shows the thinking state while streaming with no text, and the caret once text arrives", () => {
    render({ status: "streaming" });
    expect(screen.getByText(th["chat.thinking"])).toBeInTheDocument();
  });

  it("error state offers retry; stopped state is labelled", async () => {
    const { onRegenerate } = render({ status: "error", error: "HTTP 429 rate limited" });
    expect(screen.getByRole("alert")).toHaveTextContent(th["chat.error.rateLimited"]);
    await userEvent.click(screen.getByRole("button", { name: new RegExp(th["chat.retry"]) }));
    expect(onRegenerate).toHaveBeenCalled();
  });

  it("stopped answers keep their text and say so", () => {
    render({ status: "stopped", content: "ครึ่ง" });
    expect(screen.getByText("ครึ่ง")).toBeInTheDocument();
    expect(screen.getByText(th["chat.stopped"])).toBeInTheDocument();
  });

  it("user messages can be edited inline; Enter saves and resends, Escape cancels", async () => {
    const { onEdit } = render({ role: "user", content: "AIT?" });
    await userEvent.click(screen.getByRole("button", { name: th["chat.edit"] }));
    const box = screen.getByRole("textbox", { name: th["chat.edit"] });
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("textbox")).toBeNull();
    expect(onEdit).not.toHaveBeenCalled();

    await userEvent.click(screen.getByRole("button", { name: th["chat.edit"] }));
    await userEvent.clear(screen.getByRole("textbox", { name: th["chat.edit"] }));
    await userEvent.type(screen.getByRole("textbox", { name: th["chat.edit"] }), "AIT เรียนกี่ปี{Enter}");
    expect(onEdit).toHaveBeenCalledWith("AIT เรียนกี่ปี");
    expect(box).not.toBeInTheDocument();
  });
});
