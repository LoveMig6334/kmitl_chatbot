"use client";

import { useCallback, useEffect, useState } from "react";

/**
 * Returns the full text the user is probably typing (must start with `prefix`,
 * case-insensitively), or null. Swap this to plug in a model-backed source.
 */
export type GhostTextProvider = (prefix: string, signal: AbortSignal) => Promise<string | null>;

/** Prefix match over known questions (the user's past questions + the example list). */
export function localGhostTextProvider(candidates: () => readonly string[]): GhostTextProvider {
  return async (prefix) => {
    const p = prefix.toLowerCase();
    if (p.length < 2) return null;
    return candidates().find((c) => c.toLowerCase().startsWith(p) && c.length > prefix.length) ?? null;
  };
}

export interface UseGhostTextOptions {
  text: string;
  enabled: boolean;
  provider: GhostTextProvider;
  debounceMs?: number;
}

/**
 * Debounced inline completion. `suggestion` is the remainder to show after the caret;
 * `accept()` returns the full text, `dismiss()` clears it. Any change to `text` clears it
 * immediately (typing never waits on the provider); `enabled=false` cancels in-flight work.
 */
export function useGhostText({ text, enabled, provider, debounceMs = 300 }: UseGhostTextOptions) {
  // The completion remembers the text it was computed for, so a stale one is never shown.
  const [result, setResult] = useState<{ forText: string; completion: string } | null>(null);

  useEffect(() => {
    if (!enabled || !text.trim()) return;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      provider(text, controller.signal)
        .then((completion) => {
          if (controller.signal.aborted) return;
          const valid = completion && completion.toLowerCase().startsWith(text.toLowerCase()) && completion.length > text.length;
          setResult(valid ? { forText: text, completion } : null);
        })
        .catch(() => undefined);
    }, debounceMs);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [text, enabled, provider, debounceMs]);

  const current = result && result.forText === text ? result : null;
  const visible = current ? current.completion.slice(text.length) : null;

  /** Returns the completed text (the candidate's own casing) and clears the suggestion. */
  const accept = useCallback(() => {
    const full = current ? current.completion : text;
    setResult(null);
    return full;
  }, [text, current]);

  const dismiss = useCallback(() => setResult(null), []);

  return { suggestion: visible, accept, dismiss };
}
