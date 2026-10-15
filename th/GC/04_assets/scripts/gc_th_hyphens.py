#!/usr/bin/env python3
"""Turn the print's line-break hyphens into candidate soft-hyphen entries.

Where the printed Thai edition broke a word across a line it set a hyphen, and
that hyphen marks a break point a Thai typesetter judged acceptable.  The
extraction drops those hyphens from the text and records each site; this script
reads the record and proposes a dictionary entry for each one in the format
th/SJ/04_assets/template/dictionary.typ uses, where "-" marks the split.

The hard part is the word boundary, because Thai does not space its words.  A
candidate is therefore grown outward from the break for as long as the string
still occurs somewhere else in the book unbroken, which is evidence that it is
a real unit rather than an arbitrary span.  Entries the script is not confident
about are still written out, marked, so that nothing is silently dropped.

Usage:
    python3 th/GC/04_assets/scripts/gc_th_hyphens.py NOTES.tsv TEXT_DIR OUT.tsv
"""

import glob
import os
import re
import sys

THAI = re.compile(r"[฀-๿]")
MIN_SIDE = 2
MAX_SIDE = 9
MIN_HITS = 2
KEEP = 0.55


# Eight words are broken at a line end exactly once in the whole book, so the
# corpus carries no second occurrence to grow the candidate against and the
# word boundary has to be supplied.  Each is written out below with the break
# the print used.  "อาชญ-กรรม" is the print's own misspelling of อาชญากรรม,
# which is set correctly and hyphenated correctly elsewhere in the book, so it
# folds into that entry rather than becoming a dictionary row of its own.
REPAIRS = {
    "กขัต-ฤกษ์": "นักขัต-ฤกษ์",
    "ธรรม-กิตต": "คริสตธรรม-กิตติคุณ",
    "ังหา-ริมท": "อสังหา-ริมทรัพย์",
    "อาชญ-กรรม": "อาชญา-กรรม",
    "ทเทม-บากค": "วิทเทม-บาก",
    "ะราช-ชนนี": "พระราช-ชนนี",
    "กรีน-แลนด": "กรีน-แลนด์",
    "นเนต-ทิกั": "คอนเนต-ทิกัต",
}


def corpus_text(text_dir):
    parts = []
    for path in sorted(glob.glob(os.path.join(text_dir, "GC*_print_th.typ"))):
        body = open(path, encoding="utf-8").read()
        body = re.sub(r"^//.*$", "", body, flags=re.M)
        body = re.sub(r"#EGW\[[^\]]*\]", "", body)
        body = body.replace("#italic[", "").replace("\\[", "").replace("\\]", "")
        parts.append(body)
    return "\n".join(parts)


def thai_tail(s, limit):
    out = []
    for ch in reversed(s):
        if not THAI.match(ch) or len(out) >= limit:
            break
        out.append(ch)
    return "".join(reversed(out))


def thai_head(s, limit):
    out = []
    for ch in s:
        if not THAI.match(ch) or len(out) >= limit:
            break
        out.append(ch)
    return "".join(out)


def grow(corpus, left, right):
    """Return the (l, r) around the break that looks like one word.

    Each side is extended one character at a time and kept only while the
    string still occurs about as often as it did before, because a word
    boundary shows up as a steep drop: "คริสตจักร" is everywhere in this book
    and "คริสตจักรโ" is not, so the word ends at the last character before the
    drop.
    """
    def count(l, r):
        return corpus.count(l + r)

    l, r = left[-MIN_SIDE:], right[:MIN_SIDE]
    if len(l) < MIN_SIDE or len(r) < MIN_SIDE:
        return None
    base = count(l, r)
    if base < MIN_HITS:
        return None
    for size in range(MIN_SIDE + 1, min(MAX_SIDE, len(right)) + 1):
        cand = right[:size]
        c = count(l, cand)
        if c >= max(MIN_HITS, base * KEEP):
            r, base = cand, c
        else:
            break
    for size in range(MIN_SIDE + 1, min(MAX_SIDE, len(left)) + 1):
        cand = left[-size:]
        c = count(cand, r)
        if c >= max(MIN_HITS, base * KEEP):
            l, base = cand, c
        else:
            break
    return (l, r, count(l, r))


def main():
    notes, text_dir, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    corpus = corpus_text(text_dir)

    rows = []
    for line in open(notes, encoding="utf-8"):
        if not line.startswith("LINE-HYPHEN"):
            continue
        _, where, detail = line.rstrip("\n").split("\t")
        left_ctx, right_ctx = detail.split(" | ")
        left = thai_tail(left_ctx.rstrip("-"), MAX_SIDE)
        right = thai_head(right_ctx, MAX_SIDE)
        if not left or not right:
            rows.append((where, "", "", 0, "no Thai on one side of the break"))
            continue
        found = grow(corpus, left, right)
        if found:
            l, r, hits = found
            rows.append((where, f"{l}-{r}", l + r, hits, "confirmed elsewhere in the book"))
        else:
            raw = f"{left[-4:]}-{right[:4]}"
            key = f"{left}-{right}"
            entry = REPAIRS.get(key) or REPAIRS.get(raw)
            if entry:
                rows.append(
                    (where, entry, entry.replace("-", ""), 0,
                     "the word occurs once in the book, so a reader supplied the boundary")
                )
            else:
                rows.append(
                    (where, raw, raw.replace("-", ""), 0,
                     "not found elsewhere and no repair recorded; needs a reader")
                )

    seen = {}
    for where, entry, joined, hits, note in rows:
        if not entry:
            continue
        seen.setdefault(entry, [0, joined, hits, note, where])
        seen[entry][0] += 1

    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("# entry\tjoined\tsites\thits elsewhere\tfirst page\tconfidence\n")
        for entry, (count, joined, hits, note, where) in sorted(
            seen.items(), key=lambda kv: (-kv[1][0], -kv[1][2])
        ):
            fh.write(f"{entry}\t{joined}\t{count}\t{hits}\t{where}\t{note}\n")

    confirmed = sum(1 for v in seen.values() if v[2] >= MIN_HITS)
    print(f"hyphen sites read: {len(rows)}")
    print(f"distinct candidate entries: {len(seen)}")
    print(f"  confirmed by another occurrence in the book: {confirmed}")
    print(f"  boundary supplied by a reader: {len(seen) - confirmed}")


if __name__ == "__main__":
    main()
