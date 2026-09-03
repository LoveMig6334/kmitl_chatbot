# ส่งมอบให้ทีม LLM/API — วิธีต่อกับส่วน RAG

ฝั่ง RAG (ดูดข้อมูล → ค้น) เปิดเป็น **HTTP API** ให้ทีมยิงเข้ามา
**เส้นแบ่งงาน:** ฝั่ง RAG คืน **context (chunks) + citations + prompt ที่ grounded แล้ว** →
ทีม LLM เอา `prompt` ไปยิง **OpenThaiGPT** เอง → ได้ `answer` → แสดงคู่กับ `citations`

> ฝั่ง RAG ไม่ยุ่งกับ LLM / ไม่ถือ key ของ LLM — แยกกันชัด

---

## รันเซิร์ฟเวอร์ RAG

```bash
# ครั้งแรก: ต้องมี index ก่อน (สร้างจาก chunks — ทำเสร็จแล้ว อยู่ที่ data/chroma + data/bm25.pkl)
#   ถ้า index หาย: python rag/index.py --reset

uvicorn rag.api:app --host 0.0.0.0 --port 8000
```

โหลดโมเดล BGE-M3 ครั้งเดียวตอน start (~15-20s) แล้วพร้อมรับ request

---

## Endpoint

### `GET /health`
```json
{"status": "ok", "indexed_chunks": 2358}
```

### `POST /search`  ← ตัวหลักที่ทีมเรียก
**Request** (JSON, UTF-8):
```json
{ "question": "06016429 คือวิชาอะไร", "top_k": 5 }
```
- `question` (required): คำถามภาษาไทย
- `top_k` (optional): จำนวน chunk ที่คืน (default 5)

**Response**:
```json
{
  "question": "06016429 คือวิชาอะไร",
  "chunks": [
    {
      "text": "06016429 การพัฒนาเว็บฝั่งไคลเอนต์ ...",
      "doc": "IT2565",
      "page": 338,
      "course_code": "06016429",
      "chunk_type": "course",
      "score": 1.0164
    }
  ],
  "citations": [ {"doc": "IT2565", "page": 338} ],
  "prompt": "ตอบคำถามจากข้อมูลอ้างอิงด้านล่างเท่านั้น ... ===== คำถาม ===== ... ===== คำตอบ ====="
}
```

| field | ใช้ทำอะไร |
|---|---|
| `prompt` | **ส่งเข้า OpenThaiGPT ตรงๆ** ได้เลย (grounded + มี context + citation กำกับ) → ได้ `answer` |
| `citations` | เอาไปแสดงต่อท้ายคำตอบ: "อ้างอิง: {doc} หน้า {page}" |
| `chunks` | context ดิบ (เผื่อทีมอยากประกอบ prompt เอง / แสดง source) |

> `page` เป็น `null` ได้บางกรณี (หน้าที่ OCR ไม่ได้เลขหน้าพิมพ์) — จัดการเป็น "ไม่ระบุหน้า"

---

## ตัวอย่างฝั่งทีม (pseudo)

```python
import requests
r = requests.post("http://<rag-host>:8000/search",
                  json={"question": user_question}).json()

# ยิง prompt เข้า OpenThaiGPT (LLM ของทีม)
answer = openthaigpt(r["prompt"])

# แสดงคำตอบ + อ้างอิง
cites = " ; ".join(f"{c['doc']} หน้า {c['page']}" for c in r["citations"])
show(f"{answer}\n\nอ้างอิง: {cites}")
```

---

## หมายเหตุสำคัญ (ตาม skill.md)

- `prompt` สั่งให้ LLM **ตอบจาก context เท่านั้น** ถ้าไม่พอให้ตอบ "ไม่พบข้อมูลนี้ในเอกสาร" — อย่าถอด guard นี้ (กัน LLM มั่ว)
- token ภาษาไทยกินมากกว่าอังกฤษ ~2-3 เท่า — ถ้า context ยาวไป ลด `top_k`
- ปรับพฤติกรรม retrieval ได้ผ่าน env โดยไม่แก้โค้ด (ดู `.env.example`: `RETRIEVE_TOP_K`, `RRF_K`, `CODE_BOOST`, `RERANK`)
- ถ้าอยากเปิด reranker (แม่นขึ้น แลกความเร็ว/RAM): ตั้ง `RERANK=1` ก่อนรัน (โหลดโมเดลเพิ่ม ~2.3GB ครั้งแรก)
