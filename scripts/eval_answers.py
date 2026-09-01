#!/usr/bin/env python
"""Faithfulness eval for the answer layer — deterministic checks, no LLM judge.

Runs every case in ``tests/eval_answers.jsonl`` through
``gate() -> RagAnswerer(FixtureRetriever)`` and checks:

* facts       — every ``must_contain`` string present, none of ``must_not_contain``
                (digits / thousands separators / whitespace normalised)
* grounding   — every number in the answer occurs in the assembled context
                (the hallucination detector)
* citations   — non-empty; every cited chunk was retrieved; ≥1 cited chunk in
                ``gold_chunk_ids`` when given
* not_found   — ``expect_not_found`` cases contain the not-found phrase and have
                no citations
* language    — the answer's dominant script matches ``language``
* leakage     — no ``<think>``, no ``[n]`` marker without a matching chunk
* gate        — the gatekeeper let the question through (``in_scope``)

Examples::

    python scripts/eval_answers.py                  # cached (.cache/eval-answers/)
    python scripts/eval_answers.py --no-cache
    python scripts/eval_answers.py --only cmp-ait-dsba-credits --show-all
    python scripts/eval_answers.py --model typhoon-s-thaillm-8b-instruct
    python scripts/eval_answers.py --no-rewrite     # skip the follow-up/translation call

Every failure prints the full answer and the raw model output (``<think>``
included) so you can see how the 8B model actually fails.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.answerer import Turn
from gatekeeper import gate, load_settings
from rag import llm as rag_llm
from rag.answerer import RagAnswerer
from rag.checks import (
    contains_all,
    contains_any,
    dominant_script,
    language_matches,
    leakage_problems,
    ungrounded_numbers,
)
from rag.llm import load_rag_settings
from rag.prompts import is_not_found
from rag.retriever import FixtureRetriever

DEFAULT_CASES = ROOT / "tests" / "eval_answers.jsonl"
GATE_CACHE_DIR = ROOT / ".cache" / "eval"
ANSWER_CACHE_DIR = ROOT / ".cache" / "eval-answers"
CHECKS = ("gate", "facts", "grounding", "citations", "not_found", "language", "leakage")


def load_cases(path: Path, only: list[str] | None) -> list[dict]:
    cases = []
    with path.open(encoding="utf-8") as fh:
        for i, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            case = json.loads(line)
            case.setdefault("history", [])
            case.setdefault("must_contain", [])
            case.setdefault("must_not_contain", [])
            case.setdefault("expect_not_found", False)
            case.setdefault("gold_chunk_ids", [])
            case["line"] = i
            if only and case["id"] not in only:
                continue
            cases.append(case)
    return cases


async def run_case(case: dict, answerer: RagAnswerer, gate_settings, sem: asyncio.Semaphore) -> dict:
    history = [Turn(**t) for t in case["history"]]
    result: dict = {"case": case, "checks": {}, "notes": []}
    async with sem:
        started = time.perf_counter()
        decision = await gate(case["question"], settings=gate_settings)
        result["decision"] = decision
        if decision.category != "in_scope":
            result["checks"]["gate"] = (False, f"gate returned {decision.category} (decided_by={decision.decided_by}); answerer not called")
            result["answer"] = decision.direct_reply or ""
            result["debug"] = {}
            result["citations"] = []
            result["latency_ms"] = int((time.perf_counter() - started) * 1000)
            return result
        result["checks"]["gate"] = (True, "")
        if sorted(decision.programs) != sorted(case.get("programs", [])):
            result["notes"].append(f"gate programs={decision.programs} expected={case.get('programs')}")
        if case.get("question_kind") and decision.question_kind != case["question_kind"]:
            result["notes"].append(f"gate question_kind={decision.question_kind} expected={case['question_kind']}")
        if case.get("language") and decision.language != case["language"]:
            result["notes"].append(f"gate language={decision.language} expected={case['language']}")

        dbg: dict = {}
        tokens: list[str] = []
        citations: list = []
        model_used = None
        error = None
        try:
            async for ev in answerer.answer(case["question"], decision, None, history, debug=dbg):
                if ev.type == "token":
                    tokens.append(ev.text or "")
                elif ev.type == "citations":
                    citations = list(ev.citations or [])
                elif ev.type == "done":
                    model_used = ev.model_used
        except Exception as exc:  # noqa: BLE001  # an exception is itself a failed case; keep the run going
            error = f"{type(exc).__name__}: {exc}"
        result.update({
            "answer": "".join(tokens), "citations": citations, "debug": dbg, "model_used": model_used,
            "error": error, "latency_ms": int((time.perf_counter() - started) * 1000),
        })
    return result


def evaluate(result: dict) -> None:
    """Fill ``result["checks"]`` (name -> (passed | None, detail)); None = not applicable."""
    case = result["case"]
    checks = result["checks"]
    if not checks.get("gate", (False, ""))[0]:
        for name in CHECKS[1:]:
            checks[name] = (None, "")
        return
    answer: str = result["answer"]
    dbg: dict = result["debug"]
    citations = result["citations"]
    context: str = dbg.get("context", "")
    n_chunks = len(dbg.get("context_chunks", []))
    retrieved = {cid for cid, _ in dbg.get("retrieved", [])}
    if result.get("error"):
        for name in CHECKS[1:]:
            checks[name] = (False, f"answerer raised {result['error']}")
        return

    nf = case["expect_not_found"]
    # facts
    if nf:
        checks["facts"] = (None, "")
    else:
        missing = contains_all(answer, case["must_contain"])
        forbidden = contains_any(answer, case["must_not_contain"])
        detail = []
        if missing:
            detail.append(f"missing {missing}")
        if forbidden:
            detail.append(f"forbidden {forbidden}")
        checks["facts"] = (not detail, "; ".join(detail))
    # grounding
    bad = ungrounded_numbers(answer, context)
    checks["grounding"] = (not bad, f"numbers not in context: {bad}" if bad else "")
    # citations
    if nf:
        checks["citations"] = (None, "")
    else:
        problems = []
        cited = [c.chunk_id for c in citations]
        if not cited:
            problems.append("no citations")
        unknown = [c for c in cited if c not in retrieved]
        if unknown:
            problems.append(f"cited chunks not retrieved {unknown}")
        gold = case["gold_chunk_ids"]
        if gold and not set(cited) & set(gold):
            problems.append(f"no gold chunk cited (cited={cited}, gold={gold})")
        checks["citations"] = (not problems, "; ".join(problems))
    # not-found behaviour
    if nf:
        has_phrase = is_not_found(answer)
        problems = []
        if not has_phrase:
            problems.append("not-found phrase absent")
        if citations:
            problems.append(f"citations not empty ({[c.chunk_id for c in citations]})")
        forbidden = contains_any(answer, case["must_not_contain"])
        if forbidden:
            problems.append(f"forbidden {forbidden}")
        checks["not_found"] = (not problems, "; ".join(problems))
    else:
        checks["not_found"] = (None, "")
    # language
    ok = language_matches(answer, case["language"])
    checks["language"] = (ok, "" if ok else f"dominant script {dominant_script(answer)} != {case['language']}")
    # leakage
    leaks = leakage_problems(answer, n_chunks)
    checks["leakage"] = (not leaks, "; ".join(leaks))


def pct(n: int, d: int) -> str:
    return f"{100.0 * n / d:.1f}%" if d else "n/a"


def p95(values: list[float]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    return s[min(len(s) - 1, round(0.95 * (len(s) - 1)))]


def report(results: list[dict], *, show_all: bool) -> int:
    print("=" * 78)
    print("ANSWER EVAL — tests/eval_answers.jsonl")
    print("=" * 78)
    print("Per-check pass rate (passed / applicable)")
    for name in CHECKS:
        applicable = [r for r in results if r["checks"][name][0] is not None]
        passed = [r for r in applicable if r["checks"][name][0]]
        print(f"  {name:<12} {len(passed):>3}/{len(applicable):<3} {pct(len(passed), len(applicable))}")
    failed = [r for r in results if any(v[0] is False for v in r["checks"].values())]
    print(f"\nCases fully passing: {len(results) - len(failed)}/{len(results)} {pct(len(results) - len(failed), len(results))}")
    lat = [r["latency_ms"] for r in results]
    print(f"Latency: mean {statistics.mean(lat):.0f} ms, p95 {p95(lat):.0f} ms (gate + answer, cache hits are ~0 ms)")
    print("Models used: " + ", ".join(f"{k or 'none'}={v}" for k, v in sorted(Counter(r.get("model_used") for r in results).items(), key=lambda kv: str(kv[0]))))
    print(f"LLM cache: hits={rag_llm.CACHE_STATS['hits']} misses={rag_llm.CACHE_STATS['misses']}")
    notes = [(r["case"]["id"], n) for r in results for n in r["notes"]]
    if notes:
        print("\nGate metadata mismatches (informational, the real decision was used):")
        for cid, n in notes:
            print(f"  {cid}: {n}")

    rows = results if show_all else failed
    if rows:
        print("\n" + ("ALL CASES" if show_all else "FAILURES"))
        for r in rows:
            case = r["case"]
            bad = {k: v for k, v in r["checks"].items() if v[0] is False}
            flag = "OK  " if not bad else "FAIL"
            print("-" * 78)
            print(f"[{flag}] {case['id']} (line {case['line']}): {case['question']}")
            for k, (_, detail) in bad.items():
                print(f"       ✗ {k}: {detail}")
            d = r.get("decision")
            if d is not None:
                print(f"       gate: category={d.category} programs={d.programs} kind={d.question_kind} lang={d.language} decided_by={d.decided_by}")
            dbg = r.get("debug") or {}
            if dbg:
                print(f"       query: {dbg.get('query')!r} programs={dbg.get('programs')}")
                print(f"       retrieved: {dbg.get('retrieved')}")
                print(f"       context_chunks: {dbg.get('context_chunks')} ({dbg.get('context_tokens')} est. tokens)")
            print(f"       model_used={r.get('model_used')} latency={r['latency_ms']}ms citations={[c.chunk_id for c in r['citations']]}")
            print(f"       answer: {r['answer']!r}")
            for i, raw in enumerate(dbg.get("raw_outputs") or [], start=1):
                print(f"       raw[{i}] ({raw['model']}): {raw['raw']!r}")
    return len(failed)


async def run_all(cases: list[dict], answerer: RagAnswerer, gate_settings, concurrency: int) -> list[dict]:
    sem = asyncio.Semaphore(concurrency)
    return await asyncio.gather(*(run_case(c, answerer, gate_settings, sem) for c in cases))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    ap.add_argument("--only", nargs="*", default=None, help="case ids to run")
    ap.add_argument("--no-cache", action="store_true", help="bypass .cache/eval-answers and .cache/eval")
    ap.add_argument("--model", default=None, help="answer model for fact_lookup/descriptive")
    ap.add_argument("--comparison-model", default=None, help="answer model for comparisons")
    ap.add_argument("--no-rewrite", action="store_true", help="disable the follow-up rewrite / translation call")
    ap.add_argument("--min-score", type=float, default=None)
    ap.add_argument("--concurrency", type=int, default=2)
    ap.add_argument("--show-all", action="store_true")
    ap.add_argument("--strict", action="store_true", help="exit 1 if any case fails")
    args = ap.parse_args()

    cases = load_cases(args.cases, args.only)
    if not cases:
        print("no cases", file=sys.stderr)
        return 2
    gate_settings = load_settings(cache_dir=None if args.no_cache else str(GATE_CACHE_DIR))
    if args.no_cache:
        gate_settings = gate_settings.__class__(**{**gate_settings.__dict__, "cache_dir": None})
    rag_settings = load_rag_settings(
        model=args.model, comparison_model=args.comparison_model, min_score=args.min_score,
        cache_dir=None if args.no_cache else str(ANSWER_CACHE_DIR),
        query_rewrite=False if args.no_rewrite else None,
    )
    answerer = RagAnswerer(retriever=FixtureRetriever(), settings=rag_settings)
    print(
        f"Evaluating {len(cases)} cases [model={rag_settings.model} comparison={rag_settings.comparison_model} "
        f"rewrite={'on' if rag_settings.query_rewrite else 'off'} min_score={rag_settings.min_score} "
        f"cache={'off' if args.no_cache else rag_settings.cache_dir}]"
    )
    results = asyncio.run(run_all(cases, answerer, gate_settings, args.concurrency))
    for r in results:
        evaluate(r)
    failed = report(results, show_all=args.show_all)
    return 1 if (args.strict and failed) else 0


if __name__ == "__main__":
    sys.exit(main())
