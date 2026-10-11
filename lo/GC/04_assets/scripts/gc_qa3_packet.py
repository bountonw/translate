#!/usr/bin/env python3
"""gc_qa3_packet.py — build the QA3 reading packet for one GC chapter.

QA3 reads only the paragraphs that QA1 and QA2 changed. This script compares
the pre-QA Lao chapter (the base commit) with the chapter in the working
tree, block by {GC ###.#} anchor, and writes one packet block per changed
paragraph:

    EN        the English paragraph at that anchor
    PRE-QA    the Lao before QA1, as prepared for printing
    CURRENT   the Lao as it stands now
    CHANGED   each differing line, the old run in [- -] and the new in {+ +},
              runs widened to the nearest space or punctuation so a change
              never splits a Lao word

Paragraphs whose only differences are punctuation or spacing are listed at
the end by anchor and not included. Footnote lines and subheadings that sit
under an anchor belong to that anchor's block.

Usage, from the repository root:

    python3 lo/GC/04_assets/scripts/gc_qa3_packet.py --chapter 12
    python3 lo/GC/04_assets/scripts/gc_qa3_packet.py --chapter 12 --base 8802e1bb --out PATH

It prints a summary and the batch split (2200 English words per batch, a
chapter under 2700 words as one batch, cut at anchors by nearest even share)
and writes the packet to ~/claude-sandbox/gc-audit/gcNN-qa3-packet.md unless
--out is given. It reads the repository and writes only the packet.
"""
import argparse
import datetime
import difflib
import math
import os
import re
import subprocess
import sys

# "Fix GC spelling issue before publishing (#727)": the last GC edit before
# QA1 — the text prepared for printing. The book has not yet been printed.
BASE_DEFAULT = "8802e1bb"
ANCHOR = re.compile(r"^## \{GC (\d+\.\d+)\}\s*$")
PUNCT_ONLY = re.compile(r"[\s.,;:!?\"'()\[\]​“”‘’…\-–—*_#^]+")
BOUNDARY = set(" \t.,;:!?\"'()[]“”‘’…-–—*_")
WORDS_PER_BATCH = 2200
SINGLE_BATCH_BELOW = 2700


def git_show(ref, path):
    r = subprocess.run(["git", "show", f"{ref}:{path}"], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"git show {ref}:{path} failed: {r.stderr.strip()}")
    return r.stdout


def blocks(text):
    """Split a chapter into (anchor order, anchor -> non-empty lines under it)."""
    order, d, cur = [], {}, None
    for line in text.splitlines():
        m = ANCHOR.match(line)
        if m:
            cur = m.group(1)
            order.append(cur)
            d[cur] = []
            continue
        if cur is None or not line.strip():
            continue
        d[cur].append(line.rstrip())
    return order, d


def norm(s):
    return PUNCT_ONLY.sub("", s)


def widen(s, lo, hi):
    while lo > 0 and s[lo - 1] not in BOUNDARY:
        lo -= 1
    while hi < len(s) and s[hi] not in BOUNDARY:
        hi += 1
    return lo, hi


def inline_diff(o, n):
    """Render one old/new line pair with [-old-]{+new+} runs on word boundaries."""
    ops = [list(op) for op in difflib.SequenceMatcher(None, o, n, autojunk=False).get_opcodes()]
    ranges = []
    for tag, i1, i2, j1, j2 in ops:
        if tag == "equal":
            continue
        a1, a2 = widen(o, i1, i2)
        b1, b2 = widen(n, j1, j2)
        # keep both sides anchored to the same equal context
        left = min(i1 - a1, j1 - b1)
        right = min(a2 - i2, b2 - j2)
        ranges.append([i1 - left, i2 + right, j1 - left, j2 + right])
    merged = []
    for r in ranges:
        if merged and r[0] <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], r[1])
            merged[-1][3] = max(merged[-1][3], r[3])
        else:
            merged.append(r)
    out, po, pn = [], 0, 0
    for i1, i2, j1, j2 in merged:
        out.append(o[po:i1])
        old, new = o[i1:i2], n[j1:j2]
        if old:
            out.append("[-" + old + "-]")
        if new:
            out.append("{+" + new + "+}")
        po, pn = i2, j2
    out.append(o[po:])
    return "".join(out)


