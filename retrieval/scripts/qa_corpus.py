"""
qa_corpus.py — ตรวจคุณภาพ OCR corpus + chunks (รันหลัง OCR เสร็จ)

เช็ค:
- หน้าที่ output สั้นผิดปกติ (< 50 ตัวอักษร) = อาจ OCR หลุด
- หน้าที่มี hallucination pattern ตกค้าง (+++...+++, ชื่อคนแปลกๆ)
- coverage: กี่หน้ามี page_label, กี่หน้าไม่มี
- รหัสวิชา: จำนวนรหัสไม่ซ้ำ, รหัส 7 หลัก (อาจพลาด)
- chunks: จำนวน course/general, course chunk ที่ครบองค์ (มีคำอธิบาย)

ใช้:  python scripts/qa_corpus.py data/extracted/IT2565
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rag.clean import clean_document
from rag.chunk import build_chunks

HALL_PATTERNS = [r"\+{3,}[^\n]*\+{3,}"]  # +++...+++ เท่านั้น (ไม่จับ C++)
SHORT_LEN = 50


def qa(extract_dir: str) -> None:
    extract_dir = Path(extract_dir)
    md_files = sorted(extract_dir.glob("*.md"), key=lambda p: int(p.stem))
    print(f"=== QA corpus: {extract_dir}  ({len(md_files)} หน้า) ===\n")

    short_pages, hall_pages = [], []
    all_codes: Counter[str] = Counter()
    seven_digit: list[tuple[int, str]] = []

    for f in md_files:
        pg = int(f.stem)
        raw = f.read_text(encoding="utf-8")
        body = raw.strip()
        if len(body) < SHORT_LEN:
            short_pages.append((pg, len(body)))
        for pat in HALL_PATTERNS:
            if re.search(pat, raw):
                hall_pages.append((pg, pat))
                break
        for c in re.findall(r"(?<!\d)\d{8}(?!\d)", raw):
            all_codes[c] += 1
        for c in re.findall(r"(?<!\d)\d{7}(?!\d)", raw):
            seven_digit.append((pg, c))

    print(f"[1] หน้า output สั้นผิดปกติ (<{SHORT_LEN} ตัวอักษร): {len(short_pages)}")
    for pg, n in short_pages[:20]:
        print(f"      หน้า {pg}: {n} ตัวอักษร")
    print(f"\n[2] หน้าที่มี hallucination pattern ตกค้าง: {len(hall_pages)}")
    for pg, pat in hall_pages[:20]:
        print(f"      หน้า {pg}: {pat}")
    print(f"\n[3] รหัสวิชา 8 หลัก: ไม่ซ้ำ {len(all_codes)} รหัส (รวม {sum(all_codes.values())} ครั้ง)")
    print(f"      รหัส 7 หลัก (อาจ OCR พลาดเลขหาย): {len(seven_digit)}")
    for pg, c in seven_digit[:15]:
        print(f"      หน้า {pg}: {c}")

    # ----- clean + chunk -----
    print("\n=== หลัง clean + chunk ===")
    pages = clean_document(extract_dir)
    with_label = sum(1 for p in pages if p.page_label)
    print(f"[4] page_label coverage: {with_label}/{len(pages)} หน้า มีเลขหน้า "
          f"({100*with_label/len(pages):.0f}%)")

    chunks = build_chunks(extract_dir)
    course = [c for c in chunks if c.metadata["chunk_type"] == "course"]
    gen = [c for c in chunks if c.metadata["chunk_type"] == "general"]
    # course ที่ครบองค์ = มีคำอธิบาย (ยาวพอ + มี PREREQUISITE หรือ ย่อหน้าไทยยาว)
    full = [c for c in course if len(c.text) > 200 and
            ("PREREQUISITE" in c.text or "รายวิชาบังคับก่อน" in c.text)]
    uniq_course = {c.metadata["course_code"] for c in course}
    print(f"[5] chunks: รวม {len(chunks)} | รายวิชา {len(course)} (ไม่ซ้ำ {len(uniq_course)} รหัส) | ทั่วไป {len(gen)}")
    print(f"      course chunk ครบองค์ (มีคำอธิบาย+วิชาบังคับก่อน): {len(full)}")
    codes_in_chunks = {c.metadata["course_code"] for c in course}
    codes_in_raw = set(all_codes)
    missed = codes_in_raw - codes_in_chunks
    print(f"      รหัสใน corpus ที่ไม่ได้ขึ้นต้น chunk (อยู่ในตาราง/บรรทัดเดียว): {len(missed)}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("extract_dir")
    args = ap.parse_args()
    qa(args.extract_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
