"""Deterministic answer checks: number grounding, language, leakage, containment."""

from __future__ import annotations

from rag.checks import (
    contains_all,
    contains_any,
    dominant_script,
    extract_numbers,
    has_think_leak,
    language_matches,
    leakage_problems,
    normalize_digits,
    ungrounded_numbers,
)

CONTEXT = "[1] AIT หน้า 12 — โครงสร้าง\nจำนวนหน่วยกิตรวม 120 หน่วยกิต ระยะเวลา 4 ปี ค่าธรรมเนียม 32,000 บาท GPAX 2.50 รหัส 06016317 IELTS 5.5"


def test_normalize_digits():
    assert normalize_digits("๑๒๐ หน่วยกิต ๔ ปี") == "120 หน่วยกิต 4 ปี"


def test_extract_numbers_ignores_markers_and_canonicalises():
    assert extract_numbers("เรียน 120 หน่วยกิต [1] ค่าเทอม 32,000 บาท [2][3] GPAX 2.50") == ["120", "32000", "2.50"]
    assert extract_numbers("๑๒๐ หน่วยกิต") == ["120"]


def test_ungrounded_numbers_detects_hallucinated_values():
    assert ungrounded_numbers("AIT เรียน 120 หน่วยกิต 4 ปี [1] ค่าเทอม 32,000 บาท [1]", CONTEXT) == []
    assert ungrounded_numbers("AIT เรียน 129 หน่วยกิต 4 ปี [1]", CONTEXT) == ["129"]
    assert ungrounded_numbers("ค่าเทอม 32000 บาท และ 256,000 ตลอดหลักสูตร", CONTEXT) == ["256000"]
    assert ungrounded_numbers("๑๒๐ หน่วยกิต ๕ ปี", CONTEXT) == ["5"]  # 5 is not a context number ("5.5" is)


def test_ungrounded_numbers_allows_digit_runs_inside_context_numbers():
    assert ungrounded_numbers("รหัส 06016317 [1]", CONTEXT) == []
    assert ungrounded_numbers("IELTS 5.5 [1]", CONTEXT) == []


def test_dominant_script_and_language_match():
    assert dominant_script("หลักสูตร AIT เรียน 120 หน่วยกิต [1]") == "th"
    assert dominant_script("The AIT program takes 4 years [1]") == "en"
    assert dominant_script("AIT专业学制4年 [1]") == "zh"
    assert language_matches("The AIT (เทคโนโลยีปัญญาประดิษฐ์) program is 4 years long and has 120 credits in total [1]", "en")
    assert not language_matches("หลักสูตร AIT เรียน 4 ปี [1]", "en")
    assert language_matches("Answer in English", "other")


def test_leakage():
    assert has_think_leak("<think>x</think> y") and has_think_leak("</THINK>") and not has_think_leak("[1] ok")
    assert leakage_problems("ok [1][2]", 2) == []
    problems = leakage_problems("<think>a</think> ok [3]", 2)
    assert any("think" in p for p in problems) and any("[3]" in p for p in problems)


def test_contains_all_and_any_normalise():
    assert contains_all("เรียน ๑๒๐  หน่วยกิต ใช้เวลา 4 ปี", ["120", "4 ปี"]) == []
    assert contains_all("เรียน 129 หน่วยกิต", ["120", "4 ปี"]) == ["120", "4 ปี"]
    assert contains_any("ไม่พบข้อมูลในเอกสารหลักสูตร ค่ะ", ["ไม่พบข้อมูลในเอกสารหลักสูตร", "not found"]) == ["ไม่พบข้อมูลในเอกสารหลักสูตร"]