def changed_lines(base_lines, cur_lines):
    out = []
    sm = difflib.SequenceMatcher(None, base_lines, cur_lines, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        olds, news = base_lines[i1:i2], cur_lines[j1:j2]
        for k in range(max(len(olds), len(news))):
            if k < len(olds) and k < len(news):
                out.append(inline_diff(olds[k], news[k]))
            elif k < len(olds):
                out.append("[-" + olds[k] + "-]")
            else:
                out.append("{+" + news[k] + "+}")
    return out


def split_batches(items):
    """items: list of (anchor, words). Returns list of (first, last, words, count)."""
    total = sum(w for _, w in items)
    if total < SINGLE_BATCH_BELOW or len(items) < 2:
        return [(items[0][0], items[-1][0], total, len(items))] if items else []
    nb = math.ceil(total / WORDS_PER_BATCH)
    share = total / nb
    batches, start, run, count = [], 0, 0, 0
    k = 1
    for idx, (a, w) in enumerate(items):
        run += w
        count += 1
        remaining_items = len(items) - idx - 1
        remaining_batches = nb - k
        if k < nb and remaining_items >= remaining_batches:
            target = k * share
            cum = sum(x[1] for x in items[: idx + 1])
            nxt = cum + (items[idx + 1][1] if idx + 1 < len(items) else 0)
            if abs(cum - target) <= abs(nxt - target) or remaining_items == remaining_batches:
                batches.append((items[start][0], a, run, count))
                start, run, count, k = idx + 1, 0, 0, k + 1
    if count:
        batches.append((items[start][0], items[-1][0], run, count))
    return batches


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--chapter", required=True, help="chapter number, e.g. 12")
    ap.add_argument("--base", default=BASE_DEFAULT, help=f"commit holding the pre-QA text (default {BASE_DEFAULT})")
    ap.add_argument("--out", help="packet path (default ~/claude-sandbox/gc-audit/gcNN-qa3-packet.md)")
    args = ap.parse_args()
    nn = f"{int(args.chapter):02d}"
    lo_path = f"lo/GC/03_public/GC{nn}_lo.md"
    en_path = f"lo/GC/00_source/GC{nn}_en.md"
    for p in (lo_path, en_path):
        if not os.path.exists(p):
            sys.exit(f"missing {p}; run from the repository root")
    base_text = git_show(args.base, lo_path)
    cur_text = open(lo_path, encoding="utf-8").read()
    en_text = open(en_path, encoding="utf-8").read()
    if "[[" in cur_text:
        print(f"WARNING: {lo_path} still holds [[ markers; the packet will carry them as current text", file=sys.stderr)

    b_order, b = blocks(base_text)
    c_order, c = blocks(cur_text)
    _, e = blocks(en_text)

    included, punct_only, unchanged, new_anchors, gone_anchors = [], [], 0, [], []
    for a in c_order:
        if a not in b:
            new_anchors.append(a)
            included.append(a)
            continue
        if b[a] == c[a]:
            unchanged += 1
        elif norm("\n".join(b[a])) == norm("\n".join(c[a])):
            punct_only.append(a)
        else:
            included.append(a)
    for a in b_order:
        if a not in c:
            gone_anchors.append(a)

    def en_words(a):
        return sum(len(l.split()) for l in e.get(a, []))

    items = [(a, en_words(a)) for a in included]
    batches = split_batches(items)
    total_words = sum(w for _, w in items)

    out_path = args.out or os.path.expanduser(f"~/claude-sandbox/gc-audit/gc{nn}-qa3-packet.md")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    today = datetime.date.today().isoformat()
    L = []
    L.append(f"# QA3 packet — GC{nn} — pre-QA text at {args.base} against the working tree — {today}")
    L.append("")
    L.append(f"Paragraphs changed by QA1 and QA2: {len(included)} (English words behind them: {total_words}). "
             f"Punctuation-only changes, listed at the end and not included: {len(punct_only)}. Unchanged: {unchanged}.")
    if new_anchors:
        L.append(f"Anchors absent from the pre-QA text (shown with PRE-QA empty): {', '.join('{GC ' + a + '}' for a in new_anchors)}.")
    if gone_anchors:
        L.append(f"Anchors in the pre-QA text that the current chapter no longer has: {', '.join('{GC ' + a + '}' for a in gone_anchors)}.")
    L.append("")
    L.append("Batch split by English words:")
    for i, (f, l, w, n) in enumerate(batches, 1):
        L.append(f"    batch {i}: {{GC {f}}} to {{GC {l}}} — {n} paragraphs, {w} words")
    L.append("")
    for idx, a in enumerate(included, 1):
        L.append(f"## {{GC {a}}}  [{idx} of {len(included)}]")
        L.append("")
        L.append("EN:")
        L.extend(e.get(a, ["(no English paragraph at this anchor)"]))
        L.append("")
        L.append("PRE-QA:")
        L.extend(b.get(a, ["(no paragraph at this anchor in the pre-QA text)"]))
        L.append("")
        L.append("CURRENT:")
        L.extend(c[a])
        L.append("")
        L.append("CHANGED:")
        L.extend(changed_lines(b.get(a, []), c[a]))
        L.append("")
    L.append("## Punctuation-only changes (not included)")
    L.append("")
    L.append(", ".join("{GC " + a + "}" for a in punct_only) if punct_only else "none")
    L.append("")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))

    print(f"GC{nn}: {len(included)} changed paragraphs, {total_words} English words, "
          f"{len(punct_only)} punctuation-only, {unchanged} unchanged; packet {out_path}")
    for i, (f, l, w, n) in enumerate(batches, 1):
        print(f"  batch {i}: {{GC {f}}} to {{GC {l}}} — {n} paragraphs, {w} words")


if __name__ == "__main__":
    main()
