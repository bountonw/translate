#!/usr/bin/env python3
"""Pre-processing for an SJ Thai chapter: the "// {SJ ###.#}" anchor comments.

    python3 th/SJ/04_assets/scripts/sj_anchors.py --chapter 01
    python3 th/SJ/04_assets/scripts/sj_anchors.py --chapter 01 --write
    python3 th/SJ/04_assets/scripts/sj_anchors.py --all --write

The round scripts, the agents and the run checks find a paragraph by the
"// {SJ ###.#}" comment above it, as in th/SC. SJ's chapters carry only the
"#EGW[\\{SJ ###.#\\}]" tag at each paragraph's end. For every paragraph after
the #chapter(...) header that ends in one tag, this script writes the comment
and a blank line above it, the same anchor as the tag; a paragraph already
under its comment is left alone, so a second run changes nothing. Without
--write it changes nothing and prints what it would do; with --write a
chapter that has a DEFECT is still left unchanged until the defect is ruled.

It never changes a tag, and it prints one line per defect for the conductor:

    DEFECT  a paragraph with no tag or with several; a tag repeated; tags out
            of order; an English anchor no Thai tag carries; a Thai tag the
            English lacks. Each takes the translator's ruling before the
            chapter's qa1.
    FILLER  a line commented out with // that carries a tag: a filler
            paragraph from the printed book, left as it stands.
    HOLD    a paragraph tagged {SJ 666.66}, the placeholder tag: no comment is
            written.

Exit status 1 when any DEFECT line was printed.
"""
import argparse
import re
import sys
from collections import Counter

from sj_common import (PROJECT, STAGES, ROOT, COMMENT_ANCHOR, TAG_ANCHOR, FILLER,
                       anchor_key, chapter_path, parse_english, SOURCE_DIRS)

PLACEHOLDER = "666.66"


def body_start(lines):
    """The index of the first line after the #chapter(...) header."""
    for i, line in enumerate(lines):
        if line.startswith("#chapter("):
            for j in range(i, len(lines)):
                if lines[j].strip() == ")":
                    return j + 1
    return 0


def blocks(lines, start):
    """(first, last) line indexes of each run of non-blank lines from start."""
    out, i = [], start
    while i < len(lines):
        if not lines[i].strip():
            i += 1
            continue
        j = i
        while j + 1 < len(lines) and lines[j + 1].strip():
            j += 1
        out.append((i, j))
        i = j + 1
    return out


def english_anchors(nn):
    for d in SOURCE_DIRS:
        p = d / f"SJ{nn}_en.md"
        if p.exists():
            return list(parse_english(p.read_text(encoding="utf-8")))
    return None


def process(nn, write):
    path = chapter_path(nn)
    lines = path.read_text(encoding="utf-8").split("\n")
    rel = path.resolve().relative_to(ROOT)
    start = body_start(lines)
    report, tags, inserts = [], [], []
    for first, last in blocks(lines, start):
        block = lines[first:last + 1]
        if all(COMMENT_ANCHOR.match(l) for l in block):
            continue
        if all(l.lstrip().startswith("//") for l in block):
            for k, l in enumerate(block):
                if FILLER.match(l):
                    report.append(f"FILLER line {first + k + 1}: {l.strip()[:90]}")
            continue
        found = [t for l in block if not l.lstrip().startswith("//") for t in TAG_ANCHOR.findall(l)]
        if len(found) != 1:
            report.append(f"DEFECT line {first + 1}: {len(found)} tags in one paragraph: {block[0][:60]}")
            continue
        tag = found[0]
        if tag == PLACEHOLDER:
            report.append(f"HOLD line {first + 1}: placeholder tag {{SJ {PLACEHOLDER}}}: {block[0][:60]}")
            continue
        tags.append(tag)
        prev = first - 1
        while prev >= 0 and not lines[prev].strip():
            prev -= 1
        m = COMMENT_ANCHOR.match(lines[prev]) if prev >= 0 else None
        if m:
            if m.group(1) != tag:
                report.append(f"DEFECT line {prev + 1}: comment {{SJ {m.group(1)}}} above a paragraph tagged {{SJ {tag}}}")
            continue
        inserts.append((first, tag))
    for t, n in Counter(tags).items():
        if n > 1:
            report.append(f"DEFECT {{SJ {t}}}: the tag stands on {n} paragraphs")
    for a, b in zip(tags, tags[1:]):
        if anchor_key(b) <= anchor_key(a):
            report.append(f"DEFECT {{SJ {b}}}: follows {{SJ {a}}}")
    en = english_anchors(nn)
    if en is None:
        report.append(f"DEFECT: no English source SJ{nn}_en.md, so the tags were not compared")
    else:
        for a in en:
            if a not in tags:
                report.append(f"DEFECT {{SJ {a}}}: an English paragraph no Thai tag carries")
        for a in tags:
            if a not in en:
                report.append(f"DEFECT {{SJ {a}}}: a Thai tag the English lacks")
    defects = any(r.startswith("DEFECT") for r in report)
    for first, tag in reversed(inserts):
        lines[first:first] = [f"// {{SJ {tag}}}", ""]
    if write and inserts and not defects:
        path.write_text("\n".join(lines), encoding="utf-8")
    verb = "written" if write and not defects else "held until its defects are ruled" if write else "to write"
    print(f"# {rel}: {len(inserts)} anchor comment(s) {verb}, {len(tags)} tagged paragraph(s)")
    for r in report:
        print(r)
    return defects


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--chapter", nargs="*", default=[])
    ap.add_argument("--all", action="store_true", help="every chapter under 01_raw, 02_edit and 03_public")
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    if a.all:
        nns = sorted({p.name[2:4] for s in STAGES for p in (PROJECT / s).glob("SJ[0-9][0-9]_th.typ")})
    else:
        nns = [f"{int(n):02d}" for n in a.chapter]
    if not nns:
        ap.error("--chapter NN [NN ...] or --all")
    bad = [process(nn, a.write) for nn in nns]
    return 1 if any(bad) else 0


if __name__ == "__main__":
    sys.exit(main())
