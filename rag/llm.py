"""Streaming ThaiLLM chat calls for the answer layer + settings.

Reuses the gatekeeper's client factory (same base URL / key / user agent) —
there is exactly one HTTP client configuration in the project.  Raw deltas are
yielded as-is (``<think>`` blocks included); ``rag.streaming.ThinkStripper``
removes them downstream.

Optional on-disk cache (``RagSettings.cache_dir``, eval only) keyed by
sha256(model + messages + max_tokens): a cached completion is replayed in small
slices so the streaming code path is exercised even on cache hits.

Environment (all optional, see ``.env.example``):
    RAG_MODEL, RAG_COMPARISON_MODEL, RAG_FALLBACK_MODEL, RAG_REWRITE_MODEL
    RAG_TIMEOUT_S, RAG_FIRST_TOKEN_TIMEOUT_S, RAG_MAX_TOKENS, RAG_THINK_MAX_TOKENS,
    RAG_TEMPERATURE, CONTEXT_TOKEN_BUDGET, RETRIEVAL_K, RETRIEVAL_MIN_SCORE, RETRIEVAL_MIN_SCORE_CHROMA,
    RAG_QUERY_REWRITE, RAG_CACHE_DIR
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import logging
import os
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path

from gatekeeper.config import DEFAULT_BASE_URL
from gatekeeper.config import Settings as GateSettings
from gatekeeper.llm import get_async_client

from .context import DEFAULT_CONTEXT_TOKEN_BUDGET

log = logging.getLogger(__name__)

OPENTHAIGPT = "openthaigpt-thaillm-8b-instruct-v7.2"
PATHUMMA_THINK = "pathumma-thaillm-qwen3-8b-think-3.0.0"
CACHE_STATS = {"hits": 0, "misses": 0}
_REPLAY_SLICE = 8  # chars per delta when replaying a cached completion


@dataclass(frozen=True)
class RagSettings:
    model: str = OPENTHAIGPT  # fact_lookup / descriptive
    # question_kind == comparison.  Default is openthaigpt too: in the answer eval pathumma-think
    # computed derived numbers ("มากกว่า 9 หน่วยกิต", "62,000 บาท") in 2/2 comparison runs despite
    # explicit rules, and was ~2x slower.  Set RAG_COMPARISON_MODEL=pathumma-thaillm-qwen3-8b-think-3.0.0
    # to opt back in; <think> stripping and the first-token fallback are exercised either way.
    comparison_model: str = OPENTHAIGPT
    fallback_model: str = OPENTHAIGPT  # retried once when the primary times out before any visible token
    rewrite_model: str = OPENTHAIGPT
    timeout_s: float = 30.0  # HTTP connect/read timeout (read = max stall between deltas)
    first_token_timeout_s: float = 45.0  # max wait for the first *visible* token (thinking counts as waiting)
    max_tokens: int = 1500  # openthaigpt also emits a <think> block first — leave room for it
    think_max_tokens: int = 2500  # thinking models spend tokens on reasoning first
    rewrite_max_tokens: int = 400  # the rewrite model thinks first too
    temperature: float = 0.0
    context_token_budget: int = DEFAULT_CONTEXT_TOKEN_BUDGET
    k: int = 8
    min_score: float = 0.3  # no-answer gate for FixtureRetriever (IDF-weighted overlap)
    min_score_chroma: float = 0.0  # no-answer gate for ChromaRetriever (normalised RRF, top hit = 1.0); see docs/retrieval-integration.md
    query_rewrite: bool = True
    language_guard: bool = True  # for zh/en answers, one corrective pass if the model drifts to Thai
    base_url: str = DEFAULT_BASE_URL
    api_key: str | None = None
    cache_dir: str | None = None

    def gate_settings(self) -> GateSettings:
        return GateSettings(base_url=self.base_url, api_key=self.api_key, timeout_s=self.timeout_s)


def _env_bool(name: str, default: bool) -> bool:
    v = os.environ.get(name)
    return default if v is None else v.strip().lower() in ("1", "true", "yes", "on")


def load_rag_settings(**overrides: object) -> RagSettings:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:  # pragma: no cover
        pass
    env = os.environ
    values: dict[str, object] = {
        "model": env.get("RAG_MODEL", OPENTHAIGPT),
        "comparison_model": env.get("RAG_COMPARISON_MODEL", OPENTHAIGPT),
        "fallback_model": env.get("RAG_FALLBACK_MODEL", OPENTHAIGPT),
        "rewrite_model": env.get("RAG_REWRITE_MODEL", OPENTHAIGPT),
        "timeout_s": float(env.get("RAG_TIMEOUT_S", "30")),
        "first_token_timeout_s": float(env.get("RAG_FIRST_TOKEN_TIMEOUT_S", "45")),
        "max_tokens": int(env.get("RAG_MAX_TOKENS", "1500")),
        "think_max_tokens": int(env.get("RAG_THINK_MAX_TOKENS", "2500")),
        "temperature": float(env.get("RAG_TEMPERATURE", "0")),
        "context_token_budget": int(env.get("CONTEXT_TOKEN_BUDGET", str(DEFAULT_CONTEXT_TOKEN_BUDGET))),
        "k": int(env.get("RETRIEVAL_K", "8")),
        "min_score": float(env.get("RETRIEVAL_MIN_SCORE", "0.3")),
        "min_score_chroma": float(env.get("RETRIEVAL_MIN_SCORE_CHROMA", "0.0")),
        "query_rewrite": _env_bool("RAG_QUERY_REWRITE", True),
        "language_guard": _env_bool("RAG_LANGUAGE_GUARD", True),
        "base_url": env.get("THAILLM_BASE_URL", DEFAULT_BASE_URL),
        "api_key": env.get("THAILLM_API_KEY"),
        "cache_dir": env.get("RAG_CACHE_DIR") or None,
    }
    values.update({k: v for k, v in overrides.items() if v is not None})
    return RagSettings(**values)  # type: ignore[arg-type]


def with_overrides(settings: RagSettings, **overrides: object) -> RagSettings:
    return dataclasses.replace(settings, **{k: v for k, v in overrides.items() if v is not None})


# --------------------------------------------------------------------------- #
# Cache
# --------------------------------------------------------------------------- #
def cache_key(model: str, messages: list[dict], max_tokens: int) -> str:
    payload = json.dumps({"model": model, "messages": messages, "max_tokens": max_tokens}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _cache_path(settings: RagSettings, model: str, messages: list[dict], max_tokens: int) -> Path | None:
    if not settings.cache_dir:
        return None
    return Path(settings.cache_dir) / f"{cache_key(model, messages, max_tokens)}.json"


def _cache_read(path: Path | None) -> str | None:
    if path is None or not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))["text"]
    except (OSError, ValueError, KeyError):
        return None


def _cache_write(path: Path | None, model: str, text: str) -> None:
    if path is None:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"model": model, "text": text, "created_at": time.time()}, ensure_ascii=False), encoding="utf-8")
    except OSError as exc:  # cache failures must never break answering
        log.warning("rag cache write failed: %s", exc)


# --------------------------------------------------------------------------- #
# Calls
# --------------------------------------------------------------------------- #
async def stream_chat(
    messages: list[dict],
    model: str,
    settings: RagSettings,
    *,
    max_tokens: int | None = None,
) -> AsyncIterator[str]:
    """Yield raw text deltas of one streaming chat completion.

    Closing the generator (``aclose()``) closes the upstream HTTP stream, which
    cancels the request on the ThaiLLM side.
    """
    max_tokens = max_tokens or settings.max_tokens
    path = _cache_path(settings, model, messages, max_tokens)
    cached = _cache_read(path)
    if cached is not None:
        CACHE_STATS["hits"] += 1
        for i in range(0, len(cached), _REPLAY_SLICE):
            yield cached[i : i + _REPLAY_SLICE]
        return
    if path is not None:
        CACHE_STATS["misses"] += 1

    client = get_async_client(settings.gate_settings())
    stream = await client.chat.completions.create(
        model=model,
        messages=messages,  # type: ignore[arg-type]
        max_tokens=max_tokens,
        temperature=settings.temperature,
        stream=True,
    )
    parts: list[str] = []
    completed = False
    try:
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            text = getattr(delta, "content", None)
            if text:
                parts.append(text)
                yield text
        completed = True
    finally:
        await stream.close()
        if completed:
            _cache_write(path, model, "".join(parts))


async def complete_chat(messages: list[dict], model: str, settings: RagSettings, *, max_tokens: int | None = None) -> str:
    """Non-streaming convenience (rewrite step): the joined stream, cache included."""
    parts: list[str] = []
    async for delta in stream_chat(messages, model, settings, max_tokens=max_tokens):
        parts.append(delta)
    return "".join(parts)
