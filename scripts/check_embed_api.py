#!/usr/bin/env python
"""Check a hosted embedding API before pointing the deployment at it.

    EMBED_API=openai EMBED_API_URL=https://api.cloudflare.com/client/v4/accounts/<ACCOUNT_ID>/ai/v1 \
    EMBED_API_KEY=<token> EMBED_MODEL=@cf/baai/bge-m3 uv run python scripts/check_embed_api.py

Embeds three probe questions through ``rag.remote_embedder.RemoteEmbedder`` (same env vars as the
server) and, when the local model is installed (``uv sync --extra local-embed``), compares each vector
with the local BGE-M3 one — cosine must be ~1.000 for the Chroma index to stay valid.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rag.remote_embedder import RemoteEmbedder

PROBES = ["หลักสูตร AIT เรียนกี่ปี", "06016317 คือวิชาอะไร", "What careers can DSBA graduates pursue?"]


def main() -> int:
    emb = RemoteEmbedder.from_env()
    if emb is None:
        print("EMBED_API is not set", file=sys.stderr)
        return 2
    print(f"remote: {emb.describe()}")
    t = time.perf_counter()
    remote = emb.encode(PROBES)["dense_vecs"]
    print(f"  {remote.shape} in {time.perf_counter() - t:.2f}s")
    try:
        from FlagEmbedding import BGEM3FlagModel
    except ImportError:
        print("local model not installed (uv sync --extra local-embed) — skipping the comparison; the API works.")
        return 0
    local = BGEM3FlagModel("BAAI/bge-m3").encode(PROBES, max_length=512, return_dense=True, return_sparse=False, return_colbert_vecs=False)["dense_vecs"]
    worst = 1.0
    for q, lv, rv in zip(PROBES, local, remote, strict=True):
        cos = float(np.dot(lv, rv) / (np.linalg.norm(lv) * np.linalg.norm(rv)))
        worst = min(worst, cos)
        print(f"  cos={cos:.4f}  {q}")
    print("OK: vectors match the local model" if worst > 0.999 else "MISMATCH: rebuild the index with this API (python scripts/build_index.py)")
    return 0 if worst > 0.999 else 1


if __name__ == "__main__":
    sys.exit(main())
