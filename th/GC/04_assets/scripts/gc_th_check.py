#!/usr/bin/env python3
"""Mechanical checks on the extracted Thai printed edition.

Everything here is decidable without judgment, so it runs on every file after
every extraction rather than being sampled.  The paragraph-tag check compares
the tags the print carries against the English source in lo/GC/00_source/,
which is what makes it authoritative rather than merely self-consistent.

Usage:
    python3 th/GC/04_assets/scripts/gc_th_check.py DIR [--source lo/GC/00_source]
"""

import argparse
import glob
import os
import re
import sys
import unicodedata

TAG = re.compile(r"#EGW\[\\\{GC ([^\\]+)\\\}\]")
COMMENT_TAG = re.compile(r"^// \{GC ([^}]+)\}$", re.M)
THAI_DIGITS = "".join(chr(c) for c in range(0x0E50, 0x0E5A))
INVISIBLE = {0x200B, 0x200C, 0x200D, 0xFEFF, 0x00AD, 0xFFFD}
NIKHAHIT = "ํ"
SARA_AA = "า"


def source_tags(source_dir, chapter, name):
    """Return the English source's anchors, or None where there is no source.

    The cover, imprint and table of contents are the Thai publisher's own and
    have no counterpart in the English book, so nothing is compared for them.
    """
    if chapter == 0:
        if "intro" not in name:
            return None
        pattern = os.path.join(source_dir, "GC00b_introduction_en.md")
    else:
        pattern = os.path.join(source_dir, f"GC{chapter:02d}_en.md")
    if not os.path.exists(pattern):
        return None
    seen, tags = set(), []
    with open(pattern, encoding="utf-8") as fh:
        for t in re.findall(r"\{GC ([^}]+)\}", fh.read()):
            if t not in seen:
                seen.add(t)
                tags.append(t)
    return tags


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("directory")
    ap.add_argument("--source", default="lo/GC/00_source")
    args = ap.parse_args()

    failures = 0
    total_tags = 0
    for path in sorted(glob.glob(os.path.join(args.directory, "GC*_print_th.typ"))):
        name = os.path.basename(path)
        chapter = int(re.search(r"GC(\d+)_", name).group(1))
        text = open(path, encoding="utf-8").read()
        problems = []

        bad = {c for c in text if ord(c) in INVISIBLE or c in THAI_DIGITS}
        if bad:
            problems.append(
                "forbidden characters: "
                + ", ".join(f"U+{ord(c):04X} {unicodedata.name(c, '?')}" for c in sorted(bad))
            )

        for m in re.finditer(NIKHAHIT + r".{0,1}" + SARA_AA, text):
            problems.append(f"decomposed SARA AM at {m.start()}: {m.group(0)!r}")
            break

        if "<" in text and re.search(r"<\d+>", text):
            problems.append("an unmapped glyph reached the output")

        tags = TAG.findall(text)
        comments = COMMENT_TAG.findall(text)
        total_tags += len(tags)
        if comments != tags:
            problems.append(
                f"the // navigation comments and the #EGW tags disagree "
                f"({len(comments)} against {len(tags)})"
            )

        expected = source_tags(args.source, chapter, name)
        if expected is not None:
            extra = [t for t in tags if t not in expected]
            missing = [t for t in expected if t not in tags]
            order = [expected.index(t) for t in tags if t in expected]
            if extra:
                problems.append(f"tags not in the English source: {', '.join(extra)}")
            if order != sorted(order):
                problems.append("tags are out of the English source's order")
            if missing:
                dupes = sorted({t for t in tags if tags.count(t) > 1})
                problems.append(
                    f"tags the print does not carry: {', '.join(missing)}"
                    + (f" (the print repeats {', '.join(dupes)} instead)" if dupes else "")
                )

        if problems:
            failures += 1
            print(f"{name}:")
            for p in problems:
                print(f"    {p}")

    print(f"\nfiles checked: {len(glob.glob(os.path.join(args.directory, 'GC*_print_th.typ')))}")
    print(f"paragraph tags: {total_tags}")
    print(f"files with something to look at: {failures}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
