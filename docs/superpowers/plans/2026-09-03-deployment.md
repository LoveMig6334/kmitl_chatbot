# Deployment (Vercel + Hugging Face Space) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the chatbot to the public internet at zero cost: FastAPI backend (gatekeeper + RAG with the Chroma/BGE-M3 retriever + PDF files) on a free Hugging Face Docker Space, Next.js frontend on Vercel, Supabase for auth.

**Architecture:** One `deploy` branch merges the two feature branches. The backend gains a `/pdf/{program}` route and an eager retriever warm-up, and is containerised with the BGE-M3 weights baked in. The frontend gains a `PDF_BASE_URL` proxy and a longer function timeout. A Space-only branch `hf-deploy` adds the LFS-tracked index + PDFs on top of `deploy` and is pushed to the Space remote; GitHub never sees those binaries.

**Tech Stack:** Python 3.12 + uv, FastAPI/uvicorn, chromadb + FlagEmbedding + torch (CPU), Next.js 16, `hf` CLI (huggingface_hub), Vercel CLI 59, Git LFS.

**Spec:** `docs/superpowers/specs/2026-09-03-deployment-design.md`

## Global Constraints

- GitHub remote: `origin` = `https://github.com/LoveMig6334/kmitl_chatbot.git` (already pushed `main`).
- Never commit `data/raw/*.pdf`, `retrieval/data/chroma/`, `retrieval/data/bm25.pkl`, or `.env` to a branch that is pushed to `origin`. They go only on `hf-deploy`, pushed only to the `hf` remote.
- The Space must listen on port **7860** and run as uid **1000**.
- Secrets (`THAILLM_API_KEY`, Supabase keys) are typed by the owner, never by the agent. The agent may read `.env` only to confirm a variable is present, never echo its value.
- Backend edits are limited to: `api/pdf.py` (new), `api/main.py` (mount route + lifespan), `Dockerfile`, `.dockerignore`, `scripts/space/`, `README.md` front matter, `.env.example`.
- Before the web task is finished: `npm run lint && npm run typecheck && npm test && npm run build` in `web/`. Before the backend tasks are finished: `uv run pytest -q`.
- Commit messages end with the Co-Authored-By / Claude-Session trailer used elsewhere in this repo.

---

### Task 1: Create the `deploy` branch (commit redesign work, merge the retriever branch)

**Files:**
- Modify: none by hand; git only.

**Interfaces:**
- Produces: branch `deploy` containing `rag/chroma_retriever.py`, `retrieval/` (code + chunks, no index) and the redesigned `web/`.

- [ ] **Step 1: Commit the uncommitted redesign work on `feat/web-redesign`**

```bash
cd /Users/thatt/Dev/ai_project/thai_llm_kmitl
git status --short          # expect the modified web/ files + CLAUDE.md + web/src/components/landing/; retrieval/ is untracked and stays out
git add CLAUDE.md web/
git commit -m "feat(web): landing page, guest access, composer/settings polish

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_018Ec3VZprXF6jm4EKF4cneE"
```

- [ ] **Step 2: Move the untracked local index out of the way of the merge**

The untracked `retrieval/data/{chroma,bm25.pkl}` already exists locally (built earlier) and is gitignored on `feat/real-retriever`. Confirm nothing else is untracked under `retrieval/`:

```bash
git status --short --untracked-files=all retrieval | grep -v "retrieval/data/chroma\|retrieval/data/bm25.pkl"
```
Expected: empty output. If files print, they are stale copies — `git stash -u` them before merging and drop the stash afterwards.

- [ ] **Step 3: Create `deploy` and merge**

```bash
git checkout -b deploy
git merge feat/real-retriever -m "merge: real retriever (chroma) into deploy

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_018Ec3VZprXF6jm4EKF4cneE"
```
Expected conflicts: `CLAUDE.md` and `.env.example` (both branches edited them). Resolve by keeping **both** sets of content: the retriever section from `feat/real-retriever` and the UI conventions section from `feat/web-redesign`. `git add` the resolved files, `git commit --no-edit`.

- [ ] **Step 4: Verify the merged tree**

```bash
git ls-files rag/chroma_retriever.py retrieval/retrieve.py web/src/components/landing | head
uv sync
uv run pytest -q
cd web && npm run lint && npm run typecheck && npm test && npm run build && cd ..
```
Expected: all three paths listed; pytest all pass; the four npm commands succeed.

