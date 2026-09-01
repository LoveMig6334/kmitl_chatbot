"""RagAnswerer end-to-end with the LLM call mocked and the fixture retriever.  No network."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import pytest

import rag.llm as rag_llm
from api.answerer import Answerer, AnswerEvent, Turn, get_answerer
from gatekeeper.schema import GateDecision
from rag.answerer import RagAnswerer, interleave, needs_rewrite
from rag.llm import RagSettings
from rag.prompts import NOT_FOUND_PHRASES, SYSTEM_PROMPT
from rag.retriever import Chunk, FixtureRetriever

SETTINGS = RagSettings(api_key="test", timeout_s=0.5, first_token_timeout_s=0.3, query_rewrite=True, min_score=0.3)


def decision(**kw) -> GateDecision:
    base = {"category": "in_scope", "language": "th", "programs": ["AIT"], "question_kind": "fact_lookup", "decided_by": "rule"}
    base.update(kw)
    return GateDecision(**base)


def run(coro):
    return asyncio.run(coro)


async def collect(it: AsyncIterator[AnswerEvent]) -> list[AnswerEvent]:
    return [ev async for ev in it]


class FakeLLM:
    """Scripted ``stream_chat`` replacement: one script per call, in order."""

    def __init__(self, scripts: list[object]):
        self.scripts = list(scripts)
        self.calls: list[dict] = []
        self.closed = 0

    async def stream_chat(self, messages, model, settings, *, max_tokens=None):
        self.calls.append({"messages": messages, "model": model, "max_tokens": max_tokens})
        script = self.scripts.pop(0)
        try:
            if isinstance(script, BaseException):
                raise script
            if script == "hang":
                await asyncio.sleep(10)
            for delta in script:
                yield delta
        finally:
            self.closed += 1

    async def complete_chat(self, messages, model, settings, *, max_tokens=None):
        return "".join([d async for d in self.stream_chat(messages, model, settings, max_tokens=max_tokens)])


@pytest.fixture
def fake(monkeypatch):
    holder: dict = {}

    def install(scripts):
        f = FakeLLM(scripts)
        monkeypatch.setattr(rag_llm, "stream_chat", f.stream_chat)
        monkeypatch.setattr(rag_llm, "complete_chat", f.complete_chat)
        holder["llm"] = f
        return f

    return install


@pytest.fixture(scope="module")
def retriever():
    return FixtureRetriever()


def test_is_answerer(retriever):
    assert isinstance(RagAnswerer(retriever=retriever, settings=SETTINGS), Answerer)


def test_fact_lookup_streams_tokens_then_referenced_citations_then_done(fake, retriever):
    llm = fake([["หลักสูตร AIT เรียน", " 120 หน่วยกิต ใช้เวลา 4 ปี", " [1]"]])
    a = RagAnswerer(retriever=retriever, settings=SETTINGS)
    dbg: dict = {}
    events = run(collect(a.answer("AIT เรียนกี่หน่วยกิต กี่ปี", decision(), None, [], debug=dbg)))
    types = [e.type for e in events]
    assert types[:-2] == ["token"] * (len(types) - 2) and types[-2:] == ["citations", "done"]
    assert "".join(e.text for e in events if e.type == "token") == "หลักสูตร AIT เรียน 120 หน่วยกิต ใช้เวลา 4 ปี [1]"
    cits = events[-2].citations
    assert len(cits) == 1 and cits[0].chunk_id == "AIT-p12-c1" and cits[0].program == "AIT" and cits[0].page == 12
    assert cits[0].faculty == "IT" and cits[0].snippet and len(cits[0].snippet) <= 120
    assert events[-1].model_used == SETTINGS.model
    # exactly one LLM call (no rewrite: history empty, Thai), system prompt + numbered context
    assert len(llm.calls) == 1 and llm.calls[0]["model"] == SETTINGS.model
    assert llm.calls[0]["messages"][0]["content"] == SYSTEM_PROMPT
    user = llm.calls[0]["messages"][1]["content"]
    assert "[1] AIT หน้า 12" in user and "ภาษาที่ต้องใช้ตอบ: ไทย" in user and "AIT เรียนกี่หน่วยกิต" in user
    assert dbg["context_chunks"][0] == "AIT-p12-c1" and dbg["markers"] == [1]


def test_citations_only_for_markers_used_and_dangling_ignored(fake, retriever):
    fake([["ตอบ [2] และ [9]"]])
    a = RagAnswerer(retriever=retriever, settings=SETTINGS)
    events = run(collect(a.answer("ค่าธรรมเนียมการศึกษา ภาคการศึกษาละ", decision(programs=[]), None, [])))
    cits = events[-2].citations
    assert len(cits) == 1  # [9] does not exist


def test_not_found_gate_skips_llm(fake, retriever):
    llm = fake([])
    a = RagAnswerer(retriever=retriever, settings=SETTINGS)
    dbg: dict = {}
    events = run(collect(a.answer("หอพักของ AIT ราคาเท่าไหร่", decision(), None, [], debug=dbg)))
    text = "".join(e.text for e in events if e.type == "token")
    assert NOT_FOUND_PHRASES["th"] in text and "it.kmitl.ac.th" in text
    assert events[-2].type == "citations" and events[-2].citations == []
    assert events[-1].type == "done" and events[-1].model_used is None
    assert llm.calls == [] and dbg["not_found_gate"] is True


def test_not_found_gate_uses_user_language(fake, retriever):
    fake([["ตอบ"]])  # a (Thai) rewrite of the English question; retrieval still finds nothing
    a = RagAnswerer(retriever=retriever, settings=SETTINGS)
    events = run(collect(a.answer("Does AIT offer a master's degree?", decision(language="en"), None, [])))
    text = "".join(e.text for e in events if e.type == "token")
    assert NOT_FOUND_PHRASES["en"] in text


def test_model_not_found_answer_without_markers_gives_empty_citations(fake, retriever):
    fake([[f"{NOT_FOUND_PHRASES['th']}เกี่ยวกับทุน ค่ะ"]])
    a = RagAnswerer(retriever=retriever, settings=SETTINGS)
    events = run(collect(a.answer("ทุนการศึกษา AIT ให้กี่บาท", decision(), None, [])))
    assert events[-2].citations == []


def test_comparison_routes_to_thinking_model_and_strips_think(fake, retriever):
    llm = fake([["<thi", "nk>คิด", "ก่อน</think>\n\n", "AIT: 120 หน่วยกิต [1]\nDSBA: 129 หน่วยกิต [2]"]])
    a = RagAnswerer(retriever=retriever, settings=SETTINGS)
    dbg: dict = {}
    d = decision(programs=["AIT", "DSBA"], question_kind="comparison")
    events = run(collect(a.answer("AIT กับ DSBA เรียนกี่หน่วยกิต ต่างกันยังไง", d, None, [], debug=dbg)))
    text = "".join(e.text for e in events if e.type == "token")
    assert "<think>" not in text and "คิด" not in text and text.startswith("AIT: 120")
    assert llm.calls[0]["model"] == SETTINGS.comparison_model and llm.calls[0]["max_tokens"] == SETTINGS.think_max_tokens
    progs = {c.program for c in dbg["retrieved"] and [next(ch for ch in retriever.chunks if ch.chunk_id == cid) for cid, _ in dbg["retrieved"]]}
    assert progs == {"AIT", "DSBA"}  # interleaved: both programs represented
    assert {c.chunk_id for c in events[-2].citations} == {"AIT-p12-c1", "DSBA-p11-c1"}
    assert events[-1].model_used == SETTINGS.comparison_model
    assert dbg["raw_outputs"][0]["think"] == "คิดก่อน"


def test_thinking_timeout_falls_back_to_openthaigpt(fake, retriever):
    llm = fake(["hang", ["AIT: 120 [1] DSBA: 129 [2]"]])
    a = RagAnswerer(retriever=retriever, settings=SETTINGS)
    d = decision(programs=["AIT", "DSBA"], question_kind="comparison")
    events = run(collect(a.answer("AIT กับ DSBA เรียนกี่หน่วยกิต", d, None, [])))
    assert [c["model"] for c in llm.calls] == [SETTINGS.comparison_model, SETTINGS.fallback_model]
    assert events[-1].model_used == SETTINGS.fallback_model
    assert llm.closed == 2  # the hung stream was closed


def test_timeout_after_visible_tokens_is_not_retried(fake, retriever):
    async def slow_then_stall():
        yield "AIT เรียน 120 หน่วยกิต [1]"
        await asyncio.sleep(10)

    class Gen:
        def __init__(self):
            self.calls = 0

        async def stream_chat(self, messages, model, settings, *, max_tokens=None):
            self.calls += 1
            async for d in slow_then_stall():
                yield d

    g = Gen()
    import rag.llm as m

    m_orig = m.stream_chat
    m.stream_chat = g.stream_chat
    try:
        a = RagAnswerer(retriever=retriever, settings=SETTINGS)
        with pytest.raises(TimeoutError):
            run(collect(a.answer("AIT เรียนกี่หน่วยกิต", decision(), None, [])))
        assert g.calls == 1
    finally:
        m.stream_chat = m_orig


def test_aclose_cancels_upstream(fake, retriever):
    llm = fake([["ตอน", "แรก", "ต่อไป", "อีก"]])
    a = RagAnswerer(retriever=retriever, settings=SETTINGS)

    async def go():
        it = a.answer("AIT เรียนกี่หน่วยกิต", decision(), None, [])
        first = await it.__anext__()
        await it.aclose()
        return first

    first = run(go())
    assert first.type == "token" and llm.closed == 1


def test_needs_rewrite_rules():
    hist = [Turn(role="user", content="AIT เรียนกี่หน่วยกิต"), Turn(role="assistant", content="120 หน่วยกิต [1]")]
    assert needs_rewrite("แล้ว DSBA ล่ะ", hist, "th")
    assert needs_rewrite("กี่ปี", hist, "th")
    assert needs_rewrite("What about the tuition fee of that program?", hist, "en")
    assert not needs_rewrite("แล้ว DSBA ล่ะ", [], "th")  # no history: nothing to resolve
    assert not needs_rewrite("หลักสูตร DSBA มีค่าธรรมเนียมการศึกษาภาคการศึกษาละเท่าไหร่", hist, "th")
    assert needs_rewrite("How many credits does the AIT program have?", [], "en")  # translate to Thai for retrieval
    assert needs_rewrite("AIT专业总共多少学分", [], "zh")


def test_follow_up_is_rewritten_before_retrieval(fake, retriever):
    llm = fake([["หลักสูตร DSBA เรียนกี่หน่วยกิต"], ["DSBA เรียน 129 หน่วยกิต [1]"]])
    a = RagAnswerer(retriever=retriever, settings=SETTINGS)
    hist = [Turn(role="user", content="AIT เรียนกี่หน่วยกิต"), Turn(role="assistant", content="120 หน่วยกิต [1]")]
    dbg: dict = {}
    events = run(collect(a.answer("แล้ว DSBA ล่ะ", decision(programs=["DSBA"]), None, hist, debug=dbg)))
    assert llm.calls[0]["model"] == SETTINGS.rewrite_model and "แล้ว DSBA ล่ะ" in llm.calls[0]["messages"][1]["content"]
    assert dbg["query"] == "หลักสูตร DSBA เรียนกี่หน่วยกิต"
    assert events[-2].citations[0].chunk_id == "DSBA-p11-c1"


def test_rewrite_resolves_program_from_history_when_gate_saw_none(fake, retriever):
    fake([["หลักสูตร AIT ใช้เวลาเรียนกี่ปี"], ["4 ปี [1]"]])
    a = RagAnswerer(retriever=retriever, settings=SETTINGS)
    hist = [Turn(role="user", content="AIT เรียนกี่หน่วยกิต"), Turn(role="assistant", content="120 หน่วยกิต [1]")]
    dbg: dict = {}
    run(collect(a.answer("กี่ปี", decision(programs=[]), None, hist, debug=dbg)))
    assert dbg["programs"] == ["AIT"]


def test_rewrite_failure_or_garbage_keeps_original(fake, retriever):
    fake([RuntimeError("boom"), ["120 [1]"]])
    a = RagAnswerer(retriever=retriever, settings=SETTINGS)
    hist = [Turn(role="user", content="AIT เรียนกี่หน่วยกิต"), Turn(role="assistant", content="120 หน่วยกิต [1]")]
    dbg: dict = {}
    run(collect(a.answer("AIT กี่ปี", decision(), None, hist, debug=dbg)))
    assert dbg["query"] == "AIT กี่ปี"
    fake([["<think>hmm</think>only english output"], ["120 [1]"]])
    dbg = {}
    run(collect(a.answer("AIT กี่ปี", decision(), None, hist, debug=dbg)))
    assert dbg["query"] == "AIT กี่ปี"


def test_rewrite_disabled_by_settings(fake, retriever):
    llm = fake([["120 [1]"]])
    a = RagAnswerer(retriever=retriever, settings=RagSettings(api_key="test", query_rewrite=False))
    hist = [Turn(role="user", content="AIT เรียนกี่หน่วยกิต"), Turn(role="assistant", content="120 หน่วยกิต [1]")]
    run(collect(a.answer("AIT กี่ปี", decision(), None, hist)))
    assert len(llm.calls) == 1


def test_scope_narrows_when_no_program_named(fake, retriever):
    fake([["ตอบ [1]"]])
    a = RagAnswerer(retriever=retriever, settings=SETTINGS)
    dbg: dict = {}
    run(collect(a.answer("ค่าธรรมเนียมการศึกษาเท่าไหร่", decision(programs=[]), ["BIT"], [], debug=dbg)))
    assert dbg["programs"] == ["BIT"] and all(cid.startswith("BIT") for cid in dbg["usable"])


def test_interleave_round_robin_dedupe_cap():
    def c(i, p):
        return Chunk(chunk_id=f"{p}-{i}", program=p, page=i, text="x", score=1.0)

    a = [c(1, "AIT"), c(2, "AIT"), c(3, "AIT")]
    d = [c(1, "DSBA"), c(1, "DSBA")]
    assert [x.chunk_id for x in interleave([a, d], 8)] == ["AIT-1", "DSBA-1", "AIT-2", "AIT-3"]
    assert len(interleave([a, d], 2)) == 2


def test_get_answerer_rag_builds_from_env(monkeypatch):
    monkeypatch.setenv("ANSWERER", "rag")
    monkeypatch.setenv("RETRIEVER", "fixture")
    monkeypatch.setenv("THAILLM_API_KEY", "test")
    ans = get_answerer()
    assert ans.name == "rag" and isinstance(ans, RagAnswerer) and ans.retriever.name == "fixture"
