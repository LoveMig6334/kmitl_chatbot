#!/bin/sh
# Pack the retrieval index + curriculum PDFs for the deployment image (see fetch_assets.sh).
#   sh scripts/space/pack_assets.sh [out.tar.gz]     (default: .cache/assets.tar.gz)
set -eu
root="$(cd "$(dirname "$0")/../.." && pwd)"
out="${1:-$root/.cache/assets.tar.gz}"
mkdir -p "$(dirname "$out")"
cd "$root"
tar -czf "$out" retrieval/data/chroma retrieval/data/bm25.pkl data/raw/AIT.pdf data/raw/DSBA.pdf data/raw/IT2565.pdf data/raw/IT_inter2565.pdf
ls -la "$out"
