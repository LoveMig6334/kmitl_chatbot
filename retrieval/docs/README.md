# RAG Pipeline — Chatbot คณะ IT ลาดกระบัง

ส่วน **RAG + Database** ของ chatbot ตอบคำถามข้อมูลหลักสูตรคณะ IT KMITL จากไฟล์ PDF (มคอ.2)
ดูดข้อมูลจาก PDF → OCR → clean → chunk → (ต่อไป) index → retrieve → API `/query`

รายละเอียดการตัดสินใจ/ข้อควรระวังทั้งหมดอยู่ใน `skill.md` และความคืบหน้าใน `cheklist_1.md`, `checklist_2.md`, `checklist_3.md`

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

