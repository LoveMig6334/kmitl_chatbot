#!/usr/bin/env python
"""Run the gatekeeper over the tuning set ``tests/eval_tuning.jsonl``.

Two checks per row:

* **category** (deterministic) — ``gate().category`` must be one of the row's
  ``expected`` categories.  Reported overall, per stratum and per language.
* **reply quality** (judged) — for rows whose decision carries a
  ``direct_reply``, the (question, reply) pair is looked up in
  ``tests/eval_tuning_judgements.jsonl`` (verdicts written by the judge against
  ``docs/reply-rubric.md``).  Pairs without a verdict are written to
  ``.cache/eval-tuning/pending_judgements.jsonl`` together with deterministic
  rubric hints, and counted as *pending* (never as pass).

Examples::

    python scripts/eval_tuning.py                        # full run (cached ThaiLLM responses)
    python scripts/eval_tuning.py --no-cache             # full uncached run (start / end of the loop)
    python scripts/eval_tuning.py --sample 80 --seed 3   # random subset
    python scripts/eval_tuning.py --failures-only        # only rows that failed in the previous run
    python scripts/eval_tuning.py --stratum smalltalk --language th --show-all
    python scripts/eval_tuning.py --dry-run              # rule layer only
    python scripts/eval_tuning.py --no-rules             # LLM only
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import random
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gatekeeper import GateDecision, gate, load_settings
from gatekeeper.llm import CACHE_STATS
from gatekeeper.replies import sentence_count
from gatekeeper.schema import CATEGORIES

TUNING_JSONL = ROOT / "tests" / "eval_tuning.jsonl"
JUDGEMENTS_JSONL = ROOT / "tests" / "eval_tuning_judgements.jsonl"
CACHE_DIR = ROOT / ".cache" / "eval-tuning"
LLM_CACHE_DIR = ROOT / ".cache" / "eval"
PENDING_JSONL = CACHE_DIR / "pending_judgements.jsonl"
LAST_RUN_JSON = CACHE_DIR / "last_run.json"

THAI = re.compile(r"[฀-๿]")
CJK = re.compile(r"[一-鿿]")
REFUSAL = re.compile(r"ขออภัย|ไม่สามารถ|\bsorry\b|can'?t|cannot|抱歉|无法|只能", re.IGNORECASE)
INTERNALS = re.compile(
    r"system\s*prompt|<user_message>|ผู้คัดกรอง|\bjson\b|openthaigpt|typhoon|pathumma|thaillm|thalle"
    r"|in_scope|off_topic|out_of_scope|injection_or_abuse|greeting_smalltalk|คำสั่งระบบ|พรอมต์",
    re.IGNORECASE,
)
NEXT_STEP_OFFER = re.compile(r"ถาม|\bask\b|问", re.IGNORECASE)
URL_OR_CHANNEL = re.compile(r"https?://|\.ac\.th|\.go\.th|\.or\.th|\.com|mytcas|แอป|เว็บไซต์|\bapp\b|\bsite\b|网站|应用|ติดต่อ|contact|联系|เอกสาร|documentation|community|ชุมชน|社区|search engine|เครื่องมือค้นหา|搜索", re.IGNORECASE)


# --------------------------------------------------------------------------- #
# pure helpers (unit-tested)
# --------------------------------------------------------------------------- #
def judgement_hash(question: str, reply: str) -> str:
    return hashlib.sha256((question + "\n" + reply).encode("utf-8")).hexdigest()[:16]


def category_ok(category: str, expected: list[str]) -> bool:
    return category in expected


def load_rows(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def filter_rows(
    rows: list[dict],
    *,
    stratum: str | None = None,
    language: str | None = None,
    ids: set[str] | None = None,
    sample: int | None = None,
    seed: int = 0,
) -> list[dict]:
    out = rows
    if stratum:
        out = [r for r in out if r["tags"][0] == stratum]
    if language:
        out = [r for r in out if r["language"] == language]
    if ids is not None:
        out = [r for r in out if r["id"] in ids]
    if sample is not None and sample < len(out):
        out = random.Random(seed).sample(out, sample)
    return out


def _script_matches(language: str, reply: str) -> bool:
    thai, cjk = bool(THAI.search(reply)), bool(CJK.search(reply))
    if language == "th":
        return thai
    if language == "zh":
        return cjk
    return not thai and not cjk  # en / other → English


def rubric_hints(language: str, category: str, topic: str | None, reply: str) -> dict[str, bool]:
    """Deterministic first pass over rubric criteria (a)–(e).  The judge decides."""
    smalltalk = category == "greeting_smalltalk"
    if smalltalk and (topic or "greeting") in ("greeting", "identity", "help"):
        next_step = reply.count("“") >= 2
    elif smalltalk:
        next_step = bool(NEXT_STEP_OFFER.search(reply))
    elif category == "injection_or_abuse":
        next_step = True
    else:
        next_step = bool(URL_OR_CHANNEL.search(reply)) or bool(NEXT_STEP_OFFER.search(reply))
    return {
        "language": _script_matches(language, reply),
        "no_refusal": (not REFUSAL.search(reply)) if smalltalk else True,
        "next_step": next_step,
        "no_internals": not INTERNALS.search(reply),
        "length": sentence_count(reply) <= 3,
    }


def load_judgements(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    out: dict[str, dict] = {}
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                j = json.loads(line)
                out[j["hash"]] = j
    return out


def append_judgements(path: Path, items: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for j in items:
            fh.write(json.dumps(j, ensure_ascii=False) + "\n")


# --------------------------------------------------------------------------- #
# run
# --------------------------------------------------------------------------- #
async def run_all(rows: list[dict], *, dry_run: bool, no_rules: bool, settings, concurrency: int) -> list[dict]:
    sem = asyncio.Semaphore(concurrency)

    async def one(row: dict) -> dict:
        dbg: dict = {}
        async with sem:
            d: GateDecision = await gate(row["question"], settings=settings, use_llm=not dry_run, use_rules=not no_rules, debug=dbg)
        return {**row, "decision": d, "debug": dbg}

    return await asyncio.gather(*(one(r) for r in rows))


def pct(n: int, d: int) -> str:
    return f"{(100.0 * n / d):.1f}%" if d else "n/a"


def _topic_of(result: dict) -> str | None:
    reason = result["debug"].get("rule_reason") or ""
    m = re.match(r"smalltalk: (\w+)", reason)
    return m.group(1) if m else None


def report(results: list[dict], judgements: dict[str, dict], *, show_all: bool) -> tuple[list[dict], list[dict], list[dict]]:
    """Print the summary; return (category failures, reply failures, pending judgements)."""
    total = len(results)
    cat_ok = [category_ok(r["decision"].category, r["expected"]) for r in results]
    correct = sum(cat_ok)

    def table(title: str, key) -> None:
        tot: Counter = Counter(key(r) for r in results)
        ok: Counter = Counter(key(r) for r, good in zip(results, cat_ok) if good)
        print(title)
        for k in sorted(tot, key=lambda x: (x != "ambiguous", x)):
            flag = "" if not tot[k] or ok[k] / tot[k] >= 0.9 else "   <-- below 90%"
            print(f"  {k:<14}{ok[k]:>4}/{tot[k]:<4} {pct(ok[k], tot[k])}{flag}")

    print("=" * 78)
    print("TUNING SET — category check")
    print("=" * 78)
    table("Per stratum", lambda r: r["tags"][0])
    table("Per language", lambda r: r["language"])
    confusion: dict[str, Counter] = defaultdict(Counter)
    for r in results:
        confusion[r["expected"][0]][r["decision"].category] += 1
    short = {c: c.replace("off_topic_", "ot_").replace("out_of_scope_", "oos_").replace("injection_or_abuse", "inject").replace("greeting_smalltalk", "smalltalk")[:10] for c in CATEGORIES}
    print("Confusion (rows = first expected, cols = predicted)")
    print(f"  {'':<28}" + "".join(f"{short[c]:>11}" for c in CATEGORIES))
    for exp in CATEGORIES:
        if confusion[exp]:
            print(f"  {exp:<28}" + "".join(f"{confusion[exp][p]:>11}" for p in CATEGORIES))
    decided_by = Counter(r["decision"].decided_by for r in results)
    lat = [r["decision"].latency_ms for r in results]
    llm_lat = [r["decision"].latency_ms for r in results if r["decision"].decided_by != "rule"]
    print("Decided by: " + ", ".join(f"{k}={v}" for k, v in sorted(decided_by.items())))
    print(f"Latency: mean {statistics.mean(lat) if lat else 0:.0f} ms, p95 {sorted(lat)[int(0.95 * (len(lat) - 1))] if lat else 0} ms"
          + (f"; LLM path mean {statistics.mean(llm_lat):.0f} ms" if llm_lat else ""))
    print(f"\nCategory accuracy: {pct(correct, total)} ({correct}/{total})")

    # reply quality
    judged_pass = judged_fail = 0
    pending: list[dict] = []
    reply_failures: list[dict] = []
    for r in results:
        d = r["decision"]
        if not d.direct_reply:
            continue
        h = judgement_hash(r["question"], d.direct_reply)
        j = judgements.get(h)
        if j is None:
            pending.append({
                "hash": h, "id": r["id"], "question": r["question"], "language": r["language"],
                "category": d.category, "topic": _topic_of(r), "reply": d.direct_reply,
                "hints": rubric_hints(r["language"], d.category, _topic_of(r), d.direct_reply),
            })
        elif j["verdict"] == "pass":
            judged_pass += 1
        else:
            judged_fail += 1
            reply_failures.append({**r, "judgement": j})
    judged = judged_pass + judged_fail
    print("=" * 78)
    print("TUNING SET — reply quality (judged against docs/reply-rubric.md)")
    print("=" * 78)
    print(f"  rows with a direct_reply: {judged + len(pending)}   judged: {judged}   pending: {len(pending)}")
    print(f"  Reply-quality pass rate (judged only): {pct(judged_pass, judged)} ({judged_pass}/{judged})")
    if pending:
        print(f"  ! {len(pending)} pairs await a verdict → {PENDING_JSONL}")
    print("=" * 78)

    cat_failures = [r for r, good in zip(results, cat_ok) if not good]
    rows_to_show = results if show_all else cat_failures
    if rows_to_show:
        print("\nCATEGORY " + ("ALL ROWS" if show_all else "FAILURES") + f" ({len(rows_to_show)})")
        for r in rows_to_show:
            d = r["decision"]
            flag = "OK  " if category_ok(d.category, r["expected"]) else "MISS"
            print("-" * 78)
            print(f"[{flag}] {r['id']} [{r['language']}] {' '.join(r['tags'][1:])}: {r['question']}")
            print(f"       expected={r['expected']} got={d.category} decided_by={d.decided_by} conf={d.confidence} programs={d.programs}")
            print(f"       rule_reason={r['debug'].get('rule_reason')}")
            for i, raw in enumerate(r["debug"].get("raw_outputs") or [], start=1):
                print(f"       raw[{i}]: {raw!r}")
    if reply_failures:
        print(f"\nREPLY-QUALITY FAILURES ({len(reply_failures)})")
        for r in reply_failures:
            print("-" * 78)
            print(f"[FAIL] {r['id']} [{r['language']}] {r['question']}")
            print(f"       category={r['decision'].category}  reason: {r['judgement'].get('reason')}")
            print(f"       reply: {r['decision'].direct_reply}")
    return cat_failures, reply_failures, pending


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--jsonl", type=Path, default=TUNING_JSONL)
    ap.add_argument("--judgements", type=Path, default=JUDGEMENTS_JSONL)
    ap.add_argument("--stratum", default=None)
    ap.add_argument("--language", choices=["th", "en", "zh", "other"], default=None)
    ap.add_argument("--sample", type=int, default=None, help="evaluate a random subset of N rows")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--failures-only", action="store_true", help="only rows that failed (category or reply) in the previous run")
    ap.add_argument("--ids", default=None, help="comma-separated row ids")
    ap.add_argument("--dry-run", action="store_true", help="rule layer only (no API calls)")
    ap.add_argument("--no-rules", action="store_true", help="bypass rule decisions; every row goes to the LLM")
    ap.add_argument("--no-cache", action="store_true", help="do not read/write the ThaiLLM response cache")
    ap.add_argument("--model", default=None)
    ap.add_argument("--timeout", type=float, default=None)
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--show-all", action="store_true")
    ap.add_argument("--strict", action="store_true", help="exit 1 on any category/reply failure or pending judgement")
    args = ap.parse_args()
    if args.dry_run and args.no_rules:
        ap.error("--dry-run and --no-rules are mutually exclusive")

    rows = load_rows(args.jsonl)
    ids: set[str] | None = None
    if args.failures_only:
        if not LAST_RUN_JSON.exists():
            print("no previous run recorded", file=sys.stderr)
            return 2
        ids = set(json.loads(LAST_RUN_JSON.read_text(encoding="utf-8")).get("failures", []))
    if args.ids:
        ids = (ids or set()) | {x.strip() for x in args.ids.split(",") if x.strip()}
    rows = filter_rows(rows, stratum=args.stratum, language=args.language, ids=ids, sample=args.sample, seed=args.seed)
    if not rows:
        print("no rows to evaluate", file=sys.stderr)
        return 2

    settings = load_settings(model=args.model, timeout_s=args.timeout, cache_dir=None if args.no_cache else str(LLM_CACHE_DIR))
    if args.no_cache:
        settings = settings.__class__(**{**settings.__dict__, "cache_dir": None})
    mode = "DRY RUN (rules only)" if args.dry_run else (
        f"{'LLM-only' if args.no_rules else 'rules + LLM'} model={settings.model} cache={'off' if args.no_cache else 'on'}"
    )
    print(f"Evaluating {len(rows)} rows from {args.jsonl.name} [{mode}]")
    results = asyncio.run(run_all(rows, dry_run=args.dry_run, no_rules=args.no_rules, settings=settings, concurrency=args.concurrency))
    results.sort(key=lambda r: r["id"])
    judgements = load_judgements(args.judgements)
    cat_failures, reply_failures, pending = report(results, judgements, show_all=args.show_all)

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with PENDING_JSONL.open("w", encoding="utf-8") as fh:
        for p in pending:
            fh.write(json.dumps(p, ensure_ascii=False) + "\n")
    failure_ids = sorted({r["id"] for r in cat_failures} | {r["id"] for r in reply_failures} | {p["id"] for p in pending})
    LAST_RUN_JSON.write_text(json.dumps({"failures": failure_ids, "evaluated": [r["id"] for r in results]}, ensure_ascii=False), encoding="utf-8")
    if not args.dry_run:
        print(f"\nLLM cache: hits={CACHE_STATS['hits']} misses={CACHE_STATS['misses']}")
    return 1 if (args.strict and failure_ids) else 0


if __name__ == "__main__":
    sys.exit(main())
