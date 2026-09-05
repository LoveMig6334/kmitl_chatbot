# การนำเสนอส่วน AI — แชตบอตหลักสูตรคณะเทคโนโลยีสารสนเทศ สจล.

> ร่างสำหรับสไลด์ / สคริปต์พูด เน้นโครงสร้างระบบและเทคนิคที่ใช้ ไม่ลงรายละเอียดโค้ด

---

## 1. โจทย์และข้อจำกัด

- **โจทย์**: ตอบคำถามเกี่ยวกับหลักสูตรปริญญาตรี 4 หลักสูตรของคณะ IT สจล. (AIT, DSBA, BIT, IT) จากเอกสารหลักสูตรจริง (มคอ.2 PDF) พร้อมอ้างอิงหน้า
- **กติกาแข่ง (hard constraint)**: ทุกการอ่าน/วิเคราะห์/ตอบข้อความผู้ใช้ต้องผ่านโมเดล **ThaiLLM** เท่านั้น
  - มีแค่ `/chat/completions` — **ไม่มี embeddings endpoint** → ต้องออกแบบ retrieval ให้ไม่พึ่ง ThaiLLM
  - โมเดลหลัก: `openthaigpt-thaillm-8b-instruct-v7.2` (8B) → ต้องช่วยโมเดลด้วยโครงสร้างระบบ ไม่ใช่หวังพึ่งความฉลาดของโมเดลอย่างเดียว
- **ผู้ใช้เป้าหมาย**: นักเรียน ม.ปลาย / ผู้สนใจสมัคร → ภาษาต้องเข้าใจง่าย รองรับ ไทย / อังกฤษ / จีน

---

## 2. ภาพรวมสถาปัตยกรรม

```
ผู้ใช้ (Next.js)
   │  POST /chat  (SSE stream)
   ▼
FastAPI (api/)
   │
   ├─► [1] Gatekeeper  ── ไม่ใช่คำถามหลักสูตร ──► direct_reply (ตอบเองทันที ไม่มี citation)
   │        │ in_scope
   ▼
   ├─► [2] Query rewrite (ถ้าจำเป็น)
   ├─► [3] Hybrid retrieval  (BGE-M3 dense + BM25 → RRF)
   ├─► [4] Context builder   (งบ token, ใส่เลข [n])
   ├─► [5] ThaiLLM generate  (stream, ตัด <think>)
   ├─► [6] Language guard    (ตรวจว่าตอบภาษาที่ถูก)
   └─► [7] Citations         (เฉพาะ chunk ที่ถูกอ้าง [n] จริง)
```

หลักการออกแบบ 3 ข้อ

1. **ถูกที่สุดก่อน** — กฎ (0 API call) → LLM 1 call → fallback
2. **โมเดลตอบจากบริบทเท่านั้น** — ทุกประโยคข้อเท็จจริงต้องมี `[n]` ตรวจย้อนกลับได้
3. **ทุกชั้นมี eval ของตัวเอง** — วัดได้ ทำซ้ำได้ (cache) ไม่พึ่งความรู้สึก

---

## 3. Gatekeeper — ด่านคัดกรองข้อความ

**หน้าที่**: รับทุกข้อความก่อน แล้วตัดสินว่า "ส่งไป RAG" หรือ "ตอบเองเลย"

**Output (`GateDecision`)** — สัญญาที่ frontend/RAG ใช้ร่วมกัน

| ฟิลด์ | ค่า |
|---|---|
| `category` | `in_scope`, `off_topic_general`, `off_topic_other_university`, `out_of_scope_kmitl`, `injection_or_abuse`, `greeting_smalltalk` |
| `language` | th / en / zh / other |
| `programs` | ชื่อหลักสูตรที่ถูกเอ่ยถึง (ว่าง = ค้นทุกหลักสูตร) |
| `course_codes` | รหัสวิชา 8 หลักที่ regex ดึงได้ |
| `question_kind` | fact_lookup / descriptive / comparison |
| `direct_reply` | คำตอบสำเร็จรูป (เฉพาะกรณีไม่ใช่ in_scope) |

**เทคนิค: 3 ชั้น เรียงจากถูก → แพง**

1. **Rule layer (0 API call)** — ตัดสินเฉพาะเมื่อ "แน่ใจเกือบ 100 %" ไม่งั้นส่งต่อ
   - prompt injection patterns (ไทย/อังกฤษ/จีน)
   - smalltalk: ทักทาย/ขอบคุณ/ถามว่าบอทคือใคร (ข้อความต้อง "ไม่มีเนื้อหา" หลังตัดอิโมจิ/คำลงท้าย)
   - ชื่อมหาวิทยาลัยอื่น, คณะอื่นของ สจล. (redirect ไปเว็บคณะนั้น), เรื่องทั่วไปชัด ๆ
   - alias หลักสูตร + กฎแก้ความกำกวม เช่น "IT" เดี่ยว ๆ = คณะ, "อินเตอร์" = BIT
