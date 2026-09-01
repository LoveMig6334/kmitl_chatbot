"""Context assembly + budget + citation markers (pure functions)."""

from __future__ import annotations

from rag.context import (
    assemble_context,
    dangling_markers,
    estimate_tokens,
    extract_markers,
    format_chunk,
    strip_markers,
)
from rag.retriever import Chunk


def mk(i: int, score: float, text: str = "ข้อความทดสอบ " * 10, program: str = "AIT") -> Chunk:
    return Chunk(chunk_id=f"{program}-p{i}-c1", program=program, page=i, heading_path="หมวดที่ 3 > โครงสร้าง", text=text, score=score)


def test_estimate_tokens_thai_vs_latin():
    assert estimate_tokens("") == 0
    assert estimate_tokens("ก" * 30) == 10  # thai: 3 chars / token
    assert estimate_tokens("a" * 40) == 10  # other: 4 chars / token
    assert estimate_tokens("ก" * 30 + "a" * 40) == 20


def test_format_chunk_header():
    c = mk(12, 1.0, "จำนวนหน่วยกิต 120")
    assert format_chunk(3, c) == "[3] AIT หน้า 12 — หมวดที่ 3 > โครงสร้าง\nจำนวนหน่วยกิต 120"


def test_assemble_numbers_in_input_order_and_maps_markers():
    chunks = [mk(1, 0.5), mk(2, 0.9, program="DSBA"), mk(3, 0.7)]
    ctx = assemble_context(chunks, budget=10_000)
    assert [c.chunk_id for c in ctx.chunks] == ["AIT-p1-c1", "DSBA-p2-c1", "AIT-p3-c1"]
    assert ctx.text.startswith("[1] AIT หน้า 1") and "\n\n[2] DSBA หน้า 2" in ctx.text and "\n\n[3] AIT หน้า 3" in ctx.text
    assert ctx.dropped == [] and ctx.tokens > 0


def test_assemble_drops_lowest_score_first_until_budget_fits():
    chunks = [mk(1, 0.9), mk(2, 0.1), mk(3, 0.5), mk(4, 0.3)]
    one = estimate_tokens(format_chunk(1, chunks[0])) + 1
    ctx = assemble_context(chunks, budget=one * 2 + 1)
    assert [c.chunk_id for c in ctx.chunks] == ["AIT-p1-c1", "AIT-p3-c1"]  # order kept, 0.1 then 0.3 dropped
    assert [c.chunk_id for c in ctx.dropped] == ["AIT-p2-c1", "AIT-p4-c1"]
    assert ctx.tokens <= one * 2 + 1


def test_assemble_keeps_at_least_one_chunk_truncated():
    big = mk(1, 0.9, text="ก" * 3000)
    ctx = assemble_context([big, mk(2, 0.2)], budget=100)
    assert len(ctx.chunks) == 1 and ctx.chunks[0].text.endswith("…")
    assert ctx.tokens <= 110  # header + truncated text (the estimate is approximate)


def test_assemble_empty():
    ctx = assemble_context([], budget=100)
    assert ctx.text == "" and ctx.chunks == [] and ctx.tokens == 0


def test_extract_markers_variants():
    assert extract_markers("AIT เรียน 120 หน่วยกิต [1] ใช้เวลา 4 ปี [1][3] ค่าเทอม [2, 4] และ [5，6]") == [1, 3, 2, 4, 5, 6]
    assert extract_markers("no markers 120 หน่วยกิต") == []
    assert extract_markers("[12]") == [12]


def test_strip_and_dangling_markers():
    assert strip_markers("120 หน่วยกิต [1] 4 ปี [2][3]") == "120 หน่วยกิต  4 ปี "
    assert dangling_markers("[1] ok [4] bad [0] bad", n_chunks=3) == [4, 0]
    assert dangling_markers("[1][2]", n_chunks=2) == []
