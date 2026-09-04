"""``ChromaRetriever`` — the vendored hybrid retriever (``retrieval/``) behind our ``Retriever`` protocol.

Selected with ``RETRIEVER=chroma``.  Wraps the retrieval teammate's sync
``retrieval.retrieve.Retriever`` (BGE-M3 dense in Chroma + newmm BM25, fused
with RRF, 8-digit course-code boost, optional BGE reranker):

* one lazily created, thread-safe instance per ``ChromaRetriever`` — the first
  call loads BGE-M3 (seconds; logged), later calls only pay for the query;
* the blocking search runs in ``asyncio.to_thread`` so the event loop stays free;
* ``programs`` → ``doc_names`` (``DOC_NAME_TO_PROGRAM``) and is applied *inside*
  their search, upstream of the RRF fusion (Chroma ``where`` for the dense side,
  an id allow-list for BM25), so top-k is never starved by post-filtering;
* scores: their RRF scores are rank-based (~0.01–0.05, or ≥ ``CODE_BOOST`` when
  a course code matched) — ``Chunk.score`` is normalised per query as
  ``score / max score in the result`` (top hit = 1.0) so it is in ``[0, 1]`` like
  the fixture; the raw score, printed folio and rank positions live in ``Chunk.debug``.
  The no-answer gate for this retriever is ``RETRIEVAL_MIN_SCORE_CHROMA`` (see
  ``docs/retrieval-integration.md`` for the calibration).

Field mapping (their ``Hit`` → our ``Chunk``): ``chunk_id`` = their id verbatim
(``AIT::gen::0012``, ``IT2565::course::06016408``); ``program`` from ``doc_name``;
``page`` = ``page_index + 1`` — the 1-based **PDF page**, the convention used by
``docs/gold-facts.md`` and the fixtures (their ``page_label`` is the printed folio,
offset from the PDF page by tens of pages; kept in ``debug["page_label"]``) — falling
back to a numeric ``page_label`` when ``page_index`` is missing, else 1;
``heading_path`` = their ``section`` or, for course chunks without one,
``คำอธิบายรายวิชา {course_code}``; ``text`` verbatim.
"""

from __future__ import annotations

import asyncio
import logging
import re
import os
import threading
import time
from typing import Any

from .retriever import Chunk

log = logging.getLogger(__name__)

DOC_NAME_TO_PROGRAM: dict[str, str] = {"AIT": "AIT", "DSBA": "DSBA", "IT2565": "IT", "IT_inter2565": "BIT"}
PROGRAM_TO_DOC_NAME: dict[str, str] = {v: k for k, v in DOC_NAME_TO_PROGRAM.items()}
COURSE_HEADING = "คำอธิบายรายวิชา"


def _env_bool(name: str, default: bool) -> bool:
    v = os.environ.get(name)
    return default if v is None else v.strip().lower() in ("1", "true", "yes", "on")


def page_from_metadata(meta: dict[str, Any]) -> int:
    """1-based PDF page: ``page_index + 1``; fallback numeric ``page_label``; else 1."""
    idx = meta.get("page_index")
    if isinstance(idx, int) and not isinstance(idx, bool) and idx >= 0:
        return idx + 1
    label = str(meta.get("page_label") or "").strip()
    if label.isdigit() and int(label) > 0:
        return int(label)
    return 1


def heading_from_metadata(meta: dict[str, Any]) -> str:
    section = str(meta.get("section") or "").strip()
    if section:
        return section
    if meta.get("chunk_type") == "course" and meta.get("course_code"):
        return f"{COURSE_HEADING} {meta['course_code']}"
    return ""


# The AIT PDF appends the ministry curriculum-standard regulation, typeset with Thai
# numerals ("หมวดวิชาเฉพาะรวมไม่น้อยกว่า ๗๒ หน่วยกิต" = the *minimum* for any 4-year
# programme, not AIT's 90).  The programme bodies use Arabic numerals only, so Thai
# numerals next to หน่วยกิต mark regulation boilerplate that misleads credit questions.
REGULATION_CREDITS_RE = re.compile(r"[๐-๙]+\s*หน่วยกิต")


def is_regulation_boilerplate(text: str) -> bool:
    return REGULATION_CREDITS_RE.search(text) is not None


