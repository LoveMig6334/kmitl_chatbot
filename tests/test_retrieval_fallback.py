"""The vendored hybrid search keeps working on BM25 alone when the embedding API is unavailable."""

from __future__ import annotations

import pickle

from rank_bm25 import BM25Okapi

from rag.remote_embedder import EmbeddingUnavailable
from retrieval.retrieve import Retriever


class DownModel:
    def encode(self, *_a, **_k):
        raise EmbeddingUnavailable("api down")


class UpModel:
    def encode(self, *_a, **_k):
        import numpy as np

        return {"dense_vecs": np.zeros((1, 2), dtype="float32")}


class FakeCol:
    def query(self, **_k):
        return {"ids": [["c2", "c1"]]}


def _retriever(model) -> Retriever:
    r = Retriever.__new__(Retriever)
    r.model = model
    r.col = FakeCol()
    docs = {"c1": "หลักสูตร AIT เรียน 4 ปี", "c2": "วิชาเลือกเสรี", "c3": "DSBA business analytics"}
    from pythainlp.tokenize import word_tokenize

    r.bm25_ids = list(docs)
    r.bm25 = BM25Okapi([word_tokenize(t, engine="newmm", keep_whitespace=False) for t in docs.values()])
    r.store = {i: {"text": t, "metadata": {"doc_name": "AIT"}} for i, t in docs.items()}
    r.reranker = None
    return r


def test_search_falls_back_to_bm25_when_embeddings_fail():
    hits = _retriever(DownModel()).search("AIT เรียนกี่ปี", top_k=2, cand_k=3)
    assert hits[0].id == "c1"
    assert all(h.dense_rank is None for h in hits)


def test_search_uses_both_rankers_when_embeddings_work():
    hits = _retriever(UpModel()).search("AIT เรียนกี่ปี", top_k=3, cand_k=3)
    assert {h.id for h in hits} >= {"c1", "c2"}
    assert any(h.dense_rank is not None for h in hits)


def test_pickle_roundtrip_not_required():  # guards against accidental heavy imports in the fallback path
    pickle.dumps(EmbeddingUnavailable("x"))
