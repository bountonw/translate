#!/usr/bin/env python3
"""Remove the bold and italic markup from the Thai alt edition.

The English original carries no emphasis of any kind, while the Thai publisher
bolded words freely and set a few passages in italic.  Keeping that markup
would mean the Thai files assert an emphasis the source does not have, so every
run is flattened to its plain text once the chapters have been cleaned.

The flattening is done last rather than during extraction, because bold is what
marks the publisher's pop-out bubbles and is the main signal for finding them.

Usage:
    python3 th/GC/04_assets/scripts/gc_th_flatten_alt.py DIR [--apply]
"""

import argparse
import collections
import glob
import os
import re
import sys

RUN = re.compile(r"#(strong|italic)\[((?:\\.|[^\]\\])*)\]")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("directory")
    ap.add_argument("--suffix", default="alt")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    tally = collections.Counter()
    changed = 0
    pattern = os.path.join(args.directory, f"GC*_{args.suffix}_th.typ")
    for path in sorted(glob.glob(pattern)):
        text = open(path, encoding="utf-8").read()
        new = RUN.sub(lambda m: (tally.update([m.group(1)]), m.group(2))[1], text)
        if "#strong[" in new or "#italic[" in new:
            print(f"{os.path.basename(path)}: a run was left unclosed and nothing was written")
            return 1
        if new != text:
            changed += 1
            if args.apply:
                open(path, "w", encoding="utf-8").write(new)

    print(f"bold runs flattened: {tally['strong']}")
    print(f"italic runs flattened: {tally['italic']}")
    print(f"files changed: {changed}")
    print("nothing was written" if not args.apply else "changes written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
