# Checklist 2 — RAG Pipeline (OCR เต็มเล่ม + Chunking เสร็จ)

อัปเดต: 2026-09-01 | นำร่องไฟล์ **IT2565.pdf** | ต่อจาก `cheklist_1.md`

---

## สรุปสั้น

สลับมาใช้ **Typhoon API** (หลัง A/B test ชนะโลคัล) → **OCR IT2565 ครบ 294 หน้า สำเร็จ 100%** →
clean → chunk เต็มเล่มได้ **603 chunks** (คุณภาพผ่าน QA) → เขียน `data/chunks/IT2565.jsonl` แล้ว
**ปิดจ็อบขั้น ingestion + chunking ของไฟล์นำร่องครบถ้วน**

---

## ✅ ทำเสร็จเพิ่มในรอบนี้ (ต่อจาก checklist_1)

### 6. สลับ OCR engine → Typhoon API
- [x] สมัคร/รับ key, เก็บใน `.env` (gitignore) + `.env.example` ให้ทีม, โหลดด้วย python-dotenv
- [x] A/B test (หน้าตาราง+คำอธิบาย): **API ชนะ** — ไม่ hallucinate (โลคัลแต่งชื่อปลอม), รักษาตาราง, เร็ว 4-8s/หน้า
- [x] ปรับ `extract_page_label` รองรับรูปแบบเลขหน้าของ API (เลขล้วนหัวหน้า, เลี่ยงเลข section ท้ายหน้า)

### 7. OCR IT2565 เต็มเล่ม (API)
- [x] **294/294 หน้า สำเร็จ, ล้มเหลว 0** (ใช้เวลา ~27 นาที, ~5.5s/หน้าเฉลี่ย)
- [x] cache ครบที่ `data/extracted/IT2565/{page:03d}.md`

### 8. Clean + Chunk เต็มเล่ม
- [x] แก้ pollution: course chunk เคยพองถึง 44,415 → cap + boundary (`<table`, `ภาคผนวก`, `ตารางเปรียบเทียบ`) → **max 2,759**
- [x] แก้ general chunk ใหญ่เกิน: ซอยตาราง (`</tr>`) + ข้อความยาว (newmm) + catch-all → **median 1,818, max 4,024**
- [x] แก้ false positive: `+++` (hallucination) ไม่ชนกับ `C++` แล้ว
- [x] เขียน **`data/chunks/IT2565.jsonl` (603 chunks, ~1.1 MB)**

### 9. QA corpus (`scripts/qa_corpus.py`)
- [x] หน้า output สั้นผิดปกติ: **0**
- [x] hallucination `+++...+++` ตกค้าง: **0**
- [x] รหัสวิชา 7 หลัก (เลขหาย): มีแค่ 4 ตัว และเป็นเลขในฟอร์ม SLA หน้า 294 (ไม่ใช่รหัสวิชา)
- [x] page_label coverage: 71% ของหน้า / 85% ของ chunks

---

## 📊 ตัวเลข chunk (IT2565)

| ประเภท | จำนวน | median ตัวอักษร | max |
|---|---|---|---|
| รายวิชา (course) | 484 | 548 | 2,759 |
| ทั่วไป (general) | 119 | 1,818 | 4,024 |
| **รวม** | **603** | | |

- course chunk ครบองค์ (มีคำอธิบาย + วิชาบังคับก่อน): **276**
- รหัสวิชาไม่ซ้ำใน chunk: 444
- metadata ครบทุก chunk: `{doc_name, doc_type, section, page_label, page_index, course_code?, chunk_type}`
- เนื้อหา non-course สำคัญครบ (ตรวจแล้ว): ค่าธรรมเนียม, คุณสมบัติผู้สมัคร, อาชีพ, การคัดเลือก

---

## ⬜ ยังไม่ได้ทำ (รอบถัดไป)

### ขยายอีก 3 ไฟล์ (โค้ดรองรับแล้ว แค่รัน)
- [ ] OCR + clean + chunk: **AIT** (253 น.), **DSBA** (281 น.), **IT_inter2565** (206 น.) ด้วย API
- [ ] ปรับ header/footer boilerplate ต่อไฟล์ (auto อยู่แล้ว แต่ควรตรวจตา)

### ขั้นถัดไปของ pipeline (ตาม skill.md)
- [ ] **Index** — embed BGE-M3 → Chroma (persistent) + BM25 index คู่ขนาน
- [ ] **Retrieval** — hybrid (dense + BM25 + RRF), boost รหัสวิชา, (option) rerank BGE-v2-m3
- [ ] **API** — FastAPI `POST /query` → answer + citations + chunks
- [ ] **ต่อ LLM** — prompt grounded ให้ OpenThaiGPT + citation
- [ ] **Evaluation** — golden set 20-30 คำถาม, hit-rate@5

### ปรับจูน chunk (ถ้ามีเวลา — ไม่บล็อก)
- [ ] หน่วยกิต `N(N-N-N)` บางวิชาไปอยู่ท้าย chunk (ข้อมูลครบ แค่ตำแหน่ง)
- [ ] page_label ที่ยัง None (29% ของหน้า) — เติมจาก offset PDF index ได้ถ้าต้องการ citation แม่นขึ้น
- [ ] พิจารณา dedupe course chunk ที่รหัสซ้ำ (โผล่ทั้งหน้าโครงสร้าง + หน้าคำอธิบาย)

---

## ไฟล์ที่เพิ่ม/แก้ในรอบนี้
```
.env / .env.example        config OCR (key อยู่ใน .env, gitignore)
scripts/qa_corpus.py       ตรวจคุณภาพ corpus + chunks (ใหม่)
rag/ingest_ocr.py          + โหลด .env, temp=0, สลับ API/โลคัลได้
rag/clean.py               + extract_page_label ทน API, regex +++ ไม่ชน C++
rag/chunk.py               + boundary/cap course, ซอย general chunk ใหญ่
data/extracted/IT2565/*.md ผล OCR API ครบ 294 หน้า
data/chunks/IT2565.jsonl   603 chunks พร้อม index (ผลลัพธ์ขั้นนี้)
```

## ข้อควรระวังที่ยังต้องเฝ้า
1. **API key ใน `.env`** — ห้าม commit/แชร์ (runtime ที่ทีมต่อไม่ใช้ key นี้)
2. **รหัสวิชาในหน้าภาพพึ่ง OCR ล้วน** — eval ต้องสุ่มตรวจรหัสเทียบภาพจริง
3. **page_label ~29% เป็น None** — citation หน้าจะไม่ครบทุก chunk (ใช้ page_index เสริมได้)
