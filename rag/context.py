"""Context assembly with a token budget, and citation-marker helpers.  Pure functions.

Token counting: the ThaiLLM endpoint exposes no tokenizer and the four models
use different ones (Llama-3 / Qwen-3 derived), so we approximate:
``ceil(thai_chars / 3 + other_chars / 4)``.  Thai runs at roughly 2.5–3.5
chars per token on these tokenizers, Latin text at ~4; the estimate is
deliberately on the high side so the budget errs towards *shorter* prompts.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

from .retriever import Chunk

THAI_CHARS_PER_TOKEN = 3.0
OTHER_CHARS_PER_TOKEN = 4.0
DEFAULT_CONTEXT_TOKEN_BUDGET = 4500

_THAI_RE = re.compile(r"[฀-๿]")
# [2]  [1][3]  [1, 3]  [1，3]  — a bracketed list of chunk numbers.
MARKER_RE = re.compile(r"\[(\d{1,2}(?:\s*[,，]\s*\d{1,2})*)\]")


def estimate_tokens(text: str) -> int:
    thai = len(_THAI_RE.findall(text))
    other = len(text) - thai
    return math.ceil(thai / THAI_CHARS_PER_TOKEN + other / OTHER_CHARS_PER_TOKEN)


def format_chunk(index: int, chunk: Chunk) -> str:
    """``[n] {program} หน้า {page} — {heading_path}`` header line, then the text."""
    header = f"[{index}] {chunk.program} หน้า {chunk.page} — {chunk.heading_path}".rstrip(" —")
    return f"{header}\n{chunk.text.strip()}"


@dataclass
class AssembledContext:
    text: str
    chunks: list[Chunk]  # chunks[i] is referenced by marker [i+1]
    tokens: int
    dropped: list[Chunk]


def assemble_context(chunks: list[Chunk], budget: int = DEFAULT_CONTEXT_TOKEN_BUDGET) -> AssembledContext:
    """Number chunks ``[1]``, ``[2]``… and fill up to ``budget`` estimated tokens.

    The input order is preserved (the caller decides the ranking / interleaving);
    when the budget is exceeded the lowest-scored chunks are dropped first.  At
    least one chunk is always kept — if even that one does not fit, its text is
    truncated to the budget.
    """
    if not chunks:
        return AssembledContext(text="", chunks=[], tokens=0, dropped=[])
    kept = list(chunks)
    dropped: list[Chunk] = []

    def total(cs: list[Chunk]) -> int:
        return sum(estimate_tokens(format_chunk(i, c)) + 1 for i, c in enumerate(cs, start=1))

    while len(kept) > 1 and total(kept) > budget:
        victim = min(kept, key=lambda c: c.score)
        kept.remove(victim)
        dropped.append(victim)
    if total(kept) > budget:  # a single oversized chunk: truncate its text
        only = kept[0]
        header_tokens = estimate_tokens(format_chunk(1, only.model_copy(update={"text": ""})))
        room_chars = max(50, int((budget - header_tokens - 1) * THAI_CHARS_PER_TOKEN))
        kept = [only.model_copy(update={"text": only.text[:room_chars] + "…"})]
    text = "\n\n".join(format_chunk(i, c) for i, c in enumerate(kept, start=1))
    return AssembledContext(text=text, chunks=kept, tokens=estimate_tokens(text), dropped=dropped)


def extract_markers(text: str) -> list[int]:
    """Ordered, de-duplicated chunk numbers referenced as ``[n]`` in ``text``."""
    seen: list[int] = []
    for m in MARKER_RE.finditer(text):
        for part in re.split(r"[,，]", m.group(1)):
            n = int(part.strip())
            if n not in seen:
                seen.append(n)
    return seen


def strip_markers(text: str) -> str:
    return MARKER_RE.sub("", text)


def dangling_markers(text: str, n_chunks: int) -> list[int]:
    """Markers that point outside ``1..n_chunks`` (leakage / hallucinated citations)."""
    return [n for n in extract_markers(text) if n < 1 or n > n_chunks]