2. **LLM layer (1 call)** — ThaiLLM จำแนกเป็น JSON แบบเข้มงวด
   - ข้อความผู้ใช้ห่อใน `<user_message>` และถือเป็น *data* ไม่ใช่คำสั่ง (กัน injection)
   - parser ตัด `<think>` / code fence และซ่อม JSON ที่ถูกตัดกลางคัน
3. **Fallback** — timeout หรือ JSON เสีย 2 ครั้ง → ถือเป็น `in_scope` (พยายามตอบดีกว่าปฏิเสธผิด)

**บทเรียน**: โมเดล "คิดก่อนตอบ" (`<think>`) เสมอ → ต้องตั้ง `max_tokens` 1024 ไม่งั้น JSON ถูกตัด ~4 % ของแถวภาษาไทย

**การวัดผล**
- `eval_gatekeeper.py` — ชุดคำถาม easy/medium/hard, รายงาน accuracy ต่อหมวด, confusion matrix, latency p95
- `eval_tuning.py` — 543 แถว แบ่ง stratum; คำตอบ `direct_reply` ถูกตัดเกรดตาม rubric
- ชุด blind ที่ทีมไม่เปิดดู ใช้กันการ overfit prompt

---

## 4. Retrieval — ค้นเอกสารโดยไม่ใช้ ThaiLLM

### 4.1 เตรียมข้อมูล (offline)

- PDF มคอ.2 ทั้ง 4 เล่ม (~1,000 หน้า) → **Typhoon-OCR** เป็น markdown ต่อหน้า (เก็บ cache ไว้ใน repo, ไม่ต้อง OCR ซ้ำ)
- ปัญหาเฉพาะไทย: PDF ใช้ฟอนต์ TH Sarabun ที่วางสระ/วรรณยุกต์เป็น private-use codepoint → สร้างตารางแมป PUA→เครื่องหมายด้วย dictionary scoring ต่อไฟล์
- ทำความสะอาด + แบ่ง chunk ตามโครงสร้างเอกสาร → **2,347 chunks**
  - chunk ทั่วไป: `AIT::gen::0012` (มี heading path)
  - chunk รายวิชา: `IT2565::course::06016408` (ผูกรหัสวิชา)
- audit ความครอบคลุมหน้า ≥ 90 % ต่อเล่ม (เคยเจอ bug page_index=0 8.8 % ของ chunk → แก้แล้ว)

### 4.2 ค้นหา (online)

```
query ──► BGE-M3 dense (Chroma)  ─┐
      └─► BM25 (ตัดคำ newmm)     ─┤► RRF fusion ─► + course-code boost ─► top-k (12)
      filter: หลักสูตรที่ gate ระบุ ─┘  (กรอง "ก่อน" fuse ไม่ใช่หลัง)
```

- **Hybrid**: dense จับความหมาย, BM25 จับคำเฉพาะ/รหัสวิชา/ตัวเลข → รวมด้วย Reciprocal Rank Fusion
- **Program filter ก่อน fusion** — ถ้ากรองทีหลัง top-k จะโดนหลักสูตรอื่นกิน (แต่ละหลักสูตร ≈ ¼ ของ corpus)
- **Course-code boost** — ถามด้วยรหัสวิชา 8 หลัก → chunk วิชานั้นขึ้นบนสุดแน่นอน
- **Comparison** — ค้นแยกต่อหลักสูตร แล้ว interleave แบบ round-robin ให้ทุกหลักสูตรมีบริบทเท่ากัน
- **Embedding บน production**: เรียก BGE-M3 แบบ hosted API (ไม่ต้องโหลด torch 2 GB บนเซิร์ฟเวอร์ฟรี) ถ้า API ล่ม → ถอยไป BM25 อย่างเดียว ระบบไม่ล้ม
- ThaiLLM **ไม่ถูกใช้** ในขั้นนี้เลย → ไม่ผิดกติกา (โมเดลอ่าน/ตอบข้อความผู้ใช้เท่านั้น)

**การวัดผล**: `calibrate_retrieval.py` วัด gold-chunk rank / hit rate; เพิ่ม candidate ต่อ ranker 20→40 ได้ hit rate +11 จุด

---

## 5. Answer layer (RAG) — จาก chunk เป็นคำตอบพร้อมอ้างอิง

**ลำดับงาน**: rewrite → retrieve → no-answer gate → context → model → stream → language guard → citations

