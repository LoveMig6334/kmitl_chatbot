# thai_llm_kmitl — project notes for Claude

## Competition rule (hard constraint)
Only **ThaiLLM** models may read, analyse or answer anything at runtime. Every
call that touches a user message must go through the ThaiLLM OpenAI-compatible
chat API (`/chat/completions` only — there is no embeddings endpoint).
Client config lives in `src/main.py` / `src/thai_llm_kmitl/models.py`
(`THAILLM_API_KEY`, `THAILLM_BASE_URL` in `.env`). Default model:
`openthaigpt-thaillm-8b-instruct-v7.2` (override with `GATEKEEPER_MODEL`).

Specs: `docs/gatekeeper-spec.md` (gatekeeper), `docs/api-contract.md` (HTTP API for the frontend).
Answer layer (RAG): `rag/` — see the section at the end of this file.

## Scope
ONE faculty — **คณะเทคโนโลยีสารสนเทศ สจล. / Faculty of Information Technology, KMITL**
(`FACULTY = "IT"`). The scope unit is the **program**; four B.Sc. programs are
defined in `gatekeeper/config.py:PROGRAMS`:

| id | Thai | English | version |
|---|---|---|---|
| AIT | สาขาวิชาเทคโนโลยีปัญญาประดิษฐ์ | Artificial Intelligence Technology | หลักสูตรใหม่ พ.ศ. 2566 |
| DSBA | สาขาวิชาวิทยาการข้อมูลและการวิเคราะห์เชิงธุรกิจ | Data Science and Business Analytics | หลักสูตรปรับปรุง พ.ศ. 2565 |
| BIT | สาขาวิชาเทคโนโลยีสารสนเทศทางธุรกิจ (หลักสูตรนานาชาติ) | Business Information Technology (International Program) | หลักสูตรปรับปรุง พ.ศ. 2565 |
| IT | สาขาวิชาเทคโนโลยีสารสนเทศ | Information Technology | หลักสูตรปรับปรุง พ.ศ. 2565 |

Disambiguation (implemented in `gatekeeper/rules.py:resolve_programs`):
bare "IT"/"ไอที" is the program only next to สาขา/หลักสูตร/ปกติ/2565 (else it
means the faculty → `programs=[]`); อินเตอร์/inter/นานาชาติ → BIT, never IT;
other KMITL faculties (วิศวะ, สถาปัตย์, บริหารธุรกิจ, …) → `out_of_scope_kmitl` — the redirect names the
faculty and its website (`gatekeeper/config.py:OTHER_KMITL_FACULTIES`, `url=None` → www.kmitl.ac.th); questions
naming no program are still `in_scope` with `programs=[]` (RAG searches all).

## Gatekeeper (`gatekeeper/`)
Receives every message first and either forwards it to RAG or replies directly.

Routing, cheapest first — **rules decide only when near-certain, else abstain**:
1. `rules.py` — deterministic layer (0 API calls): injection patterns (TH/EN/ZH),
   pure smalltalk (`smalltalk.py`), other-university names (abstains if our faculty/program/KMITL
   is also named; a generic field name like "data science" next to another university does not count),
   other KMITL faculties, KMITL logistics topics, obvious everyday topics,
   program aliases, 8-digit course codes.
2. `llm.py` + `prompts.py` — one ThaiLLM classification call, strict JSON,
   user text wrapped in `<user_message>` delimiters and treated as data.
   `parsing.py` strips `<think>` blocks / code fences and repairs truncated JSON.
3. Fallback — after one retry (timeout or bad JSON) default to `in_scope`
   with empty metadata (better to attempt an answer than wrongly refuse).

Config env: `GATEKEEPER_MODEL`, `GATEKEEPER_TIMEOUT_S` (default 8),
`GATEKEEPER_MAX_TOKENS` (default 1024 — the model thinks first; 512 truncated ~4% of Thai rows),
`GATEKEEPER_CACHE_DIR` (eval only).

