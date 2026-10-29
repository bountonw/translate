#!/usr/bin/env python3
"""gc_linecheck.py — classify every line end of the full GC book by where it
falls in the build's word division, and list the line ends that split a word.

Module 2 divides the Lao text into words (the stage-2 files). A line may end
freely between two of those words, or inside one word only at a break the
dictionary entry allows, at that break's cost. Each line end of the PDF that
falls between two Lao letters is found in the stage-2 text and classified:

  WORD    between two words of the division (a free line end);
  COST N  inside one word, at a break its entry allows at cost N;
  SH      inside one word, at a soft hyphen (the line ends with a printed hyphen);
  SPLIT   between two words of the division, where a longer dictionary
          entry spans the line end, both pieces of that entry are dictionary
          words, and the entry itself allows no line end there at cost 0 or
          less; i.e. the line end cuts a word the dictionary knows;
  IN      inside one word where its entry allows no break (an overfull line).

A SPLIT is either a real split, which a phrase entry in
lo/assets/dictionaries/patch.txt fixes, or a correct break between two words
that happen to form a longer entry; reading decides which. A line end of cost
1000 or more is an emergency break and is always worth reading.

Usage, from the repository root, after a full build (make_book.sh):

    python3 lo/GC/04_assets/scripts/gc_linecheck.py
    python3 lo/GC/04_assets/scripts/gc_linecheck.py --list SPLIT
    python3 lo/GC/04_assets/scripts/gc_linecheck.py --list "COST 1000"
    python3 lo/GC/04_assets/scripts/gc_linecheck.py --pdf other.pdf --stage2 DIR

--pdf and --stage2 default to the build's GC_lo_full.pdf and temp folder; the
stage-2 files must be the ones the PDF was built from. Counts go to stderr;
--list prints every line end of that kind with its page, paragraph and text.
Read-only; exit code 0.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
REPO = SCRIPTS.parents[3]
LAO = re.compile(r"[຀-໿]")

# Dictionary break marks and the line-end cost each stands for.
MARKS = [("~~~~~~", -1000), ("~~~~~", -400), ("~~~~", -200), ("~~~", 0), ("~~", 100),
         ("!!", 7500), ("!", 5000), ("~", 1000), ("­", 150)]


def stage2_stream(stage2_dir):
    """Lao letters of the whole book in order, the break kind before each letter, and its paragraph."""
    chars, kind, para = [], [], []
    files = [Path(stage2_dir) / "GC00_introduction_lo_stage2.tex"] + \
        [Path(stage2_dir) / f"GC{i:02d}_lo_stage2.tex" for i in range(1, 43)]
    for f in files:
        ch = f.name.split("_")[0]
        for line in f.read_text(encoding="utf-8").split("\n"):
            m = re.findall(r"GC\\nbsp\{\}(\d+\.\d+)", line)
            anchor = f"{ch} {{GC {m[-1]}}}" if m else ch
            i, pending, inlw, depth = 0, "OTHER", False, 0
            while i < len(line):
                if line.startswith("\\laorepeat", i):
                    # The repetition mark: no line end before it, a free one after.
                    chars.append("ໆ")
                    kind.append("IN")
                    para.append(anchor)
                    pending = "OTHER"
                    i = line.index("{}", i) + 2
                    continue
                if line.startswith("\\lw{", i):
                    pending = "WORD" if pending in ("WORD", "START") else pending
                    inlw, depth, i = True, 1, i + 4
                    continue
                if inlw and line.startswith("\\p{", i):
                    j = line.index("}", i)
                    pending = "COST " + line[i + 3:j]
                    i = j + 1
                    continue
                c = line[i]
                if inlw and c == "{":
                    depth += 1
                elif inlw and c == "}":
                    depth -= 1
                    if depth == 0:
                        inlw = False
                        pending = "START"
                        i += 1
                        continue
                if c == "­":
                    pending = "SH"
                elif LAO.match(c):
                    chars.append(c)
                    kind.append(pending if pending != "START" else "OTHER")
                    para.append(anchor)
                    pending = "IN"
                elif not inlw and (c.isspace() or c not in "{}"):
                    pending = "OTHER"
                i += 1
    return "".join(chars), kind, para


def pdf_lines(pdf):
    """Body and footnote lines in page order, running headers left out."""
    text = subprocess.run(["pdftotext", "-raw", str(pdf), "-"], capture_output=True, text=True).stdout
    out = []
    for n, page in enumerate(text.split("\f"), 1):
        lines = [l for l in page.split("\n") if l.strip()]
        for i, l in enumerate(lines):
            s = l.strip()
            if i == 0 and (re.match(r"^\d+\s", s) or s.isdigit() or re.search(r"\s\d+$", s)
                           or "ປາຍທາງແຫ່ງຄວາມຫວັງ" in s):
                continue
            out.append((n, l))
    return out


def coded_costs(coded):
    """Map letter offset -> cost of a line end there, from an entry's coded form."""
    costs, n, i = {}, 0, 0
    while i < len(coded):
        m = re.match(r"\\p\{(-?\d+)\}", coded[i:])
        if m:
            costs[n] = int(m.group(1))
            i += m.end()
            continue
        for mark, cost in MARKS:
            if coded.startswith(mark, i):
                costs[n] = cost
                i += len(mark)
                break
        else:
            if LAO.match(coded[i]):
                n += 1
            i += 1
    return costs


