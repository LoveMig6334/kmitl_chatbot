"""Parse / repair the LLM's JSON verdict.  Pure functions, no API calls.

ThaiLLM models frequently wrap the answer in ``<think>…</think>`` blocks or
```json fences, and truncated outputs leave the JSON object unterminated.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from .config import FACULTIES, FACULTY_KEYS
from .schema import CATEGORIES, LANGUAGES, QUESTION_KINDS

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_OPEN_THINK_RE = re.compile(r"<think>.*$", re.DOTALL | re.IGNORECASE)
_FENCE_RE = re.compile(r"```(?:json|JSON)?\s*(.*?)\s*```", re.DOTALL)

_CATEGORY_ALIASES = {
    "in-scope": "in_scope",
    "inscope": "in_scope",
    "in scope": "in_scope",
    "off_topic": "off_topic_general",
    "off-topic": "off_topic_general",
    "off_topic_generic": "off_topic_general",
    "general": "off_topic_general",
    "other_university": "off_topic_other_university",
    "off_topic_university": "off_topic_other_university",
    "out_of_scope": "out_of_scope_kmitl",
    "kmitl_out_of_scope": "out_of_scope_kmitl",
    "injection": "injection_or_abuse",
    "abuse": "injection_or_abuse",
    "prompt_injection": "injection_or_abuse",
    "jailbreak": "injection_or_abuse",
}
_KIND_ALIASES = {
    "fact": "fact_lookup",
    "factual": "fact_lookup",
    "lookup": "fact_lookup",
    "fact-lookup": "fact_lookup",
    "description": "descriptive",
    "describe": "descriptive",
    "explain": "descriptive",
    "compare": "comparison",
    "comparative": "comparison",
}
_LANG_ALIASES = {
    "thai": "th",
    "tha": "th",
    "english": "en",
    "eng": "en",
    "chinese": "zh",
    "zh-cn": "zh",
    "zh-tw": "zh",
    "zh_cn": "zh",
    "cn": "zh",
    "mandarin": "zh",
}


@dataclass
class LLMVerdict:
    category: str
    language: str | None = None
    faculty: str | None = None
    program: str | None = None
    question_kind: str | None = None
    university: str | None = None
    topic: str | None = None
    confidence: float | None = None
    raw: str = ""


def strip_think(text: str) -> str:
    text = _THINK_RE.sub("", text)
    # An unterminated <think> that never produced JSON: drop everything after it
    # only if no JSON object follows.
    if "<think>" in text.lower() and "{" not in text.split("<think>")[-1]:
        text = _OPEN_THINK_RE.sub("", text)
    return text.strip()


def _balance(fragment: str) -> str:
    """Close open strings / brackets in a truncated JSON fragment."""
    out: list[str] = []
    stack: list[str] = []
    in_str = False
    esc = False
    for ch in fragment:
        out.append(ch)
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch in "{[":
            stack.append("}" if ch == "{" else "]")
        elif ch in "}]" and stack:
            stack.pop()
    if in_str:
        out.append('"')
    s = "".join(out).rstrip()
    # remove dangling separators like `"key":` or trailing comma
    s = re.sub(r",\s*$", "", s)
    s = re.sub(r':\s*$', ": null", s)
    s = re.sub(r',\s*"[^"]*"\s*$', "", s)  # dangling key without colon
    s = re.sub(r",\s*$", "", s)
    while stack:
        s += stack.pop()
    return s


def extract_json_object(text: str) -> dict | None:
    """Find the first JSON object in ``text``; repair truncation if needed."""
    text = strip_think(text)
    m = _FENCE_RE.search(text)
    candidates = [m.group(1)] if m else []
    start = text.find("{")
    if start >= 0:
        candidates.append(text[start:])
    for cand in candidates:
        cand = cand.strip()
        if not cand:
            continue
        try:
            obj = json.loads(cand)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass
        # take the longest prefix that ends at a closing brace, else repair
        end = cand.rfind("}")
        if end > 0:
            try:
                obj = json.loads(cand[: end + 1])
                if isinstance(obj, dict):
                    return obj
            except json.JSONDecodeError:
                pass
        try:
            obj = json.loads(_balance(cand))
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            continue
    return None


def _norm(value: object) -> str | None:
    if value is None:
        return None
    s = str(value).strip().lower()
    return s or None


def normalize_category(value: object) -> str | None:
    s = _norm(value)
    if s is None:
        return None
    s = s.replace(" ", "_")
    if s in CATEGORIES:
        return s
    return _CATEGORY_ALIASES.get(s) or _CATEGORY_ALIASES.get(s.replace("_", "-"))


def normalize_language(value: object) -> str | None:
    s = _norm(value)
    if s is None:
        return None
    if s in LANGUAGES:
        return s
    return _LANG_ALIASES.get(s) or (s.split("-")[0] if s.split("-")[0] in LANGUAGES else None)


def normalize_question_kind(value: object) -> str | None:
    s = _norm(value)
    if s is None:
        return None
    s = s.replace(" ", "_")
    if s in QUESTION_KINDS:
        return s
    return _KIND_ALIASES.get(s)


def normalize_faculty(value: object) -> str | None:
    """Map a free-form faculty string (any language) to a canonical key."""
    s = _norm(value)
    if s is None or s in ("null", "none", "n/a", "-"):
        return None
    if s.upper() in FACULTY_KEYS:
        return s.upper()
    for f in FACULTIES:
        names = (f.name_th.lower(), f.name_en.lower(), f.name_zh.lower(), *f.aliases)
        if any(n and (n in s or s in n) for n in names):
            return f.key
    return None


def normalize_program(value: object) -> str | None:
    s = _norm(value)
    if s is None or s in ("null", "none", "n/a", "-"):
        return None
    for f in FACULTIES:
        for code, aliases in f.programs.items():
            if s.upper() == code or any(a in s or s in a for a in aliases if len(a) > 1):
                return code
    return str(value).strip() or None


def _confidence(value: object) -> float | None:
    try:
        c = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if c > 1.0:
        c = c / 100.0
    return max(0.0, min(1.0, c))


def parse_verdict(raw: str) -> LLMVerdict | None:
    """Return a normalised verdict or ``None`` if no valid category is found."""
    obj = extract_json_object(raw or "")
    if not obj:
        return None
    category = normalize_category(obj.get("category") or obj.get("class") or obj.get("label"))
    if category is None:
        return None
    return LLMVerdict(
        category=category,
        language=normalize_language(obj.get("language") or obj.get("lang")),
        faculty=normalize_faculty(obj.get("faculty")),
        program=normalize_program(obj.get("program")),
        question_kind=normalize_question_kind(obj.get("question_kind") or obj.get("kind")),
        university=(_norm(obj.get("university")) and str(obj.get("university")).strip()) or None,
        topic=_norm(obj.get("topic")),
        confidence=_confidence(obj.get("confidence")),
        raw=raw,
    )
