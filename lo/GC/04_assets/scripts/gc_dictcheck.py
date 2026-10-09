#!/usr/bin/env python3
"""gc_dictcheck.py — check that every word the QA passes introduced is known
to the typesetting dictionaries.

The Lao typesetting pipeline wraps each word using the dictionary hierarchy
that helpers/dict_loader.py loads (chapter patch and dictionary, book patch
and dictionary, language patch.txt, language main.txt); a word it cannot find
becomes \\nodict{} in the typeset output. This script takes every run of text
that changed between the pre-QA baseline and the working tree, splits it into
space-delimited tokens, and reports each token that cannot be segmented into
dictionary words. Each report line gives the anchor, the token, the stretch
the segmentation cannot bridge, and how often the token appears in the pre-QA
book (a nonzero count means the word predates the QA passes and the
dictionary never knew it).

A flagged token is either a typo the QA passes introduced, which wants a FIX
marker, or a genuine new word, which wants a coded row added to
lo/assets/dictionaries/main.txt. Deciding which is reading work, not script
work: the conductor hands flagged tokens to the reader or the resolve-check
dispatch, and rows are added only after the translator's review.

Usage, from the repository root:

    python3 lo/GC/04_assets/scripts/gc_dictcheck.py --chapter 12
    python3 lo/GC/04_assets/scripts/gc_dictcheck.py --chapter 12 --base 8802e1bb

Read-only; exit code 1 when any token fails, 0 when all segment.
"""
import argparse
import difflib
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "helpers"))
from dict_loader import load_hierarchical_dictionaries  # noqa: E402

BASE_DEFAULT = "8802e1bb"  # the pre-QA baseline: prepared for printing, not printed
ANCHOR = re.compile(r"^## \{GC (\d+\.\d+)\}\s*$")
LAO = re.compile(r"[຀-໿]")
TOKEN_SPLIT = re.compile(r"[^຀-໿]+")


def git_show(ref, path):
    r = subprocess.run(["git", "show", f"{ref}:{path}"], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"git show {ref}:{path} failed: {r.stderr.strip()}")
    return r.stdout


def blocks(text):
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


def changed_new_text(base_lines, cur_lines):
    """Return the added/replaced character runs of the current side."""
    out = []
    sm = difflib.SequenceMatcher(None, "\n".join(base_lines), "\n".join(cur_lines), autojunk=False)
    for tag, _i1, _i2, j1, j2 in sm.get_opcodes():
        if tag in ("replace", "insert"):
            out.append(("\n".join(cur_lines))[j1:j2])
    return out


def build_lexicon(chapter):
    merged, _conflicts = load_hierarchical_dictionaries(chapter=f"GC{chapter}", book="GC")
    lex = set()
    for term in merged.terms:
        lex.add(term)
        for part in term.split():  # multi-word entries also license their parts
            if part:
                lex.add(part)
    lex.add("\u0ec6")  # the repetition mark is a mark, not a word; no dictionary lists it
    return lex


def segment_gap(token, lex, maxlen):
    """None if token segments into lexicon words; else (lo, hi) of the stretch
    no segmentation can bridge."""
    n = len(token)
    fwd = [False] * (n + 1)
    fwd[0] = True
    for i in range(n):
        if not fwd[i]:
            continue
        for j in range(i + 1, min(n, i + maxlen) + 1):
            if token[i:j] in lex:
                fwd[j] = True
    if fwd[n]:
        return None
    bwd = [False] * (n + 1)
    bwd[n] = True
    for j in range(n, 0, -1):
        if not bwd[j]:
            continue
        for i in range(max(0, j - maxlen), j):
            if token[i:j] in lex:
                bwd[i] = True
    lo = max((i for i in range(n + 1) if fwd[i]), default=0)
    hi = min((j for j in range(n + 1) if bwd[j]), default=n)
    if hi < lo:
        lo, hi = hi, lo
    return (lo, hi)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--chapter", required=True)
    ap.add_argument("--base", default=BASE_DEFAULT)
    args = ap.parse_args()
    nn = f"{int(args.chapter):02d}"
    lo_path = f"lo/GC/03_public/GC{nn}_lo.md"
    if not os.path.exists(lo_path):
        sys.exit(f"missing {lo_path}; run from the repository root")
    cur_text = open(lo_path, encoding="utf-8").read()
    if "[[" in cur_text:
        print(f"WARNING: {lo_path} holds [[ markers; marker text will be checked as text", file=sys.stderr)
    base_text = git_show(args.base, lo_path)
    _, b = blocks(base_text)
    c_order, c = blocks(cur_text)

    lex = build_lexicon(nn)
    maxlen = max((len(t) for t in lex), default=1)

    # The pre-QA book, for "did this token exist before the QA passes".
    preqa = []
    for k in range(1, 43):
        p = f"lo/GC/03_public/GC{k:02d}_lo.md"
        r = subprocess.run(["git", "show", f"{args.base}:{p}"], capture_output=True, text=True)
        if r.returncode == 0:
            preqa.append(r.stdout)
    preqa_all = "\n".join(preqa)

    bad = []
    seen = set()
    for a in c_order:
        runs = changed_new_text(b.get(a, []), c[a])
        for run in runs:
            for token in TOKEN_SPLIT.split(run):
                if len(token) < 2 or not LAO.search(token):
                    continue
                # widen to the full space-delimited token in the paragraph
                para = "\n".join(c[a])
                for m in re.finditer(re.escape(token), para):
                    s, e = m.start(), m.end()
                    while s > 0 and LAO.match(para[s - 1]):
                        s -= 1
                    while e < len(para) and LAO.match(para[e]):
                        e += 1
                    token = para[s:e]
                    break
                if (a, token) in seen:
                    continue
                seen.add((a, token))
                gap = segment_gap(token, lex, maxlen)
                if gap:
                    lo_i, hi_i = gap
                    stretch = token[max(0, lo_i - 2):min(len(token), hi_i + 2)]
                    bad.append((a, token, stretch, preqa_all.count(token)))

    if not bad:
        print(f"GC{nn}: every changed token segments against the typesetting dictionaries.")
        return 0
    print(f"GC{nn}: {len(bad)} changed token(s) the typesetting dictionaries cannot segment.")
    print("anchor | token | unbridged stretch | occurrences in the pre-QA book")
    for a, tok, stretch, cnt in bad:
        print(f"{{GC {a}}} | {tok} | {stretch} | {cnt}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