| ขั้น | เทคนิค |
|---|---|
| **Query rewrite** | ทำเฉพาะเมื่อจำเป็น: คำถามต่อเนื่องสั้น ๆ ("แล้ว DSBA ล่ะ") หรือคำถามไม่ใช่ภาษาไทย (เอกสารเป็นไทย → แปลก่อนค้น) ล้มเหลวก็ใช้ข้อความเดิม |
| **Context builder** | จัดรูป `[n] หลักสูตร หน้า X — heading` + เนื้อหา, งบ token ประมาณ (ไทย chars/3, อื่น chars/4) ตัดตัวคะแนนต่ำก่อน |
| **Prompt** | ภาษาไทย ~600 token: ตอบจากบริบทเท่านั้น, ทุกประโยคข้อเท็จจริงลงท้าย `[n]`, ไม่พบให้บอกว่าไม่พบ, ตอบภาษาเดียวกับผู้ถาม, few-shot ใช้ข้อมูลสมมติ (กันโมเดลจำคำตอบ) |
| **Streaming** | ตัด `<think>` แบบ incremental แม้ tag ถูกแบ่งข้าม delta; ไม่ส่งถึงผู้ใช้เลย |
| **Fallback model** | ถ้าไม่มี token ที่มองเห็นได้ภายในเวลาที่กำหนด → ลองอีกโมเดลหนึ่งครั้ง |
| **Language guard** | ถามเป็น en/zh แต่โมเดลตอบไทย → ให้ ThaiLLM แปล/ตอบใหม่ (retry 1 ครั้ง); ภาษาไทย stream สด, ภาษาอื่น buffer ก่อน |
| **Citations** | ส่งเฉพาะ chunk ที่มี `[n]` ปรากฏในคำตอบจริง → ผู้ใช้กดเปิด PDF หน้านั้นได้ |

**Safety เพิ่มเติม**: ปฏิเสธคำขอโค้ดอันตราย, ตอบเมื่อบริบทมีข้อมูลเท่านั้น

**บทเรียนจากการเลือกโมเดล**
- ทดลอง `pathumma-think` สำหรับคำถามเปรียบเทียบ → โมเดล "คำนวณเลขส่วนต่างเอง" ทุกครั้ง ซึ่งตรวจ grounding ไม่ผ่าน → กลับมาใช้ openthaigpt ทุกงาน
- คะแนน RRF เป็นอันดับ ไม่ใช่ความมั่นใจ → ใช้ threshold แยก "ตอบได้/ตอบไม่ได้" ไม่ได้ → ให้โมเดลเป็นคนบอก "ไม่พบ" ตาม prompt

**การวัดผล — `eval_answers.py` (deterministic ไม่ใช้ LLM ตัดสิน)**
- ความคาดหวังมาจาก `docs/gold-facts.md` (อ่านจาก PDF จริงเท่านั้น)
- ตรวจ: ข้อเท็จจริงที่ต้องมี/ห้ามมี, **ทุกตัวเลขในคำตอบต้องอยู่ในบริบท** (number grounding), citation ตรง gold chunk, พฤติกรรม not-found, ภาษาที่ตอบ, การรั่วของ `<think>` / `[n]` ค้าง
- แยก failure เป็น `retrieval-miss` vs `generation-miss` → รู้ว่าต้องแก้ชั้นไหน
- `run_real_test.py` ยิงชุดคำถามยากผ่าน pipeline จริง 3 รอบ เพื่อดูความเสถียร

---

## 6. การ Deploy

- Frontend: Vercel (Next.js) · Backend: Render free tier (FastAPI) · index artifacts: private HF dataset
- Embedding query ผ่าน hosted BGE-M3 → RAM ~260 MB แทน ~2.3 GB
- SSE streaming ต้นทางถึงปลายทาง; ผู้ใช้กดหยุด → ยกเลิก request ไป ThaiLLM จริง
- Rate limit ต่อ IP, CORS, ไม่ log เนื้อหาข้อความโดยปริยาย

---

## 7. สรุปจุดขายทางเทคนิค (สำหรับสไลด์ปิด)

1. **ทำงานภายใต้ข้อจำกัด ThaiLLM ได้จริง** — ไม่มี embeddings ก็สร้าง hybrid retrieval แยกต่างหาก และให้ ThaiLLM ทำเฉพาะสิ่งที่กติกากำหนด
2. **Gatekeeper 3 ชั้น** — ประหยัด, กัน injection, ตอบทักทาย/นอกขอบเขตอย่างสุภาพและชี้ทางถูก
3. **Grounded + cited** — ทุกข้อเท็จจริงชี้กลับหน้า PDF ได้ ตัวเลขทุกตัวถูกตรวจว่ามาจากเอกสาร
4. **Thai-specific engineering** — OCR ไทย, ซ่อมสระ/วรรณยุกต์ PUA, ตัดคำ newmm, ประมาณ token ภาษาไทย
5. **Eval ทุกชั้น ทำซ้ำได้** — gatekeeper / retrieval / answer มีชุดทดสอบและ cache ของตัวเอง แยกได้ว่าพังที่ชั้นไหน

---

## ภาคผนวก: ตัวเลขอ้างอิงเร็ว

| หัวข้อ | ค่า |
|---|---|
| หลักสูตร | 4 (AIT, DSBA, BIT, IT) |
| หน้า OCR | ~1,034 |
| chunks | 2,347 |
| top-k retrieval | 12 (candidate 40 ต่อ ranker) |
| งบบริบท | ~6,500 est. tokens |
| ชุด tuning gatekeeper | 543 แถว |
| โมเดล | openthaigpt-thaillm-8b-instruct-v7.2 (gate / rewrite / answer / guard) |
