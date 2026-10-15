#!/usr/bin/env python3
"""Repair the paragraph numbers the Thai editions misprint.

Both Thai editions repeat a paragraph number here and there instead of moving
on to the next one, and the printed edition leaves one paragraph unnumbered.
The paragraphs on the eight English pages concerned were counted by hand in a
printed Great Controversy and every count matched lo/GC/00_source/, so the
English numbering is right and the Thai books are wrong.

Two repairs are made, both decided by the English source rather than by
judgment.  Where a number appears twice and the anchor next to it is absent,
the occurrence on the side of the gap takes the absent number.  Where an
untagged paragraph sits between the two anchors that bracket an absent number,
it takes that number.  Anything else is reported and left alone.

Usage:
    python3 th/GC/04_assets/scripts/gc_th_renumber.py DIR SUFFIX [--source DIR] [--apply]
"""

import argparse
import glob
import os
import re
import sys

TAG_IN_BODY = re.compile(r"#EGW\[\\\{GC ([^\\]+)\\\}\]")
TAG_IN_COMMENT = re.compile(r"^// \{GC ([^}]+)\}$")


def source_tags(source_dir, chapter):
    path = os.path.join(source_dir, f"GC{chapter:02d}_en.md")
    if not os.path.exists(path):
        return []
    seen, tags = set(), []
    for t in re.findall(r"\{GC ([^}]+)\}", open(path, encoding="utf-8").read()):
        if t not in seen:
            seen.add(t)
            tags.append(t)
    return tags


def blocks_of(lines):
    """Return [(comment_index, body_index, tag)] for every paragraph in the file."""
    out = []
    pending_comment = None
    for i, line in enumerate(lines):
        m = TAG_IN_COMMENT.match(line)
        if m:
            pending_comment = (i, m.group(1))
            continue
        if not line.strip() or line.startswith("//"):
            continue
        m = TAG_IN_BODY.search(line)
        tag = m.group(1) if m else None
        out.append((pending_comment[0] if pending_comment else None, i, tag))
        pending_comment = None
    return out


def repair(path, source_dir, apply_changes):
    chapter = int(re.search(r"GC(\d+)_", os.path.basename(path)).group(1))
    expected = source_tags(source_dir, chapter)
    if not expected:
        return []
    lines = open(path, encoding="utf-8").read().split("\n")
    blocks = blocks_of(lines)
    present = [b[2] for b in blocks if b[2]]
    changes = []

    for absent in [t for t in expected if t not in present]:
        k = expected.index(absent)
        before = expected[k - 1] if k > 0 else None
        after = expected[k + 1] if k + 1 < len(expected) else None

        # The block that should carry the absent number is the one standing
        # between the two anchors that bracket it, whenever that block either
        # repeats a number used earlier or carries none at all.
        seat = None
        for n in range(len(blocks)):
            prev_tag = blocks[n - 1][2] if n > 0 else None
            next_tag = blocks[n + 1][2] if n + 1 < len(blocks) else None
            if prev_tag == before and next_tag == after:
                earlier = [b[2] for b in blocks[:n]]
                if blocks[n][2] is None or blocks[n][2] in earlier:
                    seat = n
                    break
        if seat is not None:
            was = blocks[seat][2] or "no number"
            changes.append((seat, absent,
                            f"the paragraph between {before} and {after}, "
                            f"printed as {was}, becomes {absent}"))
            continue

        hits = [n for n, b in enumerate(blocks) if b[2] == before]
        if before and len(hits) == 2:
            changes.append((hits[1], absent, f"the second {before} becomes {absent}"))
            continue
        hits = [n for n, b in enumerate(blocks) if b[2] == after]
        if after and len(hits) == 2:
            changes.append((hits[0], absent, f"the first {after} becomes {absent}"))
            continue
        changes.append((None, absent, "no repair the English source decides on its own"))

    if apply_changes:
        for index, tag, _note in changes:
            if index is None:
                continue
            ci, bi, old = blocks[index]
            if old:
                lines[bi] = TAG_IN_BODY.sub(f"#EGW[\\\\{{GC {tag}\\\\}}]", lines[bi], count=1)
            else:
                lines[bi] = lines[bi].rstrip() + f" #EGW[\\{{GC {tag}\\}}]"
            if ci is not None:
                lines[ci] = f"// {{GC {tag}}}"
            else:
                lines[bi:bi] = [f"// {{GC {tag}}}", ""]
                blocks = blocks_of(lines)
        open(path, "w", encoding="utf-8").write("\n".join(lines))
    return [(os.path.basename(path), tag, note) for _i, tag, note in changes]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("directory")
    ap.add_argument("suffix", help="print or alt")
    ap.add_argument("--source", default="lo/GC/00_source")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    total = 0
    unresolved = 0
    for path in sorted(glob.glob(os.path.join(args.directory, f"GC*_{args.suffix}_th.typ"))):
        for name, tag, note in repair(path, args.source, args.apply):
            total += 1
            if note.startswith("no repair"):
                unresolved += 1
            print(f"{name}\t{tag}\t{note}")
    print(f"\nnumbers considered: {total}; repaired: {total - unresolved}; "
          f"left alone: {unresolved}")
    print("nothing was written" if not args.apply else "changes written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
