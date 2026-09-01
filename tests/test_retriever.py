"""FixtureRetriever + fixture sanity.  No network."""

from __future__ import annotations

import asyncio
from collections import Counter

import pytest

from rag.retriever import (
    DEFAULT_FIXTURE_PATH,
    Chunk,
    FixtureRetriever,
    Retriever,
    get_retriever,
    load_chunks,
    tokenize,
)


def run(coro):
    return asyncio.run(coro)


@pytest.fixture(scope="module")
def retriever() -> FixtureRetriever:
    return FixtureRetriever(DEFAULT_FIXTURE_PATH)


def test_fixture_file_is_well_formed():
    chunks = load_chunks(DEFAULT_FIXTURE_PATH)
    assert 20 <= len(chunks) <= 40
    assert len({c.chunk_id for c in chunks}) == len(chunks), "chunk_ids must be unique"
    per_program = Counter(c.program for c in chunks)
    for pid in ("AIT", "DSBA", "BIT", "IT"):
        assert per_program[pid] >= 3, f"{pid} needs >= 3 passages"
    for c in chunks:
        assert c.page > 0 and c.text.strip() and c.heading_path.strip()


def test_fixture_covers_required_topics():
    text = " ".join(c.text for c in load_chunks(DEFAULT_FIXTURE_PATH))
    for needle in ("หน่วยกิตรวมตลอดหลักสูตร", "กำหนดเปิดสอน", "แผนการศึกษา ชั้นปีที่ 1", "คุณสมบัติของผู้เข้าศึกษา", "วิชาบังคับก่อน", "ค่าธรรมเนียม"):
        assert needle in text


def test_tokenize_drops_stopwords_and_lowercases():
    toks = tokenize("หลักสูตร AIT เรียนกี่หน่วยกิต ตลอดหลักสูตร 4 ปี ครับ")
    assert "หน่วยกิต" in toks and "ait" in toks and "4" in toks
    assert "กี่" not in toks and "ครับ" not in toks and "หลักสูตร" not in toks


def test_retriever_satisfies_protocol(retriever):
    assert isinstance(retriever, Retriever)
    assert retriever.name == "fixture"


def test_credits_question_hits_credits_chunk_first(retriever):
    res = run(retriever.retrieve("AIT เรียนกี่หน่วยกิต กี่ปี", ["AIT"], k=3))
    assert res and res[0].chunk_id == "AIT-p12-c1"
    assert all(c.program == "AIT" for c in res)
    assert all(0.0 < c.score <= 1.0 for c in res)
    assert [c.score for c in res] == sorted((c.score for c in res), reverse=True)


def test_program_filter_and_all_programs(retriever):
    only_bit = run(retriever.retrieve("ค่าธรรมเนียมการศึกษา ภาคการศึกษาละ", ["BIT"], k=5))
    assert only_bit and {c.program for c in only_bit} == {"BIT"}
    everything = run(retriever.retrieve("ค่าธรรมเนียมการศึกษา ภาคการศึกษาละ", [], k=4))
    assert {c.program for c in everything} == {"AIT", "DSBA", "BIT", "IT"}
    assert all("ค่าธรรมเนียม" in c.text for c in everything)


def test_k_limits_results(retriever):
    assert len(run(retriever.retrieve("คุณสมบัติของผู้เข้าศึกษา GPAX", [], k=2))) == 2


def test_course_code_query(retriever):
    res = run(retriever.retrieve("วิชา 06016317 เรียนอะไร", [], k=3))
    assert res[0].chunk_id == "IT-p42-c1"


def test_unrelated_query_returns_nothing_or_low_scores(retriever):
    res = run(retriever.retrieve("หอพัก ราคา ห้องพัก", [], k=5))
    assert all(c.score < 0.35 for c in res)
    assert run(retriever.retrieve("!!! ???", [], k=5)) == []


def test_returned_chunks_are_copies_with_scores(retriever):
    res = run(retriever.retrieve("หน่วยกิตรวมตลอดหลักสูตร", ["DSBA"], k=1))
    assert isinstance(res[0], Chunk) and res[0].score > 0
    original = next(c for c in retriever.chunks if c.chunk_id == res[0].chunk_id)
    assert original.score == 0.0


def test_get_retriever_env(monkeypatch):
    monkeypatch.setenv("RETRIEVER", "fixture")
    assert get_retriever().name == "fixture"
    monkeypatch.setenv("RETRIEVER", "qdrant")
    with pytest.raises(RuntimeError, match="QdrantRetriever"):
        get_retriever()
    monkeypatch.setenv("RETRIEVER", "bogus")
    with pytest.raises(RuntimeError, match="Unknown RETRIEVER"):
        get_retriever()


def test_colloquial_and_cross_lingual_synonyms(retriever):
    assert run(retriever.retrieve("AIT ปีแรกเรียนอะไรบ้าง", ["AIT"], k=1))[0].chunk_id == "AIT-p20-c1"
    assert run(retriever.retrieve("ค่าเทอม DSBA เท่าไหร่", ["DSBA"], k=1))[0].chunk_id == "DSBA-p8-c1"
    assert run(retriever.retrieve("How many credits does BIT require?", ["BIT"], k=1))[0].chunk_id == "BIT-p10-c1"
    assert run(retriever.retrieve("DSBA专业总共多少学分?学制几年?", ["DSBA"], k=1))[0].chunk_id == "DSBA-p11-c1"


def test_topic_less_comparison_falls_back_to_program_overview(retriever):
    res = run(retriever.retrieve("AIT กับ DSBA ต่างกันยังไง", ["AIT", "DSBA"], k=6))
    assert {c.program for c in res} == {"AIT", "DSBA"}
    assert {"AIT-p3-c1", "AIT-p12-c1", "DSBA-p3-c1", "DSBA-p11-c1"} <= {c.chunk_id for c in res}
    assert all(c.score == 0.3 for c in res)
    assert run(retriever.retrieve("ต่างกันยังไง", [], k=6)) == []  # no program, no topic → nothing