### `GateDecision` contract (`gatekeeper/schema.py`, `CONTRACT_VERSION = 2`) — keep stable
```python
FACULTY = "IT"

class GateDecision(BaseModel):
    category: Literal["in_scope", "off_topic_general", "off_topic_other_university",
                      "out_of_scope_kmitl", "injection_or_abuse", "greeting_smalltalk"]
    language: Literal["th", "en", "zh", "other"]
    programs: list[Literal["AIT", "DSBA", "BIT", "IT"]]  # [] = none named -> search all
    course_codes: list[str]      # regex-extracted, e.g. ["06016317"]
    question_kind: Literal["fact_lookup", "descriptive", "comparison"] | None
    direct_reply: str | None     # filled ONLY when category != in_scope
    confidence: float
    decided_by: Literal["rule", "llm", "fallback"]
    model_used: str | None
    latency_ms: int
    # properties (not serialised): .faculty == "IT", .program (single named program or None)
```
v1 → v2: `faculty` and `program` fields were removed in favour of `programs`.
2026-09-02 (additive): `greeting_smalltalk` = greetings / thanks / acks / farewells /
bot-identity questions / vague help openers ("ช่วยหน่อย", "ถามได้ไหม") **with no answerable
content**. Mixed messages ("สวัสดีครับ AIT เรียนกี่ปี") and vague-but-on-topic openers
("อยากรู้เรื่องเรียนต่อที่นี่") are `in_scope`. Its `direct_reply` is a warm welcome (what the bot
does + 2–3 rotating example questions, seeded by the message hash) — never a refusal.
Rules: `gatekeeper/smalltalk.py` (`detect_smalltalk` = whole message must be content-free after
stripping emoji/particles/laughter; `smalltalk_kind` picks the template greeting/thanks/ack/
farewell/identity/help). Web side: add the value to `ChatMeta.category` in `web/src/lib/ai.ts`.
Entry point: `async def gate(message: str, scope_filter: list[str] | None = None) -> GateDecision`
(`gatekeeper.gate_sync` for blocking code). `scope_filter` = program ids the
user ticked; it narrows program resolution and never causes a refusal.
RAG should answer in `decision.language` when `category == "in_scope"`.

### Running the eval
```
python scripts/eval_gatekeeper.py                # rules + LLM (cached)
python scripts/eval_gatekeeper.py --level easy   # easy rows only
python scripts/eval_gatekeeper.py --dry-run      # rule layer only, no API calls
python scripts/eval_gatekeeper.py --no-rules     # LLM-only: the floor when rules miss
python scripts/eval_gatekeeper.py --no-cache     # bypass .cache/eval/
python scripts/eval_gatekeeper.py --model typhoon-s-thaillm-8b-instruct --show-all
```
Prints per-category / per-level accuracy, a confusion matrix, decided_by counts,
mean/p95 latency, secondary program/kind accuracy, and every miss with the raw
LLM output. LLM responses are cached in `.cache/eval/` keyed by
sha256(model + system prompt + message); changing the prompt invalidates the cache.

### Tuning set (543 rows, judged replies)
```
python scripts/eval_tuning.py                      # category + reply-quality report (cached ThaiLLM responses)
python scripts/eval_tuning.py --no-cache           # full uncached run (start / end of a tuning loop)
python scripts/eval_tuning.py --failures-only      # only rows that failed last time
python scripts/eval_tuning.py --sample 80 --stratum smalltalk --language th --show-all
```
`tests/eval_tuning.jsonl` is generated by `scripts/gen_tuning_set.py` (hand-written questions,
strata in `docs/tuning-taxonomy.md`; `expected` is a list, ambiguous rows accept several). Category
accuracy is reported overall / per stratum / per language. Rows with a `direct_reply` are judged by
Claude against `docs/reply-rubric.md`; verdicts live in `tests/eval_tuning_judgements.jsonl` keyed by
`sha256(question + "\n" + reply)[:16]`, unjudged pairs are written to
`.cache/eval-tuning/pending_judgements.jsonl` with deterministic hints and count as *pending*.
Unparsable model replies are never cached (`gatekeeper/llm.py`), so the retry gets a fresh sample.

**Blind set:** if `tests/eval_blind.csv` exists it is evaluated too and reported
in a separate block (misses by line number only). It is a human-written held-out
set — never open, read, quote or edit it.

