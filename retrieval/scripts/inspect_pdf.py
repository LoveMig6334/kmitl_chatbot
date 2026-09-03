"""
inspect_pdf.py — ตรวจ "กับดัก" ของ PDF ต้นทางก่อน ingest (ตาม skill.md)

ตรวจ 2 อย่างต่อหน้า:
  1) ชนิดหน้า: "หน้าภาพ" (มีภาพใหญ่ >800x1200 px หรือ extract text < 100 ตัวอักษร)
     vs "หน้า text"
  2) จำนวนอักขระ PUA วรรณยุกต์ผี ช่วง U+F700–U+F71A ใน text layer

ใช้:
    python scripts/inspect_pdf.py Data/*.pdf
    python scripts/inspect_pdf.py Data/IT2565.pdf --sample 76
"""
from __future__ import annotations

import argparse
import glob
import sys
from collections import Counter

# บังคับ stdout เป็น UTF-8 (Windows console default cp1252 พิมพ์ไทยไม่ได้)
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

import pymupdf as fitz  # PyMuPDF (ชื่อ import ใหม่)

# ช่วง PUA ทั้งหมด (Unicode Private Use Area) — ฟอนต์ THSarabunPSK map
# วรรณยุกต์/สระไทยไป PUA แต่ "คนละช่วงตามการ subset ฟอนต์ของแต่ละเอกสาร":
#   IT2565 -> F052..F713 ; AIT/DSBA/IT_inter -> E005..E095
# จึงต้องนับทั้งช่วง ไม่ใช่แค่ F700-F71A (bug เดิม รายงานไฟล์ E0xx เป็น 0)
PUA_LO = 0xE000
PUA_HI = 0xF8FF

# ช่วงวรรณยุกต์/สระบน-ล่าง "ปกติ" (นอก PUA) — ใช้เช็คสุขภาพ text layer
def _is_thai_mark(cp: int) -> bool:
    return cp == 0x0E31 or 0x0E34 <= cp <= 0x0E3A or 0x0E47 <= cp <= 0x0E4E

def _is_thai_cons(cp: int) -> bool:
    return 0x0E01 <= cp <= 0x0E2E

# เกณฑ์ตัดสิน "หน้าภาพ"
IMG_MIN_W = 800
IMG_MIN_H = 1200
TEXT_MIN_CHARS = 100

# ratio วรรณยุกต์-สระ/พยัญชนะ ต่ำกว่านี้บนหน้า text = text layer พัง (มาร์กหาย/เป็น PUA)
# ภาษาไทยปกติอยู่ราว 0.15-0.35
MARK_RATIO_MIN = 0.10


def count_pua(text: str) -> Counter:
    """นับอักขระ PUA ทั้งช่วง E000-F8FF คืน Counter{codepoint: จำนวน}"""
    c = Counter()
    for ch in text:
        cp = ord(ch)
        if PUA_LO <= cp <= PUA_HI:
            c[cp] += 1
    return c


def mark_ratio(text: str) -> tuple[float, int, int]:
    """คืน (ratio, จำนวนมาร์กปกติ, จำนวนพยัญชนะ) ของหน้า"""
    marks = sum(1 for ch in text if _is_thai_mark(ord(ch)))
    cons = sum(1 for ch in text if _is_thai_cons(ord(ch)))
    return (marks / cons if cons else 0.0), marks, cons


def has_large_image(page: fitz.Page) -> tuple[bool, int, int]:
    """หน้ามีภาพใหญ่เกินเกณฑ์ไหม คืน (มี?, w, h) ของภาพที่ใหญ่สุด"""
    max_w = max_h = 0
    for img in page.get_images(full=True):
        xref = img[0]
        try:
            info = page.parent.extract_image(xref)
        except Exception:
            # fallback: ใช้ w,h จาก image list (index 2,3)
            w, h = img[2], img[3]
        else:
            w, h = info.get("width", 0), info.get("height", 0)
        if w * h > max_w * max_h:
            max_w, max_h = w, h
    is_large = max_w >= IMG_MIN_W and max_h >= IMG_MIN_H
    return is_large, max_w, max_h


