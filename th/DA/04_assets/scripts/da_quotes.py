#!/usr/bin/env python3
"""Scripture quotations and allusions in a DA chapter, with every Thai version.

    python3 th/DA/04_assets/scripts/da_quotes.py --chapter 4
    python3 th/DA/04_assets/scripts/da_quotes.py --chapter 4 --confirmed ~/claude-sandbox/da-audit/da04-confirmed.txt

Without --confirmed the script proposes. A quotation is a span in “ ” of the
English; it is matched to King James verses first by a citation in the
paragraph, then by the chapter's based-on passage, then over the whole King
James by runs of four words. The match is scored as the share of the span's
words found in order in the verses, each word weighted by its rarity in the
King James, so "Immanuel" counts for more than "shall be called"; a span under
0.60 is unmatched, and an unmatched span with no resemblance to any verse is
counted as speech or the author's words and not listed. The Revised Version
is matched beside the King James and named where it fits better. An allusion
is a run of six or more consecutive King James words outside quotation marks;
a run whose seed appears in more than five verses is common wording and is
dropped. The proposals go to ~/claude-sandbox/da-audit/daNN-quotes.md, each
with its anchor, kind, English words, verses and score, then every verse in
the King James and all ten Thai versions; the same proposals go to
daNN-proposed.txt in the line format "anchor|kind|English words|CODE ch:v-v"
that the finder edits into daNN-confirmed.txt. With --confirmed FILE the
proposals are replaced by the finder's list and the texts section is rebuilt
from it. Reads only; writes the two files. Chapter 0 is the preface.
"""
import argparse
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

from da_common import (source_path, parse_english, english_words, based_on, in_based_on, load_books,
                       load_version, version_dir, clean_verse, parse_refs, parse_ref_code, SANDBOX,
                       VERSIONS, book_names)

WORD = re.compile(r"[a-z]+(?:'[a-z]+)?")
QUOTE = re.compile(r"“([^“”]+)”")
MIN_SCORE = 0.60
LIST_SCORE = 0.35
SEED = 4
MIN_ALLUSION = 6
COMMON = 5
RARE = 60
_text = {}


def tokens(s):
    return WORD.findall(s.lower().replace("’", "'"))


class Version:
    """One English version: verses, a seed index and word rarity."""

    def __init__(self, label):
        self.refs, self.index, df = [], defaultdict(list), defaultdict(int)
        where = defaultdict(list)
        for f in sorted(version_dir(label).glob("*.txt")):
            for raw in f.read_text(encoding="utf-8").splitlines():
                parts = raw.split("|", 4)
                if len(parts) == 5 and parts[2].isdigit() and parts[3].isdigit():
                    toks = tokens(clean_verse(parts[4]))
                    i = len(self.refs)
                    self.refs.append((parts[1], int(parts[2]), int(parts[3]), toks))
                    for k in range(len(toks) - SEED + 1):
                        self.index[" ".join(toks[k:k + SEED])].append(i)
                    for t in set(toks):
                        df[t] += 1
                        where[t].append(i)
        n = len(self.refs)
        self.idf = {t: math.log((n + 1) / (c + 1)) + 0.1 for t, c in df.items()}
        # Rare words (in at most RARE verses) seed the search on their own, so a
        # quotation that keeps a rare word but reorders the common ones is found.
        self.rare = {t: v for t, v in where.items() if len(v) <= RARE}
        self.by_ref = {(c, ch, v): i for i, (c, ch, v, _) in enumerate(self.refs)}

    def weight(self, t):
        return self.idf.get(t, math.log(len(self.refs) + 1) + 0.1)

    def verse_tokens(self, code, ch, lo, hi):
        out = []
        for v in range(lo, hi + 1):
            i = self.by_ref.get((code, ch, v))
            if i is None:
                return None
            out.extend(self.refs[i][3])
        return out


def version(label):
    if label not in _text:
        _text[label] = Version(label)
    return _text[label]


def weighted_lcs(a, b, w):
    """The largest total weight of a common subsequence of token lists a and b."""
    if not a or not b:
        return 0.0
    prev = [0.0] * (len(b) + 1)
    for x in a:
        cur = [0.0]
        wx = w(x)
        for j, y in enumerate(b, 1):
            cur.append(max(prev[j], cur[j - 1], prev[j - 1] + wx if x == y else 0.0))
        prev = cur
    return prev[-1]


