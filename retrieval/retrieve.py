"""
retrieve.py — Hybrid retrieval (ตาม skill.md ขั้น Retrieval)

query →
  (a) BGE-M3 dense ค้น Chroma top-K
  (b) ตัดคำ newmm → BM25 top-K
รวมสองลิสต์ด้วย **RRF**: score(d) = Σ 1/(RRF_K + rank_i(d))
ถ้า query มี pattern รหัสวิชา (\\d{8}) → boost chunk ที่ course_code ตรง
(ถ้าเปิด) rerank top-N ด้วย BGE-reranker-v2-m3 → ส่งจริง top 3-5

ห้ามใช้ vector เดี่ยว: คำถามมีรหัสวิชา/ชื่อเฉพาะ BM25 จับแม่นกว่า;
คำถามความหมายกว้าง vector จับแม่นกว่า

ใช้:
    python rag/retrieve.py "ค่าธรรมเนียมเท่าไหร่"
    python rag/retrieve.py "06016429 คือวิชาอะไร" --k 5
    RERANK=1 python rag/retrieve.py "..."       # เปิด reranker (โหลดโมเดลเพิ่ม)
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import re
import sys
from dataclasses import dataclass
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

# ---- config ----
CHROMA_DIR = os.getenv("CHROMA_DIR", "data/chroma")
COLLECTION = os.getenv("CHROMA_COLLECTION", "it_kmitl")
BM25_PATH = os.getenv("BM25_PATH", "data/bm25.pkl")
CHUNKS_PATH = os.getenv("CHUNKS_PATH", "data/chunks/all.jsonl")
RERANK_MODEL = os.getenv("RERANK_MODEL", "BAAI/bge-reranker-v2-m3")

CAND_K = int(os.getenv("RETRIEVE_CAND_K", "20"))   # ดึงมาผสมชั้นละกี่ตัว
RRF_K = int(os.getenv("RRF_K", "60"))              # ค่าคงที่ RRF
TOP_K = int(os.getenv("RETRIEVE_TOP_K", "5"))      # ส่งจริงกี่ตัว
CODE_BOOST = float(os.getenv("CODE_BOOST", "1.0")) # โบนัส RRF เมื่อ course_code ตรง
USE_RERANK = os.getenv("RERANK", "0") == "1"

CODE_RE = re.compile(r"\d{8}")


@dataclass
class Hit:
    id: str
    text: str
    metadata: dict
    score: float
    dense_rank: int | None = None
    bm25_rank: int | None = None


class Retriever:
    def __init__(self, use_rerank: bool = USE_RERANK):
        from rag.index import load_embedder
        import chromadb

        print("โหลด index...", file=sys.stderr)
        self.model = load_embedder()
        self.col = chromadb.PersistentClient(path=CHROMA_DIR).get_collection(COLLECTION)
        with open(BM25_PATH, "rb") as f:
            bm = pickle.load(f)
        self.bm25, self.bm25_ids = bm["bm25"], bm["ids"]
        # chunk store (id -> {text, metadata}) สำหรับ lookup ผล BM25
        self.store: dict[str, dict] = {}
        with open(CHUNKS_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    c = json.loads(line)
                    self.store[c["id"]] = c

        self.reranker = None
        if use_rerank:
            from FlagEmbedding import FlagReranker
            print(f"โหลด reranker {RERANK_MODEL}...", file=sys.stderr)
            self.reranker = FlagReranker(RERANK_MODEL, use_fp16=True)

    # ---- ชั้น dense ----
    def _dense(self, query: str, k: int) -> list[str]:
        qv = self.model.encode([query], max_length=512, return_dense=True,
                               return_sparse=False, return_colbert_vecs=False)["dense_vecs"][0]
        res = self.col.query(query_embeddings=[qv.tolist()], n_results=k)
        return res["ids"][0]

    # ---- ชั้น sparse ----
    def _bm25(self, query: str, k: int) -> list[str]:
        from pythainlp.tokenize import word_tokenize
        toks = word_tokenize(query, engine="newmm", keep_whitespace=False)
        scores = self.bm25.get_scores(toks)
        top = sorted(range(len(scores)), key=lambda i: -scores[i])[:k]
        return [self.bm25_ids[i] for i in top]

    # ---- RRF ----
    @staticmethod
    def _rrf(dense_ids: list[str], bm25_ids: list[str], k: int) -> dict[str, float]:
        score: dict[str, float] = {}
        for rank, _id in enumerate(dense_ids, 1):
            score[_id] = score.get(_id, 0.0) + 1.0 / (k + rank)
        for rank, _id in enumerate(bm25_ids, 1):
            score[_id] = score.get(_id, 0.0) + 1.0 / (k + rank)
        return score

    def search(self, query: str, top_k: int = TOP_K, cand_k: int = CAND_K) -> list[Hit]:
        dense_ids = self._dense(query, cand_k)
        bm25_ids = self._bm25(query, cand_k)
        fused = self._rrf(dense_ids, bm25_ids, RRF_K)

        # boost รหัสวิชา: ถ้า query มี \d{8} และ chunk มี course_code ตรง → บวกโบนัส
        codes = set(CODE_RE.findall(query))
        if codes:
            for _id in fused:
                cc = self.store.get(_id, {}).get("metadata", {}).get("course_code")
                if cc and cc in codes:
                    fused[_id] += CODE_BOOST
            # เผื่อ chunk รหัสตรงไม่ติด candidate ทั้ง 2 ชั้น → ดึงเข้ามาด้วย
            for _id, c in self.store.items():
                if c.get("metadata", {}).get("course_code") in codes and _id not in fused:
                    fused[_id] = CODE_BOOST

        d_rank = {_id: i + 1 for i, _id in enumerate(dense_ids)}
        b_rank = {_id: i + 1 for i, _id in enumerate(bm25_ids)}
        ranked = sorted(fused.items(), key=lambda kv: -kv[1])

        # rerank (ถ้าเปิด) จาก candidate ที่ผสมแล้ว top-N
        if self.reranker is not None and ranked:
            cand = [i for i, _ in ranked[:cand_k]]
            pairs = [[query, self.store[i]["text"]] for i in cand]
            rs = self.reranker.compute_score(pairs, normalize=True)
            rs = rs if isinstance(rs, list) else [rs]
            order = sorted(range(len(cand)), key=lambda j: -rs[j])
            ranked = [(cand[j], rs[j]) for j in order] + \
                     [(i, s) for i, s in ranked[cand_k:]]

        hits: list[Hit] = []
        for _id, sc in ranked[:top_k]:
            c = self.store.get(_id, {})
            hits.append(Hit(id=_id, text=c.get("text", ""),
                            metadata=c.get("metadata", {}), score=float(sc),
                            dense_rank=d_rank.get(_id), bm25_rank=b_rank.get(_id)))
        return hits


def main() -> int:
    ap = argparse.ArgumentParser(description="Hybrid retrieval (dense+BM25+RRF+code boost)")
    ap.add_argument("query")
    ap.add_argument("--k", type=int, default=TOP_K)
    ap.add_argument("--rerank", action="store_true", help="เปิด BGE-reranker-v2-m3")
    args = ap.parse_args()

    r = Retriever(use_rerank=args.rerank or USE_RERANK)
    hits = r.search(args.query, top_k=args.k)
    print(f"\nQ: {args.query}\n{'='*70}")
    for i, h in enumerate(hits, 1):
        m = h.metadata
        tag = f"dense#{h.dense_rank}" if h.dense_rank else ""
        tag += f" bm25#{h.bm25_rank}" if h.bm25_rank else ""
        cc = m.get("course_code", "")
        print(f"\n{i}. [{h.score:.4f}] {m.get('doc_name')} p.{m.get('page_label','?')} "
              f"{cc} ({m.get('chunk_type')}) {tag}")
        print("   " + h.text[:200].replace("\n", " "))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