def hit_to_chunk(hit: Any, score: float) -> Chunk | None:
    """Map one of their ``Hit`` objects to a ``Chunk`` (``None`` for an unknown doc_name
    or a regulation-boilerplate chunk)."""
    meta: dict[str, Any] = dict(getattr(hit, "metadata", None) or {})
    if is_regulation_boilerplate(str(getattr(hit, "text", "") or "")):
        log.debug("chroma hit %s is regulation boilerplate; skipped", getattr(hit, "id", "?"))
        return None
    program = DOC_NAME_TO_PROGRAM.get(str(meta.get("doc_name", "")))
    if program is None:
        log.warning("chroma hit %s has unknown doc_name %r; skipped", getattr(hit, "id", "?"), meta.get("doc_name"))
        return None
    return Chunk(
        chunk_id=str(hit.id),
        program=program,  # type: ignore[arg-type]
        page=page_from_metadata(meta),
        heading_path=heading_from_metadata(meta),
        text=hit.text,
        score=round(score, 4),
        debug={
            "raw_score": float(hit.score),
            "page_label": meta.get("page_label"),
            "page_index": meta.get("page_index"),
            "chunk_type": meta.get("chunk_type"),
            "course_code": meta.get("course_code"),
            "dense_rank": getattr(hit, "dense_rank", None),
            "bm25_rank": getattr(hit, "bm25_rank", None),
        },
    )


def hits_to_chunks(hits: list[Any]) -> list[Chunk]:
    """Normalise scores per result set (top = 1.0), keep their order, drop unknown docs."""
    if not hits:
        return []
    top = max(float(h.score) for h in hits)
    out: list[Chunk] = []
    for h in hits:
        score = float(h.score) / top if top > 0 else 0.0
        chunk = hit_to_chunk(h, score)
        if chunk is not None:
            out.append(chunk)
    return out


def programs_to_doc_names(programs: list[str]) -> list[str] | None:
    """Program ids → their ``doc_name`` values; ``None`` = no filter (all documents)."""
    wanted = [PROGRAM_TO_DOC_NAME[p.upper()] for p in programs if p and p.upper() in PROGRAM_TO_DOC_NAME]
    return wanted or None


class ChromaRetriever:
    name = "chroma"

    def __init__(self, *, use_rerank: bool | None = None, cand_k: int | None = None):
        self.use_rerank = _env_bool("RERANK", False) if use_rerank is None else use_rerank
        self.cand_k = cand_k if cand_k is not None else int(os.environ.get("RETRIEVE_CAND_K", "40"))  # 40 > their 20: hit@12 63 % → 74 % (docs/retrieval-integration.md §5.2)
        self._impl: Any = None
        self._lock = threading.Lock()
        self.load_seconds: float | None = None

    # ------------------------------------------------------------------ init --
    def _get_impl(self) -> Any:
        if self._impl is None:
            with self._lock:
                if self._impl is None:
                    # heavy imports (torch, chromadb) stay lazy until the first query
                    from retrieval.retrieve import Retriever as _Impl

                    t0 = time.perf_counter()
                    impl = _Impl(use_rerank=self.use_rerank)
                    self.load_seconds = time.perf_counter() - t0
                    log.info("chroma retriever ready in %.1fs (rerank=%s, %d chunks)", self.load_seconds, self.use_rerank, len(impl.store))
                    self._impl = impl
        return self._impl

    def warm_up(self) -> float:
        """Load models/index now (e.g. at server start); returns the load time in seconds.
        A hosted embedder is pinged too, so a cold API (HF Inference) starts loading before the first user."""
        impl = self._get_impl()
        ping = getattr(getattr(impl, "model", None), "ping", None)
        if callable(ping):
            t0 = time.perf_counter()
            ok = ping()
            log.info("embedding API %s (%.1fs)", "ready" if ok else "UNAVAILABLE — BM25-only until it recovers", time.perf_counter() - t0)
        return self.load_seconds or 0.0

    # -------------------------------------------------------------- retrieve --
    def _search(self, query: str, k: int, doc_names: list[str] | None) -> list[Any]:
        impl = self._get_impl()
        return impl.search(query, top_k=k, cand_k=max(self.cand_k, k), doc_names=doc_names)

    async def retrieve(self, query: str, programs: list[str], k: int = 8) -> list[Chunk]:
        if not query.strip() or k <= 0:
            return []
        doc_names = programs_to_doc_names(programs)
        # over-fetch so dropping regulation boilerplate still leaves k results
        hits = await asyncio.to_thread(self._search, query, k + 5, doc_names)
        return hits_to_chunks(hits)[:k]
