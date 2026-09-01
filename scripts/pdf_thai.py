"""Thai text extraction from the curriculum PDFs (pymupdf) with PUA repair.

The documents are typeset in TH Sarabun PSK / Angsana New.  Word/PDF export
maps the *repositioned* forms of vowels and tone marks (e.g. ิ moved left of a
tall consonant, ุ lowered under ฎ) to Private Use Area codepoints, so
``page.get_text()`` yields "หลกสูตร" with an invisible U+E04A where ั should
be.  Each PDF's subset font has its own PUA assignment, so the table is derived
per file: for every PUA code, try each Thai mark and keep the one that turns the
most surrounding snippets into dictionary words (pythainlp ``thai_words``).

Derived tables are cached in ``tests/fixtures/pua_maps.json`` (small, committed)
so fixture regeneration is deterministic and the mapping can be audited.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUA_MAP_PATH = ROOT / "tests" / "fixtures" / "pua_maps.json"

# Codes the dictionary scorer could not settle but whose context is unambiguous
# (checked by hand against the page).  Applied on top of the derived table.
MANUAL_OVERRIDES: dict[str, dict[str, str]] = {
    "AIT.pdf": {
        "\ue075": "\u0e48",  # "ชื?อวิชา" → ชื่อวิชา (mai ek), 6 occurrences
        "\ue06b": "\u0e35",  # "ปีท?่1" → ปีที่ 1 (sara ii); scorer preferred ุ on 5 contexts
    },
}

THAI_MARKS = "ัิีึืุู็่้๊๋์"  # above/below vowels + tone marks + thanthakhat
CANDIDATES = THAI_MARKS + "ำญฐฎฏ"  # some fonts also remap these glyph variants
THAI_FONT_RE = re.compile(r"sarabun|angsana|cordia|browallia|tahoma|thai", re.IGNORECASE)
_PUA_RE = re.compile(f"[{chr(0xE000)}-{chr(0xF8FF)}]")  # built with chr(): editors may strip PUA literals
_THAI_CHAR = re.compile(r"[฀-๿]")


def is_pua(ch: str) -> bool:
    return 0xE000 <= ord(ch) <= 0xF8FF


@lru_cache(maxsize=1)
def _words() -> frozenset[str]:
    from pythainlp.corpus import thai_words

    return frozenset(w for w in thai_words() if len(w) >= 2)


def _spans(page):
    """Yield (text, font) for every span on the page, in reading order."""
    d = page.get_text("dict", sort=True)
    for block in d["blocks"]:
        for line in block.get("lines", []):
            for span in line["spans"]:
                yield span["text"], span["font"]
            yield "\n", ""


# Wingdings2 checkbox glyphs (verified on AIT.pdf p.2/p.4: the ticked option is E006).
SYMBOL_GLYPHS = {"\ue006": "☑ ", "\ue00c": "☐ "}


def raw_page_text(page) -> str:
    """Page text with Thai-font PUA left in place; symbol-font glyphs become ☑/☐ or are dropped."""
    out: list[str] = []
    for text, font in _spans(page):
        if text == "\n":
            out.append("\n")
            continue
        if not THAI_FONT_RE.search(font):
            text = _PUA_RE.sub(lambda m: SYMBOL_GLYPHS.get(m.group(0), ""), text)
        out.append(text)
    return "".join(out)


def _score(contexts: list[tuple[str, str]], mark: str) -> float:
    """Mean length of the dictionary word that *contains* the substituted mark (0 when none).

    Longer covering words are much stronger evidence (หลักสูตร beats ลุก), which
    is what separates the right mark from look-alikes.
    """
    from pythainlp import word_tokenize

    words = _words()
    total = 0
    for left, right in contexts:
        snippet = left + mark + right
        pos = len(left)
        offset = 0
        for tok in word_tokenize(snippet, engine="newmm", keep_whitespace=False):
            start = snippet.find(tok, offset)
            if start < 0:
                continue
            end = start + len(tok)
            if start <= pos < end:
                if tok in words and len(tok) >= 2:
                    total += len(tok)
                break
            offset = end
    return total / max(1, len(contexts))


def _contexts(doc, resolved: dict[str, str], *, max_pages: int) -> dict[str, list[tuple[str, str]]]:
    contexts: dict[str, list[tuple[str, str]]] = defaultdict(list)
    step = max(1, doc.page_count // max_pages)
    for i in range(0, doc.page_count, step):
        text = repair_partial(raw_page_text(doc[i]), resolved)
        for m in _PUA_RE.finditer(text):
            left = text[max(0, m.start() - 8) : m.start()]
            right = text[m.end() : m.end() + 8]
            left = re.sub(r"^.*?([฀-๿]*)$", r"\1", left, flags=re.DOTALL)
            right = re.sub(r"^([฀-๿]*).*$", r"\1", right, flags=re.DOTALL)
            contexts[m.group(0)].append((left, right))
    return contexts


def repair_partial(text: str, pua_map: dict[str, str]) -> str:
    """Replace only the codes present in ``pua_map``; leave unknown codes in place."""
    return _PUA_RE.sub(lambda m: pua_map.get(m.group(0), m.group(0)), text)


def derive_pua_map(doc, *, max_pages: int = 80, min_score: float = 1.5, max_passes: int = 4) -> dict[str, dict]:
    """Return {pua_char: {"to": mark|"", "score": float, "n": count, "example": str}}.

    Iterative: codes resolved with confidence in one pass are substituted before
    the next so stacked marks (ั + ้ in ตั้ง) get real context.  Stops when a pass
    resolves nothing new.
    """
    resolved: dict[str, str] = {}
    table: dict[str, dict] = {}
    for _pass in range(max_passes):
        contexts = _contexts(doc, resolved, max_pages=max_pages)
        new = 0
        for code, ctx in sorted(contexts.items()):
            if code in resolved:
                continue
            scored = sorted(((_score(ctx, m), m) for m in CANDIDATES), reverse=True)
            best_score, best = scored[0]
            example = max(ctx, key=lambda c: min(len(c[0]), len(c[1])))
            entry = {"to": best if best_score >= min_score else "", "score": round(best_score, 2), "n": len(ctx),
                     "example": example[0] + "?" + example[1], "runner_up": f"{scored[1][1]}={scored[1][0]:.2f}"}
            if best_score < min_score:
                entry["note"] = "unresolved — dropped" + (" (rare)" if len(ctx) < 3 else "")
            else:
                resolved[code] = best
                new += 1
            table[code] = entry
        if not new:
            break
    for code, mark in MANUAL_OVERRIDES.get(getattr(doc, "name", "") and Path(doc.name).name, {}).items():
        if code in table:
            table[code].update({"to": mark, "note": "manual override"})
    return table


def load_pua_maps() -> dict[str, dict[str, str]]:
    if not PUA_MAP_PATH.exists():
        return {}
    raw = json.loads(PUA_MAP_PATH.read_text(encoding="utf-8"))
    return {fname: {code: entry["to"] for code, entry in table.items()} for fname, table in raw.items()}


def save_pua_maps(tables: dict[str, dict[str, dict]]) -> None:
    PUA_MAP_PATH.parent.mkdir(parents=True, exist_ok=True)
    PUA_MAP_PATH.write_text(json.dumps(tables, ensure_ascii=False, indent=1), encoding="utf-8")


def repair(text: str, pua_map: dict[str, str]) -> str:
    text = _PUA_RE.sub(lambda m: pua_map.get(m.group(0), ""), text)
    return text.replace("\u0e4d\u0e32", "\u0e33")  # decomposed sara am (ํ + า) → ำ


def mark_ratio(text: str) -> float:
    thai = len(_THAI_CHAR.findall(text))
    marks = sum(1 for ch in text if ch in THAI_MARKS)
    return marks / thai if thai else 0.0


def page_text(page, pua_map: dict[str, str]) -> str:
    return repair(raw_page_text(page), pua_map)


def pua_stats(text: str) -> Counter:
    return Counter(_PUA_RE.findall(text))
