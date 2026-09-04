#!/usr/bin/env python
"""Run a question CSV through the REAL chat pipeline and record the answers.

This drives the exact backend the web UI talks to: it builds the FastAPI app
from ``api.main`` and POSTs each question to ``/chat`` (gate -> meta -> streamed
answer + citations), parsing the same Server-Sent-Events stream the browser
receives.  By default it runs the app in-process (no separate server to start);
pass ``--url http://localhost:8000`` to hit a running uvicorn instead.

It repeats the whole set N times (default 3) because the ThaiLLM models are not
deterministic, and writes:

  real_test_csv/results_run1.csv .. results_runN.csv   # submission format: question,level,answer
  real_test_csv/results_wide.csv                       # question,level,answer_run1..N (+ run-1 meta)
  real_test_csv/results_long.csv                       # one row per (run,question) with full metadata
  real_test_csv/results_meta.json                      # git commit, models, retriever, env, timing

Reproducibility
---------------
* Questions are processed in file order, one at a time (no concurrency), same
  order every run, so a rerun regenerates the same file structure.
* Answer generation uses temperature 0 (see rag/llm.py), but the hosted models
  still vary run to run — that is why we capture 3 runs and record the git SHA,
  model ids and retriever/embedding state in results_meta.json for traceability.
* No hidden state: it reads only the input CSV and writes only the outputs above.

Usage
-----
  python scripts/run_real_test.py
  python scripts/run_real_test.py --runs 3 --input real_test_csv/easy_normal_blank.csv
  python scripts/run_real_test.py --url http://localhost:8000        # hit a live server
  python scripts/run_real_test.py --retriever fixture                # offline, no index/API
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))  # make `api`, `gatekeeper`, `rag` importable when run as a script


def load_questions(path: Path) -> list[dict]:
    # utf-8-sig strips the BOM the source file carries.
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        q = (r.get("question") or "").strip()
        if q:
            out.append({"question": q, "level": (r.get("level") or "").strip()})
    return out


def parse_sse(chunk: str, state: dict) -> None:
    """Accumulate one SSE event (event:/data: lines) into ``state``."""
    event = None
    data = None
    for line in chunk.splitlines():
        if line.startswith("event:"):
            event = line[len("event:"):].strip()
        elif line.startswith("data:"):
            data = line[len("data:"):].strip()
    if event is None or data is None:
        return
    try:
        payload = json.loads(data)
    except json.JSONDecodeError:
        return
    if event == "meta":
        state["meta"] = payload
    elif event == "token":
        state["answer"].append(payload.get("text", ""))
    elif event == "citations":
        state["citations"] = payload.get("citations", [])
    elif event == "done":
        state["done"] = payload
    elif event == "error":
        state["error"] = payload


async def ask(client, url_path: str, question: str) -> dict:
    """POST one question to /chat and collect the streamed result."""
    state: dict = {"answer": [], "citations": [], "meta": {}, "done": {}, "error": None}
    started = time.perf_counter()
    body = {"message": question, "scope": None, "history": []}
    async with client.stream("POST", url_path, json=body) as resp:
        if resp.status_code != 200:
            text = await resp.aread()
            state["error"] = {"http_status": resp.status_code, "body": text.decode("utf-8", "replace")[:300]}
        else:
            buf = ""
            async for raw in resp.aiter_lines():
                buf += raw + "\n"
                if raw == "":  # blank line terminates one SSE event
                    parse_sse(buf, state)
                    buf = ""
            if buf.strip():
                parse_sse(buf, state)
    meta = state["meta"] or {}
    return {
        "question": question,
        "answer": "".join(state["answer"]).strip(),
        "category": meta.get("category", ""),
        "language": meta.get("language", ""),
        "decided_by": meta.get("decided_by", ""),
        "programs": ";".join(meta.get("programs", []) or []),
        "question_kind": meta.get("question_kind") or "",
        "n_citations": len(state["citations"]),
        "citations": json.dumps(state["citations"], ensure_ascii=False),
        "model_used": (state["done"] or {}).get("model_used") or meta.get("model_used") or "",
        "latency_ms": int((time.perf_counter() - started) * 1000),
        "error": json.dumps(state["error"], ensure_ascii=False) if state["error"] else "",
    }


def make_client(url: str | None):
    """Return an httpx.AsyncClient bound either to a live server or the in-process app."""
    import httpx

    if url:
        return httpx.AsyncClient(base_url=url.rstrip("/"), timeout=httpx.Timeout(180.0)), "/chat", f"live:{url}"
    # In-process: same app object uvicorn serves. Rate limiting disabled for the batch.
    from api.main import create_app

    app = create_app(rate_limit_per_minute=0)
    transport = httpx.ASGITransport(app=app)
    return (
        httpx.AsyncClient(transport=transport, base_url="http://test", timeout=httpx.Timeout(180.0)),
        "/chat",
        "in-process (ASGI)",
    )


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        return str(path)


def git_sha() -> str:
    try:
        return subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip()
    except Exception:  # noqa: BLE001
        return "unknown"


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", default="real_test_csv/easy_normal_blank.csv")
    ap.add_argument("--output-dir", default="real_test_csv")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--url", default=None, help="hit a running server (e.g. http://localhost:8000) instead of in-process")
    ap.add_argument("--answerer", default=None, help="ANSWERER (default rag)")
    ap.add_argument("--retriever", default=None, help="RETRIEVER: chroma (real, default) | fixture")
    ap.add_argument("--limit", type=int, default=0, help="only the first N questions (0 = all)")
    ap.add_argument("--retries", type=int, default=2,
                    help="re-send a question this many times if the server drops the stream (transient error)")
    args = ap.parse_args()

    # Real pipeline defaults: the RAG answerer over the real Chroma retriever.
    os.environ.setdefault("ANSWERER", args.answerer or "rag")
    os.environ.setdefault("RETRIEVER", args.retriever or "chroma")
    if args.answerer:
        os.environ["ANSWERER"] = args.answerer
    if args.retriever:
        os.environ["RETRIEVER"] = args.retriever
    try:
        from dotenv import load_dotenv

        load_dotenv(REPO / ".env")
    except Exception:  # noqa: BLE001, S110
        pass

    in_path = (REPO / args.input) if not os.path.isabs(args.input) else Path(args.input)
    out_dir = (REPO / args.output_dir) if not os.path.isabs(args.output_dir) else Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    questions = load_questions(in_path)
    if args.limit:
        questions = questions[: args.limit]
    print(f"loaded {len(questions)} questions from {in_path}")

    client, url_path, mode = make_client(args.url)
    print(f"mode: {mode} | ANSWERER={os.environ.get('ANSWERER')} RETRIEVER={os.environ.get('RETRIEVER')} "
          f"EMBED_API={os.environ.get('EMBED_API') or '(local/none)'}")

    started_all = time.perf_counter()
    all_runs: list[list[dict]] = []
    try:
        for run in range(1, args.runs + 1):
            print(f"\n=== run {run}/{args.runs} ===")
            run_rows = []
            for i, q in enumerate(questions, 1):
                # The hosted ThaiLLM server occasionally drops a stream mid-answer
                # (transient). Re-send like a user would, so a run is not spoiled by it.
                attempts = 0
                while True:
                    res = await ask(client, url_path, q["question"])
                    attempts += 1
                    if not res["error"] or attempts > args.retries:
                        break
                    await asyncio.sleep(1.0 * attempts)
                res["level"] = q["level"]
                res["run"] = run
                res["attempts"] = attempts
                run_rows.append(res)
                retry_note = f" (x{attempts})" if attempts > 1 else ""
                flag = res["error"] or f"{res['category']}/{res['language']}"
                print(f"  [{i:02d}/{len(questions)}] {flag:26s} {res['latency_ms']:>6}ms{retry_note}  {q['question'][:44]}")
            all_runs.append(run_rows)
            # per-run submission CSV (question,level,answer)
            run_csv = out_dir / f"results_run{run}.csv"
            with run_csv.open("w", encoding="utf-8-sig", newline="") as f:
                w = csv.writer(f)
                w.writerow(["question", "level", "answer"])
                for r in run_rows:
                    w.writerow([r["question"], r["level"], r["answer"] if not r["error"] else f"[ERROR] {r['error']}"])
            print(f"  wrote {rel(run_csv)}")
    finally:
        await client.aclose()

    # wide CSV: one row per question, an answer column per run
    wide = out_dir / "results_wide.csv"
    with wide.open("w", encoding="utf-8-sig", newline="") as f:
        cols = ["question", "level"] + [f"answer_run{r}" for r in range(1, args.runs + 1)] + \
               ["category_run1", "language_run1", "decided_by_run1"]
        w = csv.writer(f)
        w.writerow(cols)
        for idx, q in enumerate(questions):
            row = [q["question"], q["level"]]
            for run in range(args.runs):
                r = all_runs[run][idx]
                row.append(r["answer"] if not r["error"] else f"[ERROR] {r['error']}")
            m = all_runs[0][idx]
            row += [m["category"], m["language"], m["decided_by"]]
            w.writerow(row)

    # long CSV: one row per (run, question) with full metadata
    long_csv = out_dir / "results_long.csv"
    fields = ["run", "question", "level", "category", "language", "decided_by", "programs",
              "question_kind", "n_citations", "latency_ms", "attempts", "model_used", "answer", "citations", "error"]
    with long_csv.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for run_rows in all_runs:
            for r in run_rows:
                w.writerow(r)

    meta = {
        "generated_at": datetime.now(UTC).isoformat(),
        "git_commit": git_sha(),
        "mode": mode,
        "runs": args.runs,
        "n_questions": len(questions),
        "input": rel(in_path),
        "env": {
            "ANSWERER": os.environ.get("ANSWERER"),
            "RETRIEVER": os.environ.get("RETRIEVER"),
            "EMBED_API": os.environ.get("EMBED_API") or "(local/none)",
            "GATEKEEPER_MODEL": os.environ.get("GATEKEEPER_MODEL", "openthaigpt-thaillm-8b-instruct-v7.2"),
            "RAG_MODEL": os.environ.get("RAG_MODEL", "openthaigpt-thaillm-8b-instruct-v7.2"),
            "THAILLM_BASE_URL": os.environ.get("THAILLM_BASE_URL"),
            "RAG_LANGUAGE_GUARD": os.environ.get("RAG_LANGUAGE_GUARD", "1"),
        },
        "python": sys.version.split()[0],
        "total_seconds": round(time.perf_counter() - started_all, 1),
        "outputs": [f"results_run{r}.csv" for r in range(1, args.runs + 1)] + ["results_wide.csv", "results_long.csv"],
    }
    (out_dir / "results_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\ndone in {meta['total_seconds']}s → {rel(out_dir)}/")
    print("  results_run1..N.csv (submission format), results_wide.csv, results_long.csv, results_meta.json")
    n_err = sum(1 for run in all_runs for r in run if r["error"])
    if n_err:
        print(f"  ⚠ {n_err} request error(s) recorded in the CSVs")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
