"""
api.py — FastAPI สำหรับส่งต่อให้ทีม (ฝั่ง RAG คืน context + citations)

เส้นแบ่งงาน (ตกลงกับทีม): ฝั่งเราทำ retrieval แล้วคืน **context + citations + prompt ที่ grounded**
ทีม LLM เอา `prompt` ไปยิง OpenThaiGPT เอง → ได้ answer → แสดงคู่กับ citations
(ฝั่งเราไม่ต้องรู้/ถือ key ของ LLM)

รัน:
    uvicorn rag.api:app --host 0.0.0.0 --port 8000
    # หรือ: python rag/api.py

Endpoints:
    GET  /health                      เช็คสถานะ + จำนวน chunk ใน index
    POST /search  {"question": str, "top_k"?: int}
         → {question, chunks:[...], citations:[{doc,page}], prompt}

ตัวอย่างยิง:
    curl -X POST localhost:8000/search -H "Content-Type: application/json" \
         -d '{"question":"06016429 คือวิชาอะไร"}'
"""
from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI
from pydantic import BaseModel, Field

from rag.retrieve import Retriever, TOP_K

# prompt grounded ตาม skill.md — ทีม LLM เอาไปยิง OpenThaiGPT ได้ตรงๆ
SYSTEM_INSTRUCT = (
    "ตอบคำถามจากข้อมูลอ้างอิงด้านล่างเท่านั้น "
    "ถ้าข้อมูลไม่เพียงพอให้ตอบว่า 'ไม่พบข้อมูลนี้ในเอกสาร' ห้ามคาดเดา "
    "ตอบเป็นภาษาไทย และอ้างอิงแหล่งที่มา (เอกสาร/หน้า) ต่อท้ายคำตอบเสมอ"
)

# โหลด Retriever ครั้งเดียวตอน start (แพงเพราะโหลดโมเดล) แล้ว reuse ทุก request
_state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    _state["retriever"] = Retriever()
    _state["ready"] = True
    yield
    _state.clear()


app = FastAPI(title="RAG — Chatbot คณะ IT KMITL", version="1.0", lifespan=lifespan)


class SearchRequest(BaseModel):
    question: str = Field(..., description="คำถามภาษาไทย")
    top_k: int | None = Field(None, description="จำนวน chunk ที่คืน (default 5)")


class ChunkOut(BaseModel):
    text: str
    doc: str
    page: int | None
    course_code: str | None = None
    chunk_type: str
    score: float


class Citation(BaseModel):
    doc: str
    page: int | None


class SearchResponse(BaseModel):
    question: str
    chunks: list[ChunkOut]
    citations: list[Citation]
    prompt: str


def _page_int(v) -> int | None:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def build_prompt(question: str, chunks: list[ChunkOut]) -> str:
    """ประกอบ prompt grounded พร้อมส่งเข้า LLM (context มี citation กำกับต่อ chunk)"""
    blocks = []
    for i, c in enumerate(chunks, 1):
        src = f"[{i}] ({c.doc} หน้า {c.page if c.page is not None else '-'})"
        blocks.append(f"{src}\n{c.text}")
    context = "\n\n".join(blocks)
    return (f"{SYSTEM_INSTRUCT}\n\n===== ข้อมูลอ้างอิง =====\n{context}\n\n"
            f"===== คำถาม =====\n{question}\n\n===== คำตอบ =====")


@app.get("/health")
def health():
    r: Retriever | None = _state.get("retriever")
    n = r.col.count() if r else 0
    return {"status": "ok" if _state.get("ready") else "loading", "indexed_chunks": n}


@app.post("/search", response_model=SearchResponse)
def search(req: SearchRequest):
    r: Retriever = _state["retriever"]
    hits = r.search(req.question, top_k=req.top_k or TOP_K)

    chunks = [
        ChunkOut(
            text=h.text,
            doc=h.metadata.get("doc_name", ""),
            page=_page_int(h.metadata.get("page_label")),
            course_code=h.metadata.get("course_code"),
            chunk_type=h.metadata.get("chunk_type", ""),
            score=round(h.score, 4),
        )
        for h in hits
    ]
    # citations: dedup (doc, page) ตามลำดับที่เจอ
    seen, citations = set(), []
    for c in chunks:
        key = (c.doc, c.page)
        if key not in seen:
            seen.add(key)
            citations.append(Citation(doc=c.doc, page=c.page))

    return SearchResponse(
        question=req.question,
        chunks=chunks,
        citations=citations,
        prompt=build_prompt(req.question, chunks),
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("rag.api:app", host="0.0.0.0",
                port=int(os.getenv("PORT", "8000")), reload=False)
