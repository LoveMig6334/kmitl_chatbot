# Hugging Face Space (Docker SDK, free CPU basic): FastAPI gatekeeper + RAG with the chroma retriever.
#
# Layers, most stable first: dependencies (uv.lock) -> BGE-M3 weights (~2.2 GB, baked in so a
# sleeping Space wakes in seconds) -> application code + index + PDFs (Git LFS on the Space).
# Spaces require the app to listen on 7860 and to run as uid 1000.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    HF_HOME=/home/user/.cache/huggingface \
    HF_HUB_DISABLE_TELEMETRY=1

RUN useradd -m -u 1000 user \
    && apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /usr/local/bin/uv

WORKDIR /app

# 1. dependencies only (torch resolves to the CPU index on Linux via pyproject [tool.uv.sources])
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# 2. embedding model weights
COPY scripts/space/download_models.py scripts/space/download_models.py
RUN mkdir -p "$HF_HOME" && python scripts/space/download_models.py && chown -R user:user /home/user

# 3. application code, chunk data, index and PDFs
COPY --chown=user:user . .
RUN uv sync --frozen --no-dev && chown -R user:user /app

USER user
ENV ANSWERER=rag \
    RETRIEVER=chroma \
    WARM_UP=1 \
    RERANK=0 \
    RERANK_DEVICE=cpu \
    RETRIEVAL_K=12 \
    RETRIEVE_CAND_K=40 \
    CONTEXT_TOKEN_BUDGET=6500 \
    RETRIEVAL_MIN_SCORE_CHROMA=0.0 \
    PDF_DIR=/app/data/raw \
    TRUST_PROXY=1

EXPOSE 7860
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "7860"]
