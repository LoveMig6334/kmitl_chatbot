# Checklist 1 — RAG Pipeline (ถึงขั้น Chunking)

อัปเดต: 2026-09-01 | ขอบเขตรอบนี้: **ทำถึงขั้น chunking**, นำร่องไฟล์ **IT2565.pdf**

---

## สรุปสั้น

ตรวจ PDF ทั้ง 4 ไฟล์ → เลือกกลยุทธ์ **OCR ทั้งหมด** → ตั้ง Typhoon OCR รันโลคัลบน Ollama →
เขียน + ทดสอบ pipeline ถึง **ingest (OCR) → clean → chunk** ครบ กับ IT2565
ตอนนี้กำลัง OCR IT2565 เต็มเล่มอยู่เบื้องหลัง (จะ chunk เต็มเมื่อ OCR ครบ)

---

## ✅ ทำเสร็จแล้ว

### 1. ตรวจไฟล์ต้นทาง (inspection)
- [x] `scripts/inspect_pdf.py` — ตรวจชนิดหน้า (ภาพ/text), นับ PUA ทุกช่วง, สุขภาพ text layer
- [x] รันกับทั้ง 4 ไฟล์ → `data/inspect_report.json`
- [x] **ค้นพบสำคัญ:** ทุกไฟล์มี PUA วรรณยุกต์ผี (ไม่ใช่แค่ IT2565) แต่คนละช่วง — remap ตายตัวข้ามไฟล์ไม่ได้; ทุกไฟล์ต้องกู้ ~100%

| ไฟล์ | หน้า | %หน้าภาพ | ช่วง PUA |
|---|---|---|---|
| IT2565 | 294 | 59% | F052–F713 |
| AIT | 253 | 71% | E005–E076 |
| DSBA | 281 | 63% | E006–E08A |
| IT_inter2565 | 206 | 53% | E005–E095 |

- [x] อัปเดต `skill.md` (ส่วน ⚠️) + บันทึก memory ให้ตรงความจริง

### 2. เลือก + ติดตั้ง OCR engine
- [x] ตัดสินใจกลยุทธ์ (ยืนยันกับผู้ใช้): **OCR ทั้งหมด, นำร่อง IT2565**
- [x] เครื่องนี้ GPU 8GB → เริ่มด้วย **Typhoon OCR 1.5-3b** (Q4) รันโลคัลผ่าน Ollama
- [x] ติดตั้ง Ollama + pull โมเดล + `pip install typhoon-ocr pymupdf pythainlp python-dotenv`
- [x] **ปรับสำคัญ:** ใช้ `temperature=0` (package ตั้ง 0.1) — แม่นรหัสวิชากว่า + ลด hallucination
- [x] **A/B test แล้วสลับมา Typhoon API `typhoon-ocr` (v1.5) เป็นหลัก** — API สะอาดกว่า (ไม่ hallucinate ชื่อปลอมแบบ local 3b), รักษาตาราง, เร็ว 4-8s/หน้า, ฟรี. โลคัลเป็น fallback
- [x] เก็บ key ใน `.env` (gitignore) + ทำ `.env.example` ให้ทีม; โหลดด้วย python-dotenv

### 3. Ingestion (OCR) — `rag/ingest_ocr.py`
- [x] render หน้า PDF → PNG ด้วย PyMuPDF (เลี่ยง poppler ที่ Windows ไม่มี)
- [x] ส่งเข้า Typhoon OCR v1.5 (prompt/param เฉพาะของโมเดล) ผ่าน Ollama
- [x] cache ผลเป็น `.md` ต่อหน้า → resume ได้ (`data/extracted/{doc}/{page:03d}.md`)
- [x] อ่าน config จาก `.env` (สลับ API/โลคัลได้โดยไม่แก้โค้ด)
- [x] ทดสอบเทียบภาพจริง: ข้อความไทยถูก 100%, ตารางรหัสวิชารอด, ได้ page_label
- [~] **กำลังรัน OCR IT2565 เต็มเล่มด้วย API** (294 หน้า, ~2-4s/หน้า, ~20-30 นาที)

### 4. Cleaning — `rag/clean.py`
- [x] ดึง `page_label` จากแท็ก `<page_number>`
- [x] ตัด header/footer ซ้ำ แบบ **corpus-level อัตโนมัติ** (ไม่ hardcode) — ใช้ได้ทุกไฟล์
- [x] ตัด hallucination artifact (`+++...+++`, `*NN*`), แท็ก, เลขหน้าโดดๆ, "มคอ.2"
- [x] normalize: NFC + `pythainlp.util.normalize` (คงรหัสวิชา/อังกฤษเป๊ะ)
- [x] ทดสอบผ่านกับหน้าจริง

