"""``RagAnswerer`` — retrieved chunks → grounded, cited, streamed ThaiLLM answer.

Implements ``api.answerer.Answerer``.  Flow per call:

1. optional follow-up rewrite / translation to Thai (one small ThaiLLM call)
2. retrieve (per program + interleave for comparisons), dedupe by chunk_id
3. no-answer gate: nothing above ``min_score`` → fixed not-found reply, no LLM
4. context assembly under a token budget (``rag.context``)
5. model routing: thinking model for comparisons, openthaigpt otherwise; if the
   primary produces no visible token in time, retry once with the fallback
6. stream visible tokens (``<think>`` stripped), then ``citations`` for the
   ``[n]`` markers actually used, then ``done``

The generator is wrapped in ``try/finally`` so ``aclose()`` from the API (client
disconnect) closes the upstream ThaiLLM stream.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from collections.abc import AsyncIterator

from api.answerer import AnswerEvent, Citation, Turn, tokenize
from gatekeeper.rules import resolve_programs
from gatekeeper.schema import GateDecision

from . import llm as _llm
from .checks import answered_in_language
from .context import AssembledContext, assemble_context, extract_markers
from .llm import RagSettings, load_rag_settings
from .prompts import (
    NOT_FOUND_PHRASE_LIST,
    REWRITE_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
    build_answer_prompt,
    build_rewrite_prompt,
    build_translate_prompt,
    not_found_reply,
)
from .retriever import Chunk, Retriever, get_retriever
from .streaming import ThinkStripper

log = logging.getLogger(__name__)

ALL_PROGRAMS = ["AIT", "DSBA", "BIT", "IT"]

# "each programme / all four / rank them" questions need one retrieval per programme
# (otherwise a single pooled search returns e.g. three chunks for one programme and
# regulation text for another) — treat them like comparisons even when the gate says
# fact_lookup.
MULTI_PROGRAM_RE = re.compile(
    r"แต่ละ(หลักสูตร|สาขา)|ทุก(หลักสูตร|สาขา)|ทั้ง\s*(4|๔|สี่)\s*(หลักสูตร|สาขา)|เรียง(ลำดับ)?จาก"
    r"|(4|四|各)\s*个?\s*(专业|课程)|各专业|排列|排序|each program|all (four|4) program|rank"
    r"|มาก(ที่สุด|กว่า)|น้อย(ที่สุด|กว่า)|most|least|highest|lowest",
    re.IGNORECASE,
)


def needs_per_program_retrieval(query: str, decision: GateDecision) -> bool:
    return decision.question_kind == "comparison" or MULTI_PROGRAM_RE.search(query) is not None
SNIPPET_CHARS = 120
SHORT_MESSAGE_CHARS = 40
# Follow-up phrasings that only make sense with the previous turn.
_ANAPHORA_RE = re.compile(
    r"แล้ว.{0,25}(ล่ะ|หละ|ละ)\b|^แล้ว|อันนั้น|อันนี้|หลักสูตรนั้น|สาขานั้น|ตัวนั้น|ที่ว่า|เหมือนกันไหม|ด้วยไหม|ล่ะ\s*$"
    r"|\bwhat about\b|\bhow about\b|\band (the )?(other|others)\b|\bthat (program|one|course)\b|\bsame\b|\bit\b\s*\?$"
    r"|那个|那么|呢\s*$|也是|另一个",
    re.IGNORECASE,
)
_THAI_RE = re.compile(r"[฀-๿]")


def needs_rewrite(message: str, history: list[Turn], language: str) -> bool:
    """Rewrite when the message cannot stand alone, or is not in Thai (documents are Thai)."""
    if language in ("en", "zh", "other") and not _THAI_RE.search(message):
        return True
    if not history:
        return False
    text = message.strip()
    return len(text) < SHORT_MESSAGE_CHARS or bool(_ANAPHORA_RE.search(text))


def _clean_rewrite(raw: str, original: str) -> str | None:
    """Validate the rewrite; ``None`` means keep the original message."""
    from gatekeeper.parsing import strip_think

    text = strip_think(raw or "").strip().strip('"').strip()
    text = text.split("\n")[0].strip()
    for prefix in ("คำถามใหม่:", "คำถาม:", "Rewritten:", "Question:"):
        if text.startswith(prefix):
            text = text[len(prefix) :].strip()
    if not text or len(text) > max(200, 3 * len(original) + 100):
        return None
    if not _THAI_RE.search(text):
        return None
    return text


def interleave(groups: list[list[Chunk]], k: int) -> list[Chunk]:
    """Round-robin merge so no program starves; dedupe by chunk_id; cap at k."""
    out: list[Chunk] = []
    seen: set[str] = set()
    i = 0
    while len(out) < k and any(i < len(g) for g in groups):
        for g in groups:
            if i < len(g) and g[i].chunk_id not in seen:
                seen.add(g[i].chunk_id)
                out.append(g[i])
                if len(out) >= k:
                    break
        i += 1
    return out


class RagAnswerer:
    name = "rag"

    def __init__(self, retriever: Retriever | None = None, settings: RagSettings | None = None):
        self.retriever = retriever or get_retriever()
        self.settings = settings or load_rag_settings()

    @property
    def min_score(self) -> float:
        """No-answer gate threshold for the active retriever (scores are not comparable across retrievers)."""
        return self.settings.min_score_chroma if getattr(self.retriever, "name", "") == "chroma" else self.settings.min_score

    # ----------------------------------------------------------------- steps --
    async def rewrite_query(self, message: str, history: list[Turn], language: str) -> str:
        if not self.settings.query_rewrite or not needs_rewrite(message, history, language):
            return message
        messages = [
            {"role": "system", "content": REWRITE_SYSTEM_PROMPT},
            {"role": "user", "content": build_rewrite_prompt(history, message)},
        ]
        try:
            raw = await asyncio.wait_for(
                _llm.complete_chat(messages, self.settings.rewrite_model, self.settings, max_tokens=self.settings.rewrite_max_tokens),
                timeout=self.settings.timeout_s + 1,
            )
        except Exception as exc:  # noqa: BLE001 # any failure here must not block answering — fall back to the raw message
            log.warning("query rewrite failed (%s); using the original message", exc)
            return message
        cleaned = _clean_rewrite(raw, message)
        return cleaned or message

    def resolve_programs(self, query: str, decision: GateDecision, scope: list[str] | None) -> list[str]:
        programs = list(decision.programs)
        if not programs:
            programs = resolve_programs(query, scope)  # a rewrite may have named the program from history
        if scope:
            wanted = [s.upper() for s in scope]
            narrowed = [p for p in programs if p in wanted]
            programs = narrowed or (wanted if not programs else programs)
        return programs

    async def retrieve(self, query: str, programs: list[str], decision: GateDecision) -> list[Chunk]:
        k = self.settings.k
        if needs_per_program_retrieval(query, decision):
            targets = programs if len(programs) >= 2 else ALL_PROGRAMS
            per = max(3, k // len(targets))
            groups = await asyncio.gather(*(self.retriever.retrieve(query, [p], per) for p in targets))
            return interleave(list(groups), k)
        chunks = await self.retriever.retrieve(query, programs, k)
        seen: set[str] = set()
        out: list[Chunk] = []
        for c in chunks:
            if c.chunk_id not in seen:
                seen.add(c.chunk_id)
                out.append(c)
        return out

    def pick_model(self, decision: GateDecision) -> str:
        return self.settings.comparison_model if decision.question_kind == "comparison" else self.settings.model

    async def enforce_language(self, answer: str, language: str, model: str | None, debug: dict | None) -> str:
        """For a zh/en answer that came out in the wrong language, translate it.

        Thai always stays as-is (the models answer Thai reliably). The models
        occasionally ignore the translate instruction too, so retry once; if it
        still will not comply, keep the original — a wrong-language grounded
        answer beats none.
        """
        if language not in ("en", "zh", "other") or not self.settings.language_guard:
            return answer
        if not answer.strip() or answered_in_language(answer, language):
            return answer
        from gatekeeper.parsing import strip_think

        system, user = build_translate_prompt(answer, language)
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        for attempt in range(self.settings.language_guard_attempts):
            try:
                raw = await asyncio.wait_for(
                    _llm.complete_chat(messages, model or self.settings.model, self.settings, max_tokens=self.settings.think_max_tokens),
                    timeout=self.settings.timeout_s + 5,
                )
                translated = strip_think(raw or "").strip()
            except Exception as exc:  # noqa: BLE001 # never let the guard block the answer
                log.warning("language guard failed (%s); keeping the original answer", exc)
                return answer
            if translated and answered_in_language(translated, language):
                if debug is not None:
                    debug["language_guard"] = {"from": answer, "to": translated, "attempts": attempt + 1}
                return translated
            log.warning("language guard attempt %d did not produce %s; retrying", attempt + 1, language)
        if debug is not None:
            debug["language_guard"] = {"from": answer, "to": None, "attempts": self.settings.language_guard_attempts, "gave_up": True}
        return answer

    async def _stream_visible(self, messages: list[dict], model: str, debug: dict | None) -> AsyncIterator[str]:
        """Visible (think-stripped) tokens; raises TimeoutError if none arrives in time."""
        max_tokens = self.settings.think_max_tokens if "think" in model else self.settings.max_tokens
        agen = _llm.stream_chat(messages, model, self.settings, max_tokens=max_tokens)
        stripper = ThinkStripper()
        raw_parts: list[str] = []
        first_visible = False
        deadline = time.monotonic() + self.settings.first_token_timeout_s
        try:
            while True:
                timeout = self.settings.timeout_s if first_visible else max(0.0, deadline - time.monotonic())
                try:
                    delta = await asyncio.wait_for(agen.__anext__(), timeout=timeout)
                except StopAsyncIteration:
                    break
                raw_parts.append(delta)
                visible = stripper.feed(delta)
                if visible:
                    first_visible = True
                    yield visible
            tail = stripper.flush()
            if tail:
                yield tail
        finally:
            await agen.aclose()
            if debug is not None:
                debug.setdefault("raw_outputs", []).append({"model": model, "raw": "".join(raw_parts), "think": stripper.think_text})

    async def generate(self, messages: list[dict], primary: str, debug: dict | None) -> AsyncIterator[tuple[str, str]]:
        """Yield ``(model, visible_text)``; fall back once if the primary yields nothing in time."""
        models = [primary] + ([self.settings.fallback_model] if self.settings.fallback_model != primary else [])
        for i, model in enumerate(models):
            produced = False
            try:
                async for text in self._stream_visible(messages, model, debug):
                    produced = True
                    yield model, text
                if produced:
                    return
                log.warning("model %s produced no visible text", model)
            except Exception as exc:  # timeout, connection reset, HTTP error: retry once if nothing was shown yet
                if produced or i == len(models) - 1:
                    raise
                log.warning("model %s failed before the first visible token (%s: %s); retrying with %s", model, type(exc).__name__, exc, models[i + 1])
                continue
            if i == len(models) - 1:
                return

    # ------------------------------------------------------------------ main --
    async def answer(
        self,
        message: str,
        decision: GateDecision,
        scope: list[str] | None,
        history: list[Turn],
        *,
        debug: dict | None = None,
    ) -> AsyncIterator[AnswerEvent]:
        started = time.perf_counter()
        language = decision.language
        model_used: str | None = None
        gen: AsyncIterator | None = None
        try:
            query = await self.rewrite_query(message, history, language)
            programs = self.resolve_programs(query, decision, scope)
            chunks = await self.retrieve(query, programs, decision)
            usable = [c for c in chunks if c.score >= self.min_score]
            if debug is not None:
                debug.update({
                    "query": query, "programs": programs,
                    "retrieved": [(c.chunk_id, c.score) for c in chunks],
                    "usable": [c.chunk_id for c in usable],
                })

            if not usable:
                for tok in tokenize(not_found_reply(language)):
                    yield AnswerEvent(type="token", text=tok)
                yield AnswerEvent(type="citations", citations=[])
                yield AnswerEvent(type="done", model_used=None)
                if debug is not None:
                    debug.update({"context": "", "not_found_gate": True, "model_used": None})
                return

            ctx: AssembledContext = assemble_context(usable, self.settings.context_token_budget)
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_answer_prompt(ctx.text, query, language)},
            ]
            if debug is not None:
                debug.update({"context": ctx.text, "context_chunks": [c.chunk_id for c in ctx.chunks], "context_tokens": ctx.tokens})

            # Thai streams live; zh/en buffer so the language guard can correct a
            # wrong-language answer (the 8B models drift back to Thai) before the
            # client sees it.
            stream_live = language == "th" or not self.settings.language_guard
            parts: list[str] = []
            gen = self.generate(messages, self.pick_model(decision), debug)
            async for model, text in gen:
                model_used = model
                parts.append(text)
                if stream_live:
                    yield AnswerEvent(type="token", text=text)
            full = "".join(parts)
            if not full.strip():
                full = not_found_reply(language)
            elif not stream_live:
                full = await self.enforce_language(full, language, model_used, debug)
            # Emit anything not already streamed live: the not-found fallback (any
            # language) and the whole buffered zh/en answer.
            if not stream_live or not "".join(parts).strip():
                for tok in tokenize(full):
                    yield AnswerEvent(type="token", text=tok)

            markers = extract_markers(full)
            cited = [ctx.chunks[n - 1] for n in markers if 1 <= n <= len(ctx.chunks)]
            is_not_found = any(p in full.lower() for p in NOT_FOUND_PHRASE_LIST)
            citations = [] if (is_not_found and not cited) else [
                Citation(program=c.program, page=c.page, chunk_id=c.chunk_id, snippet=c.text[:SNIPPET_CHARS])
                for c in cited
            ]
            yield AnswerEvent(type="citations", citations=citations)
            yield AnswerEvent(type="done", model_used=model_used)
            if debug is not None:
                debug.update({
                    "answer": full, "markers": markers, "model_used": model_used, "not_found_gate": False,
                    "latency_ms": int((time.perf_counter() - started) * 1000),
                })
        finally:
            if gen is not None and hasattr(gen, "aclose"):
                await gen.aclose()  # closes the upstream ThaiLLM stream on client disconnect
