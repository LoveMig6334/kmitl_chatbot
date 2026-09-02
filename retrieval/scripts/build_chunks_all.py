"""
build_chunks_all.py — chunk ทุกไฟล์ใน data/extracted/ → data/chunks/{doc}.jsonl
+ รวมเป็น data/chunks/all.jsonl (พร้อมเข้า index ขั้นถัดไป)

ใช้:  python scripts/build_chunks_all.py
      python scripts/build_chunks_all.py --docs IT2565 AIT DSBA IT_inter2565
"""
from __future__ import annotations

import argparse
import json
import sys
import statistics
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rag.chunk import build_chunks

# ทุกไฟล์เป็นหลักสูตรคณะ IT
DOC_TYPE = "หลักสูตร"
EXTRACT_ROOT = Path("data/extracted")
CHUNK_ROOT = Path("data/chunks")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs", nargs="*", default=None,
                    help="ชื่อ doc (ชื่อโฟลเดอร์ใน data/extracted); ไม่ระบุ = ทุกไฟล์")
    args = ap.parse_args()

    CHUNK_ROOT.mkdir(parents=True, exist_ok=True)
    dirs = ([EXTRACT_ROOT / d for d in args.docs] if args.docs
            else sorted(p for p in EXTRACT_ROOT.iterdir() if p.is_dir()))

    combined: list[dict] = []
    print(f"{'doc':<16} {'หน้า':>5} {'chunks':>7} {'course':>7} {'gen':>5} {'course med':>11} {'gen med':>9}")
    print("-" * 70)
    for d in dirs:
        n_pages = len(list(d.glob("*.md")))
        if n_pages == 0:
            print(f"{d.name:<16} (ไม่มี .md — ข้าม)")
            continue
        chunks = build_chunks(d, doc_type=DOC_TYPE)
        course = [c for c in chunks if c.metadata["chunk_type"] == "course"]
        gen = [c for c in chunks if c.metadata["chunk_type"] == "general"]
        cmed = int(statistics.median([len(c.text) for c in course])) if course else 0
        gmed = int(statistics.median([len(c.text) for c in gen])) if gen else 0

        out = CHUNK_ROOT / f"{d.name}.jsonl"
        rows = [{"id": c.id, "text": c.text, "metadata": c.metadata} for c in chunks]
        with out.open("w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        combined.extend(rows)
        print(f"{d.name:<16} {n_pages:>5} {len(chunks):>7} {len(course):>7} {len(gen):>5} {cmed:>11} {gmed:>9}")

    # รวมทุกไฟล์
    all_out = CHUNK_ROOT / "all.jsonl"
    with all_out.open("w", encoding="utf-8") as f:
        for r in combined:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("-" * 70)
    print(f"รวมทั้งหมด {len(combined)} chunks -> {all_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
