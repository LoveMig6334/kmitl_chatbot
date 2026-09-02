"""Retriever protocol conformance — the same behavioural checks for every implementation.

``fixture`` always runs (synthetic chunks, no network).  ``chroma`` needs the built
index (``python scripts/build_index.py``) and the BGE-M3 weights; it is skipped when
``retrieval/data/bm25.pkl`` or the Chroma dir is missing unless
``RETRIEVER_CONFORMANCE=chroma`` forces it (then a missing index is a failure).
"""

from __future__ import annotations

import asyncio
import os
import re
from pathlib import Path

import pytest

from rag.retriever import SYNTHETIC_FIXTURE_PATH, Chunk, FixtureRetriever, Retriever

ROOT = Path(__file__).resolve().parents[1]
PROGRAMS = ("AIT", "DSBA", "BIT", "IT")

# Per-retriever specifics: chunk-id convention, a course code that exists in its corpus and the
# chunk that must come first for it.  Everything else below is retriever-agnostic.
SPECS = {
    "fixture": {
        "id_re": re.compile(r"^(AIT|DSBA|BIT|IT)-p\d+-c\d+$"),
        "course_code": "06016317", "course_chunk": "IT-p42-c1",
    },
    "chroma": {
        "id_re": re.compile(r"^(AIT|DSBA|IT2565|IT_inter2565)::(gen::\d{4}|course::\d{8})(#\d+)?$"),
        "course_code": "06016408", "course_chunk": "IT2565::course::06016408",
    },
}
GENERIC_QUERY = "หลักสูตรเรียนกี่ปี จำนวนหน่วยกิตรวมตลอดหลักสูตร"


def run(coro):
    return asyncio.run(coro)


def _chroma_index_present() -> bool:
    chroma_dir = Path(os.environ.get("CHROMA_DIR") or ROOT / "retrieval" / "data" / "chroma")
    bm25 = Path(os.environ.get("BM25_PATH") or ROOT / "retrieval" / "data" / "bm25.pkl")
    return chroma_dir.is_dir() and bm25.is_file()


@pytest.fixture(scope="module", params=["fixture", "chroma"])
def kind(request) -> str:
    if request.param == "chroma" and not _chroma_index_present():
        if os.environ.get("RETRIEVER_CONFORMANCE") == "chroma":
            pytest.fail("RETRIEVER_CONFORMANCE=chroma but the index is missing (python scripts/build_index.py)")
        pytest.skip("chroma index not built (python scripts/build_index.py)")
    return request.param


@pytest.fixture(scope="module")
def retriever(kind) -> Retriever:
    if kind == "fixture":
        return FixtureRetriever(SYNTHETIC_FIXTURE_PATH)
    from rag.chroma_retriever import ChromaRetriever

    return ChromaRetriever(use_rerank=False)


@pytest.fixture(scope="module")
def spec(kind) -> dict:
    return SPECS[kind]


def _check_shape(chunks: list[Chunk], spec: dict, k: int) -> None:
    assert len(chunks) <= k
    assert len({c.chunk_id for c in chunks}) == len(chunks), "duplicate chunk_id"
    for c in chunks:
        assert isinstance(c, Chunk)
        assert spec["id_re"].match(c.chunk_id), c.chunk_id
        assert c.program in PROGRAMS
        assert c.page >= 1
        assert c.text.strip()
        assert 0.0 <= c.score <= 1.0
    assert [c.score for c in chunks] == sorted((c.score for c in chunks), reverse=True)


def test_satisfies_protocol(retriever, kind):
    assert isinstance(retriever, Retriever) and retriever.name == kind


def test_generic_query_all_programs(retriever, spec):
    res = run(retriever.retrieve(GENERIC_QUERY, [], k=12))
    _check_shape(res, spec, 12)
    assert res and res[0].score > 0
    assert len({c.program for c in res}) >= 2, "no program filter → results should span programs"


@pytest.mark.parametrize("program", PROGRAMS)
def test_single_program_filter(retriever, spec, program):
    res = run(retriever.retrieve(GENERIC_QUERY, [program], k=5))
    _check_shape(res, spec, 5)
    assert res, f"no results for {program}"
    assert {c.program for c in res} == {program}


def test_multi_program_filter(retriever, spec):
    res = run(retriever.retrieve(GENERIC_QUERY, ["AIT", "DSBA"], k=8))
    _check_shape(res, spec, 8)
    assert res and {c.program for c in res} <= {"AIT", "DSBA"}
    assert {c.program for c in res} == {"AIT", "DSBA"}, "both requested programs should be represented in top-8"


def test_k_is_respected(retriever, spec):
    for k in (1, 3):
        res = run(retriever.retrieve(GENERIC_QUERY, [], k=k))
        _check_shape(res, spec, k)
        assert len(res) == k


def test_course_code_query_hits_the_course_chunk_first(retriever, spec):
    res = run(retriever.retrieve(f"วิชา {spec['course_code']} เรียนเกี่ยวกับอะไร", [], k=3))
    _check_shape(res, spec, 3)
    assert res[0].chunk_id == spec["course_chunk"]
    assert spec["course_code"] in res[0].text


def test_lower_case_program_ids_are_accepted(retriever, spec):
    res = run(retriever.retrieve(GENERIC_QUERY, ["bit"], k=3))
    _check_shape(res, spec, 3)
    assert res and {c.program for c in res} == {"BIT"}


def test_returned_chunks_are_independent_copies(retriever):
    a = run(retriever.retrieve(GENERIC_QUERY, ["AIT"], k=2))
    b = run(retriever.retrieve(GENERIC_QUERY, ["AIT"], k=2))
    assert [c.chunk_id for c in a] == [c.chunk_id for c in b]
    a[0].score = -1.0
    assert b[0].score >= 0.0
