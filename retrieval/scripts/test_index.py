"""
test_index.py — ตรวจว่า index ใช้งานได้ (dense + BM25 แยกกัน)
ยังไม่ใช่ hybrid retrieval (นั่นคือขั้นถัดไป) — แค่พิสูจน์ว่า index คืนผลสมเหตุสมผล

ใช้:  python scripts/test_index.py
      python scripts/test_index.py "ค่าธรรมเนียมการศึกษาเท่าไหร่"
"""
from __future__ import annotations

import os
import pickle
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-m3")
CHROMA_DIR = os.getenv("CHROMA_DIR", "data/chroma")
COLLECTION = os.getenv("CHROMA_COLLECTION", "it_kmitl")
BM25_PATH = os.getenv("BM25_PATH", "data/bm25.pkl")

DEFAULT_QUERIES = [
    "ค่าธรรมเนียมการศึกษาเท่าไหร่",
    "06016301 คือวิชาอะไร",
    "หลักสูตรมีกี่หน่วยกิต",
    "วิชาการเขียนโปรแกรมเว็บ",
]


def main() -> int:
    queries = sys.argv[1:] or DEFAULT_QUERIES

    # โหลดโมเดล + index (ใช้ helper ตัวเดียวกับ index.py)
    import chromadb
    from pythainlp.tokenize import word_tokenize
    from rag.index import load_embedder

    model = load_embedder()

    client = chromadb.PersistentClient(path=CHROMA_DIR)
    col = client.get_collection(COLLECTION)
    print(f"Chroma: {col.count()} รายการ | ", end="")

    with open(BM25_PATH, "rb") as f:
        bm = pickle.load(f)
    bm25, ids = bm["bm25"], bm["ids"]
    print(f"BM25: {len(ids)} รายการ")

    for q in queries:
        print(f"\n{'='*70}\nQ: {q}\n{'='*70}")
        # dense
        qvec = model.encode([q], max_length=512, return_dense=True,
                            return_sparse=False, return_colbert_vecs=False)["dense_vecs"][0]
        res = col.query(query_embeddings=[qvec.tolist()], n_results=3)
        print("  [DENSE top-3]")
        for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
            code = meta.get("course_code", "")
            print(f"    ({1-dist:.3f}) {meta['doc_name']} p.{meta.get('page_label','?')} {code} | {doc[:70].strip()}")

        # bm25
        toks = word_tokenize(q, engine="newmm", keep_whitespace=False)
        scores = bm25.get_scores(toks)
        top = sorted(range(len(scores)), key=lambda i: -scores[i])[:3]
        print("  [BM25 top-3]")
        got = col.get(ids=[ids[i] for i in top])
        idmap = {m_id: (d, m) for m_id, d, m in zip(got["ids"], got["documents"], got["metadatas"])}
        for i in top:
            d, m = idmap.get(ids[i], ("", {}))
            code = m.get("course_code", "")
            print(f"    ({scores[i]:.2f}) {m.get('doc_name','?')} p.{m.get('page_label','?')} {code} | {d[:70].strip()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