def inspect(path: str, sample_page: int | None = None) -> dict:
    doc = fitz.open(path)
    n = doc.page_count

    image_pages = []
    text_pages = []
    broken_text_pages = []   # หน้า text ที่ layer พัง (PUA หรือ mark ratio ต่ำ) -> ต้อง OCR ด้วย
    total_pua = Counter()
    pages_with_pua = 0

    for i in range(n):
        page = doc[i]
        text = page.get_text("text")
        nchar = len(text.strip())
        big_img, iw, ih = has_large_image(page)

        is_image_page = big_img or nchar < TEXT_MIN_CHARS
        if is_image_page:
            image_pages.append(i)
        else:
            text_pages.append(i)
            # ประเมินสุขภาพ text layer ของหน้า text
            pua_here = count_pua(text)
            ratio, marks, cons = mark_ratio(text)
            if pua_here or (cons > 50 and ratio < MARK_RATIO_MIN):
                broken_text_pages.append(i)

        pua = count_pua(text)
        if pua:
            pages_with_pua += 1
            total_pua.update(pua)

    pua_cps = sorted(total_pua)
    result = {
        "path": path,
        "pages": n,
        "image_pages": image_pages,
        "text_pages": text_pages,
        "broken_text_pages": broken_text_pages,
        "n_image_pages": len(image_pages),
        "n_text_pages": len(text_pages),
        "n_broken_text_pages": len(broken_text_pages),
        "pages_with_pua": pages_with_pua,
        "total_pua": sum(total_pua.values()),
        "pua_range": (hex(pua_cps[0]), hex(pua_cps[-1])) if pua_cps else None,
        "pua_breakdown": dict(sorted(total_pua.items())),
    }

    if sample_page is not None and 0 <= sample_page < n:
        result["sample"] = doc[sample_page].get_text("text")

    doc.close()
    return result


def print_report(r: dict) -> None:
    n = r["pages"]
    ni, nt = r["n_image_pages"], r["n_text_pages"]
    pct_img = 100 * ni / n if n else 0
    print(f"\n{'='*70}")
    print(f"ไฟล์: {r['path']}")
    print(f"{'='*70}")
    nb = r["n_broken_text_pages"]
    clean_text = nt - nb
    print(f"  หน้าทั้งหมด            : {n}")
    print(f"  หน้าภาพ (ต้อง OCR)     : {ni}  ({pct_img:.0f}%)")
    print(f"  หน้า text              : {nt}  ({100-pct_img:.0f}%)")
    print(f"    ↳ text layer พัง (PUA/มาร์กหาย → ต้อง OCR/remap) : {nb}")
    print(f"    ↳ text layer สะอาดใช้ได้เลย                       : {clean_text}")
    ocr_needed = ni + nb
    print(f"  รวมหน้าที่ต้องกู้ (OCR/remap): {ocr_needed}  ({100*ocr_needed/n:.0f}% ของเล่ม)")
    print(f"  หน้าที่มี PUA ผี       : {r['pages_with_pua']}")
    print(f"  อักขระ PUA รวม         : {r['total_pua']}  ช่วง={r['pua_range']}")
    if r["pua_breakdown"]:
        top = sorted(r["pua_breakdown"].items(), key=lambda kv: -kv[1])[:8]
        detail = ", ".join(f"U+{cp:04X}×{c}" for cp, c in top)
        print(f"  PUA เด่น               : {detail}")
    # แสดงช่วงหน้าภาพแบบย่อ
    if r["image_pages"]:
        print(f"  index หน้าภาพ (0-based): {_compact_ranges(r['image_pages'])}")
    if "sample" in r:
        print(f"\n  --- ตัวอย่าง text หน้าที่ขอ ---")
        print("  " + r["sample"].replace("\n", "\n  ")[:1500])


def _compact_ranges(nums: list[int]) -> str:
    """[1,2,3,7,8] -> '1-3, 7-8'"""
    if not nums:
        return "-"
    parts = []
    start = prev = nums[0]
    for x in nums[1:]:
        if x == prev + 1:
            prev = x
        else:
            parts.append(f"{start}-{prev}" if start != prev else f"{start}")
            start = prev = x
    parts.append(f"{start}-{prev}" if start != prev else f"{start}")
    return ", ".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser(description="ตรวจกับดัก PDF ก่อน ingest")
    ap.add_argument("paths", nargs="+", help="พาธ PDF (รับ glob ได้)")
    ap.add_argument("--sample", type=int, default=None,
                    help="พิมพ์ text ของหน้า index นี้ (0-based) ไฟล์แรก")
    ap.add_argument("--json", type=str, default=None,
                    help="เขียนผลตรวจทั้งหมดเป็นไฟล์ JSON (ให้ pipeline ใช้ต่อ)")
    args = ap.parse_args()

    # ขยาย glob เอง (Windows shell ไม่ขยายให้)
    files: list[str] = []
    for p in args.paths:
        matched = glob.glob(p)
        files.extend(matched if matched else [p])

    if not files:
        print("ไม่พบไฟล์", file=sys.stderr)
        return 1

    all_results = []
    for idx, f in enumerate(files):
        try:
            r = inspect(f, sample_page=args.sample if idx == 0 else None)
        except Exception as e:
            print(f"\n[ERROR] {f}: {e}", file=sys.stderr)
            continue
        print_report(r)
        all_results.append(r)

    if args.json:
        import json
        # ไม่เก็บ sample text ก้อนใหญ่ลง JSON
        slim = [{k: v for k, v in r.items() if k != "sample"} for r in all_results]
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(slim, fh, ensure_ascii=False, indent=2)
        print(f"\n[JSON] เขียนผลตรวจ -> {args.json}")

    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
