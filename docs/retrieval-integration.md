# Retrieval integration — the teammate's pipeline as the real `Retriever`

Branch `feat/real-retriever`.  Upstream: `https://github.com/KJ-12-GH/IT-KMITL-Hackathon-RAG.git`
at `8b75d249bdf4974dbf0cbd235fdde6336a3cb822` (2026-09-02), vendored verbatim in commit
`dfc04f4` and then adapted.  **Everything changed inside `retrieval/` is listed in §6** — the
retrieval teammate still owns that tree; keep changes there surgical and add them to the list.

## 1. Layout

| upstream | here | notes |
|---|---|---|
| `rag/*.py` | `retrieval/*.py` | `clean.py`, `chunk.py`, `index.py`, `retrieve.py`, `api.py`, `ingest_ocr.py` |
| `scripts/*.py` | `retrieval/scripts/` | run as modules: `python -m retrieval.scripts.build_chunks_all`, `python -m retrieval.scripts.test_index` |
| `Data/chunks/*.jsonl` | `retrieval/data/chunks/` | committed; **regenerated** here (see §3) |
| `Data/extracted/{doc}/NNN.md` | `retrieval/data/extracted/` | committed Typhoon-OCR cache (1,034 pages) — chunks can be rebuilt without OCR |
| `Data/inspect_report.json` | `retrieval/data/` | |
| `*.md`, `.env.example` | `retrieval/docs/` | their README / HANDOFF / skill / checklists |
| `data/chroma/`, `data/bm25.pkl` | `retrieval/data/` | **gitignored**; `python scripts/build_index.py` |
| `requirements.txt` | — | runtime deps folded into `pyproject.toml`: `FlagEmbedding`, `chromadb`, `rank-bm25`, `torch` (no `typhoon-ocr`, no Ollama) |

`retrieval/` is excluded from ruff and pytest (`pyproject.toml`).  Their standalone FastAPI
(`retrieval/api.py`, `POST /search`) is **not mounted** — it stays for their own testing; their
embedded `SYSTEM_INSTRUCT` is superseded by `rag/prompts.py`.

## 2. Adapter — `rag/chroma_retriever.py:ChromaRetriever` (`RETRIEVER=chroma`)

- One lazily created, lock-guarded instance of `retrieval.retrieve.Retriever`; the first query
  loads BGE-M3 + Chroma + BM25 (~6 s warm; the very first run downloads ~2.2 GB from Hugging Face),
  logged as `chroma retriever ready in …s`.  `warm_up()` exists for eager loading.
