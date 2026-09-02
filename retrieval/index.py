"""
index.py — สร้าง index จาก chunks (ทำ offline ครั้งเดียว)

ตาม skill.md ขั้น Index:
- embed ทุก chunk ด้วย **BGE-M3** (dense) → เก็บลง **Chroma (persistent)** พร้อมข้อความ + metadata
- สร้าง **BM25 index** คู่ขนานจากข้อความที่ตัดคำด้วย **newmm** → serialize (pickle) ไว้โหลดตอนรัน server
- ใช้ embedding โมเดลเดียวกันทั้ง index และ query (สำคัญ!)

ใช้:
    python rag/index.py                         # index จาก data/chunks/all.jsonl
    python rag/index.py --chunks data/chunks/IT2565.jsonl --reset

ผลลัพธ์:
    data/chroma/                 Chroma persistent store (dense vectors + docs + metadata)
    data/bm25.pkl                BM25Okapi + ลำดับ ids (ตัดคำ newmm แล้ว)
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import sys
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# ---- config ----
EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-m3")
CHROMA_DIR = os.getenv("CHROMA_DIR", "data/chroma")
COLLECTION = os.getenv("CHROMA_COLLECTION", "it_kmitl")
BM25_PATH = os.getenv("BM25_PATH", "data/bm25.pkl")
EMBED_MAX_LEN = int(os.getenv("EMBED_MAX_LEN", "2048"))   # chunk ยาวสุด ~4.6k ตัวอักษร พอ
EMBED_BATCH = int(os.getenv("EMBED_BATCH", "16"))


def load_chunks(path: str) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def sanitize_meta(meta: dict) -> dict:
    """Chroma รับ metadata เป็น scalar (str/int/float/bool) เท่านั้น — ทิ้ง None, แปลงชนิด"""
    out = {}
    for k, v in meta.items():
        if v is None:
            continue
        if isinstance(v, (str, int, float, bool)):
            out[k] = v
        else:
            out[k] = str(v)
    return out


def load_embedder():
    """โหลด BGE-M3 แบบทนความต่างของ API FlagEmbedding แต่ละเวอร์ชัน (devices/device)"""
    from FlagEmbedding import BGEM3FlagModel
    try:
        import torch
        use_gpu = torch.cuda.is_available()
    except Exception:
        use_gpu = False
    dev = "cuda:0" if use_gpu else "cpu"
    print(f"  embedding: {EMBED_MODEL}  (device={dev}, fp16={use_gpu})")
    for kwargs in ({"use_fp16": use_gpu, "devices": dev},
                   {"use_fp16": use_gpu, "device": dev},
                   {"use_fp16": use_gpu}):
        try:
            return BGEM3FlagModel(EMBED_MODEL, **kwargs)
        except TypeError:
            continue
    return BGEM3FlagModel(EMBED_MODEL)


def build_dense_index(chunks: list[dict], reset: bool) -> None:
    """embed ด้วย BGE-M3 → เก็บลง Chroma persistent"""
    import chromadb

    model = load_embedder()

    texts = [c["text"] for c in chunks]
    t0 = time.time()
    out = model.encode(texts, batch_size=EMBED_BATCH, max_length=EMBED_MAX_LEN,
                       return_dense=True, return_sparse=False, return_colbert_vecs=False)
    dense = out["dense_vecs"]
    print(f"  embed {len(texts)} chunks เสร็จใน {time.time()-t0:.0f}s (dim={dense.shape[1]})")

    Path(CHROMA_DIR).mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    if reset:
        try:
            client.delete_collection(COLLECTION)
        except Exception:
            pass
    col = client.get_or_create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})

    # เพิ่มทีละ batch (Chroma จำกัดขนาด add ต่อครั้ง)
    B = 1000
    for i in range(0, len(chunks), B):
        sl = slice(i, i + B)
        col.upsert(
            ids=[c["id"] for c in chunks[sl]],
            embeddings=[dense[j].tolist() for j in range(i, min(i + B, len(chunks)))],
            documents=[c["text"] for c in chunks[sl]],
            metadatas=[sanitize_meta(c["metadata"]) for c in chunks[sl]],
        )
    print(f"  เก็บลง Chroma: {col.count()} รายการ @ {CHROMA_DIR} (collection='{COLLECTION}')")


def build_bm25_index(chunks: list[dict]) -> None:
    """ตัดคำ newmm ทุก chunk → BM25Okapi → pickle พร้อมลำดับ ids"""
    from pythainlp.tokenize import word_tokenize
    from rank_bm25 import BM25Okapi

    t0 = time.time()
    tokenized = [word_tokenize(c["text"], engine="newmm", keep_whitespace=False)
                 for c in chunks]
    bm25 = BM25Okapi(tokenized)
    ids = [c["id"] for c in chunks]

    Path(BM25_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(BM25_PATH, "wb") as f:
        pickle.dump({"bm25": bm25, "ids": ids}, f)
    print(f"  BM25: {len(ids)} chunks ตัดคำ+สร้าง index เสร็จใน {time.time()-t0:.0f}s -> {BM25_PATH}")


def main() -> int:
    ap = argparse.ArgumentParser(description="สร้าง dense (Chroma) + BM25 index จาก chunks")
    ap.add_argument("--chunks", default="data/chunks/all.jsonl")
    ap.add_argument("--reset", action="store_true", help="ลบ collection เดิมก่อน (สร้างใหม่หมด)")
    ap.add_argument("--skip-dense", action="store_true")
    ap.add_argument("--skip-bm25", action="store_true")
    args = ap.parse_args()

    chunks = load_chunks(args.chunks)
    print(f"=== Index: {len(chunks)} chunks จาก {args.chunks} ===")

    if not args.skip_dense:
        print("[1/2] Dense (BGE-M3 → Chroma)")
        build_dense_index(chunks, reset=args.reset)
    if not args.skip_bm25:
        print("[2/2] BM25 (newmm)")
        build_bm25_index(chunks)

    print("=== เสร็จ ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
