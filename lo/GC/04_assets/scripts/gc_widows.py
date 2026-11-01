#!/usr/bin/env python3
"""gc_widows.py — list paragraphs of the full GC book that leave one line alone
at the top or bottom of a page, and headings left at the foot of a page.

A widow is the last line of a paragraph standing alone at the top of a page;
an orphan is the first line of a paragraph standing alone at the foot of a
page. The build discourages both (\\widowpenalty and \\clubpenalty 2000) but
does not forbid them. Each PDF line is matched to its paragraph in the
stage-2 files (one paragraph per line there), footnote text left out, so a
paragraph's lines can be counted page by page.

Usage, from the repository root, after a full build (make_book.sh):

    python3 lo/GC/04_assets/scripts/gc_widows.py
    python3 lo/GC/04_assets/scripts/gc_widows.py --pdf other.pdf --stage2 DIR

--pdf and --stage2 default to the build's GC_lo_full.pdf and temp folder; the
stage-2 files must be the ones the PDF was built from. Each finding prints its
page, paragraph and the lone line. Read-only; exit code 1 when anything is
found, 0 otherwise.
"""
import argparse
import re
import sys
from pathlib import Path

from gc_linecheck import LAO, SCRIPTS, pdf_lines


def units(stage2_dir):
    """Lao letters of the book outside footnotes, with the paragraph or heading each
    belongs to, and the letters of the footnotes."""
    chars, owner, info, notes = [], [], [], []
    files = [Path(stage2_dir) / "GC00_introduction_lo_stage2.tex"] + \
        [Path(stage2_dir) / f"GC{i:02d}_lo_stage2.tex" for i in range(1, 43)]
    for f in files:
        ch = f.name.split("_")[0]
        for line in f.read_text(encoding="utf-8").split("\n"):
            s = line.lstrip()
            if s.startswith("\\section") or s.startswith("\\laochapter"):
                kind = "heading"
            elif "\\egw{" in line:
                kind = "paragraph"
            else:
                kind = "other"
            m = re.findall(r"GC\\nbsp\{\}(\d+\.\d+)", line)
            here = len(info)
            info.append((kind, f"{ch} {{GC {m[-1]}}}" if m else ch))
            i, depth, fn = 0, 0, None
            while i < len(line):
                if line.startswith("\\footnote{", i):
                    fn, depth, i = depth, depth + 1, i + 10
                    continue
                if line.startswith("\\laorepeat", i):
                    if fn is None:
                        chars.append("ໆ")
                        owner.append(here)
                    else:
                        notes.append("ໆ")
                    i = line.index("{}", i) + 2
                    continue
                c = line[i]
                if c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if fn is not None and depth == fn:
                        fn = None
                elif LAO.match(c):
                    if fn is None:
                        chars.append(c)
                        owner.append(here)
                    else:
                        notes.append(c)
                i += 1
    return "".join(chars), owner, info, "".join(notes)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pdf", default=SCRIPTS / "build/pdf/GC_lo_full.pdf")
    ap.add_argument("--stage2", default=SCRIPTS / "build/temp")
    args = ap.parse_args()
    if not Path(args.pdf).exists():
        sys.exit(f"gc_widows.py: no PDF at {args.pdf}; build the book or pass --pdf")
    stream, owner, info, notes = units(args.stage2)
    placed, cur, ncur = [], 0, 0
    for page, text in pdf_lines(args.pdf):
        letters = "".join(LAO.findall(text))
        if len(letters) < 4 and "{GC " in text and placed:
            # A paragraph's short last line, such as "5:40). {GC 21.2}".
            placed.append((page, placed[-1][1], text.strip()))
            cur += len(letters)
            continue
        if len(letters) < 4 or "...." in text:
            continue  # too short to place, or a contents line
        probe = letters[:12]
        # A body line starts where the previous body line ended.
        p = stream.find(probe, max(0, cur - 5), cur + 200)
        if p < 0:
            q = notes.find(probe, max(0, ncur - 5), ncur + 400)
            if q >= 0:
                ncur = q + len(letters)
                continue  # a footnote line
            if len(probe) < 12:
                continue
            p = stream.find(probe, cur, cur + 5000)
            if p < 0:
                continue  # front matter outside the stage-2 files
        cur = p + len(letters)
        placed.append((page, owner[p], text.strip()))
    found = 0
    by_unit = {}
    for page, u, text in placed:
        by_unit.setdefault(u, []).append((page, text))
    order = sorted(by_unit)
    for j, u in enumerate(order):
        lines = by_unit[u]
        kind, where = info[u]
        pages = [pg for pg, _ in lines]
        if kind == "paragraph" and len(set(pages)) > 1:
            first, last = pages.count(pages[0]), pages.count(pages[-1])
            if last == 1:
                found += 1
                print(f"widow\tp{pages[-1]}\t{where}\t{lines[-1][1][:50]}")
            if first == 1:
                found += 1
                print(f"orphan\tp{pages[0]}\t{where}\t{lines[0][1][:50]}")
        if kind == "heading" and j + 1 < len(order) and by_unit[order[j + 1]][0][0] != pages[-1]:
            found += 1
            print(f"heading\tp{pages[-1]}\t{where}\t{lines[-1][1][:50]}")
    print(f"# {len(placed)} lines placed; {found} found", file=sys.stderr)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
