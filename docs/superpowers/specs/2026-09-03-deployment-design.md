# Deployment design — KMITL IT chatbot (free tier)

Date: 2026-09-03. Status: approved in chat; **revised the same day** (§ Revision) after Hugging Face
started requiring PRO for Docker Spaces.

## Goal
Put the chatbot on the public internet at zero hosting cost, with the real retriever
(Chroma + BGE-M3), the PDF source viewer, and Supabase sign-in, for the hackathon demo.

## Decisions (confirmed by the owner)
- Frontend (`web/`, Next.js 16) → **Vercel** Hobby, imported from GitHub, root directory `web`.
- Backend (FastAPI gatekeeper + RAG) → **Hugging Face Space, Docker SDK, free CPU basic**
  (2 vCPU, 16 GB RAM, sleeps after 48 h idle). Not a paid VM, not a tunnel from a laptop.
- Retriever: `RETRIEVER=chroma` (2,347 chunks, BGE-M3 dense + BM25, reranker off).
- Auth/history: Supabase (owner pauses one existing project to free a slot and creates a new one).
  Neon is not used: it provides Postgres only, and the app depends on Supabase Auth.
- PDFs are served **from the Space**, proxied by the existing Next route.
- Browser dashboards are not automated: the computer-use MCP is read-only for browsers, and the
  Claude-in-Chrome MCP is not connected. Setup goes through CLIs; the owner performs logins,
  token pastes and the Supabase project creation.

## Source control
- GitHub repo (new, private or public — owner's choice) is the single remote for both Vercel and
  the Space's sync. Branch `deploy` = `feat/real-retriever` merged into `feat/web-redesign` (after
  committing the current uncommitted redesign work) plus the deployment files below. PRs to `main`
  follow later; deployment does not wait for them.
- GitHub keeps ignoring `data/raw/` (PDFs) and `retrieval/data/chroma/`, `retrieval/data/bm25.pkl`.
- The Space is a second git remote (`hf`). The `deploy` branch is pushed there **with** the index
  and the four PDFs tracked by Git LFS (`.gitattributes`: `*.pdf`, `*.sqlite3`, `*.bin`, `*.pkl`).
  Those files are force-added only in commits on a Space-only branch `hf-deploy` (based on
  `deploy`) so GitHub history never contains them.

## Backend container (`Dockerfile` at repo root)
- `python:3.12-slim`, `uv` installed, `uv sync --frozen --no-dev` with the CPU-only torch index
  (`--extra-index-url https://download.pytorch.org/whl/cpu`) to keep the image well under the
  Space limit. Copies `api/`, `gatekeeper/`, `rag/`, `retrieval/` (code + data), `data/raw/` (LFS).
- Runs as uid 1000 (Spaces requirement), `HF_HOME=/data/hf` is not available on free tier, so the
  model cache lives in the image layer: the build step runs a tiny script that downloads
  `BAAI/bge-m3` at build time (keeps first boot to ~10 s instead of a 2.2 GB download per wake).
- `CMD uvicorn api.main:app --host 0.0.0.0 --port 7860`. Health at `GET /health`.
- Startup calls `ChromaRetriever.warm_up()` in a FastAPI lifespan hook when `RETRIEVER=chroma`
  (small change in `api/main.py`) so the first user request does not pay the model load.
- New FastAPI route `GET /pdf/{program}` serving `data/raw/<file>` with Range support (mirror of the
  Next route, using `FileResponse`/starlette static files). Program→file map reused from
  `rag`/`scripts.build_fixtures`.
- Space variables (public): `ANSWERER=rag`, `RETRIEVER=chroma`, `RERANK=0`, `RERANK_DEVICE=cpu`,
  `TRUST_PROXY=1`, `ALLOWED_ORIGINS=https://<vercel-app>.vercel.app,http://localhost:3000`,
  `RETRIEVAL_MIN_SCORE=0.0`, `THAILLM_BASE_URL`. Secrets: `THAILLM_API_KEY`.

## Frontend changes (`web/`)
- `app/api/pdf/[program]/route.ts`: when `PDF_BASE_URL` is set, proxy the request (including the
  `Range` header) to `${PDF_BASE_URL}/pdf/${program}` and stream the upstream response; otherwise
  keep the local-file path. Unit test for the proxy branch with a mocked `fetch`.