### Adding eval rows
Append a tab-separated line to `tests/eval_questions.csv`:
`question<TAB>type<TAB>level<TAB>expected_programs<TAB>expected_kind`. `type` → expected category:
คำถามเกี่ยวกับคณะ / คำถามภาษา → in_scope; คำถามทั่วไป → off_topic_general;
คำถามนอกเหนือมหาลัย → off_topic_other_university;
คำถามนอกเหนือหลักสูตร สจล. → out_of_scope_kmitl; คำถามเจาะระบบ → injection_or_abuse;
คำถามทักทาย → greeting_smalltalk.
Optional columns: `expected_category` overrides the mapping; `expected_programs`
is `;`-separated ids (`-` = expect none, blank = don't check); `expected_kind`.
Levels: easy / medium / hard. Do not copy eval questions into the few-shot prompt.

### Tests
`pytest -q` — pure-function tests only (rules, parser, language detection,
reply templates, cache) plus `gate()` with the LLM call monkeypatched.
Nothing in `tests/` calls the API.

## HTTP API (`api/`)
`uvicorn api.main:app --reload` (port 8000). Contract for the frontend team: **`docs/api-contract.md`**.

Flow: `POST /chat` → `gate()` → `meta` event → either stream `direct_reply` tokens
(non-in_scope, no citations) or `Answerer.answer()` tokens + `citations` → `done`.
Any failure becomes an `error` event; a client disconnect stops the stream and
`aclose()`s the answerer (which must cancel its upstream ThaiLLM call).
`GET /health` → `{status, answerer, models}`.

Env: `ANSWERER=stub|rag`, `ALLOWED_ORIGINS` (comma list, must include the Vercel
domain + `http://localhost:3000`), `RATE_LIMIT_PER_MINUTE` (per IP, default 30),
`LOG_CONTENT=1` to log message text, `TRUST_PROXY=1` behind a proxy,
`ANSWER_EVENT_TIMEOUT_S`, `STUB_TOKEN_DELAY_S`. See `.env.example`.

### Answerer contract (`api/answerer.py`) — the RAG teammate implements this
```python
class Answerer(Protocol):
    name: str
    def answer(self, message: str, decision: GateDecision,
               scope: list[str] | None, history: list[Turn]) -> AsyncIterator[AnswerEvent]: ...
# AnswerEvent.type: "token" (text) | "citations" (list[Citation]) | "done" (model_used)
# Citation: faculty="IT", program, page, chunk_id, snippet
```
Provide `rag/answerer.py` with `class RagAnswerer` and set `ANSWERER=rag`; the
API imports it lazily and fails with a clear message if missing. Wrap the
streaming loop in `try/finally` so `aclose()` cancels the upstream request.
`StubAnswerer` is the reference implementation.

API tests (`tests/test_api.py`) use `httpx.AsyncClient` + `ASGITransport` with
the ThaiLLM call mocked; the disconnect test drives the raw ASGI app.

## Answer layer (`rag/`) — retrieved chunks → streamed, cited answer
`ANSWERER=rag` makes `api/main.py` use `rag/answerer.py:RagAnswerer`, which
implements the `Answerer` protocol.  Retrieval is behind a seam:

```python
# rag/retriever.py — RETRIEVER=fixture (default) | chroma (rag.chroma_retriever:ChromaRetriever, the real one)
class Chunk(BaseModel):
    chunk_id: str; program: Literal["AIT","DSBA","BIT","IT"]; page: int   # page = 1-based PDF page
    heading_path: str; text: str; score: float = 0.0   # score: higher = better, in [0, 1]; debug: dict (not serialised)
class Retriever(Protocol):
    name: str
    async def retrieve(self, query: str, programs: list[str], k: int = 8) -> list[Chunk]: ...  # programs=[] → all
```
`FixtureRetriever` (`RETRIEVER=fixture`, default) is keyword overlap over
`tests/fixtures/chunks.jsonl` — **120 real passages** from the four PDFs in `data/raw/`
(gitignored; AIT.pdf→AIT, DSBA.pdf→DSBA, IT_inter2565.pdf→BIT, IT2565.pdf→IT), built by
`python scripts/build_fixtures.py`.  The PDFs typeset TH Sarabun PSK with repositioned
vowels/tone marks as private-use codepoints; `scripts/pdf_thai.py` derives a per-file
PUA→mark table by dictionary scoring (cached in `tests/fixtures/pua_maps.json`, hand
overrides in `MANUAL_OVERRIDES`) and keeps ☑/☐ checkbox glyphs.  Audit with
`python scripts/audit_fixtures.py [--sample 10]` (0 suspicious chunks expected).
`tests/fixtures/chunks_synthetic.jsonl` (invented facts) is what the unit tests use.

Flow (`RagAnswerer.answer`): rewrite → retrieve → no-answer gate → context → model → stream → citations → done.
1. **Rewrite** (`RAG_QUERY_REWRITE=1`, one openthaigpt call) only when the message is a
   short/anaphoric follow-up with history, or is not Thai (documents are Thai → translate).
   Any failure keeps the original message.  Programs are re-resolved from the rewrite with
   `gatekeeper.rules.resolve_programs` when the gate saw none.
2. **Retrieve**: `question_kind=comparison` → per-program retrieval, round-robin interleave
   (fewer than 2 programs named → all four); else one call.  Dedupe by `chunk_id`.
3. **No-answer gate**: no chunk with `score >= min_score` → fixed `NOT_FOUND_REPLY[language]`, empty
   `citations`, no model call.  `min_score` is per retriever: `RETRIEVAL_MIN_SCORE` (0.3) for the fixture,
   `RETRIEVAL_MIN_SCORE_CHROMA` (0.0) for chroma — RRF scores are rank-based and do not separate answerable
   from unanswerable questions (see `docs/retrieval-integration.md`), so not-found relies on the model.
4. **Context** (`rag/context.py`): `[n] {program} หน้า {page} — {heading_path}` + text, filled up to
   `CONTEXT_TOKEN_BUDGET` (4500) estimated tokens — `thai_chars/3 + other_chars/4` (no tokenizer
   is exposed by the API; deliberately over-estimates).  Lowest score dropped first, input order kept.
5. **Model**: `RAG_COMPARISON_MODEL` for comparisons, `RAG_MODEL` otherwise — both default to openthaigpt.
   pathumma-think was the planned comparison model but computed derived numbers (differences) in every
   eval run, which the grounding check rejects; opt back in with the env var.  **All four ThaiLLM models
   emit `<think>` blocks** (openthaigpt too), so keep `RAG_MAX_TOKENS` ≥ 1500.  If the primary yields no *visible* token within `RAG_FIRST_TOKEN_TIMEOUT_S`, retry
   once with `RAG_FALLBACK_MODEL`.  `<think>` is stripped incrementally (`rag/streaming.py`),
   even when the tag is split across deltas; it is never sent to the client.
6. **Prompt** (`rag/prompts.py`, Thai, ~600 est. tokens, fictional few-shot facts): answer only from
   the numbered context, every factual sentence ends with `[n]`, say the not-found phrase when the
   context lacks the answer, reply in `decision.language`, high-school audience, structured comparisons.
7. **Citations**: only chunks whose `[n]` marker appears in the answer (`snippet` = first 120 chars);
   an answer containing a not-found phrase with no markers → `[]`.  `done.model_used` = the model
   that actually answered.

Env: see the "Answer layer" block in `.env.example` (`RAG_*`, `RETRIEVAL_*`, `CONTEXT_TOKEN_BUDGET`).

### Real retriever (`retrieval/`, vendored from the retrieval teammate) — `RETRIEVER=chroma`
`retrieval/` is the teammate's pipeline imported verbatim (upstream `KJ-12-GH/IT-KMITL-Hackathon-RAG`)
plus a short list of integration edits, all enumerated in **`docs/retrieval-integration.md`** — keep
changes there surgical and add them to that list.  Typhoon-OCR'd pages (`retrieval/data/extracted/`,
committed) → `clean.py`/`chunk.py` → `retrieval/data/chunks/all.jsonl` (committed, 2,347 chunks;
ids `AIT::gen::0012`, `IT2565::course::06016408`; `doc_name` AIT/DSBA/IT2565→IT/IT_inter2565→BIT) →
BGE-M3 dense in Chroma + newmm BM25, RRF-fused with a course-code boost, optional BGE reranker
(`retrieval/retrieve.py`).  Index artifacts are gitignored:
```
python scripts/build_index.py                          # BGE-M3 (~2.2 GB download once) → retrieval/data/{chroma,bm25.pkl}; ~6 min CPU
python scripts/audit_retrieval_chunks.py               # page coverage per doc (must stay ≥ 90 %)
python -m retrieval.scripts.build_chunks_all           # re-chunk from the OCR cache (after editing clean.py/chunk.py)
python scripts/calibrate_retrieval.py [--rerank --k 12]  # retrieval-only: gold rank, score sweep, RSS
RETRIEVER_CONFORMANCE=chroma pytest tests/test_retriever_conformance.py
```
`rag/chroma_retriever.py:ChromaRetriever` adapts it.  **Embeddings:** with `EMBED_API=openai|hf` (the default
local `.env` and production) query vectors come from a hosted BGE-M3 (`rag/remote_embedder.py`, ~260 MB RSS, no
torch; falls back to BM25-only when the API fails); unset it for the local model (`uv sync --extra local-embed`,
lazy load on the first query, ~6 s warm, ~1 GB → ~2.3 GB RSS after the first query), `programs` → Chroma `where` + BM25 allow-list *before*
fusion, `Chunk.score` = RRF score ÷ top score of the result, `page` = `page_index + 1`.
Retrieval env: `RETRIEVE_CAND_K`, `RETRIEVAL_K`, `RRF_K`, `CODE_BOOST`, `RERANK` (+ `RERANK_DEVICE=cpu`
on macOS), `CHROMA_DIR`, `BM25_PATH`, `CHUNKS_PATH`.  Their standalone `retrieval/api.py` is not
mounted and their prompt is superseded by `rag/prompts.py`.

