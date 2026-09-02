"""ThaiLLM classification call (layer 2).  One chat-completion request.

Reuses the project's OpenAI-compatible client configuration (see
``src/main.py``): same base URL, API key, user agent and model registry.

An optional on-disk cache (``Settings.cache_dir``) keyed by
sha256(model + system prompt + message) lets the eval harness re-run without
re-hitting the shared API quota.  Production code leaves ``cache_dir`` unset.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path

from .config import USER_AGENT, Settings, load_settings
from .parsing import parse_verdict
from .prompts import SYSTEM_PROMPT, build_user_prompt

log = logging.getLogger(__name__)

_client_cache: dict[tuple[str, str | None, float], object] = {}
CACHE_STATS = {"hits": 0, "misses": 0}


def get_async_client(settings: Settings):
    """Lazily build (and cache) an ``AsyncOpenAI`` client for the ThaiLLM API."""
    from openai import AsyncOpenAI

    key = (settings.base_url, settings.api_key, settings.timeout_s)
    client = _client_cache.get(key)
    if client is None:
        if not settings.api_key:
            raise RuntimeError("THAILLM_API_KEY is not set. Copy .env.example to .env and fill it in.")
        client = AsyncOpenAI(
            base_url=settings.base_url,
            api_key=settings.api_key,
            default_headers={"User-Agent": USER_AGENT},
            timeout=settings.timeout_s,
            max_retries=0,  # the gatekeeper handles its own single retry
        )
        _client_cache[key] = client
    return client


@dataclass
class LLMResponse:
    text: str
    model: str
    attempts: int
    cached: bool = False


class LLMCallError(RuntimeError):
    pass


def cache_key(model: str, message: str, system_prompt: str = SYSTEM_PROMPT) -> str:
    return hashlib.sha256((model + system_prompt + message).encode("utf-8")).hexdigest()


def _cache_path(settings: Settings, message: str) -> Path | None:
    if not settings.cache_dir:
        return None
    return Path(settings.cache_dir) / f"{cache_key(settings.model, message)}.json"


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
    except OSError as exc:  # cache failures must never break classification
        log.warning("gatekeeper cache write failed: %s", exc)


async def request_completion(message: str, settings: Settings) -> str:
    """Perform the raw ThaiLLM request and return the response text."""
    client = get_async_client(settings)
    resp = await asyncio.wait_for(
        client.chat.completions.create(
            model=settings.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(message)},
            ],
            max_tokens=settings.max_tokens,
            temperature=settings.temperature,
        ),
        timeout=settings.timeout_s + 1.0,
    )
    return (resp.choices[0].message.content or "") if resp.choices else ""


async def call_classifier(message: str, settings: Settings | None = None) -> LLMResponse:
    """Send ONE classification request (no retry here) and return the raw text."""
    settings = settings or load_settings()
    path = _cache_path(settings, message)
    cached = _cache_read(path)
    if cached is not None:
        CACHE_STATS["hits"] += 1
        return LLMResponse(text=cached, model=settings.model, attempts=0, cached=True)
    if path is not None:
        CACHE_STATS["misses"] += 1
    text = await request_completion(message, settings)
    if parse_verdict(text) is not None:  # never cache a truncated/unparsable reply: the retry needs a fresh sample
        _cache_write(path, settings.model, text)
    return LLMResponse(text=text, model=settings.model, attempts=1)
