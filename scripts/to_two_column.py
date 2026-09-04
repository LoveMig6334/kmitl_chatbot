#!/usr/bin/env python
"""Reshape a results CSV into two columns: ``question`` and ``answer``.

Input is any CSV that has a ``question`` column and an answer column (``answer``,
or ``answer_run1`` from the wide file).  Output keeps only ``question,answer``.

Bullet-point answers are written in **long format**: each bullet becomes its own
row.  The question is shown once (on the first row of that answer); the bullet
rows below it leave the question cell empty.  A lead-in sentence before the
bullets is its own first row.  Answers with no bullets stay on a single row.

Example
-------
  question,answer
  IT2565 แบ่งภาคการศึกษาอย่างไร,หลักสูตร IT2565 แบ่งเป็น 3 ภาค ได้แก่
  ,ภาคการศึกษาที่ 1: สิงหาคม - พฤศจิกายน [2]
  ,ภาคการศึกษาที่ 2: มกราคม - เมษายน [2]
  ,ภาคฤดูร้อน: มิถุนายน - กรกฎาคม [3]

Usage
-----
  python scripts/to_two_column.py                                  # results_run1.csv -> results_run1_qa.csv
  python scripts/to_two_column.py --all                            # run1/2/3 -> *_qa.csv
  python scripts/to_two_column.py --input real_test_csv/results_run2.csv
  python scripts/to_two_column.py --input any.csv --answer-col answer_run1 --output out.csv
"""

from __future__ import annotations

import argparse
import csv
import re
from collections.abc import Sequence
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# A line is a bullet if it starts with a dash/star/bullet glyph, or a number like
# "1." / "1)" / "(1)", followed by whitespace.
_BULLET = re.compile(r"^\s*(?P<marker>[-*•–▪·]|\(?\d+[.)])\s+(?P<body>.*\S)\s*$")
_NUMBERED = re.compile(r"^\(?\d+[.)]$")


def has_bullets(answer: str) -> bool:
    return any(_BULLET.match(line) for line in answer.splitlines())


def to_segments(answer: str) -> list[str]:
    """Split a bulleted answer into ordered segments (lead paragraph + one per bullet).

    Numeric markers ("1)", "(2)") are kept so ordering survives; dash/star/bullet
    glyphs are dropped for a clean cell.  Consecutive non-bullet lines join into
    one paragraph segment; blank lines separate segments.
    """
    segments: list[str] = []
    paragraph: list[str] = []

    def flush() -> None:
        if paragraph:
            text = " ".join(p.strip() for p in paragraph).strip()
            if text:
                segments.append(text)
            paragraph.clear()

    for line in answer.splitlines():
        if not line.strip():
            flush()
            continue
        m = _BULLET.match(line)
        if m:
            flush()
            marker, body = m.group("marker"), m.group("body").strip()
            segments.append(f"{marker} {body}" if _NUMBERED.match(marker) else body)
        else:
            paragraph.append(line)
    flush()
    return segments


def reshape_rows(question: str, answer: str) -> list[tuple[str, str]]:
    answer = (answer or "").strip()
    if not answer or not has_bullets(answer):
        return [(question, answer)]
    segs = to_segments(answer)
    if not segs:
        return [(question, answer)]
    return [(question if i == 0 else "", seg) for i, seg in enumerate(segs)]


def pick_answer_col(fieldnames: Sequence[str], override: str | None) -> str:
    if override:
        return override
    for c in ("answer", "answer_run1"):
        if c in fieldnames:
            return c
    raise SystemExit(f"no answer column found; columns are {fieldnames}. Use --answer-col.")


def convert(in_path: Path, out_path: Path, answer_col: str | None) -> tuple[int, int]:
    with in_path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        col = pick_answer_col(reader.fieldnames or [], answer_col)
        rows = list(reader)
    out_rows: list[tuple[str, str]] = []
    for r in rows:
        out_rows.extend(reshape_rows((r.get("question") or "").strip(), r.get(col) or ""))
    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["question", "answer"])
        w.writerows(out_rows)
    return len(rows), len(out_rows)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", default="real_test_csv/results_run1.csv")
    ap.add_argument("--output", default=None, help="default: <input>_qa.csv next to the input")
    ap.add_argument("--answer-col", default=None, help="answer column name (auto: answer, then answer_run1)")
    ap.add_argument("--all", action="store_true", help="convert results_run1/2/3.csv in the input's folder")
    args = ap.parse_args()

    in_path = (REPO / args.input) if not Path(args.input).is_absolute() else Path(args.input)
    targets: list[tuple[Path, Path]] = []
    if args.all:
        folder = in_path.parent
        for n in (1, 2, 3):
            src = folder / f"results_run{n}.csv"
            if src.exists():
                targets.append((src, folder / f"results_run{n}_qa.csv"))
        if not targets:
            raise SystemExit(f"no results_run*.csv found in {folder}")
    else:
        out = Path(args.output) if args.output else in_path.with_name(in_path.stem + "_qa.csv")
        out = (REPO / out) if not out.is_absolute() else out
        targets.append((in_path, out))

    for src, out in targets:
        n_in, n_out = convert(src, out, args.answer_col)
        rel = out.relative_to(REPO) if out.is_relative_to(REPO) else out
        print(f"{src.name}: {n_in} questions -> {n_out} rows  ->  {rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