### 5. Chunking — `rag/chunk.py`
- [x] **1 รายวิชา = 1 chunk** สมบูรณ์ (รหัส+ชื่อไทย+อังกฤษ+หน่วยกิต+วิชาบังคับก่อน+คำอธิบาย)
- [x] ทำบนสตรีมต่อหน้า (คำอธิบายข้ามหน้าได้), track page_label ต่อ chunk
- [x] ตัดขอบ structural (หัวข้อกลุ่ม/table header/หมายเหตุ) กัน pollution บนหน้าโครงสร้างหลักสูตร
- [x] เนื้อหาทั่วไป → ตัดตามย่อหน้า ~400 token ด้วย newmm
- [x] metadata ครบ: `{doc_name, doc_type, section, page_label, page_index, course_code?, chunk_type}`
- [x] ทดสอบผ่าน: หน้าคำอธิบายรายวิชาได้ chunk สมบูรณ์, หน้า list สะอาด

---

## ⬜ ยังไม่ได้ทำ (รอบถัดไป)

### ใกล้ตัว (ปิดขั้น chunking ให้สมบูรณ์)
- [ ] รอ OCR IT2565 ครบ 294 หน้า แล้ว **รัน chunk เต็มเล่ม** → เขียน `data/chunks/IT2565.jsonl`
- [ ] ตรวจ QA รอบสุดท้าย: สุ่มหน้าเทียบภาพ, เช็ครหัสวิชาครบ, หา hallucination ตกค้าง
- [ ] (เล็ก) ปรับให้หน่วยกิต `N(N-N-N)` อยู่ต้น chunk แทนท้าย

### ขั้นถัดไปของ pipeline (ตาม skill.md — **ยังไม่แตะตามที่ผู้ใช้สั่ง**)
- [ ] **Index** — embed BGE-M3 → Chroma (persistent) + สร้าง BM25 index คู่ขนาน
- [ ] **Retrieval** — hybrid (dense + BM25) รวมด้วย RRF, boost รหัสวิชา, (option) rerank
- [ ] **API** — FastAPI `POST /query` → answer + citations + chunks
- [ ] **ต่อ LLM** — prompt grounded ให้ OpenThaiGPT (ทีม AI) + citation ต่อท้าย
- [ ] **Evaluation** — golden set 20–30 คำถาม, วัด hit-rate@5

### ขยายไฟล์อื่น
- [ ] OCR + clean + chunk อีก 3 ไฟล์ (AIT, DSBA, IT_inter2565) — โค้ดรองรับแล้ว แค่รันเพิ่ม

---

## ข้อควรระวังที่พบ (บันทึกไว้กันพลาด)
1. **PUA คนละช่วงต่อไฟล์** → ห้ามใช้ remap table ร่วม; เราเลี่ยงด้วย OCR ทั้งหมด
2. **Hallucination:** โลคัล 3b แต่งชื่อปลอมได้ (อันตรายในคลัง RAG) → **สลับมา API แก้ได้เกือบหมด**; cleaning ยังตัด pattern `+++...+++` เผื่อไว้ + เฝ้าใน eval
3. **รหัสวิชาในหน้าภาพมีแค่ใน OCR** (text layer ว่าง) → cross-check เลขไม่ได้ ต้องพึ่งความแม่น OCR
4. **API key อยู่ใน `.env` (gitignore)** — ห้าม commit/แชร์; runtime ที่ทีมต่อไม่ใช้ key นี้ (OCR เป็น offline build)
5. API วางเลขหน้าไม่สม่ำเสมอ → บางหน้า page_label=None (ยอมรับได้; ปรับ extract ให้ดึงจากหัวหน้าแล้ว)

## ไฟล์ที่สร้าง
```
scripts/inspect_pdf.py      ตรวจ PDF (page-type + PUA)
rag/ingest_ocr.py           OCR ทุกหน้า (Typhoon OCR via Ollama)
rag/clean.py                ทำความสะอาดผล OCR
rag/chunk.py                ตัด chunk structure-aware
requirements.txt            dependencies
data/inspect_report.json    ผลตรวจ 4 ไฟล์
data/extracted/IT2565/*.md  ผล OCR ต่อหน้า (กำลังสะสม)
```