- `.env.example`: document `PDF_BASE_URL`.
- Vercel env: `FASTAPI_URL=https://<user>-<space>.hf.space`, `PDF_BASE_URL` (same),
  `NEXT_PUBLIC_APP_URL=https://<app>.vercel.app`, `NEXT_PUBLIC_SUPABASE_URL`,
  `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
- Supabase: owner creates the project, runs `web/supabase/migrations/0001_chats.sql` in the SQL
  editor, enables Email + Google providers, adds `https://<app>.vercel.app/auth/callback` to the
  redirect URLs. I never touch the remote project.

## Streaming considerations
- Vercel Hobby serverless functions cap at 60 s by default; the chat route streams, and
  `maxDuration` is raised to 300 (Hobby allows up to 300 with Fluid compute) in
  `app/api/chat/route.ts`. RAG answers with cold ThaiLLM calls take 20–60 s.
- The Space sleeps after inactivity; a sleeping Space returns a build page, which the Next route
  already treats as "backend down → mock stream with `meta.mock = true`". Documented as a known
  demo-day caveat: open the Space URL a few minutes before the demo.

## Verification
- Local: `docker build` is unavailable (no Docker on this Mac); the image is validated by the
  Space build log. Python tests `pytest -q` and web checks (`lint`, `typecheck`, `test`, `build`)
  must pass on `deploy` before pushing.
- Remote: `curl https://<space>.hf.space/health` → `answerer: rag`; `curl -N -X POST …/chat` streams
  `meta` + tokens + `citations`; `curl -I …/pdf/AIT` → 200 with `Accept-Ranges`. Then
  `scripts/smoke_web.py` pointed at the Vercel URL, and a manual browser check by the owner.

## Out of scope
Custom domain, analytics, Neon, keeping the Space awake with a cron ping (can be added later
with a free cron service), CI on GitHub.

## Revision (2026-09-03, evening) — Render free + hosted BGE-M3

Hugging Face now requires a PRO subscription for Docker Spaces on the free CPU tier, so the
backend cannot run there.  Confirmed decisions (owner):

- **Embeddings from an API instead of a local model.** `rag/remote_embedder.py:RemoteEmbedder`
  returns BGE-M3 dense vectors over HTTP; `retrieval/index.py:load_embedder` returns it when
  `EMBED_API` is set (`hf` = Hugging Face Inference, `openai` = any OpenAI-compatible
  `/embeddings` endpoint such as Cloudflare Workers AI or SiliconFlow).  Primary: **HF Inference**
  (owner's choice; zero extra accounts).  HF unloads the model when idle and answers 5xx for
  ~30–60 s, so the embedder retries with backoff and pings the API every `EMBED_KEEPALIVE_S`
  (240 s) while the server is up.  Vectors verified identical to the local model (cosine 1.0000
  on three probes), so the Chroma index is unchanged.
- **torch / FlagEmbedding become an optional extra** (`uv sync --extra local-embed`) used only
  for index building, `RERANK=1`, or local embedding.  The runtime image has no torch: ~600 MB
  image, ~260 MB RSS.  `jupyter` moved to the dev group for the same reason.
- **Host: Render free web service** (`render.yaml` blueprint, Docker runtime, Singapore, branch
  `deploy`, health check `/health`).  512 MB RAM, sleeps after 15 min idle, wakes in ~30 s,
  no card required.  `ANSWER_EVENT_TIMEOUT_S=120` so a cold embedding call does not trip the
  silence timeout.  Port from `$PORT` (Render sets it; default 10000).
- **Index + PDFs** (gitignored on GitHub, ~199 MB) are packed by `scripts/space/pack_assets.sh`
  into a **private Hugging Face dataset** `Bunnana/thai-llm-kmitl-assets` and downloaded at
  image build by `scripts/space/fetch_assets.sh` using `ASSETS_URL` + `HF_TOKEN`, which Render
  passes to the build as `ARG`s.  No Git LFS branch, no Space remote (the `hf` git remote and the
  earlier `hf-deploy` plan are dropped).
- **Competition note:** the user's question (only the question, never documents) is now sent to
  a third-party embedding API.  The same BGE-M3 model embedded it locally before; hosting moved,
  the model did not.  Recorded in README "Deployment" for the team to review against the rule.
- Frontend plan (Vercel, `PDF_BASE_URL` proxy, Supabase) is unchanged; `FASTAPI_URL` /
  `PDF_BASE_URL` point at `https://thai-llm-kmitl-api.onrender.com`.
