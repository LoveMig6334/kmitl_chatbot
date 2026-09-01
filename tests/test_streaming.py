"""ThinkStripper: <think> blocks removed from a token stream, tags split across deltas."""

from __future__ import annotations

from rag.streaming import ThinkStripper


def run(deltas: list[str]) -> tuple[str, str]:
    s = ThinkStripper()
    out = "".join(s.feed(d) for d in deltas)
    out += s.flush()
    return out, s.think_text


def test_no_think_passthrough():
    out, think = run(["สวัสดี", "ครับ [1]"])
    assert out == "สวัสดีครับ [1]" and think == ""


def test_think_block_in_one_delta():
    out, think = run(["<think>reasoning here</think>\n\nคำตอบ [1]"])
    assert out == "คำตอบ [1]" and think == "reasoning here"


def test_tag_split_across_deltas():
    out, think = run(["<thi", "nk>ab", "c</th", "ink>", "\n", "คำ", "ตอบ"])
    assert out == "คำตอบ" and think == "abc"


def test_char_by_char():
    text = "<think>x y</think>Answer [2]"
    out, think = run(list(text))
    assert out == "Answer [2]" and think == "x y"


def test_multiple_blocks():
    out, _ = run(["<think>a</think>one ", "<think>b</think>two"])
    assert out == "one two"


def test_unterminated_think_is_dropped():
    out, think = run(["<think>never ", "closes"])
    assert out == "" and think == "never closes"


def test_lt_that_is_not_a_tag_is_kept():
    out, _ = run(["a < b และ <b>bold</b> ", "<t", "hree"])
    assert out == "a < b และ <b>bold</b> <three"


def test_partial_tag_at_end_is_flushed():
    out, _ = run(["ตอบ <thi"])
    assert out == "ตอบ <thi"
