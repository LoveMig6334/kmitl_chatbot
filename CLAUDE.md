# thai_llm_kmitl — project notes for Claude

## Competition rule (hard constraint)
Only **ThaiLLM** models may read, analyse or answer anything at runtime. Every
call that touches a user message must go through the ThaiLLM OpenAI-compatible
chat API (`/chat/completions` only — there is no embeddings endpoint).
Client config lives in `src/main.py` / `src/thai_llm_kmitl/models.py`
(`THAILLM_API_KEY`, `THAILLM_BASE_URL` in `.env`). Default model:
`openthaigpt-thaillm-8b-instruct-v7.2` (override with `GATEKEEPER_MODEL`).

## Gatekeeper (`gatekeeper/`)
Receives every message first and either forwards it to RAG or replies directly.

Routing, cheapest first:
1. `rules.py` — deterministic regex/keyword layer (0 API calls): injection
   patterns (TH/EN/ZH), other-university names, KMITL logistics topics,
   obvious everyday topics, faculty/program aliases, 8-digit course codes.
2. `llm.py` + `prompts.py` — one ThaiLLM classification call, strict JSON,
   user text wrapped in `<user_message>` delimiters and treated as data.
   `parsing.py` strips `<think>` blocks / code fences and repairs truncated JSON.
3. Fallback — after one retry (timeout or bad JSON) default to `in_scope`
   with null metadata (better to attempt an answer than wrongly refuse).

Config: `GATEKEEPER_MODEL`, `GATEKEEPER_TIMEOUT_S` (default 8), `GATEKEEPER_MAX_TOKENS`.
In-scope faculties and program aliases are defined in `gatekeeper/config.py`
(`FACULTIES`); three of the four were placeholders in the spec — edit there.

### `GateDecision` contract (`gatekeeper/schema.py`) — keep stable
```python
class GateDecision(BaseModel):
    category: Literal["in_scope", "off_topic_general", "off_topic_other_university",
                      "out_of_scope_kmitl", "injection_or_abuse"]
    language: Literal["th", "en", "zh", "other"]
    faculty: str | None          # canonical key: IT | ENG | SCI | BUS
    program: str | None          # e.g. "AIT", "DSBA"
    course_codes: list[str]      # regex-extracted, e.g. ["06016317"]
    question_kind: Literal["fact_lookup", "descriptive", "comparison"] | None
    direct_reply: str | None     # filled ONLY when category != in_scope
    confidence: float
    decided_by: Literal["rule", "llm", "fallback"]
    model_used: str | None
    latency_ms: int
```
Entry point: `async def gate(message: str, scope_filter: list[str] | None = None) -> GateDecision`
(`gatekeeper.gate_sync` for blocking code). `scope_filter` = faculty keys the
user ticked; it narrows faculty resolution and never causes a refusal.
RAG should answer in `decision.language` when `category == "in_scope"`.

### Running the eval
```
python scripts/eval_gatekeeper.py                # all rows, LLM enabled
python scripts/eval_gatekeeper.py --level easy   # easy rows only
python scripts/eval_gatekeeper.py --dry-run      # rule layer only, no API calls
python scripts/eval_gatekeeper.py --model typhoon-s-thaillm-8b-instruct --show-all
```
Prints per-category / per-level accuracy, a confusion matrix, decided_by
counts, mean/p95 latency, and every miss with the raw LLM output.

### Adding eval rows
Append a tab-separated line to `tests/eval_questions.csv`:
`question<TAB>type<TAB>level`. `type` → expected category:
คำถามเกี่ยวกับคณะ / คำถามภาษา → in_scope; คำถามทั่วไป → off_topic_general;
คำถามนอกเหนือมหาลัย → off_topic_other_university;
คำถามนอกเหนือหลักสูตร สจล. → out_of_scope_kmitl; คำถามเจาะระบบ → injection_or_abuse.
An optional 4th column `expected_category` overrides the mapping. Levels: easy / medium / hard.

### Tests
`pytest tests/ -q` — pure-function tests only (rules, parser, language
detection, reply templates) plus `gate()` with the LLM call monkeypatched.
Nothing in `tests/` calls the API.
