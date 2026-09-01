"""Pure-function tests for the PDF fixture pipeline (no PDFs, no network).

``scripts/pdf_thai.py`` (PUA repair) and ``scripts/build_fixtures.py`` (line
cleaning, heading tracking, block splitting) — plus invariants of the real
fixture file when it is present.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import audit_fixtures
import build_fixtures as bf
import pdf_thai

REAL = ROOT / "tests" / "fixtures" / "chunks.jsonl"


# ----------------------------------------------------------------- pdf_thai --
def test_repair_maps_pua_and_normalises_sara_am():
    pua_map = {"\ue04a": "\u0e31", "\ue04e": "\u0e35", "\ue05b": "\u0e48"}
    assert pdf_thai.repair("หล\ue04aกสูตร รายละเอ\ue04eยด อื\ue05bน", pua_map) == "หลักสูตร รายละเอียด อื่น"
    assert pdf_thai.repair("สําเร็จ", {}) == "สำเร็จ"  # ํ + า → ำ
    assert pdf_thai.repair("x\ue0ffy", {}) == "xy"  # unknown code dropped


def test_mark_ratio_and_is_pua():
    assert pdf_thai.mark_ratio("กขค") == 0.0
    assert 0.10 < pdf_thai.mark_ratio("หลักสูตรวิทยาศาสตรบัณฑิต สาขาวิชาเทคโนโลยีสารสนเทศ") < 0.3  # 0.143
    assert pdf_thai.is_pua("\ue04a") and not pdf_thai.is_pua("ก")


def test_score_prefers_long_dictionary_word():
    ctx = [("หล", "กสูตร"), ("สถาบ", "นอุดม")]
    assert pdf_thai._score(ctx, "ั") > pdf_thai._score(ctx, "ุ")
    assert pdf_thai._score([("ผู้สำเร", "จการ")], "็") > pdf_thai._score([("ผู้สำเร", "จการ")], "่")


# ----------------------------------------------------------- build_fixtures --
def test_clean_lines_strips_headers_and_footers():
    text = "3\nรายละเอียดหลักสูตร\n8. อาชีพ\nวท.บ.(สาขาวิชาเทคโนโลยีปัญญาประดิษฐ์) คณะเทคโนโลยีสารสนเทศสจล.\nมคอ. 2\nวท.บ(วิทยาการข้อมูล) สาขาวิชา\nคณะเทคโนโลยีสารสนเทศสจล.\n\nเนื้อหา  จริง"
    assert bf.clean_lines(text) == ["8. อาชีพ", "", "เนื้อหา จริง"]


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("หมวดที่3 ระบบการจัดการศึกษา", (0, "หมวดที่3 ระบบการจัดการศึกษา")),
        ("8. อาชีพที่สามารถประกอบได้หลังสำเร็จการศึกษา", (1, "8. อาชีพที่สามารถประกอบได้หลังสำเร็จการศึกษา")),
        ("2.2 คุณสมบัติของผู้เข้าศึกษา", (2, "2.2 คุณสมบัติของผู้เข้าศึกษา")),
        ("3.1.1 จำนวนหน่วยกิตรวมตลอดหลักสูตร", (3, "3.1.1 จำนวนหน่วยกิตรวมตลอดหลักสูตร")),
        ("5.6. การให้ปริญญาแก่ผู้สำเร็จการศึกษา", (2, "5.6. การให้ปริญญาแก่ผู้สำเร็จการศึกษา")),
        ("3 (3-0-6)", None),  # credit cell in a study-plan table
        ("30 ชั่วโมง", None),
        ("06046400", None),  # course code
        ("(1) นักวิทยาศาสตร์ข้อมูล", None),
        ("ก. หมวดวิชาศึกษาทั่วไป 24 หน่วยกิต", None),
    ],
)
def test_heading_level(line, expected):
    assert bf.heading_level(line) == expected


def test_split_block_respects_max_chars_on_line_boundaries():
    lines = ["ก" * 300, "ข" * 300, "ค" * 300]
    parts = bf.split_block(lines)
    assert parts == [[lines[0], lines[1]], [lines[2]]]
    assert all(len("\n".join(p)) <= bf.MAX_CHARS for p in parts)


def test_page_blocks_tracks_heading_path_across_pages():
    path: list[str] = []
    b1 = bf.page_blocks(2, ["หมวดที่1 ข้อมูลทั่วไป", "1. ชื่อหลักสูตร", "ชื่อภาษาไทย", "", "", "2. ชื่อปริญญา", "วท.บ."], path)
    b2 = bf.page_blocks(3, ["ต่อจากหน้าก่อน"], path)
    assert [b["heading_path"] for b in b1] == ["หมวดที่1 ข้อมูลทั่วไป > 1. ชื่อหลักสูตร", "หมวดที่1 ข้อมูลทั่วไป > 2. ชื่อปริญญา"]
    assert b1[0]["lines"] == ["หมวดที่1 ข้อมูลทั่วไป", "1. ชื่อหลักสูตร", "ชื่อภาษาไทย"]
    assert b2[0]["heading_path"] == "หมวดที่1 ข้อมูลทั่วไป > 2. ชื่อปริญญา" and b2[0]["page"] == 3


def test_toc_detection():
    toc = {"text": "หมวดที่ 1 ......... 1\nหมวดที่ 2 ......... 5\nหมวดที่ 3 ......... 9"}
    form = {"text": "☑ หลักสูตรปริญญาตรี4 ปี\n☐ อื่นๆ(ระบุ) ...................."}
    assert bf._is_toc(toc) and not bf._is_toc(form)


def test_select_blocks_caps_per_fact_and_records_facts():
    blocks = [{"page": i, "heading_path": "", "text": "จำนวนหน่วยกิตรวมตลอดหลักสูตร 120 หน่วยกิต " * 2, "lines": [], "part": 0} for i in range(1, 6)]
    blocks.append({"page": 9, "heading_path": "", "text": "กำหนดเปิดสอนเดือนกรกฎาคม พ.ศ. 2566 ภาคการศึกษาที่ 1", "lines": [], "part": 0})
    picked = bf.select_blocks(blocks)
    assert [b["page"] for b in picked] == [1, 2, 3, 9]
    assert picked[0]["facts"] == ["credits_total"] and picked[-1]["facts"] == ["opening"]


# -------------------------------------------------------- audit + real file --
def test_audit_suspicious_detects_damage():
    assert audit_fixtures.suspicious("หลักสูตรวิทยาศาสตรบัณฑิต สาขาวิชาเทคโนโลยีสารสนเทศ") == []
    assert any("PUA" in p for p in audit_fixtures.suspicious("หล\ue04aกสูตร"))
    assert any("floating" in p for p in audit_fixtures.suspicious("หลัก ิสูตร"))
    assert any("decomposed" in p for p in audit_fixtures.suspicious("สําเร็จ"))
    assert any("leaked" in p for p in audit_fixtures.suspicious("ข้อความ\nวท.บ.(สาขาวิชาไอที) คณะเทคโนโลยีสารสนเทศ สจล."))
    assert not any("PUA" in p for p in audit_fixtures.suspicious("3(3-0-6) 3(2-2-5)"))  # hyphens are not PUA


@pytest.mark.skipif(not REAL.exists(), reason="real fixtures not built")
def test_real_fixture_invariants():
    rows = [json.loads(line) for line in REAL.open(encoding="utf-8") if line.strip()]
    if any(r.get("synthetic") for r in rows):
        pytest.skip("chunks.jsonl is the synthetic set")
    assert 60 <= len(rows) <= 160
    assert len({r["chunk_id"] for r in rows}) == len(rows)
    per_program = Counter(r["program"] for r in rows)
    assert set(per_program) == {"AIT", "DSBA", "BIT", "IT"} and min(per_program.values()) >= 10
    assert all(isinstance(r["page"], int) and r["page"] >= 1 and len(r["text"]) <= bf.MAX_CHARS for r in rows)
    assert [r for r in rows if audit_fixtures.suspicious(r["text"])] == []
    for prog in ("AIT", "DSBA", "BIT", "IT"):
        facts = {f for r in rows if r["program"] == prog for f in r["facts"]}
        assert set(audit_fixtures.REQUIRED_FACTS) <= facts, f"{prog} missing {set(audit_fixtures.REQUIRED_FACTS) - facts}"