def best_match(span, ver, candidates):
    """(code, ch, lo, hi, score) for the best window of up to four verses among the
    candidate (code, ch, v) seeds, or among the seed index's hits when none is given."""
    toks = tokens(span)
    if len(toks) < 3:
        return None
    total = sum(ver.weight(t) for t in toks)
    seeds = set(candidates)
    if not seeds:
        hits = defaultdict(float)
        for k in range(len(toks) - SEED + 1):
            key = " ".join(toks[k:k + SEED])
            for i in ver.index.get(key, ()):
                hits[i] += sum(ver.weight(t) for t in toks[k:k + SEED])
        for t in set(toks):
            for i in ver.rare.get(t, ()):
                hits[i] += ver.weight(t)
        for i, _ in sorted(hits.items(), key=lambda kv: -kv[1])[:20]:
            c, ch, v, _ = ver.refs[i]
            seeds.add((c, ch, v))
    best = None
    for code, ch, v in seeds:
        for lo, hi in ((v, v), (v, v + 1), (v - 1, v), (v, v + 2), (v - 1, v + 1), (v - 2, v), (v, v + 3), (v - 3, v)):
            if lo < 1:
                continue
            vt = ver.verse_tokens(code, ch, lo, hi)
            if vt is None:
                continue
            score = weighted_lcs(toks, vt, ver.weight) / total
            key = (round(score, 2), -(hi - lo))
            if best is None or key > best[0]:
                best = (key, (code, ch, lo, hi, score))
    return best[1] if best else None


def allusions(text, ver):
    """Maximal runs of MIN_ALLUSION or more consecutive verse words in text, as
    [(start, end, code, ch, v, words)]; seeds in more than COMMON verses dropped."""
    toks = tokens(text)
    found, taken = [], set()
    for k in range(len(toks) - SEED + 1):
        if k in taken:
            continue
        hits = ver.index.get(" ".join(toks[k:k + SEED]), ())
        if not hits or len(hits) > COMMON:
            continue
        for i in hits:
            code, ch, v, vt = ver.refs[i]
            for j in range(len(vt) - SEED + 1):
                if vt[j:j + SEED] != toks[k:k + SEED]:
                    continue
                f = SEED
                while k + f < len(toks) and j + f < len(vt) and toks[k + f] == vt[j + f]:
                    f += 1
                b = 0
                while k - b - 1 >= 0 and j - b - 1 >= 0 and toks[k - b - 1] == vt[j - b - 1]:
                    b += 1
                if f + b >= MIN_ALLUSION:
                    found.append((k - b, k + f, code, ch, v, " ".join(toks[k - b:k + f])))
                    taken.update(range(k - b, k + f))
                break
    out, seen = [], set()
    for run in sorted(found, key=lambda r: (r[0], -(r[1] - r[0]))):
        if run[0] in seen:
            continue
        seen.add(run[0])
        out.append(run)
    return out


def fmt_ref(code, ch, lo, hi):
    return f"{code} {ch}:{lo}" if lo == hi else f"{code} {ch}:{lo}-{hi}"


def texts_block(code, ch, lo, hi, names, kjv, rv):
    lines = []
    for v in range(lo, hi + 1):
        i = kjv.by_ref.get((code, ch, v))
        lines.append(f"KJV {code} {ch}:{v}: " + (" ".join(kjv.refs[i][3]) if i is not None else "(not on disk)"))
        j = rv.by_ref.get((code, ch, v))
        if j is not None and (i is None or rv.refs[j][3] != kjv.refs[i][3]):
            lines.append(f"RV {code} {ch}:{v}: " + " ".join(rv.refs[j][3]))
    for label in VERSIONS:
        verses = load_version(label, code)
        if verses is None:
            lines.append(f"{label}: (book not on disk)")
            continue
        parts = [verses.get((ch, v)) for v in range(lo, hi + 1)]
        if any(p is None for p in parts):
            lines.append(f"{label}: (verse not on disk)")
        else:
            lines.append(f"{label} ({names.get(code, code)} {ch}:{lo}" + (f"–{hi}" if hi != lo else "") + "): " + " ".join(parts))
    return lines