def read_entries(files, keys, words):
    """Add each file's Lao entries to keys (entries of four letters or more, with the
    cost at each inner offset) and words (all entries); later files override earlier."""
    for f in files:
        if not f.exists():
            continue
        for l in f.read_text(encoding="utf-8").split("\n"):
            if "|" in l and not l.startswith("%"):
                k = re.sub(r"\s+", "", l.split("|", 1)[0])
                if k and all(LAO.match(c) for c in k):
                    words.add(k)
                    if len(k) >= 4:
                        keys[k] = coded_costs(l.split("|", 1)[1].split("%")[0].strip())


def entries():
    """Per chapter, the entries module 2 uses for it, in its order: the language
    dictionaries, the book's, then the chapter's own."""
    d = SCRIPTS / "dictionaries"
    keys, words = {}, set()
    read_entries([REPO / "lo/assets/dictionaries/main.txt", REPO / "lo/assets/dictionaries/patch.txt",
                  d / "GC_lo.txt", d / "GC_lo_patch.txt"], keys, words)
    out = {}
    for ch in ["GC00"] + [f"GC{i:02d}" for i in range(1, 43)]:
        stem = "GC00_introduction" if ch == "GC00" else ch
        ck, cw = dict(keys), set(words)
        read_entries([d / f"{stem}_lo.txt", d / f"{stem}_lo_patch.txt"], ck, cw)
        out[ch] = (ck, cw)
    return out


def spanning(stream, pos, keys, words, maxlen):
    """Entries that a free line end at pos would cut, per the SPLIT rule."""
    return [stream[s:e] for s in range(max(0, pos - maxlen + 1), pos)
            for e in range(pos + 1, min(len(stream), s + maxlen) + 1)
            if e - s >= 4 and stream[s:e] in keys
            and stream[s:pos] in words and stream[pos:e] in words
            and keys[stream[s:e]].get(pos - s, 9999) > 0]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pdf", default=SCRIPTS / "build/pdf/GC_lo_full.pdf")
    ap.add_argument("--stage2", default=SCRIPTS / "build/temp")
    ap.add_argument("--list", metavar="KIND")
    args = ap.parse_args()
    if not Path(args.pdf).exists():
        sys.exit(f"gc_linecheck.py: no PDF at {args.pdf}; build the book or pass --pdf")
    stream, kind, para = stage2_stream(args.stage2)
    by_chapter = entries()
    maxlen = max(len(k) for keys, _ in by_chapter.values() for k in keys)
    lines = pdf_lines(args.pdf)
    counts, cur = {}, 0
    for (pg, a), (_, b) in zip(lines, lines[1:]):
        a = a.rstrip()
        if a.endswith("-") and LAO.match(a[-2:-1] or " "):
            a = a[:-1]  # the hyphen printed where a line ends at a soft hyphen
        ta = "".join(LAO.findall(a))[-12:]
        hb = "".join(LAO.findall(b))[:12]
        if len(ta) < 4 or len(hb) < 4 or not LAO.match(a.rstrip()[-1:] or " ") \
                or not LAO.match(b.lstrip()[:1] or " "):
            continue
        probe = ta + hb
        p = stream.find(probe, max(0, cur - 300), cur + 20000)
        if p < 0:
            p = stream.find(probe)
        if p < 0:
            counts["UNALIGNED"] = counts.get("UNALIGNED", 0) + 1
            continue
        pos = p + len(ta)
        cur = pos
        k = kind[pos]
        span = []
        if k == "WORD":
            keys, words = by_chapter[para[pos].split()[0]]
            span = spanning(stream, pos, keys, words, maxlen)
            if span:
                k = "SPLIT"
        counts[k] = counts.get(k, 0) + 1
        if args.list and (k == args.list or k.startswith(args.list + " ")):
            extra = " / ".join(sorted(span, key=len, reverse=True)[:3])
            print(f"p{pg}\t{para[pos]}\t{k}\t{a.strip()[-30:]} | {b.strip()[:30]}\t{extra}")
    for k in sorted(counts):
        print(f"# {k}: {counts[k]}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
