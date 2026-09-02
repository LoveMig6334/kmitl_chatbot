#!/usr/bin/env python3
"""Smoke-test the Next.js ``/api/chat`` proxy against a running FastAPI backend.

Both servers must already be running (``scripts/dev.sh``).  Requests go to the
Next.js route, *not* to FastAPI directly, so the whole browser path is covered:

  a. in-scope Thai question  -> meta(in_scope), delta lines, a citations line, done
  b. off-topic question      -> meta(not in_scope), delta lines, NO citations line, done
  c. aborted request         -> socket closed after the first delta; the FastAPI
                                request log must then show status="disconnected"
                                for that conversation_id (no orphaned stream)

  python scripts/smoke_web.py
  python scripts/smoke_web.py --web http://localhost:3000 --api http://localhost:8000 \
                              --fastapi-log .cache/dev/fastapi.log

Only the standard library is used.  Exit code 1 if any check fails.
"""

from __future__ import annotations

import argparse
import http.client
import json
import socket
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen

IN_SCOPE_Q = "AIT เรียนกี่หน่วยกิต"
OFF_TOPIC_Q = "ขอสูตรต้มยำกุ้ง"


@dataclass
class Result:
    name: str
    ok: bool
    detail: str = ""


@dataclass
class Stream:
    """Parsed ``data: {...}`` lines from the Next.js route."""

    meta: dict | None = None
    deltas: list[str] = field(default_factory=list)
    citations: list[dict] | None = None  # None = no citations line at all
    done: dict | None = None
    error: dict | None = None
    status: int = 0

    @property
    def text(self) -> str:
        return "".join(self.deltas)


def _conn(url: str, timeout: float) -> tuple[http.client.HTTPConnection, str]:
    u = urlparse(url)
    port = u.port or (443 if u.scheme == "https" else 80)
    cls = http.client.HTTPSConnection if u.scheme == "https" else http.client.HTTPConnection
    return cls(u.hostname or "localhost", port, timeout=timeout), u.path.rstrip("/")


def _iter_payloads(resp: http.client.HTTPResponse):
    """Yield the JSON payload of every ``data:`` line as it arrives."""
    while True:
        line = resp.readline()
        if not line:
            return
        line = line.strip()
        if not line.startswith(b"data:"):
            continue
        try:
            yield json.loads(line[5:].strip())
        except json.JSONDecodeError:
            continue


def chat(web: str, question: str, conversation_id: str, *, timeout: float, abort_after_first_delta: bool = False) -> Stream:
    conn, base = _conn(web, timeout)
    body = json.dumps({
        "messages": [{"role": "user", "content": question}],
        "facultyScope": [],
        "conversationId": conversation_id,
    })
    out = Stream()
    try:
        conn.request("POST", f"{base}/api/chat", body=body, headers={"Content-Type": "application/json"})
        resp = conn.getresponse()
        out.status = resp.status
        if resp.status != 200:
            out.error = {"code": f"http_{resp.status}", "message": resp.read(2000).decode("utf-8", "replace")}
            return out
        for payload in _iter_payloads(resp):
            if "meta" in payload:
                out.meta = payload["meta"]
            elif "delta" in payload:
                out.deltas.append(payload["delta"])
                if abort_after_first_delta:
                    # Hard close: the Next.js server sees the socket drop and must abort upstream.
                    try:
                        conn.sock.shutdown(socket.SHUT_RDWR)
                    except OSError:
                        pass
                    return out
            elif "citations" in payload:
                out.citations = payload["citations"]
            elif "done" in payload:
                out.done = payload
            elif "error" in payload:
                out.error = payload["error"]
    finally:
        conn.close()
    return out


def wait_for_disconnect_log(log_path: Path, conversation_id: str, timeout: float) -> tuple[bool, str]:
    """Poll the FastAPI request log for status=disconnected on our conversation."""
    deadline = time.monotonic() + timeout
    last_seen = ""
    while time.monotonic() < deadline:
        if log_path.exists():
            for raw in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
                if conversation_id not in raw:
                    continue
                last_seen = raw.strip()
                try:
                    rec = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if rec.get("event") == "chat":
                    status = rec.get("status")
                    if status == "disconnected":
                        return True, f"log: status=disconnected total_ms={rec.get('total_ms')}"
                    return False, f"log: request finished with status={status!r} instead of 'disconnected' -> orphaned stream"
        time.sleep(0.5)
    if not log_path.exists():
        return False, f"log file {log_path} not found (start the backend with scripts/dev.sh or tee uvicorn output there)"
    return False, f"no chat log line for {conversation_id} within {timeout:.0f}s" + (f" (last: {last_seen})" if last_seen else "")


