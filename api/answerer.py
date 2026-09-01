"""RAG interface consumed by the API.  The RAG teammate implements ``Answerer``.

Keep this module minimal and stable — the frontend builds against the event
shapes below, and ``StubAnswerer`` lets it integrate before RAG exists.

Cancellation contract: when the client disconnects the API stops iterating and
calls ``aclose()`` on the async generator returned by ``answer()``.  An
implementation must therefore release/cancel its upstream ThaiLLM stream in a
``try/finally`` (or ``except GeneratorExit``) around its streaming loop.
"""

from __future__ import annotations

import asyncio
import importlib
import os
import re
from collections.abc import AsyncIterator
from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from gatekeeper.schema import FACULTY, GateDecision


class Turn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=8000)


class Citation(BaseModel):
    faculty: str = FACULTY  # always "IT" — single faculty in scope
    program: str | None = None  # AIT | DSBA | BIT | IT
    page: int
    chunk_id: str
    snippet: str | None = None


class AnswerEvent(BaseModel):
    type: Literal["token", "citations", "done"]
    text: str | None = None  # for token
    citations: list[Citation] | None = None  # for citations
    model_used: str | None = None  # for done


@runtime_checkable
class Answerer(Protocol):
    name: str

    def answer(
        self,
        message: str,
        decision: GateDecision,
        scope: list[str] | None,
        history: list[Turn],
    ) -> AsyncIterator[AnswerEvent]: ...


_TOKEN_RE = re.compile(r"\S+\s*|\s+")


def tokenize(text: str, max_len: int = 6) -> list[str]:
    """Split text into small streaming chunks (Thai has no spaces, so cap length)."""
    out: list[str] = []
    for piece in _TOKEN_RE.findall(text):
        while len(piece) > max_len:
            out.append(piece[:max_len])
            piece = piece[max_len:]
        if piece:
            out.append(piece)
    return out


class StubAnswerer:
    """Streams a fixed Thai notice token by token with one fake citation.

    ``cancelled`` / ``completed`` are recorded so tests (and logs) can verify
    that a client disconnect really stopped the stream.
    """

    name = "stub"

    def __init__(self, delay: float = 0.0):
        self.delay = delay
        self.cancelled = False
        self.completed = False

    async def answer(
        self,
        message: str,
        decision: GateDecision,
        scope: list[str] | None,
        history: list[Turn],
    ) -> AsyncIterator[AnswerEvent]:
        self.cancelled = False
        self.completed = False
        programs = ", ".join(decision.programs) if decision.programs else "ไม่ระบุ"
        text = f"ระบบค้นหายังไม่พร้อม — คำถามนี้ถูกจัดเป็น {decision.category}, หลักสูตร {programs}"
        try:
            for tok in tokenize(text):
                yield AnswerEvent(type="token", text=tok)
                if self.delay:
                    await asyncio.sleep(self.delay)
            yield AnswerEvent(
                type="citations",
                citations=[
                    Citation(program=decision.program, page=1, chunk_id="stub-p1-c0", snippet="(stub) ยังไม่มีการค้นหาเอกสารจริง")
                ],
            )
            yield AnswerEvent(type="done", model_used=None)
            self.completed = True
        finally:
            if not self.completed:
                self.cancelled = True  # upstream stream would be cancelled here


def get_answerer() -> Answerer:
    """Select the implementation from ``ANSWERER=stub|rag`` (default stub)."""
    kind = (os.environ.get("ANSWERER") or "stub").strip().lower()
    if kind == "stub":
        return StubAnswerer(delay=float(os.environ.get("STUB_TOKEN_DELAY_S", "0.02")))
    if kind == "rag":
        try:
            module = importlib.import_module("rag.answerer")
            cls = module.RagAnswerer
        except (ImportError, AttributeError) as exc:
            raise RuntimeError(
                "ANSWERER=rag but rag.answerer:RagAnswerer is not available "
                f"({exc}). Install the RAG package or set ANSWERER=stub."
            ) from exc
        return cls()
    raise RuntimeError(f"Unknown ANSWERER={kind!r}; expected 'stub' or 'rag'.")
