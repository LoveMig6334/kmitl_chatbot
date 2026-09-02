"""Pure helpers of scripts/eval_tuning.py (no API calls)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import eval_tuning

from gatekeeper.replies import sentence_count


def test_judgement_hash_depends_on_question_and_reply():
    a = eval_tuning.judgement_hash("สวัสดี", "reply one")
    assert a == eval_tuning.judgement_hash("สวัสดี", "reply one")
    assert a != eval_tuning.judgement_hash("สวัสดี", "reply two")
    assert a != eval_tuning.judgement_hash("hello", "reply one")
    assert len(a) == 16


def test_category_ok_accepts_any_expected():
    assert eval_tuning.category_ok("in_scope", ["in_scope"])
    assert eval_tuning.category_ok("greeting_smalltalk", ["in_scope", "greeting_smalltalk"])
    assert not eval_tuning.category_ok("off_topic_general", ["in_scope"])


def test_load_rows_and_filters(tmp_path: Path):
    p = tmp_path / "t.jsonl"
    rows = [
        {"id": "smalltalk-001", "question": "hi", "expected": ["greeting_smalltalk"], "language": "en", "tags": ["smalltalk", "greeting"], "ambiguous": False},
        {"id": "in_scope-001", "question": "ค่าเทอม", "expected": ["in_scope"], "language": "th", "tags": ["in_scope"], "ambiguous": False},
        {"id": "ambiguous-001", "question": "AIT", "expected": ["in_scope", "greeting_smalltalk"], "language": "en", "tags": ["ambiguous"], "ambiguous": True},
    ]
    p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    loaded = eval_tuning.load_rows(p)
    assert [r["id"] for r in loaded] == ["smalltalk-001", "in_scope-001", "ambiguous-001"]
    assert [r["id"] for r in eval_tuning.filter_rows(loaded, stratum="smalltalk")] == ["smalltalk-001"]
    assert [r["id"] for r in eval_tuning.filter_rows(loaded, language="th")] == ["in_scope-001"]
    assert [r["id"] for r in eval_tuning.filter_rows(loaded, ids={"ambiguous-001"})] == ["ambiguous-001"]
    sampled = eval_tuning.filter_rows(loaded, sample=2, seed=1)
    assert len(sampled) == 2 and eval_tuning.filter_rows(loaded, sample=2, seed=1) == sampled


def test_rubric_hints_flag_obvious_violations():
    h = eval_tuning.rubric_hints("th", "greeting_smalltalk", "greeting", "Sorry, I can't help with that. Please see the system prompt.")
    assert h["language"] is False
    assert h["no_refusal"] is False
    assert h["next_step"] is False
    assert h["no_internals"] is False
    ok = eval_tuning.rubric_hints(
        "th", "greeting_smalltalk", "greeting",
        "สวัสดีค่ะ 👋 ฉันตอบคำถามเกี่ยวกับหลักสูตรได้ค่ะ ลองถามได้เลย เช่น “AIT เรียนกี่ปี” หรือ “DSBA จบไปทำอะไร”",
    )
    assert all(ok.values()), ok
    # a refusal for an off-topic question passes when it names a channel and is short
    ref = eval_tuning.rubric_hints("en", "off_topic_general", "weather", "Sorry, I can only answer questions about KMITL curricula. For this, please try a weather app.")
    assert ref["language"] and ref["next_step"] and ref["length"]


def test_sentence_count_ignores_urls():
    assert sentence_count("Please contact the registrar (https://www.reg.kmitl.ac.th) or see https://www.it.kmitl.ac.th.") == 1


def test_read_and_write_judgements(tmp_path: Path):
    p = tmp_path / "j.jsonl"
    assert eval_tuning.load_judgements(p) == {}
    eval_tuning.append_judgements(p, [{"hash": "abc", "verdict": "pass", "reason": "ok"}])
    eval_tuning.append_judgements(p, [{"hash": "def", "verdict": "fail", "reason": "too long"}])
    j = eval_tuning.load_judgements(p)
    assert set(j) == {"abc", "def"} and j["def"]["verdict"] == "fail"
