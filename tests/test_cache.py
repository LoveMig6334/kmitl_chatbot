"""The eval-only response cache must short-circuit identical requests."""

import asyncio
import json

import gatekeeper.llm as llm
from gatekeeper.config import Settings
from gatekeeper.llm import cache_key, call_classifier


def test_cache_hit_avoids_second_request(tmp_path, monkeypatch):
    calls = []

    async def fake_request(message, settings):
        calls.append(message)
        return '{"category": "in_scope"}'

    monkeypatch.setattr(llm, "request_completion", fake_request)
    settings = Settings(api_key="x", cache_dir=str(tmp_path))

    r1 = asyncio.run(call_classifier("hello", settings))
    r2 = asyncio.run(call_classifier("hello", settings))
    r3 = asyncio.run(call_classifier("different", settings))
    assert calls == ["hello", "different"]
    assert r1.cached is False and r2.cached is True and r3.cached is False
    assert r1.text == r2.text == '{"category": "in_scope"}'

    files = list(tmp_path.glob("*.json"))
    assert len(files) == 2
    payload = json.loads(files[0].read_text(encoding="utf-8"))
    assert set(payload) == {"model", "text", "created_at"}


def test_cache_key_depends_on_model_prompt_and_message():
    k = cache_key("m1", "msg")
    assert k == cache_key("m1", "msg")
    assert k != cache_key("m2", "msg")
    assert k != cache_key("m1", "msg2")
    assert k != cache_key("m1", "msg", system_prompt="other prompt")
    assert len(k) == 64


def test_no_cache_dir_means_no_files(tmp_path, monkeypatch):
    async def fake_request(message, settings):
        return "{}"

    monkeypatch.setattr(llm, "request_completion", fake_request)
    asyncio.run(call_classifier("hello", Settings(api_key="x", cache_dir=None)))
    assert list(tmp_path.iterdir()) == []
