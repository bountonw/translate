#!/usr/bin/env python3
"""Dump one page of the Thai print in reading order, for checking against the page image.

The lines are the same lines the extractor joins into paragraphs, with the
column order, the restored word spaces, the composed SARA AM and the italic
marking already applied, so a reader comparing this against the rendered page
sees exactly what the extraction believes is on it.

Usage:
    python3 th/GC/04_assets/scripts/gc_th_pagedump.py QDF FIRST LAST > out.txt
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gc_th_pdf import Pdf, load_cidmap  # noqa: E402
from gc_th_extract import page_rows, line_text, Report  # noqa: E402


def main():
    qdf, first, last = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    pdf = Pdf(qdf)
    cidmap = load_cidmap(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "browallia_cid_map.tsv")
    )
    cache, report = {}, Report()
    for pno in range(first, last + 1):
        rows, two = page_rows(pdf, pdf.pages[pno - 1], cidmap, cache)
        if pno == first:
            print("Each printed line is shown on its own, and each line is wrapped in")
            print("#italic[...] separately, so an italic passage that runs over several")
            print("lines appears here as several spans and is one span in the .typ file.")
            print("Doubled spaces here are collapsed to one in the .typ file as well.")
            print()
        print(f"===== PDF page {pno} ({'two columns' if two else 'one column'})")
        last_col = None
        for col, _y, row in rows:
            if col != last_col:
                print(f"--- column {col + 1}")
                last_col = col
            pieces = line_text(row, report, f"p{pno}")
            text = "".join(
                f"#italic[{t}]" if s == "i" else (f"#strong[{t}]" if s == "b" else t)
                for t, s in pieces
            )
            if text.strip():
                print(text)
        print()


if __name__ == "__main__":
    main()
