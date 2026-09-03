export const TITLE_MAX = 40;

/** Chat title from the first user message: single line, trimmed, cut at a word boundary with an ellipsis. */
export function autoTitle(text: string, max = TITLE_MAX): string {
  const oneLine = text.replace(/\s+/g, " ").trim();
  if (oneLine.length <= max) return oneLine;
  const cut = oneLine.slice(0, max);
  const lastSpace = cut.lastIndexOf(" ");
  // Thai has no spaces between words; only back off to a space when it keeps most of the text.
  const head = lastSpace >= max * 0.6 ? cut.slice(0, lastSpace) : cut;
  return `${head.trimEnd()}…`;
}
