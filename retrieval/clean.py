"""
clean.py — ทำความสะอาดผล OCR ต่อหน้า ก่อนส่งเข้า chunking

รับผิดชอบ (ตาม skill.md ขั้น Cleaning + รับมือ artifact ของโมเดล 1.5-3b):
1. ดึง page_label จากแท็ก <page_number>NNN</page_number> (เลขหน้าที่พิมพ์บนกระดาษจริง)
2. ตัด header/footer ที่ซ้ำเกือบทุกหน้า — ตรวจอัตโนมัติแบบ corpus-level
   (บรรทัดที่โผล่บนหลายหน้าเกินเกณฑ์ = boilerplate) ใช้ได้กับทุกไฟล์ ไม่ต้อง hardcode
3. ตัด hallucination artifact ของ OCR: บรรทัด +++...+++, มาร์ก *NN* โดดๆ, แท็ก page_number
4. normalize ไทย: NFC + pythainlp.util.normalize — คงรหัสวิชา (เลข 7-8 หลัก) และอังกฤษเป๊ะ

โครงสร้างข้อมูล: CleanPage = {page_index, page_label, text}
"""
from __future__ import annotations

import re
import sys
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from pythainlp.util import normalize as thai_normalize

PAGE_NUM_TAG = re.compile(r"<page_number>\s*(\d+)\s*</page_number>", re.I)
PLUS_ARTIFACT = re.compile(r"^\s*\+{3,}.*\+{3,}\s*$")     # +++ ... +++ (hallucination; ไม่โดน C++)
STAR_MARK = re.compile(r"^\s*\*\s*\d+\s*\*\s*$")            # *25* โดดๆ
ONLY_NUM = re.compile(r"^\s*\d{1,3}\s*$")                    # เลขหน้าโดดๆ (2, 26)
MKAO = re.compile(r"^\s*มคอ\.?\s*๒?2?\s*$")                  # "มคอ. 2" / "มคอ.2"

# เกณฑ์: บรรทัดที่ปรากฏบน >= ratio ของหน้าทั้งหมด ถือเป็น header/footer
BOILERPLATE_PAGE_RATIO = 0.30
BOILERPLATE_MIN_PAGES = 5


@dataclass
class CleanPage:
    page_index: int          # index 0-based ในไฟล์ PDF
    page_label: str | None   # เลขหน้าที่พิมพ์ (จาก <page_number>) เช่น "125"
    text: str                # ข้อความสะอาด


BARE_NUM_LINE = re.compile(r"^\s*(\d{1,4})\s*$")


def extract_page_label(md: str) -> str | None:
    """เลขหน้าพิมพ์ = เลขที่ 'หัวหน้า' เท่านั้น (บน ~3 บรรทัดแรกที่มีเนื้อหา)

    รองรับ 2 รูปแบบที่พบจริง:
    - LOCAL 3b : <page_number>149</page_number> อยู่บนสุด
    - API 1.5  : เลขล้วน "213" เป็นบรรทัดแรก, ส่วน <page_number> ที่ 'ท้ายหน้า'
                 คือเลข section (เช่น 26/92) → ต้องไม่หยิบมาเป็น page_label
    จึงสแกนเฉพาะหัวหน้า และไม่ใช้แท็กท้ายหน้า
    """
    non_empty = [ln for ln in md.splitlines() if ln.strip()]
    for ln in non_empty[:3]:
        m = PAGE_NUM_TAG.search(ln)
        if m:
            return m.group(1)
        m = BARE_NUM_LINE.match(ln)
        if m:
            return m.group(1)
    return None


def _norm_line_for_compare(line: str) -> str:
    """normalize บรรทัดสำหรับเทียบหา boilerplate (ตัด page tag/เลข/ช่องว่าง)"""
    s = PAGE_NUM_TAG.sub("", line)
    s = re.sub(r"\d+", "#", s)          # เลขหน้าต่างกัน -> แทนด้วย # เพื่อจับ footer เดียวกัน
    return re.sub(r"\s+", " ", s).strip()


