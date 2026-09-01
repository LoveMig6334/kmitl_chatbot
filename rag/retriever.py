"""Retrieval seam between the retrieval teammate and the answer layer.

The answer layer (``rag/answerer.py``) only depends on ``Chunk`` and the
``Retriever`` protocol below.  ``FixtureRetriever`` is a keyword-overlap
implementation over ``tests/fixtures/chunks.jsonl`` so the answer layer is
testable today; the real ``rag.qdrant_retriever:QdrantRetriever`` replaces it
behind the same protocol (``RETRIEVER=qdrant``).

Score semantics: ``Chunk.score`` is "higher is better", ideally in ``[0, 1]``.
The answer layer applies ``RETRIEVAL_MIN_SCORE`` to it (no-answer gate), so a
new retriever must either produce scores on a comparable scale or ship its own
default threshold.  ``FixtureRetriever`` scores are IDF-weighted overlap of
query terms with the chunk (1.0 = every informative query term found).
"""

from __future__ import annotations

import importlib
import json
import math
import os
import re
from collections import Counter
from collections.abc import Iterable
from functools import lru_cache
from pathlib import Path
from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel, Field

ProgramId = Literal["AIT", "DSBA", "BIT", "IT"]
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE_PATH = ROOT / "tests" / "fixtures" / "chunks.jsonl"


class Chunk(BaseModel):
    chunk_id: str
    program: ProgramId
    page: int
    heading_path: str = ""  # e.g. "หมวดที่ 3 > โครงสร้างหลักสูตร > แผนการศึกษา ปี 1"
    text: str
    score: float = 0.0
    synthetic: bool = Field(default=False, exclude=True)  # fixture bookkeeping only


@runtime_checkable
class Retriever(Protocol):
    name: str

    async def retrieve(self, query: str, programs: list[str], k: int = 8) -> list[Chunk]:
        """Top-``k`` chunks for ``query``; ``programs`` filters by program id (empty = all)."""
        ...


