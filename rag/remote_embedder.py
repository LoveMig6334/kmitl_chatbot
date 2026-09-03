"""``RemoteEmbedder`` — BGE-M3 dense query vectors from a hosted API instead of a local torch model.

Selected with ``EMBED_API`` (see :meth:`RemoteEmbedder.from_env`); ``retrieval/index.py:load_embedder``
returns it in place of ``BGEM3FlagModel`` so the vendored retriever needs no torch / FlagEmbedding
(the free hosting tiers have ~512 MB RAM).  The interface is the subset of ``BGEM3FlagModel`` the
retriever uses: ``encode(texts, **kw)["dense_vecs"]`` → ``np.ndarray`` of L2-normalised rows.
Verified on 2026-09-03: HF Inference vectors for ``BAAI/bge-m3`` equal the local ones (cosine 1.0000),
so the Chroma index built locally is used unchanged.

Backends
* ``hf``     — Hugging Face Inference (``router.huggingface.co``), ``{"inputs": [...]}`` → list of vectors.
             Cold models answer 5xx for ~30–60 s, hence the retry loop.
* ``openai`` — any OpenAI-compatible ``POST {url}/embeddings`` (Cloudflare Workers AI, SiliconFlow, …).

Only the user's question is sent (never documents); see README "Deployment" for the competition note.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from collections.abc import Callable
from typing import Any

import httpx
import numpy as np

log = logging.getLogger(__name__)

DEFAULT_MODEL = "BAAI/bge-m3"
HF_URL = "https://router.huggingface.co/hf-inference/models/{model}/pipeline/feature-extraction"
APIS = ("hf", "openai")


class RemoteEmbedder:
    name = "remote"

    def __init__(
        self,
        *,
        api: str,
        model: str = DEFAULT_MODEL,
        url: str | None = None,
        token: str | None = None,
        timeout_s: float = 30.0,
        max_attempts: int = 5,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if api not in APIS:
            raise ValueError(f"EMBED_API={api!r}; expected one of {APIS}")
        self.api = api
        self.model = model
        self.token = token
        if api == "openai":
            if not url:
                raise ValueError("EMBED_API_URL is required for EMBED_API=openai")
            self.url = url.rstrip("/")
        else:
            self.url = url or HF_URL.format(model=model)
        self.max_attempts = max(1, max_attempts)
        self._sleep = sleep
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        self._client = httpx.Client(timeout=timeout_s, headers=headers, transport=transport)

    @classmethod
    def from_env(cls) -> RemoteEmbedder | None:
        """``EMBED_API`` unset → ``None`` (use the local model).  Env: ``EMBED_API=hf|openai``,
        ``EMBED_MODEL``, ``EMBED_API_URL`` (openai base URL), ``EMBED_API_KEY`` (or ``HF_TOKEN`` for hf),
        ``EMBED_API_TIMEOUT_S``, ``EMBED_API_MAX_ATTEMPTS``."""
        api = (os.environ.get("EMBED_API") or "").strip().lower()
        if not api:
            return None
        token = os.environ.get("EMBED_API_KEY") or (os.environ.get("HF_TOKEN") if api == "hf" else None)
        if api == "hf" and not token:  # local dev: reuse the `hf auth login` token
            try:
                from huggingface_hub import get_token

                token = get_token()
            except ImportError:  # pragma: no cover - optional dependency
                token = None
        emb = cls(
            api=api,
            model=os.environ.get("EMBED_MODEL") or DEFAULT_MODEL,
            url=os.environ.get("EMBED_API_URL") or None,
            token=token or None,
            timeout_s=float(os.environ.get("EMBED_API_TIMEOUT_S", "30")),
            max_attempts=int(os.environ.get("EMBED_API_MAX_ATTEMPTS", "5")),
        )
        keepalive = float(os.environ.get("EMBED_KEEPALIVE_S", "0") or 0)
        if keepalive > 0:
            emb.start_keepalive(keepalive)
        return emb

    def describe(self) -> str:
        return f"{self.api} {self.model} @ {self.url}"

    # ---- keep-alive: HF Inference unloads idle models and then answers 5xx for ~a minute ---------
    def keepalive_once(self) -> None:
        try:
            self.encode(["ping"])
        except (RuntimeError, ValueError) as exc:  # never crash the server over a ping
            log.warning("embedding keep-alive ping failed: %s", exc)

    def start_keepalive(self, interval_s: float) -> None:
        """Ping the API every ``interval_s`` seconds from a daemon thread (``EMBED_KEEPALIVE_S``)."""

        def loop() -> None:
            while True:
                time.sleep(interval_s)
                self.keepalive_once()

        threading.Thread(target=loop, name="embed-keepalive", daemon=True).start()
        log.info("embedding keep-alive every %.0fs", interval_s)

    # ---- BGEM3FlagModel-compatible surface -------------------------------------------------
    def encode(self, texts: list[str] | str, **_: Any) -> dict[str, np.ndarray]:
        if isinstance(texts, str):
            texts = [texts]
        vecs = self._request(list(texts))
        arr = np.asarray(vecs, dtype=np.float32)
        if arr.ndim != 2 or arr.shape[0] != len(texts):
            raise RuntimeError(f"embedding API returned shape {arr.shape} for {len(texts)} inputs")
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return {"dense_vecs": arr / norms}

    # ---- HTTP ---------------------------------------------------------------------------------
    def _request(self, texts: list[str]) -> list[list[float]]:
        if self.api == "hf":
            url, body = self.url, {"inputs": texts}
        else:
            url, body = f"{self.url}/embeddings", {"model": self.model, "input": texts}
        last: str = ""
        for attempt in range(self.max_attempts):
            try:
                r = self._client.post(url, json=body)
                if r.status_code < 500 and r.status_code != 429:
                    r.raise_for_status()
                    return self._parse(r.json(), len(texts))
                last = f"HTTP {r.status_code}: {r.text[:120]}"
            except httpx.HTTPStatusError as exc:
                raise RuntimeError(f"embedding API rejected the request ({exc.response.status_code}): {exc.response.text[:200]}") from exc
            except httpx.HTTPError as exc:
                last = f"{type(exc).__name__}: {exc}"
            if attempt + 1 < self.max_attempts:
                wait = min(2.0 ** attempt, 10.0)
                log.warning("embedding API attempt %d/%d failed (%s); retrying in %.0fs", attempt + 1, self.max_attempts, last, wait)
                self._sleep(wait)
        raise RuntimeError(f"embedding API unavailable after {self.max_attempts} attempts: {last}")

    def _parse(self, data: Any, n: int) -> list[list[float]]:
        if self.api == "openai":
            rows = sorted(data["data"], key=lambda d: d["index"])
            return [row["embedding"] for row in rows]
        # hf: a list of vectors; a single input may come back as one flat vector
        if n == 1 and data and not isinstance(data[0], list):
            return [data]
        return data
