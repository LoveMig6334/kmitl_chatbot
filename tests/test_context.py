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


def test_flatten_tables_turns_ocr_html_into_rows():
    from rag.context import flatten_tables

    html = ('3.1.4 แผนการศึกษา\n\n<table><tr><td>รหัสวิชา</td><td>ชื่อวิชา</td><td>หน่วยกิต<br/>(บรรยาย-ปฏิบัติ)</td></tr>'
            '<tr><td>06016401</td><td>คณิตศาสตร์สำหรับเทคโนโลยีสารสนเทศ<br/>MATHEMATICS FOR IT</td><td>3(3-0-6)</td></tr>'
            '<tr><td colspan="2">รวม</td><td>18</td></tr></table>\n\nรวมตลอดหลักสูตร 129 หน่วยกิต')
    flat = flatten_tables(html)
    assert "<" not in flat and ">" not in flat
    assert "รหัสวิชา | ชื่อวิชา | หน่วยกิต (บรรยาย-ปฏิบัติ)" in flat
    assert "06016401 | คณิตศาสตร์สำหรับเทคโนโลยีสารสนเทศ MATHEMATICS FOR IT | 3(3-0-6)" in flat
    assert "รวม | 18" in flat
    assert flat.startswith("3.1.4 แผนการศึกษา") and flat.endswith("รวมตลอดหลักสูตร 129 หน่วยกิต")
    assert flatten_tables("ไม่มีตาราง 120 หน่วยกิต") == "ไม่มีตาราง 120 หน่วยกิต"


def test_format_chunk_flattens_tables():
    from rag.context import format_chunk
    from rag.retriever import Chunk

    c = Chunk(chunk_id="IT2565::gen::0019", program="IT", page=26, heading_path="", text="<table><tr><td>a</td><td>b</td></tr></table>")
    assert format_chunk(1, c) == "[1] IT หน้า 26\na | b"