# --------------------------------------------------------------------------- #
# Tokenisation (pythainlp newmm for Thai; Latin/digit runs as-is, lower-cased)
# --------------------------------------------------------------------------- #
# Query-side synonyms: colloquial Thai and English/Chinese key terms mapped to the
# formal Thai wording used in curriculum documents.  A query term counts as
# present in a chunk when the term itself OR any synonym is present.  This is a
# fixture convenience; cross-lingual matching in the real retriever is the
# retrieval owner's concern (the answer layer also translates non-Thai queries
# to Thai with ThaiLLM when RAG_QUERY_REWRITE=1).
SYNONYMS: dict[str, tuple[str, ...]] = {
    "เทอม": ("ภาคการศึกษา",), "ค่าเทอม": ("ค่าธรรมเนียม",), "ค่าเรียน": ("ค่าธรรมเนียม",), "ค่าใช้จ่าย": ("ค่าธรรมเนียม",),
    "ค่า": ("ค่าธรรมเนียม",), "ทำงาน": ("อาชีพ",), "งาน": ("อาชีพ",), "จบ": ("สำเร็จการศึกษา",),
    "สมัคร": ("คุณสมบัติ", "รับสมัคร"), "เกรด": ("gpax",), "สอบเข้า": ("คุณสมบัติ", "tcas"), "รับ": ("รับสมัคร",),
    "ปี1": ("ชั้นปีที่",), "ปีหนึ่ง": ("ชั้นปีที่",), "เฟรชชี่": ("ชั้นปีที่",), "ตารางเรียน": ("แผนการศึกษา",), "แผนเรียน": ("แผนการศึกษา",),
    "เปิด": ("เปิดสอน",), "เปิดรับ": ("เปิดสอน",), "เริ่ม": ("เปิดสอน",), "ภาษาอังกฤษ": ("ภาษาอังกฤษ", "ielts"), "อินเตอร์": ("นานาชาติ",),
    "credit": ("หน่วยกิต",), "credits": ("หน่วยกิต",), "year": ("ปี",), "years": ("ปี",), "long": ("ระยะเวลา",), "duration": ("ระยะเวลา",),
    "tuition": ("ค่าธรรมเนียม",), "fee": ("ค่าธรรมเนียม",), "fees": ("ค่าธรรมเนียม",), "cost": ("ค่าธรรมเนียม",), "semester": ("ภาคการศึกษา",),
    "admission": ("คุณสมบัติ",), "requirement": ("คุณสมบัติ",), "requirements": ("คุณสมบัติ",), "apply": ("คุณสมบัติ",), "gpa": ("gpax",),
    "english": ("ภาษาอังกฤษ", "ielts"), "career": ("อาชีพ",), "careers": ("อาชีพ",), "job": ("อาชีพ",), "jobs": ("อาชีพ",),
    "open": ("เปิดสอน",), "start": ("เปิดสอน",), "started": ("เปิดสอน",), "first": ("ชั้นปีที่",), "freshman": ("ชั้นปีที่",),
    "plan": ("แผนการศึกษา",), "subjects": ("รายวิชา", "แผนการศึกษา"), "courses": ("รายวิชา", "แผนการศึกษา"), "describe": ("คำอธิบายรายวิชา",),
    "学分": ("หน่วยกิต",), "学制": ("ระยะเวลา", "ปี"), "年": ("ปี",), "学费": ("ค่าธรรมเนียม",), "费用": ("ค่าธรรมเนียม",), "学期": ("ภาคการศึกษา",),
    "入学": ("คุณสมบัติ",), "申请": ("คุณสมบัติ",), "要求": ("คุณสมบัติ",), "条件": ("คุณสมบัติ",), "英语": ("ภาษาอังกฤษ", "ielts"),
    "就业": ("อาชีพ",), "工作": ("อาชีพ",), "职业": ("อาชีพ",), "开设": ("เปิดสอน",), "招生": ("เปิดสอน", "รับสมัคร"), "开始": ("เปิดสอน",),
    "一年级": ("ชั้นปีที่",), "大一": ("ชั้นปีที่",), "国际": ("นานาชาติ",),
}
OVERVIEW_SCORE = 0.3  # nominal score for the per-program overview fallback (topic-less queries)
_OVERVIEW_ORDER = ("ข้อมูลทั่วไปของหลักสูตร", "จำนวนหน่วยกิตรวม", "อาชีพ", "ค่าธรรมเนียม", "คุณสมบัติ")
_ASCII_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9.,\-]*")
_THAI_RE = re.compile(r"[฀-๿]")
_CJK_RE = re.compile(r"[一-鿿]")
_CJK_KEYS: tuple[str, ...] = tuple(k for k in SYNONYMS if _CJK_RE.search(k))
# Very common function / question words that carry no retrieval signal.
_EXTRA_STOPWORDS = {
    "กี่", "อะไร", "เท่าไร", "เท่าไหร่", "ไหม", "มั้ย", "ครับ", "ค่ะ", "คะ", "หรือ", "เปล่า", "บ้าง", "ยังไง", "อย่างไร",
    "หน่อย", "ล่ะ", "แล้ว", "ต้อง", "ได้", "ใช้", "เรียน", "หลักสูตร", "สาขา", "สาขาวิชา", "วิชา", "ของ", "ที่", "และ",
    "มี", "เป็น", "ใน", "กับ", "ให้", "จะ", "ก็", "ว่า", "นี้", "นั้น", "คือ", "เมื่อ", "ใด", "ไร", "ไป", "มา", "ถึง",
    "สถาบัน", "สจล", "สจล.", "ลาดกระบัง", "คณะ", "นักศึกษา", "นักเรียน", "kmitl", "faculty", "university", "student", "students",
    # comparison words carry no topic: a topic-less comparison falls back to the program overview
    "ต่างกัน", "ต่าง", "แตกต่าง", "เปรียบเทียบ", "เทียบ", "ดีกว่า", "เหมือน", "เหมือนกัน", "ไหน", "อัน", "difference", "different",
    "differ", "differences", "compare", "comparison", "vs", "versus", "better", "between", "区别", "不同", "比较", "哪个",
    "the", "a", "an", "is", "are", "do", "does", "how", "many", "much", "what", "which", "when", "of", "in", "for",
    "to", "and", "or", "it", "its", "program", "programme", "course", "curriculum", "about",
    "的", "是", "有", "吗", "呢", "什么", "多少", "几", "哪", "和", "在", "了", "课程", "专业",
}


@lru_cache(maxsize=1)
def _thai_stopwords() -> frozenset[str]:
    try:
        from pythainlp.corpus import thai_stopwords

        return frozenset(thai_stopwords()) | frozenset(_EXTRA_STOPWORDS)
    except ImportError:  # pragma: no cover
        return frozenset(_EXTRA_STOPWORDS)


def tokenize(text: str) -> list[str]:
    """Lower-cased content tokens: Thai words (newmm), Latin words, numbers."""
    from pythainlp import word_tokenize

    stop = _thai_stopwords()
    out: list[str] = []
    for piece in word_tokenize(text, engine="newmm", keep_whitespace=False):
        piece = piece.strip().lower()
        if not piece:
            continue
        if _THAI_RE.search(piece):
            if len(piece) > 1 and piece not in stop:
                out.append(piece)
        elif _CJK_RE.search(piece):
            # newmm does not segment Chinese: emit every known CJK key found in the run
            out.extend(key for key in _CJK_KEYS if key in piece)
        else:
            for m in _ASCII_TOKEN_RE.findall(piece):
                tok = m.strip(".,-")
                if tok and tok not in stop:
                    out.append(tok)
    return out


