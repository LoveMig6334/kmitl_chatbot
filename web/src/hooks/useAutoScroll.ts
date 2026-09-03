"use client";

import { useCallback, useEffect, useRef, useState, type RefObject } from "react";

const THRESHOLD = 48;

/**
 * Keeps a scroll container pinned to the bottom while `dep` changes (streaming), unless the
 * user has scrolled up — then `atBottom` turns false so the UI can offer "jump to latest".
 */
export function useAutoScroll(ref: RefObject<HTMLElement | null>, dep: unknown) {
  const [atBottom, setAtBottom] = useState(true);
  const pinned = useRef(true);

  const measure = useCallback(() => {
    const el = ref.current;
    if (!el) return;
    const near = el.scrollHeight - el.scrollTop - el.clientHeight <= THRESHOLD;
    pinned.current = near;
    setAtBottom(near);
  }, [ref]);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.addEventListener("scroll", measure, { passive: true });
    return () => el.removeEventListener("scroll", measure);
  }, [ref, measure]);

  const scrollToBottom = useCallback(
    (behavior: ScrollBehavior = "smooth") => {
      const el = ref.current;
      if (!el) return;
      el.scrollTo({ top: el.scrollHeight, behavior });
      pinned.current = true;
      setAtBottom(true);
    },
    [ref],
  );

  useEffect(() => {
    if (pinned.current) ref.current?.scrollTo({ top: ref.current.scrollHeight });
  }, [dep, ref]);

  return { atBottom, scrollToBottom };
}
