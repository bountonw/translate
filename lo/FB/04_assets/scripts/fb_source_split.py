#!/usr/bin/env python3
"""Split the official 28 Fundamental Beliefs booklet text into anchored source files.

    python3 lo/FB/04_assets/scripts/fb_source_split.py source/FB/ADV-28Beliefs2020.txt lo/FB/00_source [--closing-tag] [--check YEARBOOK_TXT]

Input: the pdftotext output of source/FB/ADV-28Beliefs2020.pdf (General Conference, 2020 edition
of the statement voted at the 2015 General Conference Session).
Output: FB00_preamble_en.md and FB01_en.md to FB28_en.md, one paragraph each, anchored "## {FB N.1}"
and, with --closing-tag, the tag "{FB N.1}" at the paragraph end, in the front-matter shape of th/SC/00_source.
--check compares the prose of every belief, word by word, with a second extraction (the Yearbook)
and prints every difference; it changes nothing.
"""
import re
import sys
import difflib
from pathlib import Path

# Corrections to the booklet text, each verified against the 2024 Yearbook: three verse ranges whose
# hyphen pdftotext dropped at a line break, and two reference-list slips in the booklet itself.
HYPHEN_FIXES = {
    "5:1221": "5:12-21",   # belief 8, Rom. 5:12-21
    "9:1128": "9:11-28",   # belief 24, Heb. 9:11-28
    "1:710": "1:7-10",     # belief 25, 2 Thess. 1:7-10
    "John 3:16 2 Cor.": "John 3:16; 2 Cor.",   # belief 2: the booklet drops the semicolon; the Yearbook has it
    # belief 26, ruled 26 September 2026: the booklet prints "Rom. 6:23; 16; ... 1 Tim. 6:15"; the 2024 and
    # 2025 Yearbooks print "Rom. 6:23; ... 1 Tim. 6:15, 16", and the file follows the Yearbooks.
    "Rom. 6:23; 16; 1 Cor.": "Rom. 6:23; 1 Cor.",
    "1 Tim. 6:15; Rev. 20:1-10": "1 Tim. 6:15, 16; Rev. 20:1-10",
}

HEAD = re.compile(r"^(\d{1,2}) ([A-Z].*)$")
SKIP = {"2020", "EDITION", "Fundamental", "BELIEFS", "28 Fundamental Beliefs", "•", "adventist.org"}


def parse_booklet(text):
    lines = [l.rstrip() for l in text.replace("\f", "\n").splitlines()]
    preamble, beliefs, cur = [], {}, None
    i = 0
    # The preamble is the first complete paragraph beginning with the creed sentence and ending
    # with "Holy Word." (the cover carries a broken fragment of it before that).
    for j, l in enumerate(lines):
        if l.startswith("Seventh-day Adventists accept the Bible as their only creed"):
            k = j
            while lines[k].strip():
                preamble.append(lines[k].strip())
                k += 1
            i = k
            break
    for l in lines[i:]:
        s = l.strip()
        if not s or s.isdigit() or s in SKIP or s.startswith("Copyright ©") or s.startswith("adventist.org"):
            continue
        m = HEAD.match(s)
        if m and 1 <= int(m.group(1)) <= 28 and int(m.group(1)) not in beliefs:
            cur = int(m.group(1))
            beliefs[cur] = {"title": m.group(2).strip(), "lines": []}
            continue
        if cur is not None:
            beliefs[cur]["lines"].append(s)
    out = {}
    for n, b in beliefs.items():
        para = " ".join(b["lines"])
        para = re.sub(r"\s+", " ", para).strip()
        for bad, good in HYPHEN_FIXES.items():
            para = para.replace(bad, good)
        out[n] = (b["title"], para)
    return " ".join(preamble), out


def front_matter(number, title):
    num = str(number) if number else ""
    return (
        "---\n"
        "book:\n"
        "  title:\n"
        "    en: 28 Fundamental Beliefs of Seventh-day Adventists\n"
        "chapter:\n"
        f"  number: {num}\n"
        "  title:\n"
        f"    en: {title}\n"
        "  url: https://www.adventist.org/beliefs/\n"
        "source:\n"
        "  en: ADV-28Beliefs2020.pdf, General Conference of Seventh-day Adventists, 2020 edition; text as amended at the 2015 General Conference Session\n"
        "---\n"
    )


