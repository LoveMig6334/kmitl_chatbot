#!/usr/bin/env python
"""Retrieval-only calibration for the chroma retriever (no LLM calls).

Runs every question of ``tests/eval_answers.jsonl`` through ``ChromaRetriever``
exactly the way ``RagAnswerer.retrieve`` would (per-program retrieval + interleave
for comparisons, ``programs`` from the case) and prints, per case: the raw RRF
top-1/top-3 scores, the normalised top-3, whether a gold chunk is in the top-k,
and the rank of the first gold chunk.  Then the distributions of the raw top-1
score for *answerable* vs *expect_not_found* cases, and the gold hit rate at k,
for every candidate threshold — the evidence behind ``RETRIEVAL_MIN_SCORE_CHROMA``.

Also reports process RSS before the model load and after the first query.

    python scripts/calibrate_retrieval.py
    python scripts/calibrate_retrieval.py --k 8 --rerank        # measure the reranker's cost separately
    RETRIEVE_CAND_K=40 python scripts/calibrate_retrieval.py    # any retrieval env var applies
"""

from __future__ import annotations

import argparse
import asyncio
import json
import resource
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rag.answerer import ALL_PROGRAMS, interleave
from rag.chroma_retriever import ChromaRetriever
from rag.retriever import Chunk

DEFAULT_CASES = ROOT / "tests" / "eval_answers.jsonl"


def rss_mb() -> float:
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return rss / (1024 * 1024) if sys.platform == "darwin" else rss / 1024


def load_cases(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


async def retrieve_like_answerer(r: ChromaRetriever, question: str, programs: list[str], kind: str | None, k: int) -> list[Chunk]:
    if kind == "comparison":
        targets = programs if len(programs) >= 2 else ALL_PROGRAMS
        per = max(2, k // len(targets))
        groups = await asyncio.gather(*(r.retrieve(question, [p], per) for p in targets))
        return interleave(list(groups), k)
    return await r.retrieve(question, programs, k)


def fmt(v: float | None) -> str:
    return "   -  " if v is None else f"{v:6.4f}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    ap.add_argument("--k", type=int, default=8)
    ap.add_argument("--rerank", action="store_true")
    ap.add_argument("--json", type=Path, default=None, help="dump per-case rows")
    args = ap.parse_args()

    cases = load_cases(args.cases)
    print(f"RSS before load: {rss_mb():.0f} MB")
    r = ChromaRetriever(use_rerank=args.rerank)
    t0 = time.perf_counter()
    r.warm_up()
    print(f"model + index loaded in {time.perf_counter() - t0:.1f}s (rerank={args.rerank}); RSS {rss_mb():.0f} MB")

    rows = []
    print(f"\n{'case':<24}{'kind':<12}{'raw@1':>8}{'raw@3':>8}{'norm@3':>8}{'gold@k':>8}{'rank':>6}{'ms':>7}  top-3 ids")
    for case in cases:
        t0 = time.perf_counter()
        chunks = asyncio.run(retrieve_like_answerer(r, case["question"], case.get("programs", []), case.get("question_kind"), args.k))
        ms = (time.perf_counter() - t0) * 1000
        if not rows:
            print(f"RSS after first query: {rss_mb():.0f} MB")
        raws = [c.debug.get("raw_score", 0.0) for c in chunks]
        norms = [c.score for c in chunks]
        gold = set(case.get("gold_chunk_ids", []))
        ids = [c.chunk_id for c in chunks]
        rank = next((i + 1 for i, cid in enumerate(ids) if cid in gold), None)
        row = {
            "id": case["id"], "nf": bool(case.get("expect_not_found")), "kind": case.get("question_kind"),
            "raw1": raws[0] if raws else None, "raw3": raws[2] if len(raws) > 2 else None,
            "norm3": norms[2] if len(norms) > 2 else None, "gold_hit": bool(gold & set(ids)) if gold else None,
            "gold_rank": rank, "ms": ms, "ids": ids, "raws": raws,
        }
        rows.append(row)
        label = "NOT-FOUND" if row["nf"] else (row["kind"] or "?")
        hit = "  n/a " if row["gold_hit"] is None else ("  yes " if row["gold_hit"] else "  NO  ")
        print(f"{case['id']:<24}{label:<12}{fmt(row['raw1']):>8}{fmt(row['raw3']):>8}{fmt(row['norm3']):>8}{hit:>8}"
              f"{rank or '-'!s:>6}{ms:7.0f}  {', '.join(ids[:3])}")

    ans = [x["raw1"] for x in rows if not x["nf"] and x["raw1"] is not None]
    nf = [x["raw1"] for x in rows if x["nf"] and x["raw1"] is not None]
    print("\nraw top-1 RRF score — answerable: " + (f"min {min(ans):.4f} median {statistics.median(ans):.4f} max {max(ans):.4f} (n={len(ans)})" if ans else "n/a"))
    print("raw top-1 RRF score — not-found : " + (f"min {min(nf):.4f} median {statistics.median(nf):.4f} max {max(nf):.4f} (n={len(nf)})" if nf else "n/a"))
    with_gold = [x for x in rows if x["gold_hit"] is not None]
    if with_gold:
        hits = sum(1 for x in with_gold if x["gold_hit"])
        print(f"gold hit rate @k={args.k}: {hits}/{len(with_gold)} ({100 * hits / len(with_gold):.0f}%); "
              f"gold ranks: {sorted(x['gold_rank'] for x in with_gold if x['gold_rank'])}")
    thresholds = sorted({round(v, 4) for v in ans + nf})
    print(f"\n{'raw threshold':>14}{'answerable kept':>17}{'not-found refused':>19}")
    for t in thresholds:
        kept = sum(1 for v in ans if v >= t)
        refused = sum(1 for v in nf if v < t)
        print(f"{t:>14.4f}{kept:>9}/{len(ans):<7}{refused:>10}/{len(nf):<8}")
    lat = [x["ms"] for x in rows]
    print(f"\nretrieval latency: mean {statistics.mean(lat):.0f} ms, max {max(lat):.0f} ms (k={args.k}, rerank={args.rerank}); RSS now {rss_mb():.0f} MB")
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"wrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
