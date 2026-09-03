import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { localGhostTextProvider, useGhostText } from "./useGhostText";

const provider = localGhostTextProvider(() => ["AIT เรียนกี่หน่วยกิต", "what is DSBA about?"]);

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

describe("localGhostTextProvider", () => {
  it("completes a case-insensitive prefix of at least two characters", async () => {
    const c = new AbortController();
    expect(await provider("what is d", c.signal)).toBe("what is DSBA about?");
    expect(await provider("AIT เรียน", c.signal)).toBe("AIT เรียนกี่หน่วยกิต");
    expect(await provider("w", c.signal)).toBeNull();
    expect(await provider("nothing", c.signal)).toBeNull();
    expect(await provider("what is DSBA about?", c.signal)).toBeNull(); // nothing left to complete
  });
});

describe("useGhostText", () => {
  it("debounces, suggests, accepts on demand and dismisses", async () => {
    const { result, rerender } = renderHook(({ text }) => useGhostText({ text, enabled: true, provider }), {
      initialProps: { text: "what is d" },
    });
    expect(result.current.suggestion).toBeNull();
    await act(async () => {
      vi.advanceTimersByTime(299);
    });
    expect(result.current.suggestion).toBeNull();
    await act(async () => {
      vi.advanceTimersByTime(1);
      await Promise.resolve();
    });
    expect(result.current.suggestion).toBe("SBA about?");

    let accepted = "";
    act(() => {
      accepted = result.current.accept();
    });
    expect(accepted).toBe("what is DSBA about?");
    expect(result.current.suggestion).toBeNull();

    rerender({ text: "what is ds" });
    await act(async () => {
      vi.advanceTimersByTime(300);
      await Promise.resolve();
    });
    expect(result.current.suggestion).toBe("BA about?");
    act(() => result.current.dismiss());
    expect(result.current.suggestion).toBeNull();
  });

  it("clears immediately when the text changes and never suggests while disabled or empty", async () => {
    const { result, rerender } = renderHook(
      ({ text, enabled }) => useGhostText({ text, enabled, provider }),
      { initialProps: { text: "what is d", enabled: true } },
    );
    await act(async () => {
      vi.advanceTimersByTime(300);
      await Promise.resolve();
    });
    expect(result.current.suggestion).toBe("SBA about?");
    rerender({ text: "what is dx", enabled: true });
    expect(result.current.suggestion).toBeNull(); // stale suggestion hidden at once
    await act(async () => {
      vi.advanceTimersByTime(300);
      await Promise.resolve();
    });
    expect(result.current.suggestion).toBeNull();

    rerender({ text: "what is d", enabled: false });
    await act(async () => {
      vi.advanceTimersByTime(300);
      await Promise.resolve();
    });
    expect(result.current.suggestion).toBeNull();
    rerender({ text: "", enabled: true });
    await act(async () => {
      vi.advanceTimersByTime(300);
      await Promise.resolve();
    });
    expect(result.current.suggestion).toBeNull();
  });
});