def health(api: str, timeout: float) -> dict | None:
    try:
        with urlopen(f"{api.rstrip('/')}/health", timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception as exc:  # noqa: BLE001 - reported to the user
        print(f"!! FastAPI /health failed: {exc}", file=sys.stderr)
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--web", default="http://localhost:3000", help="Next.js base URL")
    ap.add_argument("--api", default="http://localhost:8000", help="FastAPI base URL (health + log check only)")
    ap.add_argument("--fastapi-log", default=".cache/dev/fastapi.log", help="FastAPI stdout log written by scripts/dev.sh")
    ap.add_argument("--timeout", type=float, default=120.0, help="seconds to wait for a full answer")
    ap.add_argument("--log-wait", type=float, default=30.0, help="seconds to wait for the disconnected log line")
    args = ap.parse_args()

    results: list[Result] = []
    run = uuid.uuid4().hex[:8]

    h = health(args.api, 10)
    if h is None:
        results.append(Result("health", False, "FastAPI not reachable"))
    else:
        results.append(Result("health", h.get("status") == "ok", f"answerer={h.get('answerer')}"))
        if h.get("answerer") != "rag":
            print(f"!! answerer={h.get('answerer')!r}; run the backend with ANSWERER=rag RETRIEVER=fixture for real citations", file=sys.stderr)

    # (a) in scope --------------------------------------------------------------
    print(f"[a] in-scope: {IN_SCOPE_Q!r}")
    try:
        s = chat(args.web, IN_SCOPE_Q, f"smoke-inscope-{run}", timeout=args.timeout)
        mock = bool(s.meta and s.meta.get("mock"))
        cat = (s.meta or {}).get("category")
        results.append(Result("a: meta in_scope", cat == "in_scope" and not mock, f"category={cat} mock={mock} status={s.status}"))
        results.append(Result("a: delta lines", len(s.deltas) > 0, f"{len(s.deltas)} deltas, {len(s.text)} chars"))
        results.append(Result("a: citations line", s.citations is not None, f"{len(s.citations or [])} citations" if s.citations is not None else "missing"))
        results.append(Result("a: done", bool(s.done) and not s.done.get("partial"), f"done={s.done} error={s.error}"))
        print(f"    answer: {s.text[:160]!r}")
    except Exception as exc:  # noqa: BLE001
        results.append(Result("a: request", False, repr(exc)))

    # (b) off topic -------------------------------------------------------------
    print(f"[b] off-topic: {OFF_TOPIC_Q!r}")
    try:
        s = chat(args.web, OFF_TOPIC_Q, f"smoke-offtopic-{run}", timeout=args.timeout)
        cat = (s.meta or {}).get("category")
        mock = bool(s.meta and s.meta.get("mock"))
        results.append(Result("b: meta not in_scope", cat is not None and cat != "in_scope" and not mock, f"category={cat} mock={mock}"))
        results.append(Result("b: delta lines", len(s.deltas) > 0, f"{len(s.deltas)} deltas"))
        results.append(Result("b: no citations line", s.citations is None, "absent" if s.citations is None else f"present: {s.citations}"))
        results.append(Result("b: done", bool(s.done) and not s.done.get("partial"), f"done={s.done} error={s.error}"))
        print(f"    reply: {s.text[:160]!r}")
    except Exception as exc:  # noqa: BLE001
        results.append(Result("b: request", False, repr(exc)))

    # (c) abort after the first delta ------------------------------------------
    conv = f"smoke-abort-{run}"
    print(f"[c] abort after first delta (conversation_id={conv})")
    try:
        s = chat(args.web, IN_SCOPE_Q, conv, timeout=args.timeout, abort_after_first_delta=True)
        results.append(Result("c: first delta received", len(s.deltas) == 1, f"deltas={len(s.deltas)} status={s.status} error={s.error}"))
        ok, detail = wait_for_disconnect_log(Path(args.fastapi_log), conv, args.log_wait)
        results.append(Result("c: backend logged disconnected", ok, detail))
        h2 = health(args.api, 10)
        results.append(Result("c: backend healthy after abort", bool(h2) and h2.get("status") == "ok", str(h2)))
    except Exception as exc:  # noqa: BLE001
        results.append(Result("c: request", False, repr(exc)))

    # table ---------------------------------------------------------------------
    width = max(len(r.name) for r in results)
    print()
    print(f"{'check'.ljust(width)}  result  detail")
    print(f"{'-' * width}  ------  ------")
    for r in results:
        print(f"{r.name.ljust(width)}  {'PASS' if r.ok else 'FAIL':6}  {r.detail}")
    failed = [r for r in results if not r.ok]
    print()
    print(f"{len(results) - len(failed)}/{len(results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