def match_quotation(span, text, kjv, rv, cited_seeds, based_seeds):
    """The best (code, ch, lo, hi, score, version) over the King James and the Revised Version."""
    picks = {}
    # The paragraph's own citations first, then the based-on passage, then the
    # whole version; a later, wider search replaces an earlier match only when
    # it scores clearly higher, so a based-on verse keeps a tie.
    rounds = [s for s in (cited_seeds, based_seeds) if s] + [[]]
    for label, ver in (("KJV", kjv), ("RV", rv)):
        best = None
        for seeds in rounds:
            cand = best_match(span, ver, seeds)
            if cand and (best is None or cand[4] > best[4] + 0.05):
                best = cand
            if best and best[4] >= 0.85:
                break
        picks[label] = best
    k, r = picks["KJV"], picks["RV"]
    if r and (k is None or r[4] > k[4] + 0.08 or ("R. V." in text and r[4] >= k[4])):
        return r + ("RV",)
    return (k + ("KJV",)) if k else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--chapter", type=int, required=True, help="chapter number; 0 is the preface")
    ap.add_argument("--confirmed", help="the finder's list; replaces the proposals")
    ap.add_argument("--out", help="output file; default ~/claude-sandbox/da-audit/daNN-quotes.md")
    a = ap.parse_args()
    nn = a.chapter
    english = parse_english(source_path(nn).read_text(encoding="utf-8"))
    basedon = based_on(nn)
    _, en_books = load_books()
    names = book_names()
    kjv, rv = version("KJVS"), version("RV")
    SANDBOX.mkdir(parents=True, exist_ok=True)
    out = Path(a.out) if a.out else SANDBOX / f"da{nn:02d}-quotes.md"

    proposals, unmatched, speech = [], [], 0
    if a.confirmed:
        for line in Path(a.confirmed).expanduser().read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            cells = [c.strip() for c in line.split("|")]
            if len(cells) < 4:
                unmatched.append(f"malformed line: {line}")
                continue
            ref = cells[3].replace(" RV", "")
            parsed = parse_ref_code(ref)
            if not parsed:
                unmatched.append(f"unreadable reference: {line}")
                continue
            code, ch, vv = parsed
            lo, hi = (min(vv), max(vv)) if vv else (1, 1)
            proposals.append((cells[0], cells[1], cells[2], code, ch, lo, hi, None, "RV" if cells[3].endswith(" RV") else "KJV"))
    else:
        for anchor, para in english.items():
            text = english_words(para)
            cited = parse_refs(text, en_books)
            cited_seeds = [(c, ch, v) for c, ch, vv in cited for v in (sorted(vv)[:1] if vv else [1])]
            based_seeds = [(c, ch, v) for c, ch, vv in basedon for v in (sorted(vv) if vv else range(1, 80))]
            for m in QUOTE.finditer(text):
                span = re.sub(r"\s+", " ", m.group(1)).strip()
                if len(tokens(span)) < 3:
                    continue
                best = match_quotation(span, text, kjv, rv, cited_seeds, based_seeds)
                if best and best[4] >= MIN_SCORE:
                    code, ch, lo, hi, score, ver = best
                    proposals.append((anchor, "quotation", span, code, ch, lo, hi, score, ver))
                elif best and best[4] >= LIST_SCORE:
                    unmatched.append(f"{{DA {anchor}}} “{span[:140]}” (nearest {fmt_ref(*best[:4])} at {best[4]:.2f})")
                else:
                    speech += 1
            outside = QUOTE.sub(" ", text)
            for s, e, code, ch, v, words in allusions(outside, kjv):
                proposals.append((anchor, "allusion", words, code, ch, v, v, None, "KJV"))

    L = [f"# DA{nn:02d} quotations and allusions — {'the finder’s confirmed list' if a.confirmed else 'proposals from da_quotes.py'}", ""]
    L.append("Based on: " + ("; ".join(f"{names.get(c, c)} {ch}" + (f":{min(vv)}-{max(vv)}" if vv else "") for c, ch, vv in basedon) if basedon else "no based-on passage"))
    L += ["", "## Confirmed" if a.confirmed else "## Proposals", "", "| Anchor | Kind | English words | Verses | Score | In based-on |", "|---|---|---|---|---|---|"]
    for anchor, kind, span, code, ch, lo, hi, score, ver in proposals:
        inside = bool(basedon) and all(in_based_on(basedon, code, ch, v) for v in range(lo, hi + 1))
        L.append(f"| {{DA {anchor}}} | {kind} | {span[:160]} | {fmt_ref(code, ch, lo, hi)}{' RV' if ver == 'RV' else ''} | "
                 f"{'' if score is None else f'{score:.2f}'} | {'yes' if inside else 'no'} |")
    if not proposals:
        L.append("| none | | | | | |")
    L += ["", "## Unmatched quotations (some resemblance to a verse; the finder places or rejects them)", ""] + ([f"- {u}" for u in unmatched] or ["none"])
    if not a.confirmed:
        L += ["", f"Spans in quotation marks with no resemblance to any verse, taken as speech or the author's words: {speech}."]
    L += ["", "## Texts", ""]
    for anchor, kind, span, code, ch, lo, hi, score, ver in proposals:
        L.append(f"### {{DA {anchor}}} {kind} — {fmt_ref(code, ch, lo, hi)}" + (f" (score {score:.2f})" if score is not None else ""))
        L += ["", f"EN: {span}", ""]
        L += texts_block(code, ch, lo, hi, names, kjv, rv)
        L.append("")
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    if not a.confirmed:
        plist = SANDBOX / f"da{nn:02d}-proposed.txt"
        plist.write_text("".join(f"{anchor}|{kind}|{span[:160]}|{fmt_ref(code, ch, lo, hi)}{' RV' if ver == 'RV' else ''}\n"
                                 for anchor, kind, span, code, ch, lo, hi, score, ver in proposals), encoding="utf-8")
        print(f"wrote {plist}")
    q = sum(1 for p in proposals if p[1] == "quotation")
    print(f"wrote {out}: {q} quotation(s), {len(proposals) - q} allusion(s), {len(unmatched)} unmatched, {speech} speech span(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
