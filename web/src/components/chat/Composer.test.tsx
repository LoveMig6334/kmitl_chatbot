import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "@/test/render";
import { dictionaries } from "@/i18n";
import { Composer } from "./Composer";

const th = dictionaries.th;

function setup(props: Partial<React.ComponentProps<typeof Composer>> = {}) {
  const onSend = vi.fn();
  const onStop = vi.fn();
  const onScopeChange = vi.fn();
  const utils = renderWithProviders(
    <Composer
      onSend={onSend}
      onStop={onStop}
      generating={false}
      scope={["AIT", "DSBA", "BIT", "IT"]}
      onScopeChange={onScopeChange}
      pastQuestions={["AIT เรียนกี่หน่วยกิต"]}
      {...props}
    />,
  );
  return { onSend, onStop, onScopeChange, ...utils, box: () => screen.getByRole("textbox") as HTMLTextAreaElement };
}

describe("Composer keyboard", () => {
  it("Enter sends (trimmed) and clears; Shift+Enter inserts a newline; empty never sends", async () => {
    const { onSend, box } = setup();
    await userEvent.type(box(), "  สวัสดี  {Enter}");
    expect(onSend).toHaveBeenCalledWith("สวัสดี");
    expect(box().value).toBe("");
    await userEvent.type(box(), "a{Shift>}{Enter}{/Shift}b");
    expect(box().value).toBe("a\nb");
    expect(onSend).toHaveBeenCalledTimes(1);
    await userEvent.clear(box());
    await userEvent.type(box(), "{Enter}");
    expect(onSend).toHaveBeenCalledTimes(1);
  });

  it("Escape stops generation and the send button becomes Stop", async () => {
    const { onStop, box } = setup({ generating: true });
    expect(screen.getByRole("button", { name: th["chat.stop"] })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: th["chat.send"] })).toBeNull();
    box().focus();
    await userEvent.keyboard("{Escape}");
    expect(onStop).toHaveBeenCalledTimes(1);
  });

  it("scope picker shows the summary and lets the user narrow programs (never to zero)", async () => {
    const { onScopeChange } = setup({ scope: ["AIT"] });
    const trigger = screen.getByRole("button", { name: th["chat.scope"] });
    expect(trigger).toHaveTextContent("AIT");
    await userEvent.click(trigger);
    const boxes = await screen.findAllByRole("checkbox");
    expect(boxes).toHaveLength(4);
    await userEvent.click(boxes[0]); // unticking the only one is ignored
    expect(onScopeChange).not.toHaveBeenCalled();
    await userEvent.click(boxes[3]);
    expect(onScopeChange).toHaveBeenCalledWith(["AIT", "IT"]);
    await userEvent.click(screen.getByRole("button", { name: th["chat.scopeSelectAll"] }));
    expect(onScopeChange).toHaveBeenLastCalledWith(["AIT", "DSBA", "BIT", "IT"]);
  });
});

describe("Composer ghost text", () => {
  beforeEach(() => vi.useFakeTimers({ shouldAdvanceTime: true }));
  afterEach(() => vi.useRealTimers());

  it("suggests from past questions after the debounce, Tab accepts, other keys dismiss", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const { box } = setup();
    await user.type(box(), "AIT เรียน");
    await act(async () => {
      await vi.advanceTimersByTimeAsync(350);
    });
    expect(screen.getByText("กี่หน่วยกิต")).toBeInTheDocument();
    await user.keyboard("{Tab}");
    expect(box().value).toBe("AIT เรียนกี่หน่วยกิต");
    expect(screen.queryByText("กี่หน่วยกิต")).toBeNull();

    await user.clear(box());
    await user.type(box(), "AIT เร");
    await act(async () => {
      await vi.advanceTimersByTimeAsync(350);
    });
    expect(screen.getByText("ียนกี่หน่วยกิต")).toBeInTheDocument();
    await user.keyboard("{ArrowLeft}");
    expect(screen.queryByText("ียนกี่หน่วยกิต")).toBeNull();
  });
});
