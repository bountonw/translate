#!/usr/bin/env python3
"""Scripture-citation check for an SC Thai chapter. Reads only; writes nothing.

    python3 th/SC/04_assets/scripts/sc_refcheck.py --chapter 12
    python3 th/SC/04_assets/scripts/sc_refcheck.py --chapter 12 --range 105.1 109.2

For every paragraph in range, every citation in the Thai (inline, in a
parenthesis, or inside a #footnote) is set beside every citation in the
English paragraph of the same anchor, and each difference is printed:

    REF   a finding that takes a marker: a book name not in th_books.txt, a
          chapter or verse beyond the book (bounds from the WEB text under
          ~/programming/bible/), a version label not in the known list, a
          citation the English has and the Thai lacks, or the same chapter
          cited with a different set of verses.
    NOTE  not a marker: a citation the Thai carries that the English does not
          (the translator's own apparatus, whose accuracy the bounds check
          still covers), and a THSV label, which the 16 August ruling calls
          redundant and which the batch auditor deletes silently in its range
          as the chapter runs, reporting the count.

Book names live in th_books.txt beside this script, copied from the corpus;
a name missing there is reported as unknown, never guessed. Exit status 1 when
any REF line was printed.
"""
import argparse
import os
import re
import sys
from pathlib import Path

from sc_common import (chapter_path, source_path, parse_thai, parse_english,
                       mask_markers, in_range, ROOT)

HERE = Path(__file__).resolve().parent
BIBLE = Path(os.path.expanduser("~/programming/bible"))
KNOWN_LABELS = {"THSV", "TNCV", "TKJV", "TH1940", "TH1971", "THA-ERV", "ERV", "TCV", "NTV", "TFB", "KJV"}
THAI = "฀-๿"
VERSES = r"\d+(?:\s*[-–]\s*\d+)?(?:,\s*\d+(?:\s*[-–]\s*\d+)?)*"
TH_CITE = re.compile(
    rf"(?P<book>(?:[1-3]\s)?[{THAI}]+)\s+(?P<ch>\d+)(?![{THAI}\d])(?![\s]*[{THAI}])(?::(?P<vv>{VERSES}))?"
    rf"(?:\s*[-–]\s*(?P<ch2>\d+):(?P<v2>\d+))?(?:\s+(?P<label>[A-Z][A-Z0-9-]+))?")
ONE_CHAPTER = {"OBA", "PHM", "2JN", "3JN", "JUD"}
EN_CITE = re.compile(
    r"(?P<book>(?:[1-3]\s)?[A-Z][a-z]+(?:\s(?:of\s)?[A-Z][a-z]+)?)\s+(?P<ch>\d+)(?::(?P<vv>" + VERSES + r"))?"
    r"(?:\s*[-–]\s*(?P<ch2>\d+):(?P<v2>\d+))?")
FOOTNOTE = re.compile(r"#footnote\[((?:[^\[\]]|\[[^\]]*\])*)\]")


def load_books():
    th, en = {}, {}
    for line in (HERE / "th_books.txt").read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        code, thai, english = [c.strip() for c in line.split("|")]
        if thai:
            th[thai] = code
        for name in english.split(";"):
            if name.strip():
                en[name.strip()] = code
    return th, en


def load_bounds():
    """code -> {chapter: last verse}, from the WEB pipe files; empty when absent."""
    bounds = {}
    d = BIBLE / "WEB"
    if not d.is_dir():
        return bounds
    for f in d.glob("*.txt"):
        for line in f.read_text(encoding="utf-8").splitlines():
            parts = line.split("|", 4)
            if len(parts) < 5:
                continue
            code, ch, v = parts[1], parts[2], parts[3]
            try:
                chn, vn = int(ch), int(v.split("-")[-1])
            except ValueError:
                continue
            b = bounds.setdefault(code, {})
            b[chn] = max(b.get(chn, 0), vn)
    return bounds


def expand(vv):
    out = set()
    for part in re.split(r",\s*", vv):
        a, _, b = re.split(r"(\s*[-–]\s*)", part)[0], None, None
        if re.search(r"[-–]", part):
            lo, hi = re.split(r"\s*[-–]\s*", part)
            out.update(range(int(lo), int(hi) + 1))
        else:
            out.add(int(part))
    return out


def cites(text, regex, books):
    """Every citation in text as (name, code_or_None, chapter, verses_or_None, label, raw)."""
    found = []
    for m in regex.finditer(text):
        name = re.sub(r"\s+", " ", m.group("book")).strip()
        code = books.get(name)
        if code is None and regex is EN_CITE:
            # An English capitalised word before a number is not always a book.
            words = name.split()
            if len(words) > 1 and books.get(words[-1]):
                name, code = words[-1], books[words[-1]]
            elif len(words) > 1 and books.get(" ".join(words[-2:])):
                name, code = " ".join(words[-2:]), books[" ".join(words[-2:])]
            else:
                continue
        ch = int(m.group("ch"))
        vv = expand(m.group("vv")) if m.group("vv") else None
        if code in ONE_CHAPTER and vv is None:
            # "Jude 24" names a verse of the book's only chapter.
            ch, vv = 1, {ch}
        if m.group("ch2"):
            vv = vv or set()
            vv = ("span", int(m.group("ch2")), int(m.group("v2")), vv)
        label = m.group("label") if "label" in m.groupdict() else None
        found.append((name, code, ch, vv, label, m.group(0).strip()))
    return found


