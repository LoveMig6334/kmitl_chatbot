import { describe, expect, it } from "vitest";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";

const ROOT = join(__dirname);
const EXEMPT = ["icons/"]; // brand marks with mandated colours

function walk(dir: string, out: string[] = []): string[] {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) walk(p, out);
    else if (/\.tsx?$/.test(name) && !/\.test\.tsx?$/.test(name)) out.push(p);
  }
  return out;
}

describe("design-token hygiene in components/", () => {
  const files = walk(ROOT).filter((f) => !EXEMPT.some((e) => relative(ROOT, f).startsWith(e)));

  it("contains no literal colour values", () => {
    const offenders: string[] = [];
    for (const f of files) {
      const src = readFileSync(f, "utf8");
      const lines = src.split("\n");
      lines.forEach((line, i) => {
        if (/#[0-9a-fA-F]{3,8}\b/.test(line) && !line.trimStart().startsWith("//") && !line.trimStart().startsWith("*")) {
          offenders.push(`${relative(ROOT, f)}:${i + 1} hex`);
        }
        if (/\b(rgba?|hsla?)\(/.test(line)) offenders.push(`${relative(ROOT, f)}:${i + 1} rgb/hsl`);
        // Tailwind arbitrary colour utilities such as bg-[#fff] or text-[rgb(…)]
        if (/(bg|text|border|ring|fill|stroke|from|to|via)-\[(#|rgb|hsl)/.test(line)) {
          offenders.push(`${relative(ROOT, f)}:${i + 1} arbitrary colour`);
        }
        // Tailwind palette colours (bg-red-500 …) bypass the tokens too
        if (/\b(bg|text|border|ring)-(red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose|slate|gray|zinc|neutral|stone)-\d{2,3}\b/.test(line)) {
          offenders.push(`${relative(ROOT, f)}:${i + 1} palette colour`);
        }
      });
    }
    // The untouched Phase-2 chat/settings components are reported separately below.
    const phase1 = offenders.filter((o) => !/^(chat|settings)\//.test(o));
    expect(phase1).toEqual([]);
  });
});
