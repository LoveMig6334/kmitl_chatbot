#!/usr/bin/env python
"""Audit ``tests/fixtures/chunks.jsonl`` for Thai PDF-extraction damage.

Reports per program: chunk count, mean/max length, fact-type coverage; and
overall the share of chunks with suspicious Unicode — combining marks that do
not follow a base consonant (สระลอย), left-over private-use codepoints,
decomposed ำ, doubled marks, a mark ratio far below normal Thai text (dropped
vowels), header/footer leakage.  Prints the 5 worst chunks.

Usage::

    python scripts/audit_fixtures.py
    python scripts/audit_fixtures.py --sample 10   # also print 10 random chunks per program
    python scripts/audit_fixtures.py --strict      # exit 1 if any chunk is suspicious
"""

from __future__ import annotations

import argparse
import json
import random
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATH = ROOT / "tests" / "fixtures" / "chunks.jsonl"

MARKS = "ัิีึืุู็่้๊๋์ํ"
TONES = "่้๊๋"
CONSONANT = "ก-ฮ"
# a mark that is not preceded by a consonant, a vowel mark (tone after vowel) or another mark
FLOATING_MARK = re.compile(rf"(?<![{CONSONANT}{MARKS}])[{MARKS}]")
DOUBLE_MARK = re.compile(rf"([{MARKS}])\1")
PUA = re.compile(f"[{chr(0xE000)}-{chr(0xF8FF)}]")  # private use area (built with chr so editors cannot strip it)
DECOMPOSED_AM = re.compile(r"ํา")
HEADER_LEAK = re.compile(r"วท\.บ\.\s*\(.*คณะเทคโนโลยีสารสนเทศ|^\s*มคอ\.?\s*2\s*$|^\s*รายละเอียดหลักสูตร\s*$", re.MULTILINE)
THAI = re.compile(r"[฀-๿]")
REQUIRED_FACTS = ("name_degree", "curriculum_year", "credits_total", "duration", "opening", "careers", "admission", "plan_y1s1", "course_desc")
LOW_MARK_RATIO = 0.08  # clean Thai prose sits around 0.14–0.20; below this vowels were dropped


def mark_ratio(text: str) -> float:
    thai = len(THAI.findall(text))
    return sum(1 for ch in text if ch in MARKS) / thai if thai else 0.0


def suspicious(text: str) -> list[str]:
    problems: list[str] = []
    if m := FLOATING_MARK.findall(text):
        problems.append(f"floating marks ×{len(m)}")
    if m := DOUBLE_MARK.findall(text):
        problems.append(f"doubled marks ×{len(m)}")
    if m := PUA.findall(text):
        problems.append(f"PUA codepoints ×{len(m)}")
    if DECOMPOSED_AM.search(text):
        problems.append("decomposed ำ")
    if HEADER_LEAK.search(text):
        problems.append("header/footer leaked")
    r = mark_ratio(text)
    if len(THAI.findall(text)) > 80 and r < LOW_MARK_RATIO:
        problems.append(f"low mark ratio {r:.3f} (dropped vowels?)")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--path", type=Path, default=DEFAULT_PATH)
    ap.add_argument("--sample", type=int, default=0, help="print N random chunks per program for eyeballing")
    ap.add_argument("--worst", type=int, default=5)
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    rows = [json.loads(line) for line in args.path.open(encoding="utf-8") if line.strip()]
    by_prog: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_prog[r["program"]].append(r)
    print(f"{len(rows)} chunks in {args.path.relative_to(ROOT)}  synthetic={Counter(bool(r.get('synthetic')) for r in rows)}")
    print(f"{'program':<8}{'chunks':>7}{'mean_len':>10}{'max_len':>9}{'mark_ratio':>12}  fact coverage (missing)")
    for prog in ("AIT", "DSBA", "BIT", "IT"):
        rs = by_prog.get(prog, [])
        if not rs:
            print(f"{prog:<8}{0:>7}   — no chunks —")
            continue
        lens = [len(r["text"]) for r in rs]
        facts = {f for r in rs for f in r.get("facts", [])}
        missing = [f for f in REQUIRED_FACTS if f not in facts]
        ratio = statistics.mean(mark_ratio(r["text"]) for r in rs)
        print(f"{prog:<8}{len(rs):>7}{statistics.mean(lens):>10.0f}{max(lens):>9}{ratio:>12.3f}  {len(facts)} types; missing={missing or 'none'}")
    pages_ok = all(isinstance(r["page"], int) and r["page"] >= 1 for r in rows)
    print(f"pages 1-based ints: {pages_ok};  synthetic flags: {Counter(r.get('synthetic') for r in rows)}")

    flagged = [(r, suspicious(r["text"])) for r in rows]
    flagged = [(r, p) for r, p in flagged if p]
    print(f"\nSuspicious chunks: {len(flagged)}/{len(rows)} ({100 * len(flagged) / max(1, len(rows)):.1f}%)")
    kinds = Counter(p.split(" ×")[0].split(" (")[0] for _, ps in flagged for p in ps)
    for k, v in kinds.most_common():
        print(f"  {k}: {v}")

    def badness(item: tuple[dict, list[str]]) -> int:
        return sum(int(m.group(1)) if (m := re.search(r"×(\d+)", p)) else 3 for p in item[1])

    worst = sorted(flagged, key=badness, reverse=True)[: args.worst]
    if worst:
        print(f"\nWorst {len(worst)} chunks")
        for r, ps in worst:
            print("-" * 78)
            print(f"{r['chunk_id']} p{r['page']} — {r['heading_path'][:70]}\n  problems: {ps}\n  {r['text'][:400]!r}")

    if args.sample:
        rng = random.Random(args.seed)
        for prog in ("AIT", "DSBA", "BIT", "IT"):
            rs = by_prog.get(prog, [])
            print(f"\n=== sample {prog} ===")
            for r in rng.sample(rs, min(args.sample, len(rs))):
                print(f"--- {r['chunk_id']} p{r['page']} facts={r.get('facts')} — {r['heading_path'][:80]}\n{r['text'][:500]}")
    return 1 if (args.strict and flagged) else 0


if __name__ == "__main__":
    sys.exit(main())
