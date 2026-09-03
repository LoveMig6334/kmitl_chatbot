#!/usr/bin/env bash
# Run the full stack locally: FastAPI backend (uvicorn) + Next.js frontend.
# Ctrl-C stops both.  Logs are tee'd to .cache/dev/{fastapi,web}.log so
# scripts/smoke_web.py can check the backend saw a client disconnect.
#
#   scripts/dev.sh                          # ANSWERER=rag; RETRIEVER=chroma when retrieval/data/{chroma,bm25.pkl} exist, else fixture; ports 8000 / 3000
#   RETRIEVER=fixture scripts/dev.sh        # force the keyword fixture retriever
#   ANSWERER=stub scripts/dev.sh            # fake answers, no ThaiLLM calls
#   API_PORT=8001 WEB_PORT=3001 scripts/dev.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT/.cache/dev"
mkdir -p "$LOG_DIR"

API_PORT="${API_PORT:-8000}"
WEB_PORT="${WEB_PORT:-3000}"
export ANSWERER="${ANSWERER:-rag}"
if [[ -z "${RETRIEVER:-}" ]]; then
  if [[ -d "$ROOT/retrieval/data/chroma" && -f "$ROOT/retrieval/data/bm25.pkl" ]]; then
    RETRIEVER=chroma
  else
    RETRIEVER=fixture
    echo "note: retrieval index not built (python scripts/build_index.py) — using RETRIEVER=fixture" >&2
  fi
fi
export RETRIEVER
export FASTAPI_URL="${FASTAPI_URL:-http://localhost:${API_PORT}}"
export ALLOWED_ORIGINS="${ALLOWED_ORIGINS:-http://localhost:${WEB_PORT}}"

if [[ ! -f "$ROOT/.env" ]] || ! grep -q '^THAILLM_API_KEY=.\+' "$ROOT/.env"; then
  echo "warning: $ROOT/.env has no THAILLM_API_KEY — in-scope answers will fail (cp .env.example .env)" >&2
fi
if [[ ! -d "$ROOT/web/node_modules" ]]; then
  echo "==> npm install (web/)"
  (cd "$ROOT/web" && npm install)
fi

cleanup() {
  trap - INT TERM EXIT
  echo
  echo "==> stopping fastapi + next"
  kill 0 2>/dev/null || true   # whole process group: uvicorn, next, tee
  wait 2>/dev/null || true
}
trap cleanup INT TERM EXIT

echo "==> fastapi  http://localhost:${API_PORT}  (ANSWERER=$ANSWERER RETRIEVER=$RETRIEVER, log: $LOG_DIR/fastapi.log)"
(
  cd "$ROOT"
  exec uv run uvicorn api.main:app --host 127.0.0.1 --port "$API_PORT" 2>&1 | tee "$LOG_DIR/fastapi.log"
) &

echo "==> next     http://localhost:${WEB_PORT}/chat  (FASTAPI_URL=$FASTAPI_URL, log: $LOG_DIR/web.log)"
(
  cd "$ROOT/web"
  exec npm run dev -- --port "$WEB_PORT" 2>&1 | tee "$LOG_DIR/web.log"
) &

wait