def load_chunks(path: Path | str = DEFAULT_FIXTURE_PATH) -> list[Chunk]:
    chunks: list[Chunk] = []
    with Path(path).open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                chunks.append(Chunk.model_validate(json.loads(line)))
    return chunks


class FixtureRetriever:
    """Keyword-overlap retriever over a JSONL fixture (no network, no LLM).

    score(chunk) = Σ idf(t) for query terms t found in the chunk ÷ Σ idf(t) over
    all query terms, so it is 1.0 when every informative query term is present
    and 0.0 when none is.  Program ids are excluded from the score (they are a
    filter, not evidence).
    """

    name = "fixture"

    def __init__(self, path: Path | str = DEFAULT_FIXTURE_PATH, chunks: Iterable[Chunk] | None = None):
        self.path = Path(path)
        self.chunks: list[Chunk] = list(chunks) if chunks is not None else load_chunks(self.path)
        self._tf: dict[str, Counter[str]] = {c.chunk_id: Counter(tokenize(f"{c.heading_path} {c.text}")) for c in self.chunks}
        self._terms: dict[str, set[str]] = {cid: set(tf) for cid, tf in self._tf.items()}
        df: Counter[str] = Counter()
        for terms in self._terms.values():
            df.update(terms)
        n = max(1, len(self.chunks))
        self._idf = {t: math.log(1 + n / d) for t, d in df.items()}
        self._unknown_idf = math.log(1 + n)  # a query term absent from the corpus

    def _weight(self, term: str, alternatives: tuple[str, ...]) -> float:
        known = [self._idf[t] for t in (term, *alternatives) if t in self._idf]
        return max(known) if known else self._unknown_idf

    def score(self, query_terms: set[str], chunk: Chunk) -> float:
        terms = self._terms[chunk.chunk_id]
        total = 0.0
        found = 0.0
        for t in query_terms:
            alts = SYNONYMS.get(t, ())
            w = self._weight(t, alts)
            total += w
            if t in terms or any(a in terms for a in alts):
                found += w
        return found / total if total > 0 else 0.0

    def _overview(self, wanted: set[str], k: int) -> list[Chunk]:
        """Topic-less query (e.g. "AIT กับ DSBA ต่างกันยังไง"): first pages of each named program."""
        if not wanted:
            return []
        def priority(c: Chunk) -> tuple[int, int, str]:
            rank = next((i for i, kw in enumerate(_OVERVIEW_ORDER) if kw in c.heading_path), len(_OVERVIEW_ORDER))
            return (rank, c.page, c.chunk_id)

        out: list[Chunk] = []
        for pid in sorted(wanted):
            out.extend(sorted((c for c in self.chunks if c.program == pid), key=priority)[: max(1, k // len(wanted))])
        return [c.model_copy(update={"score": OVERVIEW_SCORE}) for c in out[:k]]

    async def retrieve(self, query: str, programs: list[str], k: int = 8) -> list[Chunk]:
        wanted = {p.upper() for p in programs if p}
        q = {t for t in tokenize(query) if t.upper() not in ("AIT", "DSBA", "BIT", "IT")}
        if not q:
            return self._overview(wanted, k)
        scored: list[tuple[float, int, Chunk]] = []
        for c in self.chunks:
            if wanted and c.program not in wanted:
                continue
            s = self.score(q, c)
            if s > 0:
                # tie-breaker: how often the query terms (or synonyms) occur in the chunk
                tf = self._tf[c.chunk_id]
                hits = sum(tf[t] + sum(tf[a] for a in SYNONYMS.get(t, ())) for t in q)
                scored.append((s, hits, c))
        scored.sort(key=lambda sc: (-sc[0], -sc[1], sc[2].program, sc[2].page, sc[2].chunk_id))
        return [c.model_copy(update={"score": round(s, 4)}) for s, _, c in scored[:k]]


def get_retriever() -> Retriever:
    """Select the implementation from ``RETRIEVER=fixture|qdrant`` (default fixture)."""
    kind = (os.environ.get("RETRIEVER") or "fixture").strip().lower()
    if kind == "fixture":
        return FixtureRetriever(os.environ.get("FIXTURE_CHUNKS_PATH") or DEFAULT_FIXTURE_PATH)
    if kind == "qdrant":
        try:
            module = importlib.import_module("rag.qdrant_retriever")
            cls = module.QdrantRetriever
        except (ImportError, AttributeError) as exc:
            raise RuntimeError(
                "RETRIEVER=qdrant but rag.qdrant_retriever:QdrantRetriever is not available "
                f"({exc}). Ask the retrieval owner for it or set RETRIEVER=fixture."
            ) from exc
        return cls()
    raise RuntimeError(f"Unknown RETRIEVER={kind!r}; expected 'fixture' or 'qdrant'.")
