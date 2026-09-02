# Checklist 4 — Index + Retrieval

อัปเดต: 2026-09-02 | ต่อจาก `checklist_3.md` | ครอบคลุม **ขั้น Index + Retrieval**

---

## สรุปสั้น

จาก 2,358 chunks → สร้าง **dense index (BGE-M3 → Chroma)** + **BM25 (newmm)** →
ทำ **hybrid retrieval (RRF + code boost)** เสร็จและ validate แล้ว
คำถามรหัสวิชา/ชื่อวิชา/ความหมายกว้าง คืนผลถูกต้อง — **พร้อมต่อ FastAPI `/query`**

---

## ✅ ขั้น Index (เสร็จ) — `rag/index.py`

- [x] embed 2,358 chunks ด้วย **BGE-M3** (dense, dim 1024) บน GPU RTX 4060 → **26 วินาที**
- [x] เก็บลง **Chroma persistent** (`data/chroma/`, collection `it_kmitl`, cosine) — 2,358 รายการ (36MB)
- [x] สร้าง **BM25** (ตัดคำ newmm) → `data/bm25.pkl` (3.5MB) — **4 วินาที**
- [x] ใช้ embedding โมเดลเดียวกันทั้ง index และ query
- [x] แก้ 2 gotcha: แปลง bge-m3 `.bin→safetensors` (torch 2.5 + transformers 5.16), ทำ chunk id ไม่ซ้ำ
- [x] `scripts/test_index.py` — ตรวจ dense + BM25 แยกกัน

## ✅ ขั้น Retrieval (เสร็จ) — `rag/retrieve.py`

- [x] **dense** BGE-M3 → Chroma top-20 **+ BM25** newmm top-20
- [x] รวมด้วย **RRF** `score(d) = Σ 1/(60 + rank_i(d))`
- [x] **boost รหัสวิชา**: query match `\d{8}` → chunk ที่ `course_code` ตรง ได้โบนัส (ดึงเข้าแม้ไม่ติด candidate)
- [x] ส่งจริง **top 3–5** (ปรับด้วย `--k`)
- [x] คลาส `Retriever` (โหลด index ครั้งเดียว, reuse ได้ใน FastAPI)
- [~] **rerank BGE-reranker-v2-m3** — เขียนโค้ดครบ, default off (เปิด `--rerank` / `RERANK=1`; ต้องโหลดโมเดล ~2.3GB)

### ผล validate (ยืนยันการทำงาน)

| query | ผลอันดับ 1 | หมายเหตุ |
|---|---|---|
| `06016429 คือวิชาอะไร` | ✅ 06016429 การพัฒนาเว็บฝั่งไคลเอนต์ | code-boost ดันขึ้นบนสุด (naive BM25 เคยพลาด) |
| `วิชาการเขียนโปรแกรมเว็บ` | ✅ 06066302 การเขียนโปรแกรมเว็บพื้นฐาน | dense#1 + bm25#1 ตรงกัน |
| `ค่าธรรมเนียม...` | ✅ ค่าใช้จ่ายต่อหัว 229,192 บาท/คน/ปี + กฎการศึกษา | semantic (dense เด่น) |

---

## 📊 สรุป corpus → index

```
1,034 หน้า (4 หลักสูตร) → 2,358 chunks → index:
  data/chroma/        dense (BGE-M3, cosine)   36 MB
  data/bm25.pkl       BM25 (newmm)             3.5 MB
```

---

## ⬜ ยังไม่ได้ทำ (รอบถัดไป)

- [ ] **API** — FastAPI `POST /query` → `{answer, citations, chunks}` (ห่อ `Retriever.search`)
- [ ] **ต่อ LLM** — ส่ง context (top chunks) + prompt grounded ให้ OpenThaiGPT + citation ต่อท้าย
- [ ] **Evaluation** — golden set 20–30 คำถาม (คละ 4 หลักสูตร), วัด retrieval hit-rate@5 + ความถูกต้องคำตอบ
- [ ] (option) เปิด **rerank** จริง — วัดว่า hit-rate ดีขึ้นคุ้มเวลา/โมเดลไหม
- [ ] (option) ปรับพารามิเตอร์ retrieval (CAND_K, RRF_K, CODE_BOOST) ตามผล eval

---

## ไฟล์ที่เพิ่ม/แก้ในรอบนี้
```
rag/index.py            สร้าง dense (Chroma) + BM25 index
rag/retrieve.py         hybrid retrieval (dense+BM25+RRF+code boost, +rerank optional)
scripts/test_index.py   ทดสอบ index (dense/BM25 แยก)
data/chroma/            dense store (gitignored)
data/bm25.pkl           BM25 (gitignored)
```

## Config (ตั้งผ่าน env / .env — ปรับ retrieval ได้โดยไม่แก้โค้ด)
```
EMBED_MODEL=BAAI/bge-m3     CHROMA_DIR=data/chroma     CHROMA_COLLECTION=it_kmitl
BM25_PATH=data/bm25.pkl     RETRIEVE_CAND_K=20         RRF_K=60
RETRIEVE_TOP_K=5            CODE_BOOST=1.0             RERANK=0
```

## ข้อควรเฝ้าต่อ
1. **BM25 ดิบไม่ boost code เอง** — ต้องพึ่ง code-boost ใน retrieve.py (ทำแล้ว) — อย่าถอดออก
2. **bge-m3 safetensors** อยู่ใน HF cache — ถ้า cache หายต้องแปลง .bin ใหม่ (ดู memory: index-setup-gotchas)
3. คำตอบ "ค่าธรรมเนียม" ในเล่มไม่ได้ระบุตัวเลขตรงๆ ทุกที่ — eval ควรครอบคลุมเคสนี้