- `retrieve()` runs the blocking search in `asyncio.to_thread`.
- **Program filter** → `doc_names` (`AIT↔AIT`, `DSBA↔DSBA`, `IT↔IT2565`, `BIT↔IT_inter2565`) and
  is applied *inside* their search, upstream of RRF fusion: Chroma `where={"doc_name": {"$in": …}}`
  on the dense side, an id allow-list on the BM25 side, and the course-code pull-in respects it.
  Filtering after fusion would starve top-k (a program's chunks are ~¼ of the corpus).
- **Field mapping** (their `Hit` → our `Chunk`):
  - `chunk_id` = their id verbatim (`AIT::gen::0012`, `IT2565::course::06016408`, `…#1` for duplicates)
  - `program` from `doc_name` (unknown doc → dropped with a warning)
  - `page` = `page_index + 1` = the **1-based PDF page** (the convention of `docs/gold-facts.md`, the
    fixtures and the citation chips).  Their `page_label` is the printed folio, which the OCR reads
    from the page header; it is offset from the PDF page by +24…+79 depending on the section and
    is non-monotonic in 8 places in AIT, so it is only a fallback (numeric label when `page_index`
    is missing) and is kept in `Chunk.debug["page_label"]`.
  - `heading_path` = their `section` (a raw heading such as `คำอธิบายรายวิชา`,
    `3.5 รายวิชาในแต่ละกลุ่มทักษะ`), or `คำอธิบายรายวิชา {course_code}` for course chunks without one, else `""`.
  - `text` verbatim (OCR markdown: `**bold**`, `<table>…</table>`, `☑/☐`).
- **Score semantics.**  Their score is the RRF sum `Σ 1/(60 + rank)` over the dense and BM25
  lists (+ `CODE_BOOST`=1.0 when an 8-digit course code in the query matches `course_code`), so it is
  rank-based: 0.0164 for a chunk that is #1 in one list only, at most 0.0328 (= 2/61) for #1 in
  both, ~1.02 with a code boost.  `Chunk.score` = `score / max score in the result set` (top hit =
  1.0, everything in `[0, 1]`); the raw score and the dense/BM25 rank positions live in `Chunk.debug`.
  `Chunk.debug` is never serialised (`exclude=True`, like `synthetic`).

## 3. Chunk regeneration (page bug in the upstream chunker)

Symptom in the upstream `all.jsonl`: 208/2,358 chunks (8.8 %) had `page_index=0` and
`page_label=None` — the first 101 general chunks of AIT, the first 79 of BIT, 15 of DSBA, 13 of
IT — although they sit on PDF pages 1–105 (`AIT::gen::0100` is on `AIT/105.md`).  Usable-page
coverage per doc: AIT 82.0 %, BIT 82.6 %, DSBA 98.0 %, IT 97.8 %.

Root cause: `pythainlp.util.normalize` collapses blank lines (`"a\n\nb" → "a\nb"`), and
`clean_page()` normalised the whole page text, so no cleaned page had a paragraph break.
`chunk._emit_general` then saw the whole general section between two course chunks as one
paragraph, `_split_big_unit` cut it into 400-token windows and stamped every window with the
*first* line's page.

Fix (`retrieval/clean.py`, 2 lines): normalise each kept line instead of the joined page.
Regenerated with `python -m retrieval.scripts.build_chunks_all` from the committed OCR cache (2 s):

| | before | after |
|---|---|---|
| chunks | 2,358 (549 general / 1,809 course) | 2,347 (538 general / 1,809 course, identical course ids) |
| usable page AIT / DSBA / IT / BIT | 82.0 / 98.0 / 97.8 / 82.6 % | 99.8 / 99.9 / 99.8 / 99.8 % |
| rows without a page | 208 | 4 — the cover-page chunks `::gen::0000`, which really are on PDF page 1 |
| non-whitespace chars per doc | | within −0.03 % |

`scripts/audit_retrieval_chunks.py` reports this and exits 1 below 90 % usable for any doc.
General chunk ids (`::gen::NNNN`) were renumbered by the regeneration; course ids are stable.

Two further observations for the teammate (not changed here):
- AIT's own `0604xxxx`/`0606xxxx` course descriptions are HTML tables in the OCR output
  (`<td>06046400</td><td>แคลคูลัส 1</td>…`), so `COURSE_LINE` never matches and they stay inside
  general chunks (e.g. `AIT::gen::0147`); only the `90xxxxxx` general-education courses became
  `AIT::course::` chunks.  DSBA / IT / BIT course descriptions chunk correctly.
- The front-matter chunk `::gen::0000` of every document is ~2,000 chars of mixed content
  (title, degree names, credits, duration, language) starting on page 1; the "132 หน่วยกิต"
  fact of a program therefore also lives in the structure chunk (p13–14) and in the study-plan
  totals (`รวมตลอดหลักสูตร …`), which is why `gold_chunk_ids` list several ids per credit fact.

## 4. Index build (this machine: Apple M5 Max, CPU only, 128 GB)

`python scripts/build_index.py` (wraps `retrieval.index`, reuses one loaded embedder):

| step | time | size |
|---|---|---|
| BGE-M3 load (first run incl. download) | 57.8 s (≈6 s warm) | 4.3 GB Hugging Face cache (`.bin` + safetensors) |
| embed 2,347 chunks (`max_length` 2048, batch 16, CPU) | 311 s | Chroma dir 38 MB |
| BM25 (newmm) | 1.1 s | `bm25.pkl` 3.5 MB |
| peak RSS during the build | | 7.3 GB |

`python -m retrieval.scripts.test_index` passes (dense and BM25 both return sensible top-3).

**Memory footprint of the serving stack** (`scripts/calibrate_retrieval.py`, `ru_maxrss`):
37 MB before load → **1.04 GB** after model + index load → **2.27 GB** after the first query
(torch allocates its work buffers on the first encode); ~2.3 GB steady.  Retrieval latency ~90 ms
per query (k=8…12), 330 ms for the very first one.  With the reranker: see §5.

## 5. Calibration and evaluation

### 5.1 Threshold (`RETRIEVAL_MIN_SCORE_CHROMA`)

`scripts/calibrate_retrieval.py` runs every `tests/eval_answers.jsonl` question through the
retriever only (per-program + interleave for comparisons, exactly like `RagAnswerer`).  Raw
top-1 RRF score, cand_k=20, k=8:

| | min | median | max | n |
|---|---|---|---|---|
| answerable questions | 0.0164 | 0.0313 | 1.0135 (code boost) | 19 |
| `expect_not_found` questions | 0.0164 | 0.0314 | 0.0328 | 12 |

The distributions are identical: RRF is rank-based, the top hit of *any* query scores 0.016–0.033
regardless of whether the corpus can answer it.  Every threshold that refuses even half of the
not-found questions also refuses most answerable ones (0.0308 → refuses 6/12 not-found but keeps
only 13/19 answerable; 0.0323 → 9/12 vs 1/19).  The normalised `Chunk.score` is 1.0 for the top
hit by construction, so it cannot gate either.  **Decision: `RETRIEVAL_MIN_SCORE_CHROMA=0.0`** —
never refuse on score; the not-found behaviour comes from the model (prompt rule + fixed phrase).
The per-retriever setting lives in `RagSettings.min_score_chroma`; `RETRIEVAL_MIN_SCORE` (0.3)
still applies to the fixture retriever whose scores are overlap ratios.

### 5.2 Retrieval parameters (gold chunk in top-k, 19 answerable cases)

| setting | hit@k | gold ranks |
|---|---|---|
| cand_k 20, k 8 (upstream defaults) | 12/19 = 63 % | 1,1,1,1,2,2,4,4,5,5,7,7 |
| cand_k 40, k 8 | 13/19 = 68 % | 1,1,1,2,2,2,3,3,4,4,5,7,7 |
| cand_k 40, k 12 | 14/19 = 74 % | + one at rank 12 |
| cand_k 40, k 12, BGE reranker (`RERANK=1 RERANK_DEVICE=cpu`) | **17/19 = 89 %** | 1×8, 2,2,2,3,3,5,9,9,12 |

The reranker (`BAAI/bge-reranker-v2-m3`, 568 M params) fixes the ranking — and, unlike RRF, its
sigmoid score *does* carry a confidence signal: raw top-1 median 0.28 for answerable vs 0.007 for
not-found questions (min answerable 0.0046, max not-found 0.62, so still no clean cut).  Its cost on
CPU rules it out for serving here: **~20 s per query** (mean 20.2 s, max 45 s, scoring 40 candidate
chunks of up to ~1.5 k tokens each), model load 68 s, **RSS 8.2 GB** after the first query (1.5 GB
loaded).  On a GPU it would be ~100 ms; keep `RERANK=0` on a CPU host.  The numbers used for the
answer eval below are therefore cand_k 40, k 12, no reranker.

Misses that no setting fixes (retrieval-miss): `dsba-careers`, `cmp-ait-dsba-credits`,
`cmp-all-fewest-credits` — the "credits / careers" queries rank the regulations chunks
("ไม่น้อยกว่า … หน่วยกิต", มคอ. rules) above the program's front-matter/structure chunk.
`followup-*` cases miss in the retrieval-only run because the anaphora is only resolved by the
rewrite step in the answerer.

### 5.3 Answer eval — fixture vs chroma

Same 31 cases, same model (`openthaigpt-thaillm-8b-instruct-v7.2`), rewrite on, uncached
completions (cases that hit a ThaiLLM transport error — `ReadTimeout`, `peer closed connection`,
"no visible text" — were rerun individually; every run had 3–5 of them, the API is shared).
Chroma column = `RETRIEVE_CAND_K=40 RETRIEVAL_K=12 CONTEXT_TOKEN_BUDGET=6500`, no reranker, HTML
tables flattened in context assembly (`rag/context.py:flatten_tables`, added in this branch).

| check | fixture (120 curated passages) | chroma, upstream defaults (cand 20, k 8, budget 4500) | **chroma, tuned** |
|---|---|---|---|
| gate | 31/31 | 31/31 | 31/31 |
| facts | 15/19 = 78.9 % | 12/19 = 63.2 % | **15/19 = 78.9 %** |
| grounding | 29/31 = 93.5 % | 26/31 = 83.9 % | **30/31 = 96.8 %** |
| citations (non-empty, retrieved, gold hit) | 17/19 ¹ | 9/19 | 9/19 = 47.4 % |
| not_found | 11/12 = 91.7 % | 6/13 = 46.2 % | **12/12 = 100 %** |
| language | 29/31 | 28/31 | 30/31 = 96.8 % |
| leakage | 31/31 | 30/31 | **31/31 = 100 %** |
| cases fully passing | 10/31 | 11/31 | **19/31 = 61.3 %** |
| **retrieval hit rate** (gold retrieved / in context) | n/a ¹ | 12/18 / 11/18 | **16/19 = 84 % / 15/19 = 79 %** |

¹ fixture ids (`AIT-p12-c1`) can never match the retrieval gold ids, so its citation column counts
non-empty + retrieved only, and hit rate is not defined.

Against the targets: grounding 96.8 % (target 100 — one miss, a retrieval-miss below), leakage
100 %, not-found 100 % (≥ 80), facts 78.9 % (≥ 75).  What moved the numbers, in order of effect:
the 6500-token budget (gold chunks were retrieved at k=12 but cut from the 4500 context: 66 % →
80 % "in context"), table flattening (not-found 56 % → 100 %, leakage 84 % → 100 %, fully
passing 13 → 19 — the 8B model handles `06016401 | … | 3(3-0-6)` rows, not `<td>` soup), cand_k 40
(hit@8 63 % → 68 %, hit@12 74 %).  `CODE_BOOST` was left at 1.0 (the single course-code case
ranks first with it).

**Every failing case, diagnosed** (final run):

| case | kind | what happened |
|---|---|---|
| `cmp-ait-dsba-credits` | retrieval-miss | per-program query "AIT กับ DSBA เรียนกี่หน่วยกิต ต่างกันยังไง" ranks the มคอ. regulation chunks (`AIT::gen::0050`, `DSBA::gen::0100`: "ไม่น้อยกว่า … หน่วยกิต") above the program's credit statement; the model then computes 96/60/36 → facts + grounding fail.  The reranker puts the gold at rank 1 (§5.2) but is unaffordable on CPU. |
| `cmp-all-fewest-credits` | retrieval-miss | same query family across all four programs; AIT's 120 not retrieved (k=3 per program). |
| `dsba-careers` | retrieval-miss | "DSBA เรียนเกี่ยวกับอะไร จบไปทำงานอะไรได้บ้าง" — careers list (`DSBA::gen::0001`) not in top-12; the model answered without citations. Reranker: rank 2. |
| `ait-admission` | retrieval-miss | `AIT::gen::0008` retrieved (rank 12) but cut by the budget; the model answered from the regulations chunk without inventing a grade this time (facts pass, citation fails). |
| `dsba-credits`, `it-credits`, `followup-dsba`, `ait-opening` | generation-miss (citation attribution) | correct number/year in the answer, gold chunk in context, but the `[n]` marker points at the top-ranked chunk (`DSBA::gen::0100`, `IT2565::gen::0018`, `AIT::gen::0077` "ปีการศึกษา 2566") instead of the one that states the fact — the 8B model tends to cite `[1]`. |
| `it-careers` | generation-miss | correct careers, no `[n]` markers at all → empty citations. |
| `ait-course-desc` | generation-miss | `AIT::gen::0147` (the calculus table) in context; the model describes the course without repeating the codes 06046401 / 06046400. |
| `zh-dsba-credits` | generation-miss | Chinese question, rewrite → Thai query fine, gold in context; the model answered in Thai and omitted the numbers. |
| `zh-ait-tuition` | generation-miss (language) | correct not-found, but in Thai instead of Chinese. |

Not-found judgement calls that now pass: `bit-english` / `en-bit-english` (the model says the
document gives no admission score and cites nothing) and `dsba-gpax`.  These flip between runs —
the model is sampled at temperature 0 but the API is not deterministic across days.

## 6. Every changed line inside `retrieval/` (for the teammate)

Diff base: commit `dfc04f4` (verbatim import).  `git diff dfc04f4 -- retrieval` shows exactly this.

| file | change | why |
|---|---|---|
| `retrieve.py` | removed `sys.path.insert`; `CHROMA_DIR`/`BM25_PATH`/`CHUNKS_PATH` default to `retrieval/data/…` via `PKG_DIR` (same env vars override); `from rag.index` → `from retrieval.index` | package import, no CWD dependence |
| `retrieve.py` | `_dense(query, k, where=None)` passes `where` to `col.query`; `_bm25(query, k, allowed=None)` filters ids before taking top-k; `search(…, doc_names=None)` builds `where` + `allowed` and the course-code pull-in honours `allowed` | program filter upstream of RRF; `doc_names=None` behaves exactly as before |
| `retrieve.py` | `FlagReranker(…, devices=os.getenv("RERANK_DEVICE") or None)` | on macOS FlagEmbedding picks MPS and crashes in Metal; `RERANK_DEVICE=cpu` |
| `index.py` | path defaults package-relative; `--chunks` default package-relative | |
| `index.py` | `load_embedder()` returns `rag.remote_embedder.RemoteEmbedder` when `EMBED_API` is set (hosted BGE-M3 via HTTP; same `encode(...)["dense_vecs"]` surface) | free hosting has ~512 MB RAM: no torch/FlagEmbedding at runtime; vectors verified identical to local (cosine 1.0000) |
| `retrieve.py` | `search()` wraps `_dense()` in `try/except rag.remote_embedder.EmbeddingUnavailable` → `dense_ids = []` (BM25-only) with a stderr note; module-level import of that exception | the hosted embedding API can be cold/down/misconfigured; the chatbot must still answer |
| `api.py` | removed `sys.path.insert`; `rag.retrieve` → `retrieval.retrieve`; uvicorn target `retrieval.api:app` | not mounted by us |
| `chunk.py` | `from rag.clean` → `from retrieval.clean` | |
| `clean.py` | `clean_page()`: `out_lines.append(normalize_thai(cleaned))` per line; `return text` instead of `normalize_thai(text)` | **the page bug** (§3) |
| `ingest_ocr.py` | `OCR_OUT` default package-relative | never imported here (needs `typhoon_ocr`) |
| `scripts/build_chunks_all.py`, `scripts/qa_corpus.py`, `scripts/test_index.py` | removed `sys.path.insert`; `rag.*` → `retrieval.*`; data roots package-relative | run as `python -m retrieval.scripts.<name>` |
| `data/chunks/*.jsonl` | regenerated after the `clean.py` fix | 2,358 → 2,347 chunks |

### What to tell the teammate

1. **Blank lines are lost in `clean_page()`** — `pythainlp.util.normalize` on the whole page
   collapses them, so the paragraph-aware general chunking and `page_index` stamping never worked
   for the front matter.  Normalise per line (2-line fix above).  Please pull this into the upstream
   repo so the next `all.jsonl` is not regenerated without it.
2. `search()` now takes `doc_names=` (list of `doc_name` values) to restrict both rankers before
   fusion — that is how the chatbot narrows to the program(s) the user named.
3. Paths default relative to the package directory; the env vars are unchanged.
4. Citations use `page_index + 1` (PDF page).  `page_label` (printed folio) is noisy: offset from
   the PDF page and non-monotonic in AIT.
5. AIT's own course descriptions are OCR'd as HTML tables and never become `::course::` chunks
   (`COURSE_LINE` only matches `^\d{8}\s+…` lines) — worth a table-aware rule in `chunk.py`.
6. `RERANK=1` needs `RERANK_DEVICE=cpu` on macOS.
7. RRF scores cannot be used as a confidence threshold (§5.1); if a "no answer" signal is wanted
   from retrieval it has to come from something else (e.g. the reranker's calibrated score).

## 7. Eval label changes (re-derived from `docs/gold-facts.md`)

`tests/eval_answers.jsonl` had been written for the synthetic fixture; it is now derived only from
the gold-facts table (19 answerable + 12 `expect_not_found`).  Full row-by-row list in commit
`2988038`.  Items that need your adjudication:

- `bit-english` / `en-bit-english` are `expect_not_found` per gold-facts ("0 hits for IELTS"), but
  the OCR corpus contains "IELTS (Academic) score of 5.5 or higher" as the *target level* of the
  English courses 96644006 / 90644006 and IELTS/TOEFL in the credit-transfer rules.  The model
  answers "5.5" from the course description.  Either accept that as a not-found failure (current
  label) or re-label as answerable with `must_contain ["5.5"]`.
- `dsba-gpax`: the model writes "เอกสารหลักสูตรไม่ได้ระบุ GPAX ขั้นต่ำที่ชัดเจน" with citations — the
  right content, but neither the fixed not-found phrase nor empty citations, so it fails the
  not-found check.  Label stays; this is a prompt/phrase-list question, not retrieval.
- `nf-robotics-elective` → `nf-ait-dorm` and `nf-year3-plan` → `nf-dsba-tcas`: the original
  "absent" topics exist in the real documents (AIT course 06046418 mentions หุ่นยนต์; DSBA has a
  year-3 plan), so they were replaced by topics from the gold-facts absent table (หอพัก, TCAS).
- `ait-course-desc` asks about แคลคูลัส 2 instead of "พื้นฐานปัญญาประดิษฐ์" (not in gold-facts).
- Gold ids for the credit totals list every chunk that states `รวม/จำนวนหน่วยกิต … ตลอดหลักสูตร N`
  (front matter, structure section, study-plan totals) — the model legitimately cites any of them.
- Grounding check: numbers that appear in the *question* (a course code echoed in a not-found
  reply) are no longer counted as ungrounded (`scripts/eval_answers.py`).
