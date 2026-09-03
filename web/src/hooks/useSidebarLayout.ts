"use client";

import { useCallback, useMemo, useRef, useState, useSyncExternalStore } from "react";

const KEY = "kmitl.sidebar";
const EVENT = "kmitl:sidebar";
export const SIDEBAR_MIN = 220;
export const SIDEBAR_MAX = 420;
export const SIDEBAR_DEFAULT = 280;

interface Layout {
  width: number;
  collapsed: boolean;
}

function clamp(n: number) {
  return Math.min(SIDEBAR_MAX, Math.max(SIDEBAR_MIN, Math.round(n)));
}

function readRaw() {
  try {
    return window.localStorage.getItem(KEY) ?? "";
  } catch {
    return "";
  }
}
function parse(raw: string): Layout {
  try {
    const p = raw ? (JSON.parse(raw) as Partial<Layout>) : {};
    return { width: clamp(Number(p.width) || SIDEBAR_DEFAULT), collapsed: p.collapsed === true };
  } catch {
    return { width: SIDEBAR_DEFAULT, collapsed: false };
  }
}
function write(layout: Layout) {
  try {
    window.localStorage.setItem(KEY, JSON.stringify(layout));
  } catch {
    /* ignore */
  }
  window.dispatchEvent(new Event(EVENT));
}
function subscribe(cb: () => void) {
  window.addEventListener(EVENT, cb);
  window.addEventListener("storage", cb);
  return () => {
    window.removeEventListener(EVENT, cb);
    window.removeEventListener("storage", cb);
  };
}
const serverRaw = () => "";

/** Desktop sidebar width (drag or arrow keys) and collapsed state, persisted per browser. */
export function useSidebarLayout() {
  const raw = useSyncExternalStore(subscribe, readRaw, serverRaw);
  const stored = useMemo(() => parse(raw), [raw]);
  const [dragWidth, setDragWidth] = useState<number | null>(null);
  const dragging = useRef<{ startX: number; startWidth: number } | null>(null);
  const width = dragWidth ?? stored.width;
  const collapsed = stored.collapsed;

  const startResize = useCallback(
    (e: React.PointerEvent) => {
      e.preventDefault();
      dragging.current = { startX: e.clientX, startWidth: width };
      const onMove = (ev: PointerEvent) => {
        if (dragging.current) setDragWidth(clamp(dragging.current.startWidth + ev.clientX - dragging.current.startX));
      };
      const onUp = (ev: PointerEvent) => {
        if (dragging.current) {
          write({ width: clamp(dragging.current.startWidth + ev.clientX - dragging.current.startX), collapsed: false });
        }
        dragging.current = null;
        setDragWidth(null);
        window.removeEventListener("pointermove", onMove);
        window.removeEventListener("pointerup", onUp);
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
      };
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
      window.addEventListener("pointermove", onMove);
      window.addEventListener("pointerup", onUp);
    },
    [width],
  );

  const onResizeKey = useCallback(
    (e: React.KeyboardEvent) => {
      const step = e.shiftKey ? 40 : 16;
      let next = width;
      if (e.key === "ArrowLeft") next = clamp(width - step);
      else if (e.key === "ArrowRight") next = clamp(width + step);
      else if (e.key === "Home") next = SIDEBAR_MIN;
      else if (e.key === "End") next = SIDEBAR_MAX;
      else return;
      e.preventDefault();
      write({ width: next, collapsed });
    },
    [width, collapsed],
  );

  const collapse = useCallback(() => write({ width, collapsed: true }), [width]);
  const expand = useCallback(() => write({ width, collapsed: false }), [width]);

  return { width, collapsed, min: SIDEBAR_MIN, max: SIDEBAR_MAX, startResize, onResizeKey, collapse, expand };
}
