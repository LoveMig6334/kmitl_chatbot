"""
ingest_ocr.py — OCR ทุกหน้าของ PDF ด้วย Typhoon OCR (รันโลคัลผ่าน Ollama)

กลยุทธ์ (ตัดสินใจแล้ว): OCR ทุกหน้าทุกไฟล์ เพราะ text layer พังเกือบ 100% ทุกไฟล์
(ดู data/inspect_report.json). เลี่ยงกับดัก PUA วรรณยุกต์ผีทั้งหมดด้วยการ OCR ภาพ.

จุดสำคัญ:
- render หน้าเป็น PNG ด้วย PyMuPDF เอง (ไม่พึ่ง poppler/pdftoppm ที่ Windows ไม่มี)
- ส่ง PNG เข้า typhoon_ocr.ocr_document(task_type="v1.5") ซึ่งจะ:
    * ใช้ prompt v1.5 เฉพาะของโมเดล (โมเดลนี้ "ใช้ prompt อื่นไม่ได้")
    * ไม่ต้องใช้ anchor text
    * ตั้ง temperature=0.1, top_p=0.6, repetition_penalty=1.1 ให้อัตโนมัติ
- cache ผลเป็น .md ต่อหน้า (data/extracted/{doc}/{page:03d}.md) -> resume ได้ ไม่ OCR ซ้ำ

รันโมเดลผ่าน Ollama:
    ollama pull scb10x/typhoon-ocr1.5-3b
    ollama serve            # (Ollama app เปิด service ให้อยู่แล้ว)

ใช้:
    python rag/ingest_ocr.py Data/IT2565.pdf                 # ทั้งไฟล์ (resume)
    python rag/ingest_ocr.py Data/IT2565.pdf --limit 3       # ทดสอบ 3 หน้าแรก
    python rag/ingest_ocr.py Data/IT2565.pdf --pages 76-80   # เจาะช่วงหน้า
    python rag/ingest_ocr.py Data/IT2565.pdf --force         # OCR ใหม่ทับ cache
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
import time
from pathlib import Path

# stdout UTF-8 (Windows console default cp1252)
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

import pymupdf
from openai import OpenAI
from typhoon_ocr.ocr_utils import prepare_ocr_messages

# โหลด .env (key/endpoint) ถ้ามี — ปลอดภัยกว่า hardcode
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# ---- config (override ได้ด้วย env) ----
OCR_BASE_URL = os.getenv("OCR_BASE_URL", "http://localhost:11434/v1")
OCR_MODEL = os.getenv("OCR_MODEL", "scb10x/typhoon-ocr1.5-3b")
OCR_API_KEY = os.getenv("OCR_API_KEY", "ollama")  # Ollama ไม่ตรวจ key
FIGURE_LANG = os.getenv("OCR_FIGURE_LANG", "Thai")
# temperature=0 (พิสูจน์แล้วว่าแม่นรหัสวิชากว่า + hallucination ก้อนใหญ่หาย เทียบ 0.1 ที่ package ตั้ง)
OCR_TEMP = float(os.getenv("OCR_TEMP", "0.0"))
TARGET_IMAGE_DIM = int(os.getenv("OCR_IMAGE_DIM", "1800"))  # v1.5 resize ด้านยาวเหลือเท่านี้

_client = OpenAI(base_url=OCR_BASE_URL, api_key=OCR_API_KEY)

# render หน้าให้ด้านยาวสุด ~2000px แล้วปล่อยให้ v1.5 resize เหลือ 1800 (คมกว่าการ render เล็ก)
RENDER_LONGEST_PX = int(os.getenv("OCR_RENDER_PX", "2000"))
EXTRACT_ROOT = Path(os.getenv("OCR_OUT", "data/extracted"))

MAX_RETRY = 3


def render_page_png(page: pymupdf.Page, out_path: str, longest_px: int = RENDER_LONGEST_PX) -> None:
    """render หน้า PDF เป็น PNG ให้ด้านยาวสุด = longest_px"""
    rect = page.rect
    longest_pt = max(rect.width, rect.height) or 1.0
    zoom = longest_px / longest_pt
    mat = pymupdf.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    pix.save(out_path)


def ocr_one_page(png_path: str) -> str:
    """เรียก Typhoon OCR v1.5 กับ PNG หนึ่งหน้า มี retry

    เรียก endpoint ตรงๆ (ไม่ผ่าน ocr_document) เพื่อบังคับ temperature=0
    — ocr_document ของ package hardcode temp=0.1 ซึ่งพบว่าทำรหัสวิชาผิดและ
    hallucinate มากกว่า. reuse prepare_ocr_messages เพื่อคง prompt v1.5 + resize เป๊ะ.
    """
    messages = prepare_ocr_messages(
        pdf_or_image_path=png_path,
        task_type="v1.5",
        target_image_dim=TARGET_IMAGE_DIM,
        figure_language=FIGURE_LANG,
    )
    last_err = None
    for attempt in range(1, MAX_RETRY + 1):
        try:
            resp = _client.chat.completions.create(
                model=OCR_MODEL,
                messages=messages,
                max_tokens=16384,
                extra_body={
                    "repetition_penalty": 1.1,
                    "temperature": OCR_TEMP,
                    "top_p": 0.6,
                },
            )
            return resp.choices[0].message.content or ""
        except Exception as e:  # network/model hiccup
            last_err = e
            wait = 2 * attempt
            print(f"      [retry {attempt}/{MAX_RETRY}] {type(e).__name__}: {e} -> รอ {wait}s", flush=True)
            time.sleep(wait)
    raise RuntimeError(f"OCR ล้มเหลวหลัง {MAX_RETRY} ครั้ง: {last_err}")


def parse_pages(spec: str | None, n: int) -> list[int]:
    """แปลง '76-80,90' เป็น list ของ index 0-based; None = ทุกหน้า"""
    if not spec:
        return list(range(n))
    out: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-")
            for p in range(int(a), int(b) + 1):
                out.add(p - 1)  # หน้าที่พิมพ์ 1-based -> index
        else:
            out.add(int(part) - 1)
    return sorted(p for p in out if 0 <= p < n)


def ingest_pdf(pdf_path: str, pages: str | None = None, limit: int | None = None,
               force: bool = False) -> dict:
    doc = pymupdf.open(pdf_path)
    doc_name = Path(pdf_path).stem
    out_dir = EXTRACT_ROOT / doc_name
    out_dir.mkdir(parents=True, exist_ok=True)

    idxs = parse_pages(pages, doc.page_count)
    if limit is not None:
        idxs = idxs[:limit]

    print(f"\n=== OCR: {pdf_path} ({doc.page_count} หน้า) ===")
    print(f"    โมเดล : {OCR_MODEL} @ {OCR_BASE_URL}")
    print(f"    output: {out_dir}  |  จะทำ {len(idxs)} หน้า  |  force={force}")

    done = skipped = failed = 0
    t0 = time.time()
    with tempfile.TemporaryDirectory() as td:
        for k, i in enumerate(idxs, 1):
            md_path = out_dir / f"{i + 1:03d}.md"
            if md_path.exists() and md_path.stat().st_size > 0 and not force:
                skipped += 1
                continue
            png = os.path.join(td, f"p{i + 1}.png")
            tp = time.time()
            try:
                render_page_png(doc[i], png)
                md = ocr_one_page(png)
            except Exception as e:
                failed += 1
                print(f"  [{k}/{len(idxs)}] หน้า {i + 1:>3}  ✗ {e}", flush=True)
                continue
            md_path.write_text(md.strip() + "\n", encoding="utf-8")
            done += 1
            dt = time.time() - tp
            preview = md.strip().replace("\n", " ")[:60]
            print(f"  [{k}/{len(idxs)}] หน้า {i + 1:>3}  ✓ {dt:5.1f}s  {len(md):>5} ตัวอักษร  | {preview}", flush=True)

    doc.close()
    dt = time.time() - t0
    print(f"--- เสร็จ: OCR ใหม่ {done}, ข้าม(cache) {skipped}, ล้มเหลว {failed}  ใช้เวลา {dt:.0f}s ---")
    return {"doc": doc_name, "done": done, "skipped": skipped, "failed": failed}


def main() -> int:
    ap = argparse.ArgumentParser(description="OCR ทุกหน้าของ PDF ด้วย Typhoon OCR (Ollama)")
    ap.add_argument("pdf", help="พาธ PDF")
    ap.add_argument("--pages", default=None, help="ช่วงหน้าที่พิมพ์ 1-based เช่น '76-80,90'")
    ap.add_argument("--limit", type=int, default=None, help="ทำแค่ N หน้าแรก (ทดสอบ)")
    ap.add_argument("--force", action="store_true", help="OCR ทับ cache เดิม")
    args = ap.parse_args()

    if not Path(args.pdf).exists():
        print(f"ไม่พบไฟล์: {args.pdf}", file=sys.stderr)
        return 1

    ingest_pdf(args.pdf, pages=args.pages, limit=args.limit, force=args.force)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
