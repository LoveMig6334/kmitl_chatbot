import "@testing-library/jest-dom/vitest";
import { afterEach, vi } from "vitest";
import { cleanup } from "@testing-library/react";

const hasDom = typeof window !== "undefined";

afterEach(() => {
  cleanup();
  if (hasDom) {
    window.localStorage.clear();
    // the locale cookie mirror must not leak between tests
    for (const c of document.cookie.split(";")) {
      const name = c.split("=")[0]?.trim();
      if (name) document.cookie = `${name}=; path=/; max-age=0`;
    }
  }
});

if (hasDom) {

// jsdom has no matchMedia; default to a light system theme.
if (!window.matchMedia) {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }),
  });
}

// Radix needs these in jsdom.
if (!Element.prototype.hasPointerCapture) {
  Element.prototype.hasPointerCapture = () => false;
  Element.prototype.setPointerCapture = () => {};
  Element.prototype.releasePointerCapture = () => {};
}
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = () => {};
}
if (!window.ResizeObserver) {
  window.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver;
}
}
