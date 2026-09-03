---
name: RAG Pipeline — Chatbot คณะ IT ลาดกระบัง (Hackathon)
description: สร้างและพัฒนา RAG pipeline สำหรับ chatbot ตอบคำถามข้อมูลคณะ IT ลาดกระบัง (KMITL) จากไฟล์ PDF มคอ./หลักสูตร ใช้เมื่อทำงานใดๆ เกี่ยวกับ ingestion, OCR, chunking, embedding, vector search, retrieval หรือ API ของส่วน RAG ในโปรเจกต์นี้
---

# RAG Pipeline — Chatbot คณะ IT ลาดกระบัง (Hackathon)

## ภาพรวมโปรเจกต์ (อ่านให้เข้าใจก่อนแตะโค้ด)

Chatbot ตอบคำถามนักศึกษาเกี่ยวกับคณะ IT KMITL จากเอกสาร PDF (มคอ.2 หลักสูตร, ประกาศ ฯลฯ) แบ่งงาน 3 ส่วน:

1. **UI** — หน้าเว็บแชต (ทีมอื่นรับผิดชอบ)
2. **LLM** — ตัวตอบคำถาม ใช้ **OpenThaiGPT** (ทีมอื่นรับผิดชอบ)
3. **RAG + Database** — ส่วนที่ skill นี้ครอบคลุม: ดูดข้อมูลจาก PDF → index → ค้น → ส่ง context + citation ให้ LLM

คุณภาพของ chatbot ทั้งระบบขึ้นกับส่วน RAG มากที่สุด: ถ้า retrieval หยิบผิด LLM จะตอบผิดเสมอ

## ⚠️ ข้อเท็จจริงสำคัญเกี่ยวกับไฟล์ PDF ต้นทาง (ตรวจพิสูจน์แล้วจากไฟล์จริงทั้ง 4 ไฟล์ 2026-09-01)

ตรวจด้วย `scripts/inspect_pdf.py` (ผลละเอียด: `data/inspect_report.json`) แล้วพบว่า **ทั้ง 4 ไฟล์ใน `Data/` ใช้ฟอนต์ THSarabunPSK และมีกับดัก PUA เหมือนกันหมด — ไม่ใช่แค่ IT2565** — **ห้ามใช้ PDF loader มาตรฐาน (PyPDFLoader ฯลฯ) ดูดข้อความตรงๆ เด็ดขาด** เพราะจะได้ข้อมูลขยะโดยไม่มี error ใดๆ:

1. **วรรณยุกต์/สระในหน้า text layer เป็นตัวอักษรผี (PUA) ทุกไฟล์ แต่ "คนละช่วง" ตามการ subset ฟอนต์รายเอกสาร:**

   | ไฟล์ | หน้า | %หน้าภาพ | ช่วง PUA | หน้าที่ต้องกู้ (OCR/remap) |
   |---|---|---|---|---|
   | `IT2565.pdf` | 294 | 59% | `F052–F713` (เช่น ้=F70B) | 293 (100%) |
   | `AIT.pdf` | 253 | 71% | `E005–E076` | 253 (100%) |
   | `DSBA.pdf` | 281 | 63% | `E006–E08A` | 281 (100%) |
   | `IT_inter2565.pdf` | 206 | 53% | `E005–E095` | 205 (100%) |

   `pythainlp.normalize` + NFC **แก้ไม่ได้** ต้อง remap ด้วยตาราง PUA→Thai. **สำคัญ: ตาราง remap ใช้ร่วมกันข้ามไฟล์ไม่ได้** — codepoint→อักษรไทย ต่างกันรายเอกสาร (F700–F71A ใน skill เดิมใช้ได้กับ IT2565 เท่านั้น) ต้อง derive ตารางต่อไฟล์

2. **53–71% ของทุกเล่มเป็นภาพเต็มหน้า:** เนื้อหาที่ถูกถามบ่อยสุด (ตารางรหัสวิชา, คำอธิบายรายวิชา, หมวดศึกษาทั่วไป) ล็อกอยู่ในรูป ข่าวดี: ภาพคม born-digital ไม่ใช่สแกน OCR จะแม่นมาก

3. **แทบไม่มีหน้า text ที่ layer สะอาดเลย:** ทุกไฟล์เหลือหน้าสะอาดใช้ตรงๆ ได้แค่ 0–1 หน้า → แม้แต่ "หน้า text" ก็ต้องกู้ ⇒ **รวมทั้ง database ต้องกู้ ~100% ทุกไฟล์**

