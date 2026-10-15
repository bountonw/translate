#!/usr/bin/env python3
"""Check the book's notes file against the chapters.

    python3 th/SC/04_assets/scripts/sc_notescheck.py [--chapter 13]

The notes file th/SC/04_assets/notes/SC_notes.txt records wordings the
translator kept on purpose, one line per site, sorted by anchor:

    {SC 116.1} | English words | Thai span copied from the chapter | his reason

Lines starting with # are headings. Prints one STALE line per note whose
anchor is in no chapter or whose Thai span is no longer in that paragraph,
one FORMAT line per malformed note, one ORDER line per note out of anchor
order, and a closing count. --chapter limits the span check to the notes of
that chapter. Read-only.
"""
import argparse
import re
import sys

from sc_common import PROJECT, STAGES, anchor_key, chapter_path, parse_thai

NOTES = PROJECT / "04_assets" / "notes" / "SC_notes.txt"
NOTE = re.compile(r"^\{SC (\d+\.\d+)\} \| ([^|]+) \| ([^|]+) \| (.+)$")


def chapters():
    """The chapter numbers present in any stage."""
    found = set()
    for stage in STAGES:
        for p in (PROJECT / stage).glob("SC[0-9][0-9]_th.typ"):
            found.add(p.name[2:4])
    return sorted(found)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--chapter")
    only = ap.parse_args().chapter
    if not NOTES.exists():
        print(f"no notes file {NOTES.relative_to(PROJECT.parents[1])}; 0 notes")
        return
    body, home = {}, {}
    for nn in chapters():
        _, paras = parse_thai(chapter_path(nn).read_text(encoding="utf-8"))
        for p in paras:
            body[p.anchor] = "\n".join(p.lines)
            home[p.anchor] = nn
    want = f"{int(only):02d}" if only else None
    count = bad = 0
    last = None
    for i, line in enumerate(NOTES.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        m = NOTE.match(line)
        if not m:
            bad += 1
            print(f"FORMAT line {i}: not '{{SC ###.#}} | English | Thai | reason'")
            continue
        anchor, span = m.group(1), m.group(3).strip()
        if last and anchor_key(anchor) < anchor_key(last):
            bad += 1
            print(f"ORDER {{SC {anchor}}}: comes after {{SC {last}}}")
        last = anchor
        if want and home.get(anchor) not in (want, None):
            continue
        count += 1
        if anchor not in body:
            bad += 1
            print(f"STALE {{SC {anchor}}}: no such paragraph in any chapter")
        elif span not in body[anchor]:
            bad += 1
            print(f"STALE {{SC {anchor}}}: the Thai span is no longer in the paragraph: {span}")
    print(f"{count} notes checked, {bad} stale, malformed or out of order")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
