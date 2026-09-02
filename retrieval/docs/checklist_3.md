# Checklist 3 — OCR + Chunking ครบทั้ง 4 ไฟล์ (ปิดจ็อบส่วน Ingestion)

อัปเดต: 2026-09-02 | ต่อจาก `checklist_2.md` | **ขอบเขต: ครบทั้ง 4 ไฟล์ ยังไม่ทำ Index**

---

## สรุปสั้น

OCR อีก 3 ไฟล์ (AIT, DSBA, IT_inter2565) ด้วย Typhoon API + chunk เสร็จครบ →
รวมกับ IT2565 เดิม เป็น **corpus ครบทั้ง 4 หลักสูตร: 1,034 หน้า → 2,357 chunks** →
เขียน `data/chunks/{doc}.jsonl` + `data/chunks/all.jsonl` (4.2 MB) **พร้อมเข้าขั้น Index**

---

## ✅ ทำเสร็จในรอบนี้

### 10. OCR อีก 3 ไฟล์ (Typhoon API)
- [x] **AIT** (เทคโนโลยีปัญญาประดิษฐ์) — 253/253 หน้า, ล้มเหลว 0
- [x] **DSBA** (วิทยาการข้อมูลฯ) — 281/281 หน้า, ล้มเหลว 0
- [x] **IT_inter2565** (IT นานาชาติ) — 206/206 หน้า (205 API + 1 placeholder)
- [x] รันต่อกันใน job เดียว เลี่ยงชน rate limit 20 RPM

### 11. Edge case: หน้า OCR ไม่ได้ 1 หน้า
- [x] IT_inter2565 หน้า 104 = **ตารางเมทริกซ์ Curriculum Mapping** ซับซ้อนเกิน →
      API ตอบ 408 timeout (~9 นาที/ครั้ง), local 3b พ่น prompt กลับ (ทั้งคู่แพ้)
- [x] ตัดสินใจ: ใส่ **placeholder ซื่อสัตย์** (อธิบายเนื้อหาจากการดูภาพจริง + marker `OCR_SKIPPED`)
      แทนการปล่อย garbage — หน้า mapping มูลค่า retrieval ต่ำ

### 12. Chunk ครบ 4 ไฟล์ (`scripts/build_chunks_all.py`)
- [x] chunk.py **generalize ได้ดีทั้ง 4 หลักสูตร** (ตรวจ course chunk จริงของ AI/DataSci/นานาชาติ — ครบองค์)
- [x] เขียน `data/chunks/{doc}.jsonl` แยกไฟล์ + `data/chunks/all.jsonl` รวม

### 13. QA รวบยอด (สะอาดทั้ง 4)
- [x] hallucination `+++...+++` ตกค้าง: **0 ทุกไฟล์**
- [x] chunk ใหญ่เกิน 5,000 ตัวอักษร: **0 ทุกไฟล์** (pollution แก้หมด)
- [x] chunk สั้นผิดปกติ: 1 (AIT, ไม่กระทบ)

---

## 📊 ตัวเลข corpus รวม

| ไฟล์ | หน้า | chunks | course | general | page_label |
|---|---|---|---|---|---|
| AIT | 253 | 562 | 395 | 167 | 65% |
| DSBA | 281 | 740 | 592 | 148 | 88% |
| IT2565 | 294 | 603 | 484 | 119 | 85% |
| IT_inter2565 | 206 | 452 | 338 | 114 | 80% |
| **รวม** | **1,034** | **2,357** | **1,809** | **548** | — |

- metadata ครบทุก chunk: `{doc_name, doc_type=หลักสูตร, section, page_label, page_index, course_code?, chunk_type}`
- ขนาด chunk: course median ~320–550, general median ~1,670–1,820 ตัวอักษร (ไม่มีก้อนยักษ์)

---

## ⬜ ยังไม่ได้ทำ (รอบถัดไป — Index เป็นต้นไป ตามที่สั่งให้ยังไม่ทำ)

- [ ] **Index** — embed BGE-M3 → Chroma (persistent) + BM25 index คู่ขนาน (จาก `all.jsonl`)
- [ ] **Retrieval** — hybrid (dense + BM25 + RRF), boost รหัสวิชา, (option) rerank BGE-v2-m3
- [ ] **API** — FastAPI `POST /query` → answer + citations + chunks
- [ ] **ต่อ LLM** — prompt grounded ให้ OpenThaiGPT + citation
- [ ] **Evaluation** — golden set 20–30 คำถาม (คละ 4 หลักสูตร), hit-rate@5

### ปรับจูนเล็ก (ไม่บล็อก)
- [ ] page_label ที่ None (12–35% ตามไฟล์) — เติมจาก offset PDF index ได้ถ้าต้อง citation แม่นขึ้น
- [ ] หน้า 104 IT_inter2565 — ถ้าต้องการเนื้อหาเมทริกซ์จริง ต้อง OCR วิธีพิเศษ (crop เป็นส่วนๆ)
- [ ] dedupe course chunk รหัสซ้ำ (โผล่ทั้งหน้าโครงสร้าง + คำอธิบาย)

---

## ไฟล์ผลลัพธ์ (พร้อมส่งเข้า Index)
```
data/extracted/{AIT,DSBA,IT2565,IT_inter2565}/*.md   ผล OCR ต่อหน้า (1,034 หน้า)
data/chunks/AIT.jsonl              562 chunks
data/chunks/DSBA.jsonl             740 chunks
data/chunks/IT2565.jsonl           603 chunks
data/chunks/IT_inter2565.jsonl     452 chunks
data/chunks/all.jsonl              2,357 chunks รวม (4.2 MB) ← input ของขั้น Index
scripts/build_chunks_all.py        driver chunk ทุกไฟล์
```

## ข้อควรเฝ้าต่อ
1. **API key ใน `.env` (gitignore)** — runtime ที่ทีมต่อไม่ใช้ key นี้ (OCR เป็น offline build)
2. **รหัสวิชาในหน้าภาพพึ่ง OCR ล้วน** — eval ต้องสุ่มตรวจเทียบภาพจริง
3. **หน้า 104 IT_inter2565 เป็น placeholder** — ไม่มีข้อมูลเมทริกซ์จริง (มูลค่าต่ำ)
