"""ChromaRetriever mapping (their Hit -> our Chunk) — pure functions, no index, no models."""

from __future__ import annotations

from dataclasses import dataclass, field

from rag.chroma_retriever import (
    DOC_NAME_TO_PROGRAM,
    PROGRAM_TO_DOC_NAME,
    ChromaRetriever,
    heading_from_metadata,
    hit_to_chunk,
    hits_to_chunks,
    page_from_metadata,
    programs_to_doc_names,
)
from rag.retriever import Chunk, Retriever


@dataclass
class FakeHit:
    id: str
    text: str
    metadata: dict = field(default_factory=dict)
    score: float = 0.0
    dense_rank: int | None = None
    bm25_rank: int | None = None


def test_doc_name_program_map_is_a_bijection_over_the_four_programs():
    assert set(DOC_NAME_TO_PROGRAM.values()) == {"AIT", "DSBA", "BIT", "IT"}
    assert PROGRAM_TO_DOC_NAME["BIT"] == "IT_inter2565" and PROGRAM_TO_DOC_NAME["IT"] == "IT2565"
    assert programs_to_doc_names([]) is None
    assert programs_to_doc_names(["bit", "IT"]) == ["IT_inter2565", "IT2565"]
    assert programs_to_doc_names(["XYZ"]) is None


def test_page_is_the_pdf_page_from_page_index():
    assert page_from_metadata({"page_index": 104, "page_label": "133"}) == 105  # PDF page, not the printed folio
    assert page_from_metadata({"page_index": 0, "page_label": None}) == 1
    assert page_from_metadata({"page_label": "12"}) == 12  # no page_index -> numeric folio
    assert page_from_metadata({"page_label": "ก"}) == 1
    assert page_from_metadata({}) == 1


def test_heading_path_from_section_or_course_code():
    assert heading_from_metadata({"section": "3.5 รายวิชาในแต่ละกลุ่มทักษะ"}) == "3.5 รายวิชาในแต่ละกลุ่มทักษะ"
    assert heading_from_metadata({"section": "", "chunk_type": "course", "course_code": "06016408"}) == "คำอธิบายรายวิชา 06016408"
    assert heading_from_metadata({"section": "", "chunk_type": "general"}) == ""


def test_hit_to_chunk_keeps_id_and_text_verbatim_and_fills_debug():
    hit = FakeHit(id="IT2565::course::06016408", text="06016408 การสร้างโปรแกรมเชิงวัตถุ\n3(2-2-5)",
                  metadata={"doc_name": "IT2565", "page_index": 247, "page_label": "270", "section": "คำอธิบายรายวิชา",
                            "chunk_type": "course", "course_code": "06016408"}, score=1.0164, dense_rank=1, bm25_rank=2)
    c = hit_to_chunk(hit, 1.0)
    assert isinstance(c, Chunk)
    assert c.chunk_id == "IT2565::course::06016408" and c.program == "IT" and c.page == 248
    assert c.text == hit.text and c.heading_path == "คำอธิบายรายวิชา" and c.score == 1.0
    assert c.debug["raw_score"] == 1.0164 and c.debug["page_label"] == "270" and c.debug["dense_rank"] == 1
    assert "debug" not in c.model_dump() and "synthetic" not in c.model_dump()


def test_unknown_doc_name_is_dropped():
    assert hit_to_chunk(FakeHit(id="X::gen::0001", text="…", metadata={"doc_name": "OTHER"}), 1.0) is None


def test_hits_to_chunks_normalises_scores_per_result_set():
    hits = [FakeHit("AIT::gen::0001", "a", {"doc_name": "AIT", "page_index": 1}, 0.032),
            FakeHit("DSBA::gen::0002", "b", {"doc_name": "DSBA", "page_index": 2}, 0.016),
            FakeHit("X::gen::0003", "c", {"doc_name": "OTHER"}, 0.010)]
    out = hits_to_chunks(hits)
    assert [c.chunk_id for c in out] == ["AIT::gen::0001", "DSBA::gen::0002"]
    assert out[0].score == 1.0 and out[1].score == 0.5
    assert out[0].debug["raw_score"] == 0.032
    assert hits_to_chunks([]) == []
    zero = hits_to_chunks([FakeHit("AIT::gen::0001", "a", {"doc_name": "AIT"}, 0.0)])
    assert zero[0].score == 0.0


def test_chroma_retriever_is_lazy_and_satisfies_the_protocol(monkeypatch):
    monkeypatch.setenv("RERANK", "1")
    monkeypatch.setenv("RETRIEVE_CAND_K", "33")
    r = ChromaRetriever()
    assert isinstance(r, Retriever) and r.name == "chroma"
    assert r.use_rerank is True and r.cand_k == 33 and r.load_seconds is None  # nothing loaded yet
    assert ChromaRetriever(use_rerank=False, cand_k=5).cand_k == 5
