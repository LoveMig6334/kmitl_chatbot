#!/usr/bin/env python
"""(Re)build ``tests/fixtures/chunks.jsonl`` — the retrieval fixtures used by the
answer-layer tests and ``scripts/eval_answers.py``.

Real PDFs (``data/raw/*.pdf``, file name → program: AIT.pdf→AIT, DSBA.pdf→DSBA,
IT_inter2565.pdf→BIT, IT2565.pdf→IT):

1. text is extracted with pymupdf and the TH Sarabun PSK private-use-area
   codepoints are repaired into real Thai vowels/tone marks
   (``scripts/pdf_thai.py``; tables in ``tests/fixtures/pua_maps.json``);
2. page headers/footers are stripped and numbered headings tracked into
   ``heading_path`` (``หมวดที่3 … > 3.1 โครงสร้างหลักสูตร… > 3.1.1 …``);
3. blocks are split at headings / paragraph gaps and capped at
   ``MAX_CHARS`` (700) on line boundaries;
4. a keyword pass keeps the blocks that carry the fact types the eval needs
   (``FACT_PATTERNS``) plus the first course descriptions of the year-1 plan.
   Every chunk records ``facts`` (which fact types matched) and ``source``.

Without PDFs the synthetic set is written (``"synthetic": true``).

Usage::

    python scripts/build_fixtures.py            # auto: PDFs if present, else synthetic
    python scripts/build_fixtures.py --synthetic
    python scripts/build_fixtures.py --dump-pages AIT.pdf 2 4   # print repaired page text
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
DEFAULT_OUT = ROOT / "tests" / "fixtures" / "chunks.jsonl"
DEFAULT_PDF_DIR = ROOT / "data" / "raw"
PUA_MAP_FILE = ROOT / "tests" / "fixtures" / "pua_maps.json"
MAX_CHARS = 700
PER_FACT_LIMIT = 3  # blocks kept per fact type per program

PDF_PROGRAM = {"AIT.pdf": "AIT", "DSBA.pdf": "DSBA", "IT_inter2565.pdf": "BIT", "IT2565.pdf": "IT"}

# --------------------------------------------------------------------------- #
# Fact types to cover per program.  (name, regex over heading + text)
# --------------------------------------------------------------------------- #
FACT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("name_degree", re.compile(r"ชื่อปริญญาและสาขาวิชา|ชื่อเต็ม\s*\(ภาษาไทย\)|^1\.\s*ชื่อหลักสูตร", re.MULTILINE)),
    ("curriculum_year", re.compile(r"หลักสูตร(ใหม่|ปรับปรุง)\s*พ\.?ศ\.?\s*25\d\d")),
    ("credits_total", re.compile(r"จำนวนหน่วยกิต(ที่เรียน|รวม)ตลอดหลักสูตร")),
    ("duration", re.compile(r"ระยะเวล?าการศึกษาของหลักสูตร|หลักสูตรปริญญาตรี\s*4\s*ปี")),
    ("opening", re.compile(r"กำหนดเปิดสอน")),
    ("careers", re.compile(r"อาชีพที่สามารถประกอบได้")),
    ("admission", re.compile(r"คุณสมบัติของผู้เข้าศึกษา")),
    ("structure", re.compile(r"โครงสร้างหลักสูตร\s*$|^3\.?1\.?2\s*โครงสร้างหลักสูตร|3\.3\.1\.2\s*โครงสร้างหลักสูตร", re.MULTILINE)),
    ("plan_y1s1", re.compile(r"ปีที่\s*1\s*ภาคการศึกษาที่\s*1")),
    ("plan_y1s2", re.compile(r"ปีที่\s*1\s*ภาคการศึกษาที่\s*2")),
    ("fees", re.compile(r"ค่าธรรมเนียม|ค่าเล่าเรียน|ค่าใช้จ่ายต่อหัว|งบประมาณ")),
    ("philosophy", re.compile(r"^1\.?\s*ปรัชญา|ปรัชญาของหลักสูตร|1\.1\s*ปรัชญา", re.MULTILINE)),
    ("objectives", re.compile(r"วัตถุประสงค์ของหลักสูตร|1\.2\s*วัตถุประสงค์", re.MULTILINE)),
    ("tracks", re.compile(r"กลุ่มวิชาสาขา|แขนงวิชา|วิชาเอกหรือความเชี่ยวชาญ")),
    ("internship", re.compile(r"สหกิจศึกษา|ฝึกงาน")),
    ("language_of_instruction", re.compile(r"ภาษาที่ใช้")),
    ("admission_plan", re.compile(r"แผนการรับนักศึกษา|จำนวนนักศึกษาที่จะรับ|จำนวนรับ")),
]
COURSE_DESC_HEADING = re.compile(r"คำอธิบายรายวิชา")
COURSE_CODE_LINE = re.compile(r"^\s*(\d{8})\s*$", re.MULTILINE)
COURSE_DESC_START = re.compile(r"^\s*(\d{8})\s+\S", re.MULTILINE)

PAGE_NUMBER = re.compile(r"^\s*\d{1,3}\s*$")  # only stripped at the very top/bottom of a page (tables hold bare numbers too)
HEADER_PATTERNS = (
    re.compile(r"^\s*(รายละเอียดหลักสูตร|มคอ\.?\s*2)\s*$"),
    re.compile(r"^\s*วท\.บ\.?\s*\("),  # running footer, line 1 ("วท.บ.(สาขาวิชา…) คณะ…")
    re.compile(r"^\s*คณะเทคโนโลยีสารสนเทศ\s*สจล\.?\s*$"),  # running footer, line 2 (DSBA wraps it)
)
TOC_LINE = re.compile(r"\.{6,}\s*\d+\s*$", re.MULTILINE)
TOP_HEADING = re.compile(r"^\s*หมวดที่\s*\d+\s*\S")
NUM_HEADING = re.compile(r"^\s*(\d+\.(?:\d+\.?){0,3})\s*([^\W\d(].*)$")  # "8. อาชีพ…", "2.2 คุณสมบัติ…", not "3 (3-0-6)"
DOTTED_LEADER = re.compile(r"\.{6,}")


def clean_lines(text: str) -> list[str]:
    out: list[str] = []
    for raw in text.split("\n"):
        line = re.sub(r"[ \t ]+", " ", raw).strip()
        if not line:
            out.append("")
            continue
        if any(p.match(line) for p in HEADER_PATTERNS):
            continue
        out.append(line)
    # page number: a bare number among the first two non-empty lines (all four PDFs number pages at the top)
    nonempty = [i for i, ln in enumerate(out) if ln]
    for i in nonempty[:2]:
        if PAGE_NUMBER.match(out[i]):
            out[i] = ""
    while out and not out[0]:
        out.pop(0)
    while out and not out[-1]:
        out.pop()
    return out


def heading_level(line: str) -> tuple[int, str] | None:
    if TOP_HEADING.match(line):
        return 0, line
    m = NUM_HEADING.match(line)
    if m and len(m.group(2)) <= 90:
        depth = m.group(1).rstrip(".").count(".") + 1
        if depth <= 3 and not re.search(r"หน่วยกิต\s*$", line) and not DOTTED_LEADER.search(line):
            return depth, line
    return None


def split_block(lines: list[str]) -> list[list[str]]:
    """Split a long block on line boundaries so each part stays under MAX_CHARS."""
    parts: list[list[str]] = []
    cur: list[str] = []
    size = 0
    for ln in lines:
        if cur and size + len(ln) + 1 > MAX_CHARS:
            parts.append(cur)
            cur, size = [], 0
        cur.append(ln)
        size += len(ln) + 1
    if cur:
        parts.append(cur)
    return parts


def page_blocks(page_no: int, lines: list[str], path: list[str]) -> list[dict]:
    """Group lines into heading-delimited blocks; ``path`` (mutable) carries headings across pages."""
    blocks: list[dict] = []
    cur: list[str] = []
    blank_run = 0

    def flush() -> None:
        nonlocal cur
        text_lines = [ln for ln in cur if ln]
        if text_lines:
            for i, part in enumerate(split_block(text_lines)):
                blocks.append({"page": page_no, "heading_path": " > ".join(p for p in path if p), "lines": part, "part": i})
        cur = []

    for ln in lines:
        if not ln:
            blank_run += 1
            if blank_run >= 2:
                flush()
            continue
        blank_run = 0
        hl = heading_level(ln)
        if hl is not None:
            if any(heading_level(x) is None for x in cur if x):
                flush()  # a heading starts a new block — unless the block so far is only headings
            depth, title = hl
            del path[depth:]
            path.extend([""] * (depth - len(path)))
            # "3.2.7 …" belongs under "3.2 …"/"3. …": blank stale intermediate headings from another section
            number = title.split()[0].rstrip(".") if depth else ""
            for level in range(1, depth):
                parent = path[level]
                parent_number = parent.split()[0].rstrip(".") if parent else ""
                expected = ".".join(number.split(".")[:level])
                if parent_number != expected:
                    path[level] = ""
            path.append(title[:80])
        cur.append(ln)
    flush()
    return blocks


def extract_blocks(doc, pua_map: dict[str, str]) -> list[dict]:
    from pdf_thai import page_text

    path: list[str] = []
    blocks: list[dict] = []
    for i in range(doc.page_count):
        lines = clean_lines(page_text(doc[i], pua_map))
        blocks.extend(page_blocks(i + 1, lines, path))
    for b in blocks:
        b["text"] = "\n".join(b["lines"])
    return blocks


def _is_toc(b: dict) -> bool:
    """Table-of-contents blocks: several lines ending in dotted leaders + page numbers."""
    return len(TOC_LINE.findall(b["text"])) >= 3


def select_blocks(blocks: list[dict]) -> list[dict]:
    """Keyword pass: keep blocks carrying the fact types + first year-1 course descriptions."""
    chosen: dict[int, dict] = {}
    fact_hits: dict[str, int] = {}
    for idx, b in enumerate(blocks):
        if _is_toc(b) or len(b["text"]) < 20:
            continue
        hay = b["heading_path"] + "\n" + b["text"]
        facts = [name for name, pat in FACT_PATTERNS if pat.search(hay)]
        keep = [f for f in facts if fact_hits.get(f, 0) < PER_FACT_LIMIT]
        if not keep:
            continue
        for f in keep:
            fact_hits[f] = fact_hits.get(f, 0) + 1
        chosen[idx] = {**b, "facts": facts}
    return [chosen[i] for i in sorted(chosen)]


COURSE_ENTRY_START = re.compile(r"^\s*(\d{8})(\s+\S.*)?$")
PREREQ = re.compile(r"วิชาบังคับก่อน|PREREQUISITE", re.IGNORECASE)


def course_descriptions(doc, pua_map: dict[str, str], wanted_codes: set[str], *, limit: int = 4) -> list[dict]:
    """Course-description entries from the appendix (``คำอธิบายรายวิชา``), one chunk per course.

    An entry starts at a line holding the 8-digit code (alone, or followed by
    the Thai name) and runs to the next code line; only entries with a
    prerequisite line are real descriptions (study-plan tables also list codes).
    Year-1 courses are preferred; entries are truncated to MAX_CHARS.
    """
    from pdf_thai import page_text

    start_page = None
    for i in range(doc.page_count // 2, doc.page_count):
        if "คำอธิบายรายวิชา" in page_text(doc[i], pua_map):
            start_page = i
            break
    if start_page is None:
        return []
    entries: list[dict] = []
    for i in range(start_page, doc.page_count):
        lines = clean_lines(page_text(doc[i], pua_map))
        cur: list[str] | None = None
        code = ""
        for ln in lines:
            m = COURSE_ENTRY_START.match(ln)
            if m:
                if cur:
                    entries.append({"page": i + 1, "code": code, "lines": cur})
                cur, code = [ln], m.group(1)
            elif cur is not None and ln:
                cur.append(ln)
        if cur:
            entries.append({"page": i + 1, "code": code, "lines": cur})
    real = [e for e in entries if PREREQ.search("\n".join(e["lines"]))]
    preferred = [e for e in real if e["code"] in wanted_codes]
    out: list[dict] = []
    seen: set[str] = set()
    for e in preferred + real:
        if e["code"] in seen or len(out) >= limit:
            continue
        seen.add(e["code"])
        text = "\n".join(e["lines"])[:MAX_CHARS]
        out.append({"page": e["page"], "heading_path": "ภาคผนวก > คำอธิบายรายวิชา", "text": text, "facts": ["course_desc"], "lines": e["lines"]})
    return out


def _year1_codes(picked: list[dict]) -> set[str]:
    codes: set[str] = set()
    for b in picked:
        if any(f.startswith("plan_y1") for f in b["facts"]):
            codes.update(COURSE_CODE_LINE.findall(b["text"]))
            codes.update(re.findall(r"^\s*(\d{8})\s", b["text"], re.MULTILINE))
    return codes




def _dropped_pua(doc, table: dict) -> dict[str, int]:
    """Occurrences of PUA codes that the table maps to '' (lost vowels/tone marks), whole document."""
    from pdf_thai import pua_stats, raw_page_text

    counts: dict[str, int] = {}
    for i in range(doc.page_count):
        for code, n in pua_stats(raw_page_text(doc[i])).items():
            if not table.get(code, {}).get("to"):
                counts[hex(ord(code))] = counts.get(hex(ord(code)), 0) + n
    return dict(sorted(counts.items(), key=lambda kv: -kv[1]))


def pdf_rows(pdf_dir: Path) -> list[dict]:
    import pymupdf
    from pdf_thai import derive_pua_map, load_pua_maps, save_pua_maps

    maps = load_pua_maps()
    tables: dict = json.loads(PUA_MAP_FILE.read_text(encoding="utf-8")) if PUA_MAP_FILE.exists() else {}
    rows: list[dict] = []
    for pdf in sorted(pdf_dir.glob("*.pdf")):
        prog = PDF_PROGRAM.get(pdf.name)
        if prog is None:
            print(f"! {pdf.name}: not in PDF_PROGRAM — skipped", file=sys.stderr)
            continue
        doc = pymupdf.open(pdf)
        if pdf.name not in maps:
            print(f"deriving PUA table for {pdf.name} …", file=sys.stderr)
            tables[pdf.name] = derive_pua_map(doc)
            save_pua_maps(tables)
            maps = load_pua_maps()
        blocks = extract_blocks(doc, maps[pdf.name])
        dropped = _dropped_pua(doc, tables.get(pdf.name, {}))
        if dropped:
            print(f"{pdf.name}: PUA codes dropped (unresolved): {dropped}", file=sys.stderr)
        picked = select_blocks(blocks)
        picked += course_descriptions(doc, maps[pdf.name], _year1_codes(picked))
        picked.sort(key=lambda b: b["page"])
        counter: dict[int, int] = {}
        for b in picked:
            counter[b["page"]] = counter.get(b["page"], 0) + 1
            rows.append({
                "chunk_id": f"{prog}-p{b['page']}-c{counter[b['page']]}",
                "program": prog,
                "page": b["page"],
                "heading_path": b["heading_path"] or "(ไม่มีหัวข้อ)",
                "text": b["text"],
                "score": 0.0,
                "synthetic": False,
                "facts": b["facts"],
                "source": pdf.name,
            })
        covered = sorted({f for b in picked for f in b["facts"]})
        missing = [name for name, _ in FACT_PATTERNS if name not in covered]
        print(f"{pdf.name}: {prog} — {len(picked)} chunks from {len(blocks)} blocks; missing fact types: {missing}", file=sys.stderr)
    return rows


def synthetic_rows() -> list[dict]:
    from synthetic_fixtures import SYNTHETIC

    return [
        {"chunk_id": cid, "program": prog, "page": page, "heading_path": heading, "text": " ".join(text.split()), "score": 0.0, "synthetic": True}
        for cid, prog, page, heading, text in SYNTHETIC
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--pdf-dir", type=Path, default=DEFAULT_PDF_DIR)
    ap.add_argument("--synthetic", action="store_true", help="force the synthetic set even if PDFs exist")
    ap.add_argument("--dump-pages", nargs="+", metavar="ARG", help="PDF name followed by page numbers: print repaired text and exit")
    args = ap.parse_args()

    if args.dump_pages:
        import pymupdf
        from pdf_thai import load_pua_maps, page_text

        name, *pages = args.dump_pages
        doc = pymupdf.open(args.pdf_dir / name)
        pua = load_pua_maps().get(name, {})
        for pg in pages:
            print(f"######## {name} page {pg}")
            print("\n".join(clean_lines(page_text(doc[int(pg) - 1], pua))))
        return 0

    use_pdf = not args.synthetic and args.pdf_dir.is_dir() and any(args.pdf_dir.glob("*.pdf"))
    rows = pdf_rows(args.pdf_dir) if use_pdf else synthetic_rows()
    if not rows:
        print("no passages extracted", file=sys.stderr)
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"wrote {len(rows)} {'real PDF' if use_pdf else 'SYNTHETIC'} chunks to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
