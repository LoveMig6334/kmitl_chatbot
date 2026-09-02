"""Parse / repair the LLM's JSON verdict.  Pure functions, no API calls.

ThaiLLM models frequently wrap the answer in ``<think>…</think>`` blocks or
```json fences, and truncated outputs leave the JSON object unterminated.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from .config import PROGRAM_IDS, PROGRAMS
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
    "greeting": "greeting_smalltalk",
    "greetings": "greeting_smalltalk",
    "smalltalk": "greeting_smalltalk",
    "small_talk": "greeting_smalltalk",
    "small-talk": "greeting_smalltalk",
    "chitchat": "greeting_smalltalk",
    "chit_chat": "greeting_smalltalk",
    "greeting_or_smalltalk": "greeting_smalltalk",
    "greeting_small_talk": "greeting_smalltalk",
    "greeting/smalltalk": "greeting_smalltalk",
    "social": "greeting_smalltalk",
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
    programs: list[str] = field(default_factory=list)
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


def _program_id_for(value: str) -> str | None:
    s = value.strip().lower()
    if not s or s in ("null", "none", "n/a", "-"):
        return None
    if s.upper() in PROGRAM_IDS:
        return s.upper()
    for p in PROGRAMS:
        names = (p.name_th.lower(), p.name_en.lower(), *p.aliases, *(a.lower() for a in p.exact_aliases), *p.weak_aliases)
        for n in names:
            if not n:
                continue
            if n.isascii():
                if re.search(rf"(?<![a-z]){re.escape(n)}(?![a-z])", s):
                    return p.id
            elif n in s or s in n:
                return p.id
    return None


def normalize_programs(value: object) -> list[str]:
    """Map a free-form program string/list (any language) to canonical ids."""
    if value is None:
        return []
    items: list[str]
    if isinstance(value, (list, tuple, set)):
        items = [str(v) for v in value if v is not None]
    else:
        items = re.split(r"[,/;]|\s+(?:and|กับ|และ|与|和)\s+", str(value))
    out: list[str] = []
    for item in items:
        pid = _program_id_for(item)
        if pid and pid not in out:
            out.append(pid)
    return out


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
        programs=normalize_programs(obj.get("programs") if obj.get("programs") is not None else obj.get("program")),
        question_kind=normalize_question_kind(obj.get("question_kind") or obj.get("kind")),
        university=(_norm(obj.get("university")) and str(obj.get("university")).strip()) or None,
        topic=_norm(obj.get("topic")),
        confidence=_confidence(obj.get("confidence")),
        raw=raw,
    )