def write_files(preamble, beliefs, outdir, closing):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    tag = lambda n: f" {{FB {n}.1}}" if closing else ""
    p = outdir / "FB00_preamble_en.md"
    p.write_text(front_matter(None, "Preamble") + "\n## {FB 0.1}\n\n" + preamble + tag(0) + "\n", encoding="utf-8")
    for n in sorted(beliefs):
        title, para = beliefs[n]
        p = outdir / f"FB{n:02d}_en.md"
        p.write_text(front_matter(n, title) + f"\n## {{FB {n}.1}}\n\n" + para + tag(n) + "\n", encoding="utf-8")
    return len(beliefs) + 1


def parse_yearbook(text, titles):
    """Find each belief in the check text by its own '<n>. <Title>' line; page order does not matter.
    Where the extraction drops another belief into the middle of this one, that block is skipped
    from its title line to the close of its reference list."""
    lines = [l.strip() for l in text.replace("\f", "\n").splitlines()]
    all_titles = {f"{k}. {t}" for k, t in titles.items()}
    out = {}
    for n, title in titles.items():
        want = f"{n}. {title}"
        try:
            i = next(k for k, l in enumerate(lines) if l == want)
        except StopIteration:
            continue
        buf, skipping = "", False
        for l in lines[i + 1:]:
            if not l or l.isdigit() or l.startswith("FUNDAMENTAL BELIEFS") or l.startswith("of Seventh-day Adventists"):
                continue
            if l in all_titles:
                skipping = True
                continue
            if skipping:
                if l.endswith(".)"):
                    skipping = False
                continue
            if buf.endswith("-"):
                buf = buf[:-1] + l          # a word broken at the line end
            else:
                buf = (buf + " " + l).strip()
            if l.endswith(".)"):
                break
        out[n] = re.sub(r"\s+", " ", buf)
    return out


def prose(para):
    """The prose before the closing reference list, lowercased, punctuation stripped."""
    body = re.sub(r"\s*\([^()]*\.\)\s*$", "", para)
    body = body.lower().replace("’", "'")
    body = re.sub(r"[^a-z0-9' -]", " ", body)
    return body.split()


def refs(para):
    m = re.search(r"\(([^()]*)\.\)\s*$", para)
    return re.sub(r"[^0-9;:,\- ]", "", m.group(1)) if m else ""


def check(beliefs, yb_text):
    yb = parse_yearbook(yb_text, {n: t for n, (t, _) in beliefs.items()})
    diffs = 0
    for n in sorted(beliefs):
        title, para = beliefs[n]
        if n not in yb:
            print(f"FB{n:02d}: not found in the check text")
            diffs += 1
            continue
        a, b = prose(para), prose(yb[n])
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
            if tag != "equal":
                ctx = " ".join(a[max(0, i1 - 3):i1])
                print(f"FB{n:02d} prose after {ctx!r}: booklet {' '.join(a[i1:i2])!r} | check {' '.join(b[j1:j2])!r}")
                diffs += 1
        ra, rb = refs(para), refs(yb[n])
        if re.sub(r"[\s-]", "", ra) != re.sub(r"[\s-]", "", rb):
            print(f"FB{n:02d} refs differ:\n  booklet {ra}\n  check   {rb}")
            diffs += 1
    print(f"check: {len(beliefs)} beliefs compared, {diffs} differences")
    return diffs


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    text = Path(argv[1]).read_text(encoding="utf-8")
    preamble, beliefs = parse_booklet(text)
    n = write_files(preamble, beliefs, argv[2], "--closing-tag" in argv)
    print(f"wrote {n} files to {argv[2]}: preamble + beliefs {min(beliefs)}-{max(beliefs)}")
    for k in sorted(beliefs):
        t, p = beliefs[k]
        print(f"  FB{k:02d} {t}: {len(p.split())} words")
    if "--check" in argv:
        check(beliefs, Path(argv[argv.index("--check") + 1]).read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
