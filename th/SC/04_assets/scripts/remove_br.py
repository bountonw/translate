#!/usr/bin/env python3
"""Remove `#br ` soft-line-break markers from all chapter files.

`#br` is the manual justified-line-break alias (linebreak(justify: true)).
This strips each marker together with its trailing space so the surrounding
text can be reflowed; the space that preceded the marker stays as the normal
word separator (so `word #br next` -> `word next`).

Usage:  python3 remove_br.py
"""
import glob
import os
import re
import sys

CHAPTERS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chapters")
MARKER = "#br "  # the marker plus its trailing space


def main() -> int:
    total = 0
    for path in sorted(glob.glob(os.path.join(CHAPTERS, "[0-9]*.md"))):
        text = open(path, encoding="utf-8").read()
        n = text.count(MARKER)
        if n:
            open(path, "w", encoding="utf-8").write(text.replace(MARKER, ""))
            total += n
        # Defensive: warn about any `#br` left without a trailing space.
        stray = len(re.findall(r"#br(?! )", open(path, encoding="utf-8").read()))
        if stray:
            print(f"  ! {os.path.basename(path)}: {stray} stray '#br' (no trailing "
                  f"space) left in place", file=sys.stderr)
    print(f"Removed {total} '#br ' markers from chapters/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
