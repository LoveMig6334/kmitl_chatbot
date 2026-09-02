#!/usr/bin/env python
"""Audit the vendored retrieval chunks (``retrieval/data/chunks/all.jsonl``).

Per ``doc_name``: chunk count, % with ``page_label``, % with ``page_index > 0``,
% with a *usable* page (either of those), % with ``course_code``, text length
min / median / p95 / max, and a few sample chunks.  Exit code 1 when any doc has
usable-page coverage below ``--min-usable`` (default 90 %) — user-facing
citations say "หน้า X", so missing pages are a blocker, not a nuisance.

    python scripts/audit_retrieval_chunks.py
    python scripts/audit_retrieval_chunks.py --chunks path/to/other.jsonl --samples 2
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHUNKS = ROOT / "retrieval" / "data" / "chunks" / "all.jsonl"


def load(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def has_label(meta: dict) -> bool:
    return meta.get("page_label") not in (None, "", 0)


def has_index(meta: dict) -> bool:
    return (meta.get("page_index") or 0) > 0


def pct(n: int, d: int) -> str:
    return f"{100.0 * n / d:5.1f}%" if d else "  n/a"


def p95(values: list[int]) -> int:
    s = sorted(values)
    return s[min(len(s) - 1, round(0.95 * (len(s) - 1)))] if s else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS)
    ap.add_argument("--samples", type=int, default=5)
    ap.add_argument("--min-usable", type=float, default=90.0, help="fail below this usable-page %% for any doc")
    args = ap.parse_args()

    rows = load(args.chunks)
    by_doc: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_doc[r["metadata"].get("doc_name", "?")].append(r)
    ids = [r["id"] for r in rows]
    dup = len(ids) - len(set(ids))

    print(f"{args.chunks}  —  {len(rows)} chunks, {len(by_doc)} docs, duplicate ids: {dup}")
    print(f"{'doc_name':<14}{'chunks':>7}{'label':>8}{'index>0':>9}{'usable':>8}{'course':>8}{'len min':>9}{'median':>8}{'p95':>7}{'max':>7}")
    failed = False
    for doc, rs in sorted(by_doc.items()):
        n = len(rs)
        label = sum(has_label(r["metadata"]) for r in rs)
        index = sum(has_index(r["metadata"]) for r in rs)
        usable = sum(has_label(r["metadata"]) or has_index(r["metadata"]) for r in rs)
        course = sum(bool(r["metadata"].get("course_code")) for r in rs)
        lens = [len(r["text"]) for r in rs]
        usable_pct = 100.0 * usable / n
        flag = "" if usable_pct >= args.min_usable else "   <-- below threshold"
        failed = failed or bool(flag)
        print(f"{doc:<14}{n:>7}{pct(label, n):>8}{pct(index, n):>9}{pct(usable, n):>8}{pct(course, n):>8}"
              f"{min(lens):>9}{int(statistics.median(lens)):>8}{p95(lens):>7}{max(lens):>7}{flag}")
    print("chunk_type:", dict(Counter(r["metadata"].get("chunk_type") for r in rows)))
    no_page = [r["id"] for r in rows if not (has_label(r["metadata"]) or has_index(r["metadata"]))]
    print(f"chunks without a usable page: {len(no_page)}  e.g. {no_page[:6]}")

    if args.samples:
        for doc, rs in sorted(by_doc.items()):
            print(f"\n=== {doc}: {args.samples} samples (evenly spaced) ===")
            step = max(1, len(rs) // args.samples)
            for r in rs[::step][: args.samples]:
                m = r["metadata"]
                print(f"- {r['id']}  page_label={m.get('page_label')} page_index={m.get('page_index')} "
                      f"section={m.get('section', '')[:40]!r} course_code={m.get('course_code')}")
                print("    " + r["text"][:160].replace("\n", " ⏎ "))
    if failed:
        print(f"\nFAIL: usable-page coverage below {args.min_usable}% for at least one doc", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
