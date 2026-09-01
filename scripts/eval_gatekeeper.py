#!/usr/bin/env python
"""Evaluate the gatekeeper against ``tests/eval_questions.csv``.

Examples::

    python scripts/eval_gatekeeper.py                 # full run (LLM enabled)
    python scripts/eval_gatekeeper.py --level easy    # only easy rows
    python scripts/eval_gatekeeper.py --dry-run       # rule layer only, 0 API calls
    python scripts/eval_gatekeeper.py --model typhoon-s-thaillm-8b-instruct

The CSV is tab-separated with columns ``question``, ``type``, ``level`` and an
optional ``expected_category`` override.  ``type`` maps to a category via
``TYPE_TO_CATEGORY`` below.  Append rows to add cases.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gatekeeper import GateDecision, gate, load_settings
from gatekeeper.schema import CATEGORIES

TYPE_TO_CATEGORY = {
    "คำถามเกี่ยวกับคณะ": "in_scope",
    "คำถามภาษา": "in_scope",
    "คำถามทั่วไป": "off_topic_general",
    "คำถามนอกเหนือมหาลัย": "off_topic_other_university",
    "คำถามนอกเหนือหลักสูตร สจล.": "out_of_scope_kmitl",
    "คำถามเจาะระบบ": "injection_or_abuse",
}
DEFAULT_CSV = ROOT / "tests" / "eval_questions.csv"


def load_rows(path: Path, level: str | None) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        for i, row in enumerate(reader, start=2):
            q = (row.get("question") or "").strip()
            if not q:
                continue
            expected = (row.get("expected_category") or "").strip() or TYPE_TO_CATEGORY.get((row.get("type") or "").strip())
            if expected not in CATEGORIES:
                print(f"! line {i}: unknown type/expected_category {row.get('type')!r} — skipped", file=sys.stderr)
                continue
            lvl = (row.get("level") or "").strip() or "easy"
            if level and lvl != level:
                continue
            rows.append({"line": i, "question": q, "type": row.get("type", ""), "level": lvl, "expected": expected})
    return rows


async def run_all(rows: list[dict], *, dry_run: bool, settings, concurrency: int) -> list[dict]:
    sem = asyncio.Semaphore(concurrency)

    async def one(row: dict) -> dict:
        dbg: dict = {}
        async with sem:
            t0 = time.perf_counter()
            decision: GateDecision = await gate(row["question"], settings=settings, use_llm=not dry_run, debug=dbg)
            wall = (time.perf_counter() - t0) * 1000
        return {**row, "decision": decision, "debug": dbg, "wall_ms": wall}

    return await asyncio.gather(*(one(r) for r in rows))


def pct(n: int, d: int) -> str:
    return f"{(100.0 * n / d):.1f}%" if d else "n/a"


def p95(values: list[float]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    return s[min(len(s) - 1, int(round(0.95 * (len(s) - 1))))]


def report(results: list[dict], *, show_all: bool) -> int:
    total = len(results)
    correct = sum(r["decision"].category == r["expected"] for r in results)
    by_cat_total: Counter = Counter(r["expected"] for r in results)
    by_cat_correct: Counter = Counter(r["expected"] for r in results if r["decision"].category == r["expected"])
    by_level_total: Counter = Counter(r["level"] for r in results)
    by_level_correct: Counter = Counter(r["level"] for r in results if r["decision"].category == r["expected"])
    confusion: dict[str, Counter] = defaultdict(Counter)
    for r in results:
        confusion[r["expected"]][r["decision"].category] += 1
    decided_by = Counter(r["decision"].decided_by for r in results)
    latencies = [r["decision"].latency_ms for r in results]
    llm_lat = [r["decision"].latency_ms for r in results if r["decision"].decided_by != "rule"]

    print("=" * 78)
    print("Per-category accuracy")
    for cat in CATEGORIES:
        if by_cat_total[cat]:
            print(f"  {cat:<28} {by_cat_correct[cat]:>3}/{by_cat_total[cat]:<3} {pct(by_cat_correct[cat], by_cat_total[cat])}")
    print("Per-level accuracy")
    for lvl in ("easy", "medium", "hard"):
        if by_level_total[lvl]:
            print(f"  {lvl:<28} {by_level_correct[lvl]:>3}/{by_level_total[lvl]:<3} {pct(by_level_correct[lvl], by_level_total[lvl])}")
    print()
    short = {c: c.replace("off_topic_", "ot_").replace("out_of_scope_", "oos_").replace("injection_or_abuse", "inject")[:10] for c in CATEGORIES}
    print("Confusion (rows = expected, cols = predicted)")
    print(f"  {'':<28}" + "".join(f"{short[c]:>11}" for c in CATEGORIES))
    for exp in CATEGORIES:
        if by_cat_total[exp]:
            print(f"  {exp:<28}" + "".join(f"{confusion[exp][pred]:>11}" for pred in CATEGORIES))
    print()
    print("Decided by: " + ", ".join(f"{k}={v}" for k, v in sorted(decided_by.items())))
    print(f"Latency (all):      mean {statistics.mean(latencies) if latencies else 0:.0f} ms, p95 {p95(latencies):.0f} ms")
    if llm_lat:
        print(f"Latency (LLM path): mean {statistics.mean(llm_lat):.0f} ms, p95 {p95(llm_lat):.0f} ms")
    print()
    print(f"Overall category accuracy: {pct(correct, total)} ({correct}/{total})")
    print("=" * 78)

    misses = [r for r in results if r["decision"].category != r["expected"]]
    rows_to_show = results if show_all else misses
    if rows_to_show:
        print("\nMISSES" if not show_all else "\nALL ROWS")
        for r in rows_to_show:
            d = r["decision"]
            flag = "OK  " if d.category == r["expected"] else "MISS"
            print("-" * 78)
            print(f"[{flag}] line {r['line']} ({r['level']}): {r['question']}")
            print(f"       expected={r['expected']}  got={d.category}  decided_by={d.decided_by}  conf={d.confidence}  lang={d.language}")
            print(f"       faculty={d.faculty} program={d.program} codes={d.course_codes} kind={d.question_kind} latency={d.latency_ms}ms")
            print(f"       rule_reason={r['debug'].get('rule_reason')}")
            for i, raw in enumerate(r["debug"].get("raw_outputs") or [], start=1):
                print(f"       raw[{i}]: {raw!r}")
            if d.direct_reply:
                print(f"       reply: {d.direct_reply}")
    return len(misses)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    ap.add_argument("--level", choices=["easy", "medium", "hard"], default=None)
    ap.add_argument("--dry-run", action="store_true", help="rule layer only (no API calls)")
    ap.add_argument("--model", default=None, help="ThaiLLM model id (default: GATEKEEPER_MODEL or project default)")
    ap.add_argument("--timeout", type=float, default=None, help="per-call timeout in seconds")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--show-all", action="store_true", help="print every row, not only misses")
    ap.add_argument("--strict", action="store_true", help="exit 1 if any row misses")
    args = ap.parse_args()

    rows = load_rows(args.csv, args.level)
    if not rows:
        print("no rows to evaluate", file=sys.stderr)
        return 2
    settings = load_settings(model=args.model, timeout_s=args.timeout)
    mode = "DRY RUN (rules only)" if args.dry_run else f"model={settings.model} timeout={settings.timeout_s}s"
    print(f"Evaluating {len(rows)} rows from {args.csv} [{mode}]")
    results = asyncio.run(run_all(rows, dry_run=args.dry_run, settings=settings, concurrency=args.concurrency))
    misses = report(results, show_all=args.show_all)
    return 1 if (args.strict and misses) else 0


if __name__ == "__main__":
    sys.exit(main())
