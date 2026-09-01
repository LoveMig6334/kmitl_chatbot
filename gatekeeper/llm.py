"""ThaiLLM classification call (layer 2).  One chat-completion request.

Reuses the project's OpenAI-compatible client configuration (see
``src/main.py``): same base URL, API key, user agent and model registry.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from .config import USER_AGENT, Settings, load_settings
from .prompts import SYSTEM_PROMPT, build_user_prompt

log = logging.getLogger(__name__)

_client_cache: dict[tuple[str, str | None, float], object] = {}


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


class LLMCallError(RuntimeError):
    pass


async def call_classifier(message: str, settings: Settings | None = None) -> LLMResponse:
    """Send ONE classification request (no retry here) and return the raw text."""
    settings = settings or load_settings()
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
    text = (resp.choices[0].message.content or "") if resp.choices else ""
    return LLMResponse(text=text, model=settings.model, attempts=1)