### Answer eval (deterministic, no LLM judge)
```
python scripts/eval_answers.py                 # fixture retriever, cached in .cache/eval-answers/
python scripts/eval_answers.py --retriever chroma --json .cache/eval-answers/run.json
python scripts/eval_answers.py --no-cache --only cmp-ait-dsba-credits --show-all
python scripts/eval_answers.py --no-rewrite --model typhoon-s-thaillm-8b-instruct
```
Cases: `tests/eval_answers.jsonl` (`id, question, [history], programs, question_kind, language,
must_contain, must_not_contain, expect_not_found, gold_chunk_ids`) — expectations are derived
**only** from `docs/gold-facts.md` (real PDFs); `gold_chunk_ids` are retrieval ids.  Checks per case:
gate, facts, number grounding (every number in the answer must occur in the assembled context),
citations (non-empty, retrieved, gold hit), not-found behaviour, dominant-script language,
leakage (`<think>`, dangling `[n]`).  Also reported: retrieval hit rate (gold chunk retrieved / in
context) and each failing case tagged `retrieval-miss` or `generation-miss`.  Failures print the
answer and the raw model output.  Pure functions behind the checks live in `rag/checks.py`.

## Frontend (`web/`, Next.js 16) — redesigned in-house (see "UI conventions" below); teammate is walked through changes
Browser → `web/src/app/api/chat/route.ts` → `web/src/lib/ai.ts:streamChat` → FastAPI `POST /chat`
(`FASTAPI_URL`, server-side only, default `http://localhost:8000`).  The route re-emits the
backend SSE as `data: {…}` lines: `{meta}` / `{delta}` / `{citations}` / `{done, partial}` /
`{error}`.  `partial` is derived in `ai.ts` (stream ended without `done`) — it is **not** a
backend event.  Client abort → route aborts the upstream fetch (both `req.signal` and the
`ReadableStream.cancel` path) → FastAPI logs `status: "disconnected"`.  Backend down → mock
stream with `meta.mock = true`.  Scope chips send program ids (`PROGRAMS` in `lib/constants.ts`;
`FACULTIES` is an alias so the untouched components keep working).  Citations live on
`Message.citations`, rendered by `components/chat/Citations.tsx`.
Local stack: `scripts/dev.sh` (both servers, logs in `.cache/dev/`); `scripts/smoke_web.py`
drives the Next route (in-scope, off-topic, abort → checks the FastAPI log for `disconnected`).

