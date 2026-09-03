"""``RemoteEmbedder`` — BGE-M3 dense vectors from an HTTP API instead of a local torch model."""

from __future__ import annotations

import json

import httpx
import numpy as np
import pytest

from rag.remote_embedder import RemoteEmbedder


def _hf_server(calls: list[dict], fail_first: int = 0):
    state = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        state["n"] += 1
        calls.append({"url": str(request.url), "auth": request.headers.get("authorization"), "body": json.loads(request.content)})
        if state["n"] <= fail_first:
            return httpx.Response(504, text="Gateway Time-out")
        inputs = calls[-1]["body"]["inputs"]
        return httpx.Response(200, json=[[3.0, 4.0] for _ in inputs])

    return httpx.MockTransport(handler)


def test_hf_backend_posts_inputs_and_normalises():
    calls: list[dict] = []
    emb = RemoteEmbedder(api="hf", model="BAAI/bge-m3", token="tok", transport=_hf_server(calls), sleep=lambda _s: None)
    out = emb.encode(["a", "b"], max_length=512, return_dense=True, return_sparse=False, return_colbert_vecs=False)
    vecs = out["dense_vecs"]
    assert isinstance(vecs, np.ndarray) and vecs.shape == (2, 2)
    assert np.allclose(vecs, [[0.6, 0.8], [0.6, 0.8]])
    assert calls[0]["url"] == "https://router.huggingface.co/hf-inference/models/BAAI/bge-m3/pipeline/feature-extraction"
    assert calls[0]["auth"] == "Bearer tok"
    assert calls[0]["body"] == {"inputs": ["a", "b"]}


def test_hf_backend_retries_on_5xx():
    calls: list[dict] = []
    slept: list[float] = []
    emb = RemoteEmbedder(api="hf", model="BAAI/bge-m3", token=None, transport=_hf_server(calls, fail_first=2), max_attempts=4, sleep=slept.append)
    vecs = emb.encode(["q"])["dense_vecs"]
    assert vecs.shape == (1, 2)
    assert len(calls) == 3 and len(slept) == 2
    assert calls[0]["auth"] is None


def test_hf_backend_gives_up():
    emb = RemoteEmbedder(api="hf", model="m", token=None, transport=_hf_server([], fail_first=99), max_attempts=2, sleep=lambda _s: None)
    with pytest.raises(RuntimeError, match="embedding API"):
        emb.encode(["q"])


def test_openai_backend():
    calls: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append({"url": str(request.url), "body": json.loads(request.content)})
        return httpx.Response(200, json={"data": [{"index": 1, "embedding": [0.0, 1.0]}, {"index": 0, "embedding": [1.0, 0.0]}]})

    emb = RemoteEmbedder(api="openai", url="https://api.example/v1/", model="@cf/baai/bge-m3", token="k", transport=httpx.MockTransport(handler))
    vecs = emb.encode(["first", "second"])["dense_vecs"]
    assert calls[0]["url"] == "https://api.example/v1/embeddings"
    assert calls[0]["body"] == {"model": "@cf/baai/bge-m3", "input": ["first", "second"]}
    assert np.allclose(vecs, [[1.0, 0.0], [0.0, 1.0]])  # re-ordered by index


def test_from_env(monkeypatch):
    monkeypatch.delenv("EMBED_API", raising=False)
    assert RemoteEmbedder.from_env() is None
    monkeypatch.setenv("EMBED_API", "hf")
    monkeypatch.setenv("HF_TOKEN", "t")
    emb = RemoteEmbedder.from_env()
    assert emb is not None and emb.api == "hf" and emb.model == "BAAI/bge-m3" and emb.token == "t"
    monkeypatch.setenv("EMBED_API", "openai")
    monkeypatch.setenv("EMBED_API_URL", "https://x/v1")
    monkeypatch.setenv("EMBED_API_KEY", "k")
    monkeypatch.setenv("EMBED_MODEL", "custom")
    emb = RemoteEmbedder.from_env()
    assert emb is not None and (emb.api, emb.url, emb.token, emb.model) == ("openai", "https://x/v1", "k", "custom")
    monkeypatch.setenv("EMBED_API", "bogus")
    from rag.remote_embedder import UnavailableEmbedder

    assert isinstance(RemoteEmbedder.from_env(), UnavailableEmbedder)


def test_keepalive_pings_and_swallows_errors():
    calls: list[dict] = []
    emb = RemoteEmbedder(api="hf", model="m", token=None, transport=_hf_server(calls, fail_first=99), max_attempts=1, sleep=lambda _s: None)
    emb.keepalive_once()  # API down → logged, not raised
    assert len(calls) == 1
    ok = RemoteEmbedder(api="hf", model="m", token=None, transport=_hf_server(calls), sleep=lambda _s: None)
    ok.keepalive_once()
    assert calls[-1]["body"] == {"inputs": ["ping"]}


def test_from_env_starts_keepalive(monkeypatch):
    started: list[float] = []
    monkeypatch.setattr(RemoteEmbedder, "start_keepalive", lambda self, s: started.append(s))
    monkeypatch.setenv("EMBED_API", "hf")
    monkeypatch.setenv("EMBED_KEEPALIVE_S", "300")
    RemoteEmbedder.from_env()
    assert started == [300.0]


def test_failures_raise_embedding_unavailable():
    from rag.remote_embedder import EmbeddingUnavailable

    down = RemoteEmbedder(api="hf", model="m", token=None, transport=_hf_server([], fail_first=99), max_attempts=1, sleep=lambda _s: None)
    with pytest.raises(EmbeddingUnavailable):
        down.encode(["q"])

    def reject(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "bad token"})

    bad = RemoteEmbedder(api="hf", model="m", token="x", transport=httpx.MockTransport(reject))
    with pytest.raises(EmbeddingUnavailable, match="401"):
        bad.encode(["q"])


def test_from_env_misconfiguration_degrades_instead_of_crashing(monkeypatch):
    from rag.remote_embedder import EmbeddingUnavailable

    monkeypatch.setenv("EMBED_API", "openai")
    monkeypatch.delenv("EMBED_API_URL", raising=False)
    emb = RemoteEmbedder.from_env()
    assert emb is not None
    with pytest.raises(EmbeddingUnavailable, match="EMBED_API_URL"):
        emb.encode(["q"])
    emb.ping()  # never raises
