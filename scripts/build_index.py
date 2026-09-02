#!/usr/bin/env python
"""Build the vendored retrieval index (BGE-M3 -> Chroma, newmm -> BM25) with timings.

Thin wrapper around ``retrieval.index`` (teammate-owned): loads the embedder
once (timed separately — the first run downloads ~2.2 GB from Hugging Face),
reuses it for the dense build, then builds BM25, and reports on-disk sizes.

    python scripts/build_index.py                 # retrieval/data/chunks/all.jsonl -> retrieval/data/{chroma,bm25.pkl}
    python scripts/build_index.py --chunks other.jsonl --no-reset
Env overrides are the teammate's: CHROMA_DIR, CHROMA_COLLECTION, BM25_PATH, EMBED_MODEL, EMBED_BATCH, EMBED_MAX_LEN.
"""

from __future__ import annotations

import argparse
import resource
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from retrieval import index as ri


def dir_size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file()) if path.exists() else 0


def rss_mb() -> float:
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return rss / (1024 * 1024) if sys.platform == "darwin" else rss / 1024


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--chunks", default=str(ROOT / "retrieval" / "data" / "chunks" / "all.jsonl"))
    ap.add_argument("--no-reset", action="store_true", help="keep the existing Chroma collection (default: drop + rebuild)")
    ap.add_argument("--skip-dense", action="store_true")
    ap.add_argument("--skip-bm25", action="store_true")
    args = ap.parse_args()

    chunks = ri.load_chunks(args.chunks)
    print(f"=== build_index: {len(chunks)} chunks from {args.chunks} ===")
    print(f"    CHROMA_DIR={ri.CHROMA_DIR} collection={ri.COLLECTION} BM25_PATH={ri.BM25_PATH} model={ri.EMBED_MODEL}")
    timings: dict[str, float] = {}

    if not args.skip_dense:
        t0 = time.perf_counter()
        model = ri.load_embedder()
        timings["model_load_s"] = time.perf_counter() - t0
        print(f"[model] loaded in {timings['model_load_s']:.1f}s  (max RSS {rss_mb():.0f} MB)")
        ri.load_embedder = lambda: model  # reuse the loaded model inside build_dense_index (our wrapper only)
        t0 = time.perf_counter()
        ri.build_dense_index(chunks, reset=not args.no_reset)
        timings["dense_build_s"] = time.perf_counter() - t0
        print(f"[dense] built in {timings['dense_build_s']:.1f}s  (max RSS {rss_mb():.0f} MB)")
    if not args.skip_bm25:
        t0 = time.perf_counter()
        ri.build_bm25_index(chunks)
        timings["bm25_build_s"] = time.perf_counter() - t0
        print(f"[bm25] built in {timings['bm25_build_s']:.1f}s")

    chroma_mb = dir_size(Path(ri.CHROMA_DIR)) / 1e6
    bm25_mb = dir_size(Path(ri.BM25_PATH)) / 1e6
    print("=== summary ===")
    for k, v in timings.items():
        print(f"  {k:<14} {v:8.1f}")
    print(f"  chroma_dir_mb  {chroma_mb:8.1f}   ({ri.CHROMA_DIR})")
    print(f"  bm25_pkl_mb    {bm25_mb:8.1f}   ({ri.BM25_PATH})")
    print(f"  max_rss_mb     {rss_mb():8.0f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
