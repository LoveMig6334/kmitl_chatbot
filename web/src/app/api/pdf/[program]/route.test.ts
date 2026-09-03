// @vitest-environment node
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { GET, HEAD } from "./route";

const dir = mkdtempSync(path.join(tmpdir(), "pdf-"));
const bytes = Buffer.from("0123456789abcdef");
const ctx = (program: string) => ({ params: Promise.resolve({ program }) });
const ENV = process.env.PDF_DIR;

beforeAll(() => {
  writeFileSync(path.join(dir, "AIT.pdf"), bytes);
  process.env.PDF_DIR = dir;
});
afterAll(() => {
  process.env.PDF_DIR = ENV;
});

describe("GET /api/pdf/[program]", () => {
  it("serves the whole file with Accept-Ranges", async () => {
    const res = await GET(new Request("http://x/api/pdf/ait"), ctx("ait"));
    expect(res.status).toBe(200);
    expect(res.headers.get("accept-ranges")).toBe("bytes");
    expect(res.headers.get("content-type")).toBe("application/pdf");
    expect(Buffer.from(await res.arrayBuffer()).toString()).toBe("0123456789abcdef");
  });

  it("honours byte ranges (start-end, open-ended, suffix) and rejects bad ones", async () => {
    const range = async (r: string) => {
      const res = await GET(new Request("http://x/api/pdf/AIT", { headers: { range: r } }), ctx("AIT"));
      return { status: res.status, cr: res.headers.get("content-range"), body: Buffer.from(await res.arrayBuffer()).toString() };
    };
    expect(await range("bytes=2-5")).toEqual({ status: 206, cr: "bytes 2-5/16", body: "2345" });
    expect(await range("bytes=12-")).toEqual({ status: 206, cr: "bytes 12-15/16", body: "cdef" });
    expect(await range("bytes=-4")).toEqual({ status: 206, cr: "bytes 12-15/16", body: "cdef" });
    expect(await range("bytes=0-100")).toMatchObject({ status: 206, cr: "bytes 0-15/16" });
    expect((await range("bytes=99-")).status).toBe(416);
  });

  it("404s unknown programs and missing files; no path traversal possible", async () => {
    expect((await GET(new Request("http://x/api/pdf/x"), ctx("../../etc/passwd"))).status).toBe(404);
    expect((await GET(new Request("http://x/api/pdf/dsba"), ctx("dsba"))).status).toBe(404); // file absent in tmp dir
    const head = await HEAD(new Request("http://x/api/pdf/AIT"), ctx("AIT"));
    expect(head.status).toBe(200);
    expect(await head.text()).toBe("");
  });
});
