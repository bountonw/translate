#!/usr/bin/env python3
"""gc_chapterends.py — list chapters of the full GC book whose last page holds
only a few lines of text.

Each chapter opens on a right-hand page, so a chapter whose last page holds
one or two lines costs the book two pages. The fixes are in
module2_preprocess.py: PAGE_FIXES lets the page before hold one more line,
and LOOSENESS_FIXES asks TeX to set the chapter's last paragraphs one line
shorter each.

Usage, from the repository root, after a full build (make_book.sh):

    python3 lo/GC/04_assets/scripts/gc_chapterends.py
    python3 lo/GC/04_assets/scripts/gc_chapterends.py --max-lines 5
    python3 lo/GC/04_assets/scripts/gc_chapterends.py --pdf other.pdf --toc other.toc

--pdf and --toc default to the build's GC_lo_full.pdf and full-output.toc.
The chapter openings come from the .toc; each chapter's last page with text
is found in the PDF, stepping back over the blank page before the next
chapter. Read-only; exit code 1 when any chapter's last page holds
--max-lines (default 3) or fewer lines, 0 otherwise.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pdf", default=SCRIPTS / "build/pdf/GC_lo_full.pdf")
    ap.add_argument("--toc", default=SCRIPTS / "build/pdf/logs/full-output.toc")
    ap.add_argument("--max-lines", type=int, default=3)
    args = ap.parse_args()
    if not Path(args.pdf).exists():
        sys.exit(f"gc_chapterends.py: no PDF at {args.pdf}; build the book or pass --pdf")
    # -raw keeps each printed line on one text line; -layout splits off raised tone marks.
    pages = subprocess.run(["pdftotext", "-raw", str(args.pdf), "-"], capture_output=True,
                           text=True).stdout.split("\f")[:-1]
    # Folio offset: the first page after the front matter whose header carries an arabic folio.
    offset = None
    for i, p in enumerate(pages):
        lines = [l for l in p.splitlines() if l.strip()]
        if not lines:
            continue
        m = re.match(r"\s*(\d+)\s", lines[0]) or re.search(r"\s(\d+)\s*$", lines[0])
        if m and i > 20:
            offset = i + 1 - int(m.group(1))
            break
    toc = Path(args.toc).read_text(encoding="utf-8")
    starts = [int(m) for m in re.findall(r"\\contentsline \{chapter\}\{.*?\}\{(\d+)\}", toc)]
    # The book's last page is the QR code for the online version, not chapter 42's text.
    last_text = max(i for i, p in enumerate(pages) if p.strip() and "laoegw.com/GC" not in p)
    print(f"{len(pages)} pages, of which the last with text is page {last_text + 1}; "
          f"{len(starts)} chapters in the contents")
    found = 0
    ends = [s - 1 for s in starts[1:]] + [None]
    for n, e in enumerate(ends, 1):
        idx = last_text if e is None else e + offset - 1
        while idx > 0 and not pages[idx].strip():
            idx -= 1  # the blank left-hand page before a chapter opening
        body = [l for l in pages[idx].splitlines() if l.strip()][1:]
        if len(body) <= args.max_lines:
            found += 1
            print(f"chapter {n}: last page {idx + 1} (folio {idx + 1 - offset}) holds {len(body)} "
                  f"line(s): {' / '.join(x.strip()[:40] for x in body)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
