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
other KMITL faculties (วิศวะ, สถาปัตย์, …) → `out_of_scope_kmitl`; questions
naming no program are still `in_scope` with `programs=[]` (RAG searches all).

## Gatekeeper (`gatekeeper/`)
Receives every message first and either forwards it to RAG or replies directly.

Routing, cheapest first — **rules decide only when near-certain, else abstain**:
1. `rules.py` — deterministic layer (0 API calls): injection patterns (TH/EN/ZH),
   other-university names (abstains if our faculty/program/KMITL is also named),
   other KMITL faculties, KMITL logistics topics, obvious everyday topics,
   program aliases, 8-digit course codes.
2. `llm.py` + `prompts.py` — one ThaiLLM classification call, strict JSON,
   user text wrapped in `<user_message>` delimiters and treated as data.
   `parsing.py` strips `<think>` blocks / code fences and repairs truncated JSON.
3. Fallback — after one retry (timeout or bad JSON) default to `in_scope`
   with empty metadata (better to attempt an answer than wrongly refuse).

Config env: `GATEKEEPER_MODEL`, `GATEKEEPER_TIMEOUT_S` (default 8),
`GATEKEEPER_MAX_TOKENS`, `GATEKEEPER_CACHE_DIR` (eval only).

### `GateDecision` contract (`gatekeeper/schema.py`, `CONTRACT_VERSION = 2`) — keep stable
```python
FACULTY = "IT"

class GateDecision(BaseModel):
    category: Literal["in_scope", "off_topic_general", "off_topic_other_university",
                      "out_of_scope_kmitl", "injection_or_abuse"]
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

**Blind set:** if `tests/eval_blind.csv` exists it is evaluated too and reported
in a separate block (misses by line number only). It is a human-written held-out
set — never open, read, quote or edit it.

### Adding eval rows
Append a tab-separated line to `tests/eval_questions.csv`:
`question<TAB>type<TAB>level<TAB>expected_programs<TAB>expected_kind`. `type` → expected category:
คำถามเกี่ยวกับคณะ / คำถามภาษา → in_scope; คำถามทั่วไป → off_topic_general;
คำถามนอกเหนือมหาลัย → off_topic_other_university;
คำถามนอกเหนือหลักสูตร สจล. → out_of_scope_kmitl; คำถามเจาะระบบ → injection_or_abuse.
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
# rag/retriever.py — the retrieval teammate implements this (RETRIEVER=qdrant → rag.qdrant_retriever:QdrantRetriever)
class Chunk(BaseModel):
    chunk_id: str; program: Literal["AIT","DSBA","BIT","IT"]; page: int
    heading_path: str; text: str; score: float = 0.0   # score: higher = better, ideally in [0, 1]
class Retriever(Protocol):
    name: str
    async def retrieve(self, query: str, programs: list[str], k: int = 8) -> list[Chunk]: ...  # programs=[] → all
```
`FixtureRetriever` (`RETRIEVER=fixture`, default) is keyword overlap over
`tests/fixtures/chunks.jsonl` — **121 real passages** from the four PDFs in `data/raw/`
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
3. **No-answer gate**: no chunk with `score >= RETRIEVAL_MIN_SCORE` (0.3, calibrated for the
   fixture retriever — re-tune for Qdrant) → fixed `NOT_FOUND_REPLY[language]`, empty
   `citations`, no model call.
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

### Answer eval (deterministic, no LLM judge)
```
python scripts/eval_answers.py                 # cached in .cache/eval-answers/
python scripts/eval_answers.py --no-cache --only cmp-ait-dsba-credits --show-all
python scripts/eval_answers.py --no-rewrite --model typhoon-s-thaillm-8b-instruct
```
Cases: `tests/eval_answers.jsonl` (`id, question, [history], programs, question_kind, language,
must_contain, must_not_contain, expect_not_found, gold_chunk_ids`).  Checks per case: gate,
facts, number grounding (every number in the answer must occur in the assembled context),
citations (non-empty, retrieved, gold hit), not-found behaviour, dominant-script language,
leakage (`<think>`, dangling `[n]`).  Failures print the answer and the raw model output.
Pure functions behind the checks live in `rag/checks.py` and are unit-tested.
