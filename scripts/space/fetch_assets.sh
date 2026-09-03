#!/bin/sh
# Download the retrieval index + curriculum PDFs (gitignored on GitHub) into the image at build time.
#   HF_TOKEN=… sh scripts/space/fetch_assets.sh https://huggingface.co/datasets/<user>/<repo>/resolve/main/assets.tar.gz
# HF_TOKEN (optional) is sent as a bearer token so a private Hugging Face dataset works.
# The tarball is produced by scripts/space/pack_assets.sh and contains
#   retrieval/data/chroma/**  retrieval/data/bm25.pkl  data/raw/*.pdf
set -eu
url="$1"
echo "==> fetching assets from $url"
if [ -n "${HF_TOKEN:-}" ]; then
  echo "    (with HF_TOKEN, ${#HF_TOKEN} chars)"
  status=$(curl -sSL --retry 3 -H "Authorization: Bearer $HF_TOKEN" -o /tmp/assets.tar.gz -w '%{http_code}' "$url")
else
  echo "    (no HF_TOKEN — the dataset must be public)"
  status=$(curl -sSL --retry 3 -o /tmp/assets.tar.gz -w '%{http_code}' "$url")
fi
if [ "$status" != "200" ]; then
  echo "!! asset download failed with HTTP $status" >&2
  case "$status" in
    401|403) echo "!! HF_TOKEN is missing, invalid, or lacks 'Read access to contents of all repos under your personal namespace' (the dataset is private)" >&2 ;;
    404) echo "!! ASSETS_URL not found: $url" >&2 ;;
  esac
  exit 1
fi
tar -xzf /tmp/assets.tar.gz -C "$(dirname "$0")/../.."
rm -f /tmp/assets.tar.gz
ls -la retrieval/data/chroma data/raw