## UI conventions (chatbot frontend, `web/`)
- Design system: all colours/spacing/radius/type come from the shared tokens in `web/src/app/globals.css`
  (`@theme` → `bg-surface`, `text-fg-muted`, `border-border`, `rounded-lg`, …); never use raw hex/px values in
  components. `web/src/components/design-tokens.test.ts` fails on literal or Tailwind-palette colours (only
  `components/icons/` is exempt, for brand marks).
- Visual direction: ChatGPT / Claude.ai style — neutral palette, one accent (KMITL orange), generous whitespace,
  subtle borders. No gradients or glass effects. Font: Anuphan (Thai + Latin) with line-heights ≥ 1.6 for stacked marks.
- Primitives live in `web/src/components/ui/` on top of Radix (`radix-ui`): Button, Input/PasswordInput, Card,
  Dialog, DropdownMenu, Tooltip, Toast (`useToast`), Avatar, Skeleton, Switch, Checkbox, Select, Alert.
- i18n: every user-visible string goes through `t()` (`useTranslation()` / `useLocale()` from
  `web/src/providers/LocaleProvider.tsx`); keys live in `web/src/i18n/th.ts` (source of truth) and `en.ts`
  (typed to the same key set — a test fails if they drift). Thai is the default locale; `?lang=en` switches.