- [ ] **Step 5: Push the branch to GitHub**

```bash
git push -u origin deploy
```

---

### Task 2: Backend `/pdf/{program}` route with Range support

**Files:**
- Create: `api/pdf.py`
- Modify: `api/main.py` (register the router inside `create_app`, after the `/health` route)
- Test: `tests/test_api_pdf.py`

**Interfaces:**
- Consumes: env `PDF_DIR` (default `data/raw`), program→file map.
- Produces: `GET`/`HEAD /pdf/{program}` returning `application/pdf`, `Accept-Ranges: bytes`, 206 for `Range`, 404 for unknown program or missing file, 416 for unsatisfiable range. Exported `PDF_FILES: dict[str, str]` and `pdf_dir() -> Path`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_api_pdf.py
"""GET /pdf/{program}: the curriculum PDFs for the frontend source viewer (Range-capable)."""
import pytest
from httpx import ASGITransport, AsyncClient

from api.answerer import StubAnswerer
from api.main import create_app
from tests.test_api import GATE_SETTINGS


@pytest.fixture
def pdf_app(tmp_path, monkeypatch):
    (tmp_path / "AIT.pdf").write_bytes(b"0123456789abcdef")
    monkeypatch.setenv("PDF_DIR", str(tmp_path))
    return create_app(answerer=StubAnswerer(), gate_settings=GATE_SETTINGS)


