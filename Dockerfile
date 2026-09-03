# Backend container (Render free web service, 512 MB RAM): FastAPI gatekeeper + RAG with the
# chroma retriever.  BGE-M3 query vectors come from a hosted API (EMBED_API, rag/remote_embedder.py)
# so no torch / FlagEmbedding is installed — the image is ~600 MB and idles at ~260 MB RSS.
#
# Layers, most stable first: dependencies (uv.lock) → application code + chunk index + PDFs.
# The chroma index and the PDFs are gitignored on GitHub and pulled in at build time by
# scripts/space/fetch_assets.sh from ASSETS_URL (a private Hugging Face dataset, read with
# HF_TOKEN).  Render passes service env vars to the build as build args when declared with ARG.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    HF_HUB_DISABLE_TELEMETRY=1

RUN useradd -m -u 1000 user \
    && apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /usr/local/bin/uv

WORKDIR /app

# 1. dependencies only (no optional local-embed extra → no torch)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# 2. application code (+ chroma index and PDFs when present in the build context)
COPY --chown=user:user . .
RUN uv sync --frozen --no-dev && chown -R user:user /app

# 3. index + PDFs from a release asset when they are not in the build context
# HF_TOKEN is read by the script from its environment (build ARGs are env vars inside RUN) and is
# deliberately NOT referenced on the RUN line: BuildKit prints expanded ARG values in the step title.
ARG ASSETS_URL=""
ARG HF_TOKEN=""
RUN if [ -n "$ASSETS_URL" ]; then sh scripts/space/fetch_assets.sh "$ASSETS_URL" && chown -R user:user /app; fi

USER user
ENV ANSWERER=rag \
    RETRIEVER=chroma \
    EMBED_API=hf \
    EMBED_KEEPALIVE_S=240 \
    WARM_UP=1 \
    RERANK=0 \
    RETRIEVAL_K=12 \
    RETRIEVE_CAND_K=40 \
    CONTEXT_TOKEN_BUDGET=6500 \
    RETRIEVAL_MIN_SCORE_CHROMA=0.0 \
    ANSWER_EVENT_TIMEOUT_S=120 \
    PDF_DIR=/app/data/raw \
    TRUST_PROXY=1 \
    PORT=10000

EXPOSE 10000
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT}"]
