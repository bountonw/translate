#!/usr/bin/env python3
"""Character-level check of the finished Thai books. Reads only; writes nothing.

    python3 th/assets/scripts/th_charcheck.py            # MB, PP and LBF
    python3 th/assets/scripts/th_charcheck.py --book PP  # one book
    python3 th/assets/scripts/th_charcheck.py FILE ...   # named files

Each line printed is a finding: file, paragraph anchor, check, context. The
checks are the mechanical ones of th/SC/04_assets/scripts/sc_punctcheck.py
that do not depend on SC's Typst layout: Thai and Lao digits, invisible
characters (soft hyphen included), Thai marks in the wrong order or doubled,
and every form the glossary's spelling table lists as incorrect. Exit status
1 when anything was found.
"""
import argparse
import glob
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GLOSSARY = ROOT / "th" / "assets" / "translation_profile" / "thai-glossary.txt"
BOOKS = {
    "MB": ["th/MB/03_public/MB0*_th.md"],
    "PP": ["th/PP/03_public/*_th.typ", "th/PP/02_edit/PP*_th.typ"],
    "LBF": ["th/LBF/03_public/*_th.md"],
}

CHECKS = {
    "thai-digit": re.compile("[๐-๙]"),
    "lao-digit": re.compile("[໐-໙]"),
    "invisible": re.compile("[​‌‍⁠﻿­  ]"),
    # Mai taikhu takes no tone mark; a tone mark follows its vowel, never precedes it,
    # except sara am, which follows its tone mark.
    "mark-order": re.compile("็[่-๋]|[่-๋][ัิ-ฺ็]|ำ[่-๋]"),
    "double-mark": re.compile("([ัิ-ฺ็-๎])\\1|[่-๋][่-๋]"),
    "split-am": re.compile("ํา|ํ[่-๋]า"),
    "double-sara-e": re.compile("เเ"),
}
ANCHOR = re.compile(r"\{(?:MB|LBF) [\d.]+\}|\\\{PP [\d.]+\\\}")


def spelling_pairs():
    """(incorrect, correct) pairs from the glossary's "## 3. Spelling" table."""
    pairs, inside = [], False
    for line in GLOSSARY.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            inside = "Spelling" in line
            continue
        if not inside or not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3 or cells[1] in ("Correct", "") or set(cells[1]) <= {"-"}:
            continue
        pairs += [(w.strip(), cells[1]) for w in cells[2].split("/") if w.strip()]
    return pairs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", choices=sorted(BOOKS))
    ap.add_argument("files", nargs="*")
    args = ap.parse_args()
    if args.files:
        files = args.files
    else:
        books = [args.book] if args.book else list(BOOKS)
        files = sorted(f for b in books for g in BOOKS[b] for f in glob.glob(str(ROOT / g)))
    pairs = spelling_pairs()
    found = 0
    for f in files:
        for line in Path(f).read_text(encoding="utf-8").splitlines():
            hits = [(k, m.start()) for k, rx in CHECKS.items() for m in rx.finditer(line)]
            hits += [(f"spelling {w} -> {r}", m.start()) for w, r in pairs for m in re.finditer(re.escape(w), line)]
            for check, i in hits:
                a = ANCHOR.search(line, i)
                anchor = a.group(0).replace("\\", "") if a else "?"
                print(f"{Path(f).name}\t{anchor}\t{check}\t{line[max(0, i - 20):i + 20]!r}")
                found += 1
    sys.exit(1 if found else 0)


if __name__ == "__main__":
    main()
