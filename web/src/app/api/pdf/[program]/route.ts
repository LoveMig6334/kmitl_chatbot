import { createReadStream, promises as fs } from "node:fs";
import path from "node:path";
import { Readable } from "node:stream";
import { NextResponse } from "next/server";
import { PROGRAM_IDS, type ProgramId } from "@/lib/constants";
import { PDF_FILES as FILES, pdfBaseUrl, pdfDir } from "@/lib/pdf";

/**
 * Serves the curriculum PDFs for the source viewer with HTTP Range support, so the
 * browser's PDF plugin can jump to `#page=N` without downloading 60 MB first.
 * Files live outside the web app (`PDF_DIR`, default ../data/raw — gitignored). When `PDF_BASE_URL`
 * is set (Vercel → Hugging Face Space) the request is proxied to the backend's `GET /pdf/{program}`.
 */
function isProgram(v: string): v is ProgramId {
  return (PROGRAM_IDS as readonly string[]).includes(v);
}

export async function GET(req: Request, ctx: { params: Promise<{ program: string }> }) {
  const { program } = await ctx.params;
  const id = program.toUpperCase();
  if (!isProgram(id)) return NextResponse.json({ error: "unknown program" }, { status: 404 });

  const base = pdfBaseUrl();
  if (base) return proxy(base, id, req);

  const file = path.join(pdfDir(), FILES[id]);
  let size: number;
  try {
    size = (await fs.stat(file)).size;
  } catch {
    return NextResponse.json({ error: "pdf not available" }, { status: 404 });
  }

  const headers: Record<string, string> = {
    "Content-Type": "application/pdf",
    "Accept-Ranges": "bytes",
    "Cache-Control": "private, max-age=3600",
    "Content-Disposition": `inline; filename="${FILES[id]}"`,
  };

  const range = req.headers.get("range");
  const m = range && /^bytes=(\d*)-(\d*)$/.exec(range.trim());
  if (m && (m[1] || m[2])) {
    const start = m[1] ? Number(m[1]) : Math.max(0, size - Number(m[2]));
    const end = m[1] && m[2] ? Math.min(Number(m[2]), size - 1) : size - 1;
    if (start >= size || start > end) {
      return new Response(null, { status: 416, headers: { "Content-Range": `bytes */${size}` } });
    }
    const stream = Readable.toWeb(createReadStream(file, { start, end })) as ReadableStream;
    return new Response(stream, {
      status: 206,
      headers: { ...headers, "Content-Range": `bytes ${start}-${end}/${size}`, "Content-Length": String(end - start + 1) },
    });
  }

  const stream = Readable.toWeb(createReadStream(file)) as ReadableStream;
  return new Response(stream, { status: 200, headers: { ...headers, "Content-Length": String(size) } });
}

export async function HEAD(req: Request, ctx: { params: Promise<{ program: string }> }) {
  const res = await GET(new Request(req.url, { method: "GET" }), ctx);
  return new Response(null, { status: res.status, headers: res.headers });
}

const RELAYED = ["content-type", "content-length", "content-range", "accept-ranges", "content-disposition", "cache-control"];

async function proxy(base: string, id: ProgramId, req: Request): Promise<Response> {
  const headers: Record<string, string> = {};
  const range = req.headers.get("range");
  if (range) headers.range = range;
  let upstream: Response;
  try {
    upstream = await fetch(`${base}/pdf/${id}`, { method: "GET", headers, cache: "no-store" });
  } catch {
    return NextResponse.json({ error: "pdf not available" }, { status: 502 });
  }
  const out = new Headers();
  for (const h of RELAYED) {
    const v = upstream.headers.get(h);
    if (v) out.set(h, v);
  }
  return new Response(upstream.body, { status: upstream.status, headers: out });
}
