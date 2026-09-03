---
title: KMITL IT Curriculum Chat API
emoji: 🎓
colorFrom: orange
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
---

# thai_llm_kmitl

RAG chatbot for the **KMITL Faculty of Information Technology** Open House: answers
high-school students' questions about the four B.Sc. programs (AIT, DSBA, BIT, IT)
from the official curriculum documents. Competition rule: **only ThaiLLM models**
may read, analyse or answer anything at runtime (chat completions only, no embeddings).

## Quickstart

```bash
uv sync                                  # Python >= 3.12; installs runtime + dev deps
cp .env.example .env                     # fill in THAILLM_API_KEY
uv run pytest -q                         # pure-function + mocked tests, no network
uv run ruff check                        # lint
```

Run the API (stub answerer — real event shapes, fake answer, no retrieval):

```bash
ANSWERER=stub uv run uvicorn api.main:app --reload      # http://localhost:8000
ANSWERER=rag RETRIEVER=fixture uv run uvicorn api.main:app --reload   # real answer layer over 120 real curriculum passages (tests/fixtures/chunks.jsonl)
curl -N localhost:8000/chat -H 'content-type: application/json' \
     -d '{"message": "หลักสูตร AIT เรียนกี่หน่วยกิต"}'
curl localhost:8000/health
```

## Run the full stack locally

Frontend (`web/`, Next.js) → `POST /api/chat` (Next route) → FastAPI `POST /chat` (gate → RAG, SSE).

One command (starts both, Ctrl-C stops both, logs in `.cache/dev/`):

```bash
scripts/dev.sh                     # ANSWERER=rag RETRIEVER=fixture on :8000, Next.js on :3000
```

Or two terminals:

```bash
# terminal A — backend
ANSWERER=rag RETRIEVER=fixture uv run uvicorn api.main:app --port 8000
# terminal B — frontend
cd web && npm install && FASTAPI_URL=http://localhost:8000 npm run dev
```

Open http://localhost:3000/chat. Frontend env lives in `web/.env.example` (`FASTAPI_URL` is
server-side only; the app falls back to a mock stream if the backend is down).

Smoke test through the Next.js route (both servers running):

```bash
uv run python scripts/smoke_web.py      # in-scope (deltas + citations + done), off-topic (no citations), abort → backend logs "disconnected"
```

## Evals

| command | what it measures |
|---|---|
| `uv run python scripts/eval_gatekeeper.py` | gatekeeper classification (rules + ThaiLLM, responses cached in `.cache/eval/`) |
| `uv run python scripts/eval_gatekeeper.py --dry-run` | rule layer only, 0 API calls |
| `uv run python scripts/eval_gatekeeper.py --no-rules` | LLM-only floor |
| `uv run python scripts/eval_gatekeeper.py --level easy --show-all` | one level, print every row |
| `uv run python scripts/eval_answers.py` | answer layer faithfulness (facts, number grounding, citations, not-found, language, leakage) against `tests/fixtures/chunks.jsonl` |

Cases live in `tests/eval_questions.csv` (gatekeeper, tab-separated) and
`tests/eval_answers.jsonl` (answer layer); see `CLAUDE.md` for the columns.
`tests/eval_blind.csv`, if present, is a human-written held-out set — never open or edit it.

## Fixtures

`tests/fixtures/chunks.jsonl` holds real passages extracted from the four curriculum
PDFs in `data/raw/` (gitignored — obtain them separately). Rebuild and audit with:

```bash
uv run python scripts/build_fixtures.py      # PDFs -> chunks.jsonl (+ pua_maps.json)
uv run python scripts/audit_fixtures.py      # 0 suspicious chunks expected
```

Gold facts hand-checked against the PDFs: `docs/gold-facts.md`.

## Where the contracts live

| contract | file | consumer |
|---|---|---|
| `GateDecision` (v2) | `gatekeeper/schema.py` | RAG answerer, API |
| `/chat` SSE events, `/health` | `docs/api-contract.md` | Next.js frontend |
| `Answerer` protocol, `AnswerEvent`, `Citation` | `api/answerer.py` | implemented by `rag/answerer.py:RagAnswerer` |
| `Retriever` protocol, `Chunk` | `rag/retriever.py` | retrieval teammate implements `rag/qdrant_retriever.py:QdrantRetriever` |
| Gatekeeper behaviour | `docs/gatekeeper-spec.md` | — |