**รันสคริปต์ตรวจ (page-type + PUA range/count) กับทุกไฟล์ก่อน ingest เสมอ** — `python scripts/inspect_pdf.py "Data/*.pdf"`

## Stack ที่ตัดสินใจแล้ว (อย่าเปลี่ยนเองโดยไม่ถาม)

| ส่วน | เครื่องมือ |
|---|---|
| OCR | **Typhoon OCR** (scb10x) — รักษาตาราง output เป็น Markdown. **ใช้ Typhoon API `typhoon-ocr` (v1.5) เป็นหลัก** (ฟรี, เร็ว 4-8s/หน้า, ไม่ hallucinate); โลคัล `typhoon-ocr1.5-3b` ผ่าน Ollama เป็น fallback. เรียกด้วย temp=0. ตั้งค่าผ่าน `.env` (ดู `rag/ingest_ocr.py`) |
| ดึง text layer / render หน้า | **PyMuPDF** (`pymupdf`) |
| Normalize ไทย | ตาราง remap PUA F700–F71A + `unicodedata.normalize("NFC")` + `pythainlp.util.normalize` |
| ตัดคำไทย | **PyThaiNLP** `newmm` |
| Embedding | **BGE-M3** (`FlagEmbedding`) — ใช้ dense vector; โมเดลเดียวกันทั้ง index และ query |
| Vector DB | **Chroma** (persistent local) |
| Keyword search | **`rank_bm25`** (Chroma ไม่มี sparse ในตัว — ทำ hybrid เองตามข้างล่าง) |
| Rerank (ถ้ามีเวลา) | **BGE-reranker-v2-m3** |
| LLM ตอบคำถาม | **OpenThaiGPT** (ทีม AI ต่อ; RAG ส่งแค่ context) |
| Backend | **Python เพียวๆ + FastAPI** — ไม่ใช้ LangChain/LlamaIndex เขียนตรงๆ ให้อ่านง่าย debug ง่าย |

## Pipeline (ingest ทำครั้งเดียว offline → เสิร์ฟด้วย FastAPI)

### 1) Ingestion — แยกจัดการรายหน้า

สำหรับแต่ละหน้าของแต่ละ PDF:

- **ตรวจชนิดหน้า:** มีภาพขนาด >800×1200 px หรือ text ที่ extract ได้ <100 ตัวอักษร → "หน้าภาพ"; นอกนั้น → "หน้า text"
- **หน้าภาพ:** render ด้วย PyMuPDF ที่ **dpi ≥ 200** → ส่งเข้า Typhoon OCR → ได้ Markdown (ตารางต้องรอดเป็น Markdown table)
- **หน้า text:** extract ด้วย PyMuPDF → นับอักขระช่วง `U+F700–U+F71A`; ถ้าพบ ให้ remap เป็น Unicode ไทยจริงด้วยตารางแปลง (mai ek/tho/tri/chattawa และสระตำแหน่งพิเศษ) → ถ้า remap แล้วยังผิดปกติ (เช็คด้วยสุ่มเทียบกับภาพ) ให้ถอยไปใช้ OCR ทั้งหน้าแทน
- **Cache ผลลัพธ์** เป็นไฟล์ .md ต่อหน้า (`data/extracted/{doc}/{page:03d}.md`) — จะได้ไม่ต้อง OCR ซ้ำเวลาแก้ขั้นถัดไป

### 2) Cleaning

- ตัด header/footer ที่ซ้ำทุกหน้า: `"มคอ.2"`, `"วท.บ.(เทคโนโลยีสารสนเทศ) สาขาวิชาเทคโนโลยีสารสนเทศ คณะเทคโนโลยีสารสนเทศ สจล."`, เลขหน้า — ถ้าไม่ตัดจะ dilute ทุก chunk
- `NFC` + `pythainlp.util.normalize` ทุกข้อความ (หลัง remap PUA แล้ว)
- คงรหัสวิชา (เช่น `06016301`, `90642072`) และชื่ออังกฤษไว้ตามต้นฉบับเป๊ะๆ

### 3) Chunking — structure-aware

