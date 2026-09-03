import { render, type RenderOptions } from "@testing-library/react";
import { AppProviders } from "@/providers/AppProviders";

export function renderWithProviders(ui: React.ReactElement, options?: RenderOptions) {
  return render(ui, { wrapper: AppProviders, ...options });
}

/** Every user-visible string on the page: text nodes, placeholders, aria-labels, titles. */
export function visibleStrings(root: HTMLElement = document.body): string[] {
  const out: string[] = [];
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    const text = node.textContent?.trim() ?? "";
    if (text && !/^[\s·•|]+$/.test(text)) out.push(text);
  }
  root.querySelectorAll<HTMLElement>("[placeholder], [aria-label], [title]").forEach((el) => {
    for (const attr of ["placeholder", "aria-label", "title"]) {
      const v = el.getAttribute(attr)?.trim();
      if (v) out.push(v);
    }
  });
  return out;
}
