# RAG Pipeline — Chatbot คณะ IT ลาดกระบัง

ส่วน **RAG + Database** ของ chatbot ตอบคำถามข้อมูลหลักสูตรคณะ IT KMITL จากไฟล์ PDF (มคอ.2)
ดูดข้อมูลจาก PDF → OCR → clean → chunk → (ต่อไป) index → retrieve → API `/query`

รายละเอียดการตัดสินใจ/ข้อควรระวังทั้งหมดอยู่ใน `skill.md` และความคืบหน้าใน `cheklist_1.md`, `checklist_2.md`, `checklist_3.md`

---

## สถานะปัจจุบัน

| ขั้น | สถานะ |
|---|---|
| Inspect PDF (page-type + PUA) | ✅ เสร็จ |
| **OCR (Typhoon API)** | ✅ **ปิดจ็อบแล้ว** — 4 ไฟล์ 1,034 หน้า |
| Clean + Chunk | ✅ เสร็จ — **2,358 chunks** (`data/chunks/all.jsonl`) |
| Index (BGE-M3→Chroma + BM25) | ✅ เสร็จ (`data/chroma/`, `data/bm25.pkl`) |
| Retrieval (hybrid RRF + code boost) | ✅ เสร็จ (`rag/retrieve.py`) |
| **API `/search`** (ส่งมอบทีม) | ✅ เสร็จ (`rag/api.py` — ดู **`HANDOFF.md`**) |
| LLM (ทีมอื่นทำ) / Evaluation | ⬜ ยังไม่ทำ |

> หมายเหตุ: IT_inter2565 หน้า 104 (ตารางเมทริกซ์ Curriculum Mapping) OCR sub-text แนวตั้งไม่ได้ 100% — ใส่ marker `OCR_PARTIAL` ไว้ (ดูหัวข้อ "กลับมาแก้ OCR")

---

## Setup

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt      # Windows
cp .env.example .env                                # แล้วใส่ TYPHOON_API_KEY จริง
```

`.env` เก็บ key + เลือก OCR engine (API หรือโลคัล Ollama) — อยู่ใน `.gitignore` **ห้าม commit**

---

## โครงสร้างโปรเจกต์

```
Data/                         PDF ต้นทาง 4 ไฟล์
rag/
  ingest_ocr.py               OCR ทุกหน้า (Typhoon API/โลคัล) → cache .md ต่อหน้า
  clean.py                    ตัด header/footer/artifact + normalize ไทย
  chunk.py                    ตัด chunk structure-aware (1 วิชา = 1 chunk)
scripts/
  inspect_pdf.py              ตรวจ page-type + PUA ก่อน ingest
  build_chunks_all.py         chunk ทุกไฟล์ → data/chunks/*.jsonl + all.jsonl
  qa_corpus.py                ตรวจคุณภาพ OCR corpus + chunks
data/
  extracted/{doc}/{page}.md   ผล OCR ต่อหน้า (cache, resume ได้)
  chunks/{doc}.jsonl          chunk แยกไฟล์
  chunks/all.jsonl            chunk รวมทุกไฟล์ ← input ของขั้น Index
  inspect_report.json         ผลตรวจ PDF 4 ไฟล์
```

---

## รัน pipeline (offline ครั้งเดียว)

```bash
# 1) ตรวจ PDF (ทำครั้งเดียว)
python scripts/inspect_pdf.py "Data/*.pdf" --json data/inspect_report.json

# 2) OCR (ทั้งไฟล์ / เจาะหน้า / ทดสอบ)
python rag/ingest_ocr.py Data/IT2565.pdf                # ทั้งไฟล์ (resume จาก cache)
python rag/ingest_ocr.py Data/IT2565.pdf --pages 76-80  # เจาะช่วงหน้า
python rag/ingest_ocr.py Data/IT2565.pdf --limit 3      # ทดสอบ 3 หน้าแรก

# 3) chunk ทุกไฟล์ + รวม all.jsonl
python scripts/build_chunks_all.py

# 4) ตรวจคุณภาพ
python scripts/qa_corpus.py data/extracted/IT2565

# 5) สร้าง index (BGE-M3 → Chroma + BM25)  [ต้องมี GPU/CPU + โมเดล]
python rag/index.py --reset

# 6) ค้นแบบ hybrid (ทดสอบ)
python rag/retrieve.py "06016429 คือวิชาอะไร" --k 5
```

---

## 🔧 กลับมาแก้ OCR ภายหลัง (สำคัญ)

OCR cache เป็นไฟล์ `.md` **ต่อหน้า** แยกกัน → แก้เฉพาะจุดได้ ไม่ต้องรื้อทั้งระบบ

### ขั้นตอน

```bash
# หา page ที่ยังไม่สมบูรณ์ (มี marker)
grep -rl "OCR_PARTIAL\|OCR_SKIPPED" data/extracted/

# แก้ OCR page นั้น — เลือกวิธีใดวิธีหนึ่ง:
#   (ก) แก้มือ: เปิด data/extracted/{doc}/{page}.md แล้วพิมพ์แก้ตรงๆ
#   (ข) OCR ใหม่: (--force = เขียนทับ cache เดิม)
python rag/ingest_ocr.py Data/IT_inter2565.pdf --pages 104 --force

# rebuild chunk ให้สะท้อนการแก้ (ไม่กี่วินาที)
python scripts/build_chunks_all.py
#   ...ถ้ามี Index แล้ว: rebuild index จาก data/chunks/all.jsonl ต่อ
```

### กระทบส่วนอื่นแค่ไหน?

Pipeline เป็นสายโซ่ทางเดียว: **OCR (.md) → chunk → Index → API**
แก้ OCR 1 หน้า → รัน downstream ใหม่**เฉพาะที่ต่อจากมัน**เท่านั้น

- ✅ **ไม่กระทบ**อีก 3 ไฟล์ (แต่ละไฟล์ chunk แยกกัน)
- ✅ **ไม่ต้องแก้โค้ด** stage ไหน (clean/chunk/index เป็น deterministic rerun ได้)
- ✅ **ไม่กระทบงานเพื่อน** (UI/LLM ต่อกับ API `/query` + index ที่ rebuild ให้ — ไม่เห็น OCR)
- ⚠️ ต้องจำแค่: แก้ .md แล้ว **รัน `build_chunks_all.py` ใหม่** (+ rebuild index ถ้ามีแล้ว)

> ตอนนี้ยังไม่มี Index → แก้ OCR = แค่ re-chunk อย่างเดียว จบ (จังหวะที่แก้ง่ายสุด)

### สลับ OCR engine (แก้ที่ `.env` ไม่ต้องแตะโค้ด)

```ini
# ใช้ Typhoon API (ค่าปัจจุบัน — เร็ว, แม่น)
OCR_BASE_URL=https://api.opentyphoon.ai/v1
OCR_MODEL=typhoon-ocr
OCR_API_KEY=sk-...s

# หรือใช้โลคัล Ollama (ฟรี ไม่ต้อง key — ต้อง ollama pull scb10x/typhoon-ocr1.5-3b ก่อน)
# OCR_BASE_URL=http://localhost:11434/v1
# OCR_MODEL=scb10x/typhoon-ocr1.5-3b
# OCR_API_KEY=ollama
```

---

## ขั้นถัดไป (ยังไม่ทำ)

Index (BGE-M3 → Chroma + BM25) → Retrieval (hybrid RRF) → FastAPI `/query` → Evaluation
