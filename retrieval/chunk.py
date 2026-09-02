"""
chunk.py — ตัด chunk แบบ structure-aware จากหน้าที่ cleaning แล้ว

หลักการ (ตาม skill.md ขั้น Chunking):
- **1 รายวิชา = 1 chunk สมบูรณ์**: รหัส + ชื่อไทย + ชื่ออังกฤษ + หน่วยกิต + วิชาบังคับก่อน
  + คำอธิบาย (ไทย+อังกฤษ). วิชาใหม่เริ่มที่บรรทัดรหัส 8 หลักเสมอ. คำอธิบายข้ามหน้าได้
  → ทำบน "สตรีมที่ต่อทุกหน้าแล้ว" ไม่ใช่รายหน้า
- เนื้อหาทั่วไป (ไม่ใช่รายวิชา) → ตัดตามย่อหน้า ~300-500 token, overlap เล็กน้อย,
  ใช้ newmm หาขอบเขตไม่ตัดกลางคำไทย
- metadata ทุก chunk: {doc_name, doc_type, section, page_label, course_code?, chunk_type}

โครงสร้างผลลัพธ์: Chunk = {id, text, metadata}
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from pythainlp.tokenize import word_tokenize

from rag.clean import clean_document, CleanPage

# --- รูปแบบรหัสวิชา ---
# รหัส 8 หลักขึ้นต้นบรรทัด ตามด้วยชื่อ (รหัสในเล่มนี้ขึ้นต้น 06.. / 90..)
COURSE_LINE = re.compile(r"^\s*(\d{8})\s+(.+)$")
CREDIT_PAT = re.compile(r"(\d)\s*\(\s*\d+\s*-\s*\d+\s*-\s*\d+\s*\)")
# หัวข้อหมวด/section (ใช้ track section ปัจจุบัน)
SECTION_HEAD = re.compile(
    r"^\s*(หมวดที่\s*\d+.*|คำอธิบายรายวิชา.*|\d+\.\s*\S.*|[0-9]+\.[0-9]+\s*\S.*)$"
)

# บรรทัด "โครงสร้าง" ที่บอกจบรายวิชา (กันหน้าโครงสร้างหลักสูตรกวาด header กลุ่มถัดไปเข้า chunk)
COURSE_BOUNDARY = re.compile(
    r"^\s*("
    r"รหัสวิชา\s+ชื่อวิชา.*"          # หัวตารางรายวิชา
    r"|กลุ่มวิชา\S.*"                  # หัวข้อกลุ่มวิชา
    r"|หมวดวิชา\S.*"
    r"|หมวดที่\s*\d+.*"
    r"|ภาคผนวก\s*\S.*"                 # ขึ้นภาคผนวก -> จบรายวิชา
    r"|ตารางเปรียบเทียบ.*"            # ตารางเทียบหลักสูตร (ภาคผนวก)
    r"|<table.*"                       # ตาราง = หน่วยแยก ไม่ควรอยู่ในคำอธิบายรายวิชา
    r"|\d+\)\s*$"                       # เลขกลุ่ม เช่น "2)" "3)"
    r"|[ก-๙].*\d+\s*หน่วยกิต\s*$"       # ยอดหน่วยกิตกลุ่ม
    r"|\*.*"                            # หมายเหตุขึ้นต้น *
    r"|90644xxx.*|06\d{2}xxx.*"        # placeholder รหัสวิชาเลือก
    r")"
)

# cap ความยาว course chunk (กันพองผิดปกติเมื่อไม่เจอ boundary/รหัสถัดไป)
MAX_COURSE_CHARS = 2500

# เป้าหมายขนาด chunk ทั่วไป (token ~= คำ newmm)
TARGET_TOKENS = 400
MAX_TOKENS = 500
OVERLAP_TOKENS = 50


@dataclass
class Chunk:
    id: str
    text: str
    metadata: dict = field(default_factory=dict)


def _count_tokens(text: str) -> int:
    return len(word_tokenize(text, engine="newmm"))


@dataclass
class _Line:
    text: str
    page_label: str | None
    page_index: int


def _flatten(pages: list[CleanPage]) -> list[_Line]:
    """แปลงหลายหน้าเป็นสตรีมบรรทัดเดียว พก page_label/page_index ติดไปแต่ละบรรทัด"""
    lines: list[_Line] = []
    for p in pages:
        for ln in p.text.splitlines():
            lines.append(_Line(ln, p.page_label, p.page_index))
    return lines


def _is_course_start(line: str) -> tuple[str, str] | None:
    """คืน (course_code, rest) ถ้าบรรทัดนี้เริ่มรายวิชาใหม่ (รหัส 8 หลัก + ชื่อ)"""
    m = COURSE_LINE.match(line)
    if not m:
        return None
    code, rest = m.group(1), m.group(2).strip()
    # กันเลข 8 หลักที่ไม่ใช่รหัสวิชา: ต้องมีตัวอักษรไทย/อังกฤษตามหลัง
    if re.search(r"[ก-๙A-Za-z]", rest):
        return code, rest
    return None


def _detect_section(line: str, current: str) -> str:
    m = SECTION_HEAD.match(line.strip())
    if m and len(line.strip()) < 80:
        return line.strip()
    return current


def chunk_pages(pages: list[CleanPage], doc_name: str,
                doc_type: str = "หลักสูตร") -> list[Chunk]:
    lines = _flatten(pages)
    chunks: list[Chunk] = []
    section = ""

    # buffer สำหรับเนื้อหาทั่วไป (ไม่ใช่รายวิชา)
    gen_buf: list[_Line] = []

    def flush_general():
        nonlocal gen_buf
        if not gen_buf:
            return
        _emit_general(gen_buf, chunks, doc_name, doc_type)
        gen_buf = []

    i = 0
    n = len(lines)
    while i < n:
        ln = lines[i]
        section = _detect_section(ln.text, section)

        cs = _is_course_start(ln.text)
        if cs:
            # ปิด general ก่อน
            flush_general()
            code, _ = cs
            # เก็บบรรทัดของรายวิชานี้จนกว่าจะเจอรหัสถัดไป
            start = i
            j = i + 1
            acc = len(ln.text)
            # จบรายวิชาเมื่อ: เจอรหัสถัดไป / บรรทัดโครงสร้าง (header กลุ่ม/ตาราง/หมายเหตุ) / ยาวเกิน cap
            while j < n and not _is_course_start(lines[j].text) \
                    and not COURSE_BOUNDARY.match(lines[j].text) \
                    and acc <= MAX_COURSE_CHARS:
                acc += len(lines[j].text) + 1
                j += 1
            body_lines = lines[start:j]
            text = "\n".join(l.text for l in body_lines).strip()
            page_label = body_lines[0].page_label
            page_index = body_lines[0].page_index
            chunks.append(Chunk(
                id=f"{doc_name}::course::{code}",
                text=text,
                metadata={
                    "doc_name": doc_name,
                    "doc_type": doc_type,
                    "section": section or "คำอธิบายรายวิชา",
                    "page_label": page_label,
                    "page_index": page_index,
                    "course_code": code,
                    "chunk_type": "course",
                },
            ))
            i = j
            continue

        # เนื้อหาทั่วไป
        gen_buf.append(ln)
        i += 1

    flush_general()

    # ทำให้ id ไม่ซ้ำ (วิชาเดียวอาจโผล่ทั้งหน้าโครงสร้าง+คำอธิบาย → id course ซ้ำได้)
    # Chroma ต้องการ id unique; เติม suffix เฉพาะตัวที่ซ้ำ คง id หลักอ่านง่าย
    seen: dict[str, int] = {}
    for c in chunks:
        if c.id in seen:
            seen[c.id] += 1
            c.id = f"{c.id}#{seen[c.id]}"
        else:
            seen[c.id] = 0
    return chunks


def _split_big_unit(text: str, page_label, page_index) -> list[_Line]:
    """ซอยข้อความก้อนเดียวที่ใหญ่เกิน MAX_TOKENS ให้เป็นหลาย unit

    - ถ้าเป็นตาราง (<table>): ซอยตาม </tr> แล้วห่อ <table>..</table> ใหม่ต่อกลุ่ม
    - ถ้าเป็นข้อความยาว: ซอยตามคำ newmm เป็นหน้าต่าง ~TARGET_TOKENS
    """
    if _count_tokens(text) <= MAX_TOKENS:
        return [_Line(text, page_label, page_index)]

    def word_split(s: str) -> list[str]:
        w = word_tokenize(s, engine="newmm")
        return ["".join(w[k:k + TARGET_TOKENS]).strip() for k in range(0, len(w), TARGET_TOKENS)]

    raw_units: list[str] = []
    if "<table" in text:
        rows = re.split(r"(?<=</tr>)", text)
        cur, cur_tok = [], 0
        for r in rows:
            if not r.strip():
                continue
            rt = _count_tokens(r)
            if cur_tok + rt > TARGET_TOKENS and cur:
                body = "".join(cur)
                raw_units.append(f"<table>{body}</table>" if "<table" not in body else body)
                cur, cur_tok = [], 0
            cur.append(r); cur_tok += rt
        if cur:
            body = "".join(cur)
            raw_units.append(f"<table>{body}</table>" if "<table" not in body else body)
    else:
        raw_units = word_split(text)

    # ด่านสุดท้าย: หน่วยไหนยังใหญ่เกิน MAX_TOKENS (เช่นตารางแถวเดียวยักษ์) ซอยตามคำ
    out: list[_Line] = []
    for u in raw_units:
        if _count_tokens(u) > MAX_TOKENS:
            out.extend(_Line(s, page_label, page_index) for s in word_split(u) if s.strip())
        elif u.strip():
            out.append(_Line(u, page_label, page_index))
    return out


def _emit_general(buf: list[_Line], chunks: list[Chunk], doc_name: str, doc_type: str) -> None:
    """ตัดเนื้อหาทั่วไปเป็น chunk ~TARGET_TOKENS ตามขอบย่อหน้า (ซอยก้อนใหญ่ก่อน)"""
    # จัดกลุ่มเป็นย่อหน้าตามบรรทัดว่าง แล้วซอยย่อหน้าที่ใหญ่เกิน
    paras: list[list[_Line]] = []
    cur: list[_Line] = []
    for ln in buf:
        if ln.text.strip() == "":
            if cur:
                paras.append(cur); cur = []
        else:
            cur.append(ln)
    if cur:
        paras.append(cur)

    # ซอยย่อหน้าที่ใหญ่เกิน MAX_TOKENS (ตารางใหญ่/ข้อความยาว) เป็นหลายย่อหน้าเล็ก
    split_paras: list[list[_Line]] = []
    for para in paras:
        ptext = "\n".join(l.text for l in para)
        if _count_tokens(ptext) <= MAX_TOKENS:
            split_paras.append(para)
        else:
            pl, pi = para[0].page_label, para[0].page_index
            for u in _split_big_unit(ptext, pl, pi):
                split_paras.append([u])
    paras = split_paras

    batch: list[_Line] = []
    batch_tokens = 0

    def emit(bl: list[_Line]):
        if not bl:
            return
        text = "\n".join(l.text for l in bl).strip()
        if not text:
            return
        idx = len([c for c in chunks if c.metadata.get("chunk_type") == "general"])
        chunks.append(Chunk(
            id=f"{doc_name}::gen::{idx:04d}",
            text=text,
            metadata={
                "doc_name": doc_name,
                "doc_type": doc_type,
                "section": "",
                "page_label": bl[0].page_label,
                "page_index": bl[0].page_index,
                "chunk_type": "general",
            },
        ))

    for para in paras:
        ptext = "\n".join(l.text for l in para)
        ptok = _count_tokens(ptext)
        if batch_tokens + ptok > MAX_TOKENS and batch:
            emit(batch)
            # overlap: เก็บย่อหน้าท้ายไว้เริ่มก้อนใหม่ ถ้าไม่ใหญ่ไป
            batch = []
            batch_tokens = 0
        batch.extend(para)
        batch.append(_Line("", para[-1].page_label, para[-1].page_index))  # เว้นบรรทัด
        batch_tokens += ptok
        if batch_tokens >= TARGET_TOKENS:
            emit(batch)
            batch = []
            batch_tokens = 0
    emit(batch)


def build_chunks(extract_dir: str | Path, doc_name: str | None = None,
                 doc_type: str = "หลักสูตร") -> list[Chunk]:
    extract_dir = Path(extract_dir)
    doc_name = doc_name or extract_dir.name
    pages = clean_document(extract_dir)
    return chunk_pages(pages, doc_name=doc_name, doc_type=doc_type)


def main() -> int:
    ap = argparse.ArgumentParser(description="ตัด chunk จากหน้าที่ OCR+clean แล้ว")
    ap.add_argument("extract_dir", help="เช่น data/extracted/IT2565")
    ap.add_argument("--doc-type", default="หลักสูตร")
    ap.add_argument("--out", default=None, help="เขียน chunks เป็น JSONL")
    ap.add_argument("--show", type=int, default=5)
    args = ap.parse_args()

    chunks = build_chunks(args.extract_dir, doc_type=args.doc_type)
    course = [c for c in chunks if c.metadata["chunk_type"] == "course"]
    gen = [c for c in chunks if c.metadata["chunk_type"] == "general"]
    print(f"chunks รวม {len(chunks)}  |  รายวิชา {len(course)}  |  ทั่วไป {len(gen)}")

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            for c in chunks:
                f.write(json.dumps(asdict(c), ensure_ascii=False) + "\n")
        print(f"เขียน -> {args.out}")

    print("\n--- ตัวอย่าง course chunks ---")
    for c in course[:args.show]:
        print(f"\n[{c.id}] page_label={c.metadata['page_label']} code={c.metadata['course_code']}")
        print(c.text[:400])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
