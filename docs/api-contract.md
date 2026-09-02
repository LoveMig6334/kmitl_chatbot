# Chat API contract (for the Next.js frontend)

Base URL: `http://localhost:8000` in development (`uvicorn api.main:app --reload`).
All request/response bodies are UTF-8 JSON; `/chat` streams **Server-Sent Events**.

The backend is *gate-first*: every message is classified by the gatekeeper
(ThaiLLM) before anything else. In-scope questions are answered by the RAG
`Answerer`; everything else gets a fixed, language-matched reply.

Scope: one faculty — คณะเทคโนโลยีสารสนเทศ สจล. (`faculty` is always `"IT"`).
Program ids: `AIT`, `DSBA`, `BIT`, `IT`.

---

## `POST /chat`

### Request
```json
{
  "message": "หลักสูตร AIT เรียนกี่หน่วยกิต",
  "conversation_id": "c_123",                 // string | null — echoed into server logs only
  "scope": ["AIT", "DSBA"],                   // program ids the user ticked | null = all
  "history": [                                // prior turns, oldest first, max 50
    {"role": "user", "content": "สวัสดี"},
    {"role": "assistant", "content": "สวัสดีค่ะ"}
  ]
}
```
Validation: `message` 1–4000 chars (422 otherwise); `history[].role` ∈ `user|assistant`.
`scope` never causes a refusal — it only narrows which program the question is
resolved to.

### Response: `text/event-stream`
Headers: `Content-Type: text/event-stream`, `Cache-Control: no-cache`, `X-Accel-Buffering: no`.
Each event is `event: <name>\ndata: <json>\n\n`. Events arrive **in this order**:

| event | data | when |
|---|---|---|
| `meta` | `{category, language, faculty, programs, question_kind, decided_by, model_used}` | always first, before any token |
| `token` | `{text}` | many; concatenate in order |
| `citations` | `{citations: [{faculty, program, page, chunk_id, snippet}]}` | **only** when `category == "in_scope"`; exactly once, after the last token; may be `[]` |
| `done` | `{latency_ms, model_used}` | last event on success |
| `error` | `{code, message}` | terminates the stream; no `done` follows |

`meta.category` ∈ `in_scope | off_topic_general | off_topic_other_university | out_of_scope_kmitl | injection_or_abuse | greeting_smalltalk`.
`greeting_smalltalk` (added 2026-09-02, additive) = greetings / thanks / "ok" / bye / "who are you" / vague
"can I ask?" openers with no answerable content.  It behaves like every other non-`in_scope` category —
the tokens are a fixed reply (a warm welcome with example questions, never a refusal) and no `citations`
event is sent — so a client that only branches on `in_scope` needs no change.  Frontend: add the value to
the `ChatMeta.category` union in `web/src/lib/ai.ts`; optionally render it without the "out of scope" styling.
`meta.language` ∈ `th | en | zh | other` (reply and answer are in this language).
`meta.programs` is a list (empty = none named); `meta.question_kind` ∈ `fact_lookup | descriptive | comparison | null`.
`meta.decided_by` ∈ `rule | llm | fallback`.

For non-`in_scope` categories the tokens are the gatekeeper's fixed reply
(decline + redirect) and **no `citations` event is sent**.

Error codes: `gate_failed`, `answerer_failed`, `upstream_timeout`.
HTTP-level errors (no stream): `422` validation, `429 {code: "rate_limited", message}` with `Retry-After` seconds.

### Example — in scope
```
event: meta
data: {"category": "in_scope", "language": "th", "faculty": "IT", "programs": ["AIT"], "question_kind": "fact_lookup", "decided_by": "rule", "model_used": null}

event: token
data: {"text": "ระบบค้น"}

event: token
data: {"text": "หายัง"}
...
event: citations
data: {"citations": [{"faculty": "IT", "program": "AIT", "page": 1, "chunk_id": "stub-p1-c0", "snippet": "(stub) ..."}]}

event: done
data: {"latency_ms": 412, "model_used": null}
```

### Example — off topic
```
event: meta
data: {"category": "off_topic_general", "language": "th", "faculty": "IT", "programs": [], "question_kind": null, "decided_by": "rule", "model_used": null}

event: token
data: {"text": "ขออภัย"}
...
event: done
data: {"latency_ms": 3, "model_used": null}
```

### Stop button / disconnect
Closing the connection (`AbortController.abort()` on `fetch`) is the stop
signal. The server detects the disconnect, stops streaming and cancels the
upstream ThaiLLM request. Nothing else is required from the client.

### Reading the stream in the browser
`EventSource` cannot POST; use `fetch` + `ReadableStream` and split on blank
lines, or a small SSE parser (e.g. `eventsource-parser`). Always handle `error`
as terminal and treat a closed stream without `done` as an aborted answer.

---

## `GET /health`
```json
{"status": "ok", "answerer": "stub", "models": ["openthaigpt-thaillm-8b-instruct-v7.2", "..."]}
```
`answerer` is `stub` until the RAG pipeline is wired in (`ANSWERER=rag`).
While it is `stub`, in-scope answers are the fixed notice
"ระบบค้นหายังไม่พร้อม — คำถามนี้ถูกจัดเป็น in_scope, หลักสูตร AIT" with one fake citation,
so the UI can be built against real event shapes.

---

## CORS, limits, environment
- Allowed origins come from `ALLOWED_ORIGINS` (comma-separated). Development
  default: `http://localhost:3000`. Add the Vercel domain (and preview domains
  if needed) — a disallowed origin gets no `Access-Control-Allow-Origin` header.
- Rate limit: `RATE_LIMIT_PER_MINUTE` per client IP (default 30) → `429`.
- Per-request logs are structured JSON without message content unless `LOG_CONTENT=1`.
- See `.env.example` for all variables.
