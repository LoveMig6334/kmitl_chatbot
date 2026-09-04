"""Deterministic answer checks shared by the eval harness and the unit tests.

No LLM judge: number grounding, dominant-script language check, ``<think>``
leakage and dangling citation markers are all pure string functions.
"""

from __future__ import annotations

import re

from gatekeeper.language import script_counts

from .context import dangling_markers, strip_markers

_THAI_DIGITS = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")
_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)*")


def normalize_digits(text: str) -> str:
    """Thai digits → Arabic digits."""
    return text.translate(_THAI_DIGITS)


def normalize_text(text: str) -> str:
    """Digits normalised, thousands separators dropped, whitespace collapsed — for ``must_contain`` matching."""
    text = re.sub(r"(?<=\d),(?=\d{3})", "", normalize_digits(text))
    return re.sub(r"\s+", " ", text).strip()


def _canon(num: str) -> str:
    # "32,000" -> "32000"; "2.50" stays "2.50"; trailing "." dropped
    return num.replace(",", "").rstrip(".")


def extract_numbers(text: str, *, ignore_markers: bool = True) -> list[str]:
    """Canonical number tokens in ``text`` (Arabic or Thai digits), markers excluded."""
    src = normalize_digits(strip_markers(text) if ignore_markers else text)
    return [_canon(m.group(0)) for m in _NUMBER_RE.finditer(src)]


def ungrounded_numbers(answer: str, context: str) -> list[str]:
    """Numbers in ``answer`` that appear nowhere in ``context`` (hallucination detector).

    A number is grounded if the same canonical token occurs in the context, or
    if it is at least 3 characters long and contained in a context number
    (``"2.5"`` inside ``"2.50"``, a course-code prefix).  Short numbers must
    match exactly (``"5"`` is NOT grounded by ``"5.5"``).
    """
    ctx_numbers = set(extract_numbers(context, ignore_markers=False))
    out: list[str] = []
    for n in extract_numbers(answer):
        if n in ctx_numbers:
            continue
        if len(n) >= 3 and any(n in c for c in ctx_numbers):
            continue
        if n not in out:
            out.append(n)
    return out


def dominant_script(text: str) -> str:
    """``th`` / ``en`` / ``zh`` / ``other``: the script with the most letters (digits, markers ignored).

    Unlike the gatekeeper's ``detect_language`` (which favours Thai for mixed
    *questions*), an *answer* in English may quote Thai program names — the
    majority script decides.  Ties go to Thai.
    """
    c = script_counts(strip_markers(text))
    thai, cjk, latin = c["thai"], c["cjk"], c["latin"]
    if thai == cjk == latin == 0:
        return "other"
    if thai >= cjk and thai >= latin:
        return "th"
    if cjk >= latin:
        return "zh"
    return "en"


def language_matches(answer: str, language: str) -> bool:
    expected = "en" if language == "other" else language
    return dominant_script(answer) == expected


def answered_in_language(answer: str, language: str) -> bool:
    """Lenient check for the answer-language guard: is the answer written in ``language``?

    Compares only the target script against Thai, so a Chinese or English answer
    that keeps English course names / codes (as instructed) is still accepted —
    unlike ``dominant_script``, where enough Latin course names can tip a valid
    Chinese answer to ``en``. The failure this guards against is "answered in
    Thai", so the rule is: the target script is present and is not out-weighed by
    Thai.
    """
    c = script_counts(strip_markers(answer))
    thai, cjk, latin = c["thai"], c["cjk"], c["latin"]
    if language == "th":
        return thai > 0 and thai >= cjk
    if language == "zh":
        return cjk > 0 and cjk >= thai
    # en / other: Latin present and at least as much as Thai (may quote Thai names)
    return latin > 0 and latin >= thai


def has_think_leak(text: str) -> bool:
    return "<think>" in text.lower() or "</think>" in text.lower()


def leakage_problems(answer: str, n_chunks: int) -> list[str]:
    problems: list[str] = []
    if has_think_leak(answer):
        problems.append("<think> leaked")
    dangling = dangling_markers(answer, n_chunks)
    if dangling:
        problems.append(f"dangling markers {dangling} (only 1..{n_chunks} exist)")
    return problems


def contains_all(answer: str, needles: list[str]) -> list[str]:
    """Return the ``needles`` NOT found in ``answer`` (after digit/whitespace normalisation)."""
    hay = normalize_text(answer)
    return [n for n in needles if normalize_text(n) not in hay]


def contains_any(answer: str, needles: list[str]) -> list[str]:
    """Return the ``needles`` that ARE found in ``answer``."""
    hay = normalize_text(answer)
    return [n for n in needles if normalize_text(n) in hay]