- ตัดตามโครงสร้างเอกสารก่อนเสมอ: หมวด → หัวข้อ → ย่อหน้า ห้ามตัดด้วยจำนวนตัวอักษรดิบ
- **1 รายวิชา = 1 chunk สมบูรณ์ในตัว:** รหัสวิชา + ชื่อไทย + ชื่ออังกฤษ + หน่วยกิต + คำอธิบายรายวิชา (นี่คือ chunk ที่มีค่าที่สุดของระบบ)
- ตารางเก็บเป็น Markdown table ทั้งก้อน ห้ามตัดกลางตาราง
- chunk ทั่วไป ~300–500 token, overlap 10–15%, ใช้ `newmm` หา boundary ไม่ตัดกลางคำไทย
- **metadata ทุก chunk:** `{doc_name, doc_type(หลักสูตร|ศึกษาทั่วไป|ประกาศ), section, page_label(เลขหน้าที่พิมพ์บนกระดาษ ไม่ใช่ index PDF), course_code?}`

### 4) Index

- embed ด้วย BGE-M3 → เก็บลง Chroma (persistent) พร้อมข้อความต้นฉบับ + metadata
- สร้าง BM25 index คู่ขนานจากข้อความที่ตัดคำด้วย `newmm` แล้ว (`rank_bm25.BM25Okapi`) — serialize เก็บไว้โหลดตอนรัน server

### 5) Retrieval — hybrid บังคับ ห้ามใช้ vector เดี่ยว

เหตุผล: คำถามนักศึกษามีรหัสวิชา/ชื่อเฉพาะ (`06016301`, ชื่ออาจารย์, ชื่อทุน) ที่ BM25 จับแม่นกว่า vector; คำถามความหมายกว้าง ("ค่าเทอมเท่าไหร่" → "อัตราค่าธรรมเนียม") vector จับแม่นกว่า

- query → (a) BGE-M3 dense ค้น Chroma top-20 (b) ตัดคำ query ด้วย `newmm` → BM25 top-20
- รวมสองลิสต์ด้วย **RRF**: `score(d) = Σ 1/(60 + rank_i(d))`
- (ถ้ามีเวลา) rerank top-20 ด้วย BGE-reranker-v2-m3 → ส่งจริง **top 3–5**
- ถ้า query มี pattern รหัสวิชา (`\d{8}`) ให้ boost/filter chunk ที่ `course_code` ตรง

### 6) ส่งต่อให้ LLM + Citation

FastAPI endpoint เดียว ตกลงกับทีมแล้ว:

```
POST /query  {"question": str}
→ {"answer": str, "citations": [{"doc": str, "page": int}], "chunks": [{"text": str, "doc": str, "page": int, "score": float}]}
```

- prompt ที่ส่งให้ OpenThaiGPT ต้อง **grounded**: "ตอบจากข้อมูลอ้างอิงด้านล่างเท่านั้น ถ้าข้อมูลไม่เพียงพอให้ตอบว่า 'ไม่พบข้อมูลนี้ในเอกสาร' ห้ามคาดเดา ตอบเป็นภาษาไทย"
- citation ต่อท้ายคำตอบเสมอ: `อ้างอิง: {doc_name} หน้า {page_label}` — ใช้ page_label จาก metadata
- ระวัง context window: token ภาษาไทยกินมากกว่าอังกฤษ ~2-3 เท่า อย่ายัด chunk เกิน

### 7) Evaluation (ทำก่อนเดโม — จุดขายกับกรรมการ)

- สร้าง golden set 20–30 คำถามจริง (รหัสวิชา, หน่วยกิต, โครงสร้างหลักสูตร, ค่าธรรมเนียม, ชื่ออาจารย์) พร้อมเฉลย + หน้าอ้างอิง
- วัด: retrieval hit-rate@5 (chunk ถูกต้องติด top-5 ไหม) และความถูกต้องคำตอบ
- ทุกครั้งที่แก้ pipeline ให้รัน eval ซ้ำ — ห้ามจูนด้วยความรู้สึก

## Do / Don't

- ✅ เปิดไฟล์ extract แล้วอ่านด้วยตาเทียบกับ PDF จริงก่อนเชื่อว่าสะอาด
- ✅ ingest ครั้งเดียว cache ทุกขั้น — แก้ขั้นหลังไม่ต้องรื้อขั้นหน้า
- ✅ ใช้ embedding โมเดลเดียวกันทั้ง index และ query
- ❌ ห้ามใช้ PyPDFLoader/pdfminer ดูดข้อความตรงๆ โดยไม่ผ่านขั้นตรวจ PUA/หน้าภาพ
- ❌ ห้ามใช้ Tesseract เป็น OCR หลัก (ภาษาไทยอ่อนเกิน)
- ❌ ห้ามตัด chunk กลางตารางหรือกลางรายวิชา
- ❌ ห้ามให้ LLM ตอบโดยไม่มี context (ปิด fallback เป็นความรู้ทั่วไปของโมเดล)