def fmt_vv(vv):
    if vv is None:
        return ""
    if isinstance(vv, tuple):
        return f":{min(vv[3]) if vv[3] else '?'}–{vv[1]}:{vv[2]}"
    vs = sorted(vv)
    runs, start, prev = [], vs[0], vs[0]
    for v in vs[1:]:
        if v == prev + 1:
            prev = v
            continue
        runs.append((start, prev))
        start = prev = v
    runs.append((start, prev))
    return ":" + ", ".join(f"{a}" if a == b else f"{a}–{b}" for a, b in runs)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--chapter", type=int, required=True)
    ap.add_argument("--range", nargs=2, metavar=("FIRST", "LAST"))
    a = ap.parse_args()
    first, last = a.range if a.range else (None, None)
    th_books, en_books = load_books()
    bounds = load_bounds()
    chapter = chapter_path(a.chapter)
    source = source_path(a.chapter)
    _, paras = parse_thai(chapter.read_text(encoding="utf-8"))
    english = parse_english(source.read_text(encoding="utf-8"))
    refs, notes = [], []
    th_all = {p.anchor: cites(mask_markers(p.text), TH_CITE, th_books) for p in paras}
    order = [p.anchor for p in paras]

    def union(found, code, ch):
        """(verse set, chapter-only or span seen) over every citation of code ch."""
        vs, loose = set(), False
        for f in found:
            if f[1] == code and f[2] == ch:
                if f[3] is None or isinstance(f[3], tuple):
                    loose = True
                else:
                    vs |= f[3]
        return vs, loose

    for i, p in enumerate(paras):
        if not in_range(p.anchor, first, last):
            continue
        th = th_all[p.anchor]
        en = cites(english.get(p.anchor, ""), EN_CITE, en_books)
        if p.anchor not in english:
            refs.append(f"{{SC {p.anchor}}} REF align: no English paragraph carries this anchor")
        seen_pairs = set()
        for name, code, ch, vv, label, raw in th:
            if code is None:
                refs.append(f"{{SC {p.anchor}}} REF unknown-book: \"{raw}\" — {name} is not in th_books.txt")
                continue
            if label and label not in KNOWN_LABELS:
                refs.append(f"{{SC {p.anchor}}} REF label: \"{raw}\" — {label} is not a known version label")
            if label == "THSV":
                notes.append(f"{{SC {p.anchor}}} NOTE thsv-label: \"{raw}\" — THSV is the default; the batch auditor deletes the label in its range and reports the count")
            b = bounds.get(code)
            if b:
                if ch not in b:
                    refs.append(f"{{SC {p.anchor}}} REF bounds: \"{raw}\" — {code} has {max(b)} chapters")
                elif vv and not isinstance(vv, tuple) and max(vv) > b[ch]:
                    refs.append(f"{{SC {p.anchor}}} REF bounds: \"{raw}\" — {code} {ch} has {b[ch]} verses")
            if (code, ch) in seen_pairs:
                continue
            seen_pairs.add((code, ch))
            en_vs, en_loose = union(en, code, ch)
            if not en_vs and not en_loose:
                notes.append(f"{{SC {p.anchor}}} NOTE extra: \"{raw}\" — the English paragraph does not cite {code} {ch}; translator's own apparatus, accuracy checked above only")
                continue
            th_vs, th_loose = union(th, code, ch)
            if en_vs and th_vs and not en_loose and not th_loose and th_vs != en_vs:
                if th_vs > en_vs:
                    notes.append(f"{{SC {p.anchor}}} NOTE extra-verses: TH cites {code} {ch}{fmt_vv(th_vs)} — EN cites {code} {ch}{fmt_vv(en_vs)}; the extra verses are the translator's own apparatus")
                else:
                    refs.append(f"{{SC {p.anchor}}} REF verses: TH cites {code} {ch}{fmt_vv(th_vs)} — EN cites {code} {ch}{fmt_vv(en_vs)}")
        for name, code, ch, vv, label, raw in en:
            if any(t[1] == code and t[2] == ch for t in th):
                continue
            near = [order[j] for j in (i - 1, i + 1) if 0 <= j < len(order)
                    and any(t[1] == code and t[2] == ch for t in th_all[order[j]])]
            if near:
                notes.append(f"{{SC {p.anchor}}} NOTE moved: EN \"{raw}\" is cited in the Thai at {{SC {near[0]}}} instead")
            else:
                refs.append(f"{{SC {p.anchor}}} REF missing: EN \"{raw}\" — no Thai citation of {code} {ch} in the paragraph")

    for line in refs + notes:
        print(line)
    rel = chapter.resolve().relative_to(ROOT)
    n = sum(1 for p in paras if in_range(p.anchor, first, last))
    print(f"# {rel}: {len(refs)} REF finding(s), {len(notes)} note(s) in {n} paragraph(s)"
          + ("" if bounds else "; no WEB text under ~/programming/bible, so chapter and verse bounds were not checked"))
    return 1 if refs else 0


if __name__ == "__main__":
    sys.exit(main())
