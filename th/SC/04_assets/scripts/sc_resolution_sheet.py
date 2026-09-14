#!/usr/bin/env python3
"""Build the resolution sheet for an SC Thai chapter under a round.

For every [[...]] marker in the Thai chapter, emit a block giving the marker's
number, class, severity, its {SC ###.#} anchor, the proposed change, the
auditor's note, and the FULL English paragraph for that anchor, so the marker
can be judged without leaving the sheet. Damaged markers (an unterminated
bracket, a header that no longer parses) are listed under RESIDUE, because a
damaged marker is what is easiest to miss by eye. The translator's inline
questions, written as {{Q#4|...}} or {{Q|...}} anywhere in the chapter, are
collected at the end so they can be answered in one pass.

    python3 th/SC/04_assets/scripts/sc_resolution_sheet.py --chapter 12

The only file written is the sheet, at ~/claude-sandbox/sc-audit/scNN-resolution-sheet.md.
The last line printed is the summary the conductor reads: intact markers,
damaged markers, unterminated brackets, and markers whose old side is not in
the chapter as committed at HEAD — that last count means an agent typed a span
from memory instead of copying it.
"""
import argparse
import re
import sys

from sc_common import (chapter_path, source_path, parse_thai, parse_english,
                       committed_text, MARKER, SANDBOX, ROOT)

ANY_MARKER = re.compile(r"\[\[(.*?)\]\]", re.S)
QUESTION = re.compile(r"\{\{Q(?P<num>#\d+[a-z]?)?\s*\|?(?P<q>.*?)\}\}", re.S)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--chapter", type=int, required=True)
    a = ap.parse_args()
    chapter = chapter_path(a.chapter)
    text = chapter.read_text(encoding="utf-8")
    _, paras = parse_thai(text)
    english = parse_english(source_path(a.chapter).read_text(encoding="utf-8"))
    committed = committed_text(chapter)

    blocks, residue, questions = [], [], []
    intact = damaged = unterminated = not_committed = 0
    for p in paras:
        body = p.text
        seen = set()
        for m in MARKER.finditer(body):
            seen.add(m.span())
            intact += 1
            old = m.group("old")
            missing = bool(old) and committed is not None and old not in committed
            if missing:
                not_committed += 1
            blocks.append(
                f"## #{m.group('num')} {m.group('cls')}{' ' + m.group('sev') if m.group('sev') else ''} — {{SC {p.anchor}}}\n\n"
                f"OLD: {old or '(insertion)'}\n\n"
                f"NEW: {m.group('new') or '(deletion, or an open question where the note begins verify:)'}\n\n"
                f"NOTE: {m.group('note')}\n\n"
                + ("WARNING: the old side is not in the committed chapter; the span was not copied from the file.\n\n" if missing else "")
                + f"EN {{SC {p.anchor}}}: {english.get(p.anchor, '(no English paragraph carries this anchor)')}\n")
        for m in ANY_MARKER.finditer(body):
            if not any(s <= m.start() < e for s, e in seen):
                damaged += 1
                residue.append(f"- {{SC {p.anchor}}} damaged: [[{m.group(1)[:80]}...")
        opens = body.count("[[")
        closes = body.count("]]")
        if opens != closes:
            unterminated += abs(opens - closes)
            residue.append(f"- {{SC {p.anchor}}} unterminated: {opens} opening and {closes} closing brackets")
        for m in QUESTION.finditer(body):
            questions.append(f"- {{SC {p.anchor}}} {m.group('num') or ''} {m.group('q').strip()}")

    SANDBOX.mkdir(parents=True, exist_ok=True)
    out = SANDBOX / f"sc{a.chapter:02d}-resolution-sheet.md"
    rel = chapter.resolve().relative_to(ROOT)
    parts = [f"# SC{a.chapter:02d} resolution sheet — {rel}\n"]
    parts += blocks or ["No intact markers.\n"]
    if residue:
        parts.append("## RESIDUE\n\n" + "\n".join(residue) + "\n")
    if questions:
        parts.append("## QUESTIONS\n\n" + "\n".join(questions) + "\n")
    out.write_text("\n".join(parts), encoding="utf-8")
    print(f"sheet: {out}")
    print(f"summary: {intact} intact, {damaged} damaged, {unterminated} unterminated, "
          f"{not_committed} old side not in committed chapter"
          + ("" if committed is not None else " (HEAD not readable, so that count is 0 by default)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