def find_boilerplate(pages_md: list[str]) -> set[str]:
    """หา header/footer ซ้ำแบบ corpus-level คืน set ของบรรทัด (normalized) ที่เป็น boilerplate"""
    n = len(pages_md)
    counter: Counter[str] = Counter()
    for md in pages_md:
        seen = set()
        for line in md.splitlines():
            key = _norm_line_for_compare(line)
            if len(key) >= 8 and key not in seen:   # ยาวพอจะเป็นข้อความ ไม่ใช่เลขโดดๆ
                seen.add(key)
                counter[key] += 1
    threshold = max(BOILERPLATE_MIN_PAGES, int(n * BOILERPLATE_PAGE_RATIO))
    return {key for key, c in counter.items() if c >= threshold}


def normalize_thai(text: str) -> str:
    """NFC + pythainlp normalize (ปลอดภัยกับรหัสวิชา/อังกฤษ)"""
    text = unicodedata.normalize("NFC", text)
    text = thai_normalize(text)
    return text


def clean_page(md: str, boilerplate: set[str]) -> str:
    """ตัด header/footer/artifact/แท็ก ออกจากหน้าเดียว แล้ว normalize"""
    out_lines: list[str] = []
    for line in md.splitlines():
        raw = line.rstrip()
        if not raw.strip():
            out_lines.append("")
            continue
        # ตัด artifact
        if PLUS_ARTIFACT.match(raw) or STAR_MARK.match(raw) or MKAO.match(raw):
            continue
        # เลขหน้าโดดๆ
        if ONLY_NUM.match(raw):
            continue
        # boilerplate (header/footer ซ้ำ)
        if _norm_line_for_compare(raw) in boilerplate:
            continue
        # เอาแท็ก page_number ออกจากตัวเนื้อ (ดึง label ไปแล้ว)
        cleaned = PAGE_NUM_TAG.sub("", raw).rstrip()
        if cleaned.strip():
            out_lines.append(cleaned)
    text = "\n".join(out_lines)
    # ยุบบรรทัดว่างซ้อน
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return normalize_thai(text)


def clean_document(extract_dir: str | Path) -> list[CleanPage]:
    """โหลดทุกหน้า .md ของเอกสาร → หา boilerplate → คืน CleanPage เรียงตามหน้า"""
    extract_dir = Path(extract_dir)
    md_files = sorted(extract_dir.glob("*.md"), key=lambda p: int(p.stem))
    if not md_files:
        raise FileNotFoundError(f"ไม่พบ .md ใน {extract_dir}")

    raw_pages = [f.read_text(encoding="utf-8") for f in md_files]
    boiler = find_boilerplate(raw_pages)

    result: list[CleanPage] = []
    for f, md in zip(md_files, raw_pages):
        page_index = int(f.stem) - 1
        label = extract_page_label(md)
        text = clean_page(md, boiler)
        result.append(CleanPage(page_index=page_index, page_label=label, text=text))
    return result


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="ทดสอบ cleaning กับหน้าที่ OCR แล้ว")
    ap.add_argument("extract_dir", help="เช่น data/extracted/IT2565")
    ap.add_argument("--show", type=int, default=3, help="โชว์กี่หน้า")
    args = ap.parse_args()

    pages = clean_document(args.extract_dir)
    print(f"โหลด {len(pages)} หน้า")
    boiler = find_boilerplate([Path(args.extract_dir, f"{p.page_index+1:03d}.md").read_text(encoding='utf-8') for p in pages])
    print(f"\nboilerplate ที่ตรวจพบ ({len(boiler)} รูปแบบ):")
    for b in list(boiler)[:10]:
        print(f"  · {b[:80]}")
    print()
    for p in pages[:args.show]:
        print(f"\n===== หน้า index {p.page_index}  (page_label={p.page_label}) =====")
        print(p.text[:800])
