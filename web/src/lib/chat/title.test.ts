import { describe, expect, it } from "vitest";
import { autoTitle } from "./title";

describe("autoTitle", () => {
  it("keeps short titles and collapses whitespace", () => {
    expect(autoTitle("  AIT เรียนกี่ปี\n ")).toBe("AIT เรียนกี่ปี");
  });
  it("truncates English at a word boundary with an ellipsis", () => {
    const t = autoTitle("what courses does the AIT program teach in the first year of study?");
    expect(t.length).toBeLessThanOrEqual(41);
    expect(t.endsWith("…")).toBe(true);
    expect(t).toBe("what courses does the AIT program teach…");
  });
  it("truncates Thai (no spaces) at the limit", () => {
    const long = "หลักสูตรเทคโนโลยีปัญญาประดิษฐ์ต้องเรียนวิชาอะไรบ้างในปีหนึ่งและปีสอง";
    const t = autoTitle(long);
    expect(t).toBe(long.slice(0, 40) + "…");
  });
  it("honours a custom max", () => {
    expect(autoTitle("abcdefghij", 5)).toBe("abcde…");
  });
});
