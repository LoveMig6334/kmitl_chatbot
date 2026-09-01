"""Script-based language detection (pure, no API calls).

We only need coarse buckets: ``th`` / ``en`` / ``zh`` / ``other``.  Thai
questions frequently embed English program names or course codes, so Thai wins
whenever it makes up a meaningful share of the letters.
"""

from __future__ import annotations

import unicodedata

from .schema import Language

_THAI = ("฀", "๿")
_CJK_RANGES = (
    ("一", "鿿"),  # CJK Unified Ideographs
    ("㐀", "䶿"),  # Extension A
    ("　", "〿"),  # CJK punctuation (counted as zh signal)
    ("＀", "￯"),  # full-width forms
)
_KANA = (("぀", "ヿ"),)
_HANGUL = (("가", "힯"), ("ᄀ", "ᇿ"))

THAI_SHARE_THRESHOLD = 0.25
CJK_SHARE_THRESHOLD = 0.25


def _in(ch: str, ranges) -> bool:
    return any(lo <= ch <= hi for lo, hi in ranges)


def script_counts(text: str) -> dict[str, int]:
    counts = {"thai": 0, "cjk": 0, "latin": 0, "kana": 0, "hangul": 0, "other": 0}
    for ch in text:
        if ch.isspace() or ch.isdigit():
            continue
        cat = unicodedata.category(ch)
        if _THAI[0] <= ch <= _THAI[1]:
            counts["thai"] += 1
        elif _in(ch, _KANA):
            counts["kana"] += 1
        elif _in(ch, _HANGUL):
            counts["hangul"] += 1
        elif _in(ch, _CJK_RANGES):
            if cat.startswith("L"):
                counts["cjk"] += 1
        elif cat.startswith("L"):
            if ch.isascii() or unicodedata.name(ch, "").startswith("LATIN"):
                counts["latin"] += 1
            else:
                counts["other"] += 1
    return counts


def detect_language(text: str) -> Language:
    c = script_counts(text)
    letters = c["thai"] + c["cjk"] + c["latin"] + c["kana"] + c["hangul"] + c["other"]
    if letters == 0:
        return "other"
    if c["kana"] > 0 and c["kana"] >= c["cjk"] * 0.3:
        return "other"  # Japanese
    if c["hangul"] / letters >= 0.25:
        return "other"
    if c["thai"] / letters >= THAI_SHARE_THRESHOLD:
        return "th"
    if c["cjk"] / letters >= CJK_SHARE_THRESHOLD:
        return "zh"
    if c["latin"] / letters >= 0.5:
        return "en"
    if c["thai"] >= c["cjk"] and c["thai"] >= c["latin"] and c["thai"] > 0:
        return "th"
    if c["cjk"] > 0 and c["cjk"] >= c["latin"]:
        return "zh"
    if c["latin"] > 0:
        return "en"
    return "other"