async def _get(app, path, **headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        return await c.get(path, headers=headers)


@pytest.mark.asyncio
async def test_pdf_whole_file(pdf_app):
    r = await _get(pdf_app, "/pdf/ait")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.headers["accept-ranges"] == "bytes"
    assert r.content == b"0123456789abcdef"


@pytest.mark.asyncio
async def test_pdf_ranges(pdf_app):
    r = await _get(pdf_app, "/pdf/AIT", range="bytes=2-5")
    assert (r.status_code, r.headers["content-range"], r.content) == (206, "bytes 2-5/16", b"2345")
    r = await _get(pdf_app, "/pdf/AIT", range="bytes=12-")
    assert (r.status_code, r.content) == (206, b"cdef")
    r = await _get(pdf_app, "/pdf/AIT", range="bytes=-4")
    assert (r.status_code, r.headers["content-range"]) == (206, "bytes 12-15/16")
    r = await _get(pdf_app, "/pdf/AIT", range="bytes=99-")
    assert r.status_code == 416


@pytest.mark.asyncio
async def test_pdf_404s(pdf_app):
    assert (await _get(pdf_app, "/pdf/nope")).status_code == 404
    assert (await _get(pdf_app, "/pdf/DSBA")).status_code == 404  # file absent
    async with AsyncClient(transport=ASGITransport(app=pdf_app), base_url="http://t") as c:
        head = await c.head("/pdf/AIT")
    assert head.status_code == 200 and head.content == b""
```

Check how `tests/test_api.py` marks async tests (it may use `pytest.mark.anyio` or an asyncio auto mode in `pyproject.toml`); mirror it exactly.

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_api_pdf.py -q`
Expected: FAIL — 404 (route missing) on the first test.

- [ ] **Step 3: Implement `api/pdf.py`**

```python
"""``GET /pdf/{program}`` — curriculum PDFs for the frontend source viewer.

Mirrors ``web/src/app/api/pdf/[program]/route.ts`` so the Vercel-hosted frontend can
proxy to this route (``PDF_BASE_URL``) when the PDFs are not on its own filesystem.
Files live in ``PDF_DIR`` (default ``data/raw``, gitignored on GitHub, LFS on the Space).
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from fastapi import APIRouter, Request, Response
from fastapi.responses import FileResponse, JSONResponse

router = APIRouter()

PDF_FILES: dict[str, str] = {"AIT": "AIT.pdf", "DSBA": "DSBA.pdf", "BIT": "IT_inter2565.pdf", "IT": "IT2565.pdf"}
_RANGE = re.compile(r"^bytes=(\d*)-(\d*)$")


def pdf_dir() -> Path:
    return Path(os.environ.get("PDF_DIR") or Path(__file__).resolve().parents[1] / "data" / "raw")


def _headers(name: str) -> dict[str, str]:
    return {
        "Accept-Ranges": "bytes",
        "Cache-Control": "private, max-age=3600",
        "Content-Disposition": f'inline; filename="{name}"',
    }


@router.api_route("/pdf/{program}", methods=["GET", "HEAD"])
async def pdf(program: str, request: Request) -> Response:
    name = PDF_FILES.get(program.upper())
    if name is None:
        return JSONResponse({"error": "unknown program"}, status_code=404)
    file = pdf_dir() / name
    if not file.is_file():
        return JSONResponse({"error": "pdf not available"}, status_code=404)
    size = file.stat().st_size
    headers = _headers(name)

    m = _RANGE.match((request.headers.get("range") or "").strip())
    if m and (m.group(1) or m.group(2)):
        start = int(m.group(1)) if m.group(1) else max(0, size - int(m.group(2)))
        end = min(int(m.group(2)), size - 1) if (m.group(1) and m.group(2)) else size - 1
        if start >= size or start > end:
            return Response(status_code=416, headers={"Content-Range": f"bytes */{size}"})
        headers["Content-Range"] = f"bytes {start}-{end}/{size}"
        headers["Content-Length"] = str(end - start + 1)
        if request.method == "HEAD":
            return Response(status_code=206, headers=headers, media_type="application/pdf")
        return Response(_read(file, start, end), status_code=206, headers=headers, media_type="application/pdf")

    if request.method == "HEAD":
        headers["Content-Length"] = str(size)
        return Response(status_code=200, headers=headers, media_type="application/pdf")
    return FileResponse(file, media_type="application/pdf", headers=headers)


def _read(file: Path, start: int, end: int) -> bytes:
    with file.open("rb") as fh:
        fh.seek(start)
        return fh.read(end - start + 1)
```

Note: range responses are read into memory. Browsers request ranges of a few hundred KB at a time for `#page=N`, so this is fine; whole-file requests stream via `FileResponse`.

- [ ] **Step 4: Register the router in `api/main.py`**

Add `from .pdf import router as pdf_router` to the imports and, right after the `@app.get("/health")` handler inside `create_app`, add:

```python
    app.include_router(pdf_router)
```

- [ ] **Step 5: Run the tests**

Run: `uv run pytest tests/test_api_pdf.py tests/test_api.py -q`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add api/pdf.py api/main.py tests/test_api_pdf.py
git commit -m "feat(api): GET /pdf/{program} with Range support for the hosted source viewer

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_018Ec3VZprXF6jm4EKF4cneE"
```

---

### Task 3: Eager retriever warm-up on startup

**Files:**
- Modify: `api/main.py` (`create_app`: lifespan)
- Test: `tests/test_api.py` (append one test)

**Interfaces:**
- Consumes: `ChromaRetriever.warm_up() -> float` (seconds), reachable as `answerer.retriever` on `RagAnswerer`.
- Produces: env `WARM_UP=1` → on startup, if the answerer has a `retriever` with a `warm_up` method, call it in a thread and log the seconds.

- [ ] **Step 1: Write the failing test** (append to `tests/test_api.py`)

```python
async def test_warm_up_runs_on_startup(monkeypatch):
    calls: list[str] = []

    class Retr:
        name = "chroma"
        def warm_up(self) -> float:
            calls.append("warm")
            return 0.01

    answerer = StubAnswerer()
    answerer.retriever = Retr()  # type: ignore[attr-defined]
    monkeypatch.setenv("WARM_UP", "1")
    app = create_app(answerer=answerer, gate_settings=GATE_SETTINGS)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t"):
        async with app.router.lifespan_context(app):
            pass
    assert calls == ["warm"]
```

Use the same async marker as the other tests in that file.

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_api.py::test_warm_up_runs_on_startup -q`
Expected: FAIL — `calls == []`.

- [ ] **Step 3: Implement the lifespan**

In `api/main.py`, add `from contextlib import asynccontextmanager` and, before `app = FastAPI(...)` inside `create_app`:

```python
    warm = _env_bool("WARM_UP")

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        retriever = getattr(answerer, "retriever", None)
        if warm and hasattr(retriever, "warm_up"):
            log.info("warming up retriever %s…", getattr(retriever, "name", "?"))
            secs = await asyncio.to_thread(retriever.warm_up)
            log.info("retriever ready in %.1fs", secs)
        yield
```

and change the constructor to `app = FastAPI(title="KMITL IT curriculum chat", version="0.1.0", lifespan=lifespan)`.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest -q`
Expected: all PASS.

- [ ] **Step 5: Document and commit**

Add to `.env.example`, in the API block: `WARM_UP=0                     # 1 = load the retriever (BGE-M3, Chroma) at startup instead of on the first request`.

```bash
git add api/main.py tests/test_api.py .env.example
git commit -m "feat(api): WARM_UP=1 loads the retriever at startup

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_018Ec3VZprXF6jm4EKF4cneE"
```

---

### Task 4: Frontend — PDF proxy via `PDF_BASE_URL` and chat route timeout

**Files:**
- Modify: `web/src/lib/pdf.ts` (add `pdfBaseUrl()`)
- Modify: `web/src/app/api/pdf/[program]/route.ts` (proxy branch)
- Modify: `web/src/app/api/chat/route.ts` (export `maxDuration`)
- Modify: `web/.env.example`
- Test: `web/src/app/api/pdf/[program]/route.test.ts`

**Interfaces:**
- Produces: when `PDF_BASE_URL` is set, `GET/HEAD /api/pdf/<program>` forwards to `${PDF_BASE_URL}/pdf/<PROGRAM>` with the `Range` header and returns the upstream status, body stream and the headers `content-type`, `content-length`, `content-range`, `accept-ranges`, `content-disposition`, `cache-control`.

- [ ] **Step 1: Write the failing test** (append to `route.test.ts`)

```ts
describe("GET /api/pdf/[program] with PDF_BASE_URL", () => {
  const calls: { url: string; range: string | null; method: string }[] = [];
  const realFetch = globalThis.fetch;
  beforeAll(() => {
    process.env.PDF_BASE_URL = "https://space.example/";
    globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
      const h = new Headers(init?.headers);
      calls.push({ url: String(input), range: h.get("range"), method: init?.method ?? "GET" });
      return new Response("2345", {
        status: 206,
        headers: { "content-type": "application/pdf", "content-range": "bytes 2-5/16", "accept-ranges": "bytes", "content-length": "4" },
      });
    }) as typeof fetch;
  });
  afterAll(() => {
    delete process.env.PDF_BASE_URL;
    globalThis.fetch = realFetch;
  });

  it("forwards Range to <PDF_BASE_URL>/pdf/<PROGRAM> and relays status + headers", async () => {
    const res = await GET(new Request("http://x/api/pdf/ait", { headers: { range: "bytes=2-5" } }), ctx("ait"));
    expect(calls.at(-1)).toEqual({ url: "https://space.example/pdf/AIT", range: "bytes=2-5", method: "GET" });
    expect(res.status).toBe(206);
    expect(res.headers.get("content-range")).toBe("bytes 2-5/16");
    expect(await res.text()).toBe("2345");
  });

  it("still 404s unknown programs without calling upstream", async () => {
    const before = calls.length;
    expect((await GET(new Request("http://x/api/pdf/x"), ctx("x"))).status).toBe(404);
    expect(calls.length).toBe(before);
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd web && npx vitest run src/app/api/pdf`
Expected: FAIL — the first new test reads the local temp file (200) instead of calling upstream.

- [ ] **Step 3: Implement**

`web/src/lib/pdf.ts` — append:

```ts
/** Backend base URL that serves GET /pdf/{program} (the Hugging Face Space). Unset = read PDF_DIR locally. */
export function pdfBaseUrl(): string | null {
  const v = process.env.PDF_BASE_URL?.trim();
  return v ? v.replace(/\/+$/, "") : null;
}
```

`route.ts` — import `pdfBaseUrl` alongside `PDF_FILES`/`pdfDir`, and insert right after the `isProgram` check in `GET`:

```ts
  const base = pdfBaseUrl();
  if (base) return proxy(base, id, req);
```

and add the helper at the bottom of the file:

```ts
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
```

`HEAD` already delegates to `GET`, so it proxies too.

`web/src/app/api/chat/route.ts` — add near the top-level constants:

```ts
// RAG answers (gate + retrieval + a ThaiLLM stream) can take up to a minute; Vercel's default is 60 s.
export const maxDuration = 300;
```

`web/.env.example` — under the Source viewer block add:

```
# When the PDFs are served by the backend (Hugging Face Space: GET /pdf/{program}), set this to the
# backend base URL and the route proxies to it instead of reading PDF_DIR.
#PDF_BASE_URL=https://<user>-<space>.hf.space
```

- [ ] **Step 4: Run the web checks**

Run: `cd web && npm run lint && npm run typecheck && npm test && npm run build`
Expected: all succeed.

- [ ] **Step 5: Commit**

```bash
git add web/src/lib/pdf.ts "web/src/app/api/pdf/[program]/route.ts" "web/src/app/api/pdf/[program]/route.test.ts" web/src/app/api/chat/route.ts web/.env.example
git commit -m "feat(web): proxy the PDF viewer to PDF_BASE_URL; 300 s chat route timeout

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_018Ec3VZprXF6jm4EKF4cneE"
```

---

### Task 5: Dockerfile for the Space

**Files:**
- Create: `Dockerfile`, `.dockerignore`, `scripts/space/download_models.py`
- Modify: `README.md` (Hugging Face front matter at the very top)

**Interfaces:**
- Produces: an image that starts `uvicorn api.main:app --host 0.0.0.0 --port 7860` with `ANSWERER=rag RETRIEVER=chroma WARM_UP=1` and BGE-M3 cached under `/home/user/.cache/huggingface`.

- [ ] **Step 1: `scripts/space/download_models.py`**

```python
"""Pre-download the embedding model at image build time so the Space boots without a 2.2 GB fetch."""
import os

from huggingface_hub import snapshot_download

model = os.environ.get("EMBED_MODEL", "BAAI/bge-m3")
path = snapshot_download(model, allow_patterns=["*.json", "*.safetensors", "*.txt", "*.model"])
print(f"cached {model} at {path}")
```

`snapshot_download` with these patterns skips the duplicate `pytorch_model.bin` (2.2 GB) and keeps `model.safetensors`; FlagEmbedding loads safetensors fine.

- [ ] **Step 2: `.dockerignore`**

```
.git
.venv
.cache
web
node_modules
docs
tests
notebooks
*.ipynb
retrieval/data/extracted
retrieval/docs
.env
```

- [ ] **Step 3: `Dockerfile`**

```dockerfile
# Hugging Face Space (Docker SDK, free CPU basic): FastAPI gatekeeper + RAG with the chroma retriever.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    HF_HOME=/home/user/.cache/huggingface \
    HF_HUB_DISABLE_TELEMETRY=1 \
    PORT=7860

RUN useradd -m -u 1000 user && apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /usr/local/bin/uv

WORKDIR /app
# 1. dependencies only (cached layer); CPU-only torch keeps the image ~3 GB smaller
COPY pyproject.toml uv.lock ./
RUN UV_TORCH_BACKEND=cpu uv sync --frozen --no-dev --no-install-project

# 2. model weights (cached layer, ~2.2 GB)
COPY scripts/space/download_models.py scripts/space/download_models.py
RUN mkdir -p $HF_HOME && python scripts/space/download_models.py && chown -R user:user /home/user

# 3. application code + index + PDFs (LFS on the Space)
COPY --chown=user:user . .
RUN uv sync --frozen --no-dev

USER user
ENV ANSWERER=rag RETRIEVER=chroma WARM_UP=1 RERANK=0 RERANK_DEVICE=cpu \
    RETRIEVAL_K=12 RETRIEVE_CAND_K=40 CONTEXT_TOKEN_BUDGET=6500 RETRIEVAL_MIN_SCORE_CHROMA=0.0 \
    PDF_DIR=/app/data/raw TRUST_PROXY=1
EXPOSE 7860
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "7860"]
```

If `uv.lock` does not exist on `deploy`, run `uv lock` first and commit it. `UV_TORCH_BACKEND=cpu` is the uv setting for selecting the CPU torch index; if the pinned uv version does not support it, replace that line with `uv pip install --python /opt/venv torch --index-url https://download.pytorch.org/whl/cpu` after `uv sync`.

- [ ] **Step 4: README front matter** — prepend to `README.md` (Spaces read it from the repo root):

```markdown
---
title: KMITL IT Curriculum Chat API
emoji: 🎓
colorFrom: orange
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
---
```

- [ ] **Step 5: Sanity check without Docker** (Docker is not installed on this Mac)

```bash
uv run python -c "import ast,sys; ast.parse(open('scripts/space/download_models.py').read()); print('ok')"
grep -c "^COPY\|^RUN" Dockerfile
```
The build itself is validated by the Space build log in Task 6.

- [ ] **Step 6: Commit**

```bash
git add Dockerfile .dockerignore scripts/space/download_models.py README.md
git commit -m "build: Dockerfile for the Hugging Face Space (BGE-M3 baked in, port 7860)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_018Ec3VZprXF6jm4EKF4cneE"
git push origin deploy
```

---

### Task 6: Create the Space and push `hf-deploy` (LFS index + PDFs)

**Files:**
- Create (on `hf-deploy` only): `.gitattributes`, force-added `data/raw/*.pdf`, `retrieval/data/chroma/**`, `retrieval/data/bm25.pkl`.

**Interfaces:**
- Consumes: `hf` CLI login (done), Space name chosen by the owner (default `thai-llm-kmitl`).
- Produces: `https://<user>-thai-llm-kmitl.hf.space` answering `/health`.

- [ ] **Step 1: Create the Space and add the remote**

```bash
HF_USER=$(uvx --from huggingface_hub hf auth whoami | head -1)
uvx --from huggingface_hub hf repos create thai-llm-kmitl --repo-type space --space_sdk docker
git remote add hf "https://huggingface.co/spaces/$HF_USER/thai-llm-kmitl"
```
If `hf repos create` does not accept `--space_sdk` in the installed version, use:
`uvx --from huggingface_hub python -c "from huggingface_hub import HfApi; HfApi().create_repo('thai-llm-kmitl', repo_type='space', space_sdk='docker', private=False)"`.

- [ ] **Step 2: Build `hf-deploy` with LFS-tracked binaries**

```bash
git lfs install --local
git checkout -b hf-deploy deploy
printf '*.pdf filter=lfs diff=lfs merge=lfs -text\n*.sqlite3 filter=lfs diff=lfs merge=lfs -text\n*.bin filter=lfs diff=lfs merge=lfs -text\n*.pkl filter=lfs diff=lfs merge=lfs -text\n' > .gitattributes
git add .gitattributes
git add -f data/raw/AIT.pdf data/raw/DSBA.pdf data/raw/IT2565.pdf data/raw/IT_inter2565.pdf retrieval/data/chroma retrieval/data/bm25.pkl
git commit -m "space: LFS index + curriculum PDFs (Space-only branch, never pushed to GitHub)"
git lfs ls-files | wc -l    # expect 4 PDFs + chroma files + bm25.pkl
```
Install `git-lfs` with `brew install git-lfs` if `git lfs` is missing.

- [ ] **Step 3: Push to the Space**

```bash
git push hf hf-deploy:main
```
Expected: LFS upload of ~220 MB, then the Space starts building. Watch the build:
`uvx --from huggingface_hub hf repos ... ` has no log command; open `https://huggingface.co/spaces/$HF_USER/thai-llm-kmitl?logs=build` in the browser (owner) or poll:

```bash
uvx --from huggingface_hub python -c "from huggingface_hub import HfApi; print(HfApi().get_space_runtime('$HF_USER/thai-llm-kmitl').stage)"
```
until it prints `RUNNING`. A build takes 10–20 minutes (torch + model download).

- [ ] **Step 4: Variables and secrets** — variables by the agent, the secret by the owner:

```bash
uvx --from huggingface_hub python - <<'EOF'
from huggingface_hub import HfApi
api = HfApi(); rid = "$HF_USER/thai-llm-kmitl"
for k, v in {
    "THAILLM_BASE_URL": "http://thaillm.or.th/api/v1",
    "ALLOWED_ORIGINS": "http://localhost:3000",   # Vercel URL appended in Task 7
    "RATE_LIMIT_PER_MINUTE": "30",
}.items():
    api.add_space_variable(rid, k, v)
EOF
```
Owner runs (reads the key from `.env`, never printed):
```
! uvx --from huggingface_hub python -c "from huggingface_hub import HfApi; import dotenv; v=dotenv.dotenv_values('.env')['THAILLM_API_KEY']; HfApi().add_space_secret('<HF_USER>/thai-llm-kmitl','THAILLM_API_KEY',v)"
```

- [ ] **Step 5: Verify**

```bash
curl -s https://$HF_USER-thai-llm-kmitl.hf.space/health
curl -sI https://$HF_USER-thai-llm-kmitl.hf.space/pdf/AIT | head -5
curl -sN -X POST https://$HF_USER-thai-llm-kmitl.hf.space/chat -H 'content-type: application/json' -d '{"message":"AIT เรียนกี่ปี"}' | head -20
```
Expected: `{"status":"ok","answerer":"rag",…}`; `200` with `accept-ranges: bytes`; SSE `meta` event followed by tokens and `citations`.

---

### Task 7: Vercel project + Supabase wiring

**Files:** none in the repo (Vercel CLI + env only).

**Interfaces:**
- Consumes: Space URL from Task 6; Supabase URL + anon key from the owner; GitHub repo `LoveMig6334/kmitl_chatbot`.
- Produces: `https://<project>.vercel.app`.

- [ ] **Step 1: Link and connect Git**

```bash
cd web
npx vercel link --yes --project thai-llm-kmitl
npx vercel git connect https://github.com/LoveMig6334/kmitl_chatbot.git
```
Then set **Root Directory = `web`** and **Production Branch = `deploy`**: `npx vercel project` has no flag for these, so the owner sets them in Vercel → Project → Settings → General (Root Directory) and Settings → Git (Production Branch). The agent verifies with a screenshot of Chrome.

- [ ] **Step 2: Environment variables** (production + preview)

```bash
SPACE=https://$HF_USER-thai-llm-kmitl.hf.space
for env in production preview; do
  echo "$SPACE" | npx vercel env add FASTAPI_URL $env
  echo "$SPACE" | npx vercel env add PDF_BASE_URL $env
done
```
Owner adds (values from the Supabase dashboard; the anon key is public but the owner types it):
```
! cd web && npx vercel env add NEXT_PUBLIC_SUPABASE_URL production
! cd web && npx vercel env add NEXT_PUBLIC_SUPABASE_ANON_KEY production
```

- [ ] **Step 3: First deploy and app URL**

```bash
npx vercel deploy --prod
```
Take the printed URL `https://thai-llm-kmitl-<hash>.vercel.app` / alias `https://thai-llm-kmitl.vercel.app`; then
```bash
echo "https://thai-llm-kmitl.vercel.app" | npx vercel env add NEXT_PUBLIC_APP_URL production
```
and update the Space variable `ALLOWED_ORIGINS` to `https://thai-llm-kmitl.vercel.app,http://localhost:3000` (same `add_space_variable` call as Task 6 Step 4; it overwrites). Redeploy once more with `npx vercel deploy --prod`.

- [ ] **Step 4: Supabase (owner, in the dashboard)**
1. SQL editor → paste `web/supabase/migrations/0001_chats.sql` → run.
2. Authentication → Providers → enable Email and Google.
3. Authentication → URL Configuration → Site URL `https://thai-llm-kmitl.vercel.app`; add redirect `https://thai-llm-kmitl.vercel.app/auth/callback`.

---

### Task 8: End-to-end verification

- [ ] **Step 1: Backend from the deployed frontend**

```bash
uv run python scripts/smoke_web.py --web https://thai-llm-kmitl.vercel.app --api https://$HF_USER-thai-llm-kmitl.hf.space
```
The `--fastapi-log` check is local-only; pass no log path and accept that the disconnect assertion is skipped (or reads as not-applicable) — report what the script prints.

- [ ] **Step 2: Browser check (screenshot only)**
Owner opens `https://thai-llm-kmitl.vercel.app/chat?q=AIT เรียนกี่ปี`; agent screenshots Chrome to confirm the streamed answer, citation chips and the PDF panel opening from the Space.

- [ ] **Step 3: Record**
Append a "Deployment" section to `README.md` (URLs, which branch deploys where, the `hf-deploy` LFS rule, the Space sleep caveat) and commit on `deploy`; push to `origin`; merge `deploy` into `hf-deploy` and push to `hf` again so both remotes hold the same code.
