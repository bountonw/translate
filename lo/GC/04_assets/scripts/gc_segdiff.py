#!/usr/bin/env python3
"""gc_segdiff.py — list every place in the GC book whose word division changed
between two module 2 runs, and flag the changes a new dictionary entry should
not cause.

A new or changed entry in a dictionary changes how module 2 divides the text
into words wherever the entry matches, which can be far from the place it was
written for. This script compares the stage-2 files of two runs group by
group (a group is a run of adjacent words), prints each distinct change once
with its count and up to five places, and names the entry that caused it.
In the old and new columns, | is a free line end between words and <N> is a
line end inside a word at cost N (<sh> a soft hyphen).

The check column reads:
  ok           the change only joins words inside the entry, or changes the
               cost of a line end inside it;
  NEW BREAK    the change adds a free line end that was not there before;
  OUTSIDE      the change moves a word boundary outside the entry;
  ?            no entry in --rows explains the change.
Every row not marked ok wants reading before the entry is kept.

Usage, from lo/GC/04_assets (the build folder is scripts/build, which git
ignores):

    cp -r scripts/build/temp scripts/build/temp_before
    # edit the dictionary, then rerun module 2 for every chapter
    python3 scripts/gc_segdiff.py scripts/build/temp_before --rows new_rows.txt

--rows names a file holding the new or changed dictionary lines (the coded
form after | is ignored); --new defaults to scripts/build/temp. Read-only;
exit code 1 when any row is not ok, 0 otherwise.
"""
import argparse
import collections
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
LW = re.compile(r"\\lw\{((?:[^{}]|\{[^{}]*\})*)\}")
ANCHOR = re.compile(r"(?<=GC)(?:\\nbsp\{\}| )?\d+\.\d+")


def groups(line):
    out, cur, pos = [], [], 0
    for m in LW.finditer(line):
        if m.start() != pos and cur:
            out.append(cur)
            cur = []
        cur.append(m.group(1))
        pos = m.end()
    if cur:
        out.append(cur)
    return out


def render(g):
    return "|".join(re.sub(r"\\p\{(-?\d+)\}", r"<\1>", w).replace("\u00ad", "<sh>") for w in g)


def bounds(rendered):
    """Offsets of the free line ends in a rendered group, and its plain letters."""
    s = re.sub(r"<[^>]*>", "", rendered)
    out, n = set(), 0
    for c in s:
        if c == "|":
            out.add(n)
        else:
            n += 1
    return out, s.replace("|", "")


def check(old, new, cause):
    bo, plain = bounds(old)
    bn, _ = bounds(new)
    if bn - bo:
        return "NEW BREAK"
    if cause == "?":
        return "?"
    start = plain.find(cause)
    if any(not (start < b < start + len(cause)) for b in bo - bn):
        return "OUTSIDE"
    return "ok"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("old")
    ap.add_argument("--new", default=SCRIPTS / "build/temp")
    ap.add_argument("--rows")
    args = ap.parse_args()
    keys = []
    if args.rows:
        keys = sorted((l.split("|", 1)[0].strip() for l in open(args.rows, encoding="utf-8")
                       if "|" in l and not l.startswith("%")), key=len, reverse=True)
    pairs = collections.OrderedDict()
    for old in sorted(Path(args.old).glob("*_stage2.tex")):
        new = Path(args.new) / old.name
        ch = old.name.split("_")[0]
        a = old.read_text(encoding="utf-8").split("\n")
        b = new.read_text(encoding="utf-8").split("\n")
        anchor = ""
        for la, lb in zip(a, b):
            m = ["GC " + re.sub(r"^(\\nbsp\{\}| )", "", x) for x in ANCHOR.findall(la)]
            if la != lb:
                here = m[-1] if m else anchor
                ga, gb = groups(la), groups(lb)
                if len(ga) != len(gb):
                    pairs.setdefault(("GROUPCOUNT", ch, "?"), []).append(f"{ch} {{{here}}}")
                else:
                    for x, y in zip(ga, gb):
                        if x != y:
                            ry = render(y)
                            cause = next((k for k in keys if any(
                                k == re.sub(r"<[^>]*>", "", render([w])) for w in y)), "?")
                            pairs.setdefault((render(x), ry, cause), []).append(f"{ch} {{{here}}}")
            if m:
                anchor = m[-1]
    print("count\tcheck\tentry\told\tnew\tplaces")
    bad = 0
    for (old, new, cause), locs in sorted(pairs.items(), key=lambda kv: (kv[0][2], kv[0][0])):
        verdict = "?" if old == "GROUPCOUNT" else check(old, new, cause)
        bad += verdict != "ok"
        print(f"{len(locs)}\t{verdict}\t{cause}\t{old}\t{new}\t{'; '.join(locs[:5])}")
    print(f"# {len(pairs)} distinct changes, {bad} not ok", file=sys.stderr)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