## Layout

```
src/thai_llm_kmitl/   model registry + demo client
gatekeeper/           classification + routing (rules → one ThaiLLM call → fallback)
api/                  FastAPI app: POST /chat (SSE), GET /health
rag/                  answer layer: Retriever seam, RagAnswerer, prompts, context budget, checks
scripts/              eval harnesses
tests/                pytest (no network) + eval data
docs/                 specs and contracts
```

Environment variables: see `.env.example` (every variable the code reads is listed there).

## Deployment (free tier)

| part | where | source |
|---|---|---|
| Frontend (`web/`) | Vercel, project `thai-llm-kmitl` → https://thai-llm-kmitl.vercel.app | GitHub `LoveMig6334/kmitl_chatbot`, branch `deploy`, Root Directory `web` |
| Backend (FastAPI) | Render free web service `thai-llm-kmitl-api` → https://thai-llm-kmitl-api.onrender.com | same repo/branch via `render.yaml` (Docker) |
| Auth + chat history | Supabase (`web/supabase/migrations/0001_chats.sql`) | keys in Vercel env |
| Retrieval index + PDFs | private Hugging Face dataset `Bunnana/thai-llm-kmitl-assets` (`assets.tar.gz`, ~199 MB) | `scripts/space/pack_assets.sh` → `hf upload`; fetched at image build by `scripts/space/fetch_assets.sh` (`ASSETS_URL` + `HF_TOKEN`) |

**Backend design on 512 MB.**  The image has no torch: BGE-M3 *query* vectors come from a hosted API
(`rag/remote_embedder.py`, `EMBED_API=openai` → Cloudflare Workers AI `@cf/baai/bge-m3`, or
`EMBED_API=hf` → Hugging Face Inference).  Vectors were verified identical to the local model
(cosine 1.0000), so the Chroma index built with `uv sync --extra local-embed` is used unchanged.
If the API is cold, down or misconfigured, `retrieval/retrieve.py:search` falls back to BM25-only
ranking and the bot still answers (a `dense layer unavailable` line appears in the logs).  Check a
provider before pointing Render at it: `EMBED_API=… EMBED_API_URL=… EMBED_API_KEY=… uv run python
scripts/check_embed_api.py`.

**Env on Render** (`render.yaml`; secrets set in the dashboard): `THAILLM_API_KEY`, `HF_TOKEN` (read
token, used for the asset download), `EMBED_API_URL` = `https://api.cloudflare.com/client/v4/accounts/<ACCOUNT_ID>/ai/v1`,
`EMBED_API_KEY` (Cloudflare token with *Workers AI* permission), `ALLOWED_ORIGINS` (must list the Vercel
domain).  **Env on Vercel**: `FASTAPI_URL`, `PDF_BASE_URL` (both the Render URL — the PDF viewer proxies
`GET /pdf/{program}`), `NEXT_PUBLIC_APP_URL`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`.

**Demo-day caveats.**  Render free sleeps after 15 min idle and wakes in ~30 s (the first request may
see the mock reply from the Next route); open https://thai-llm-kmitl-api.onrender.com/health a few
minutes before presenting.  Hugging Face Docker Spaces are no longer free (PRO required) — that is why
the backend is on Render.

**Competition note.**  With a hosted embedder the user's *question* (never the documents) is sent to
a third-party embedding API.  The same BGE-M3 model embedded it locally before; only the hosting
moved.  Whether this fits the "only ThaiLLM touches user messages" rule is for the team to decide;
`EMBED_API` unset + `uv sync --extra local-embed` restores fully local embedding on a bigger machine.

**Re-deploying.**  Push to `deploy` (Vercel and Render both auto-deploy), or `npx vercel deploy --prod`
from the repo root.  Rebuilt index → `sh scripts/space/pack_assets.sh && uvx --from huggingface_hub hf
upload Bunnana/thai-llm-kmitl-assets .cache/assets.tar.gz assets.tar.gz --repo-type dataset`, then
"Clear build cache & deploy" on Render.
