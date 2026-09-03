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
  curl -fsSL --retry 3 -H "Authorization: Bearer $HF_TOKEN" -o /tmp/assets.tar.gz "$url"
else
  curl -fsSL --retry 3 -o /tmp/assets.tar.gz "$url"
fi
tar -xzf /tmp/assets.tar.gz -C "$(dirname "$0")/../.."
rm -f /tmp/assets.tar.gz
ls -la retrieval/data/chroma data/raw