- Theme: light/dark/system via `ThemeProvider` (`useTheme()`), stored in `localStorage["kmitl.theme"]`, applied as
  `html.dark` by an inline head script (no flash); components must look correct in both.
- Auth: Supabase Auth — Google OAuth + email/password only (`web/src/lib/auth/`). Display name lives in
  `user_metadata.display_name`. Route protection is `web/src/proxy.ts` (Next 16 proxy, formerly middleware) using the
  pure rules in `lib/auth/routes.ts`; without Supabase keys the app runs in demo mode (simulated sign-in, no protection).
  Supabase errors are mapped to `AuthErrorCode` in `lib/auth/errors.ts` — raw messages are never shown.
- Guest access: `PROTECTED_PATHS` is empty — `/chat` works signed-out (history in localStorage via
  `LocalChatRepository`; signing in switches to Supabase but does not migrate local chats). `UserMenu` and
  `SettingsDialog` show a sign-in prompt for guests. `/chat?q=…` pre-fills the composer (landing example questions).
- Landing page `/` (`web/src/components/landing/`): laid out like a cited document — headline with a live `[1]`
  marker (hover reveal, not a link), table of contents with dot leaders, 4 program boxes, prose features, numbered
  pipeline steps, marquee of example questions linking to `/chat?q=`. Accent only on citations + primary button.
  Product claims in `landing.*` strings must stay true to the backend (the preview fact "AIT 120 credits, 4 years"
  is from `AIT-p12-c1`).
- Chat page: `web/src/components/chat/` on `hooks/useChatController.ts` (send/stream/stop, replace-edit,
  regenerate, rename/delete, per-chat scope) over `lib/chat/` (stream reducer, payload, `ChatRepository`:
  localStorage in demo mode, Supabase otherwise). Routes `/chat` and `/chat/<id>` share one optional
  catch-all page so switching chats never remounts. Citations open a right panel whose PDF viewer streams
  from `app/api/pdf/[program]` (`PDF_DIR`, default `../data/raw`).
- Never run Supabase migrations or write to a remote project; produce SQL files under
  `web/supabase/migrations/` and stop (current schema: `0001_chats.sql`).
- Backend (FastAPI) is out of scope for `web/` tasks — never edit it; report needed API changes instead.
- Before finishing any `web/` task: `npm run lint && npm run typecheck && npm test && npm run build` (in `web/`).
