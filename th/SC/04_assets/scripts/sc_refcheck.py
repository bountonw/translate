#!/usr/bin/env python3
"""Scripture-citation check for an SC Thai chapter. Reads only; writes nothing.

    python3 th/SC/04_assets/scripts/sc_refcheck.py --chapter 12
    python3 th/SC/04_assets/scripts/sc_refcheck.py --chapter 12 --range 105.1 109.2

For every paragraph in range, every citation in the Thai (inline, in a
parenthesis, or inside a #footnote) is set beside every citation in the
English paragraph of the same anchor, and a quotation followed by its
citation is compared word for word with the cited version from the offline
Bible corpus (path in sc_common.py; New Testament books only are on disk).
A #footnote[...] call inside a quotation is removed before the comparison.

    REF   a finding that takes a marker: a book name not in th_books.txt, a
          chapter or verse beyond the book, a version label not in the known
          list, a citation the English has and the Thai lacks, the same
          chapter cited with fewer verses than the English, or a quotation
          that differs from its version (the version's text is printed).
    NOTE  not a marker: a citation the Thai carries beyond the English, extra
          verses, a THSV label, a quotation that could not be compared.

Exit status 1 when any REF line was printed.
"""
import argparse
import re
import sys
from pathlib import Path

from sc_common import (chapter_path, source_path, parse_thai, parse_english,
                       mask_markers, in_range, ROOT, BIBLE, version_dir)

HERE = Path(__file__).resolve().parent
KNOWN_LABELS = {"THSV", "TNCV", "TKJV", "TH1940", "TH1971", "THA-ERV", "ERV", "TCV", "NTV", "TFB", "KJV"}
THAI = "฀-๿"
VERSES = r"\d+(?:\s*[-–]\s*\d+)?(?:,\s*\d+(?:\s*[-–]\s*\d+)?)*"
TH_CITE = re.compile(
    rf"(?P<book>(?:[1-3]\s)?[{THAI}]+)\s+(?P<ch>\d+)(?![{THAI}\d])(?![\s]*[{THAI}])(?::(?P<vv>{VERSES}))?"
    rf"(?:\s*[-–]\s*(?P<ch2>\d+):(?P<v2>\d+))?(?:\s+(?P<label>[A-Z][A-Z0-9-]+))?")
EN_CITE = re.compile(
    r"(?P<book>(?:[1-3]\s)?[A-Z][a-z]+(?:\s(?:of\s)?[A-Z][a-z]+)?)\s+(?P<ch>\d+)(?::(?P<vv>" + VERSES + r"))?"
    r"(?:\s*[-–]\s*(?P<ch2>\d+):(?P<v2>\d+))?")
ONE_CHAPTER = {"OBA", "PHM", "2JN", "3JN", "JUD"}
VERSE_SPLIT = re.compile(r"(?:^|(?<=[\s“‘(\[]))(\d{1,3})(?=[^\d\s:.,-])")
HEADER = re.compile(rf"^(?:[1-3]\s)?[{THAI}]+\s(\d+)$")
STRIP = re.compile(r"[\s​‌‍﻿ “”‘’\"'.,;:!?()\[\]<>…\-–—]")
ELLIPSIS = re.compile(r"…|\.\.\.")
# Typst function markup inside a quotation, as "#italic[", is not Scripture.
TYPST_FN = re.compile(r"#[A-Za-z_][\w.]*(?:\([^()]*\))?\[")
_versions = {}


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
    d = version_dir("WEB")
    if not d.is_dir():
        return bounds
    for f in d.glob("*.txt"):
        for line in f.read_text(encoding="utf-8").splitlines():
            parts = line.split("|", 4)
            if len(parts) < 5:
                continue
            try:
                chn, vn = int(parts[2]), int(parts[3].split("-")[-1])
            except ValueError:
                continue
            b = bounds.setdefault(parts[1], {})
            b[chn] = max(b.get(chn, 0), vn)
    return bounds


def load_version(label, code):
    """(chapter, verse) -> text for one book of one version, or None when not on disk."""
    key = (label, code)
    if key in _versions:
        return _versions[key]
    vd = version_dir(label)
    files = list(vd.glob(f"*{code}.txt")) if vd.is_dir() else []
    if not files:
        _versions[key] = None
        return None
    verses, ch, last = {}, 0, None
    text = files[0].read_text(encoding="utf-8")
    if "|" in text[:20]:
        # Pipe layout: "VER|BOOK|ch|v|text"; a heading has H in the verse field.
        for raw in text.splitlines():
            parts = raw.split("|", 4)
            if len(parts) == 5 and parts[2].isdigit() and parts[3].isdigit():
                t = re.sub(r"\{[HG]\d+\}", "", parts[4]).replace("\u200b", "")
                t = re.sub(r"\s*§\d*\s*", " ", t).replace("¶", " ")
                t = re.sub(r"\s+", " ", t).strip()
                verses[(int(parts[2]), int(parts[3]))] = t
        _versions[key] = verses
        return verses
    for raw in files[0].read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        m = HEADER.match(line)
        if m:
            ch, last = int(m.group(1)), None
            continue
        parts = VERSE_SPLIT.split(line)
        # parts: [lead, num, text, num, text, ...]; a line with no number is a
        # continuation of the last verse (poetry), a heading, or a parallel reference.
        if len(parts) == 1:
            if last and line and not line.startswith("("):
                verses[last] += " " + line
            continue
        for i in range(1, len(parts) - 1, 2):
            last = (ch, int(parts[i]))
            verses[last] = parts[i - 1].strip() + " " + parts[i + 1].strip() if i == 1 and parts[0].strip() else parts[i + 1].strip()
    _versions[key] = verses
    return verses


def expand(vv):
    out = set()
    for part in re.split(r",\s*", vv):
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
            ch, vv = 1, {ch}
        if m.group("ch2"):
            vv = ("span", int(m.group("ch2")), int(m.group("v2")), vv or set())
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


QUOTE = re.compile(r"“([^“”]{12,})”")
CITE_PAREN = re.compile(r"\(([^()]*\d+:\d+[^()]*)\)")
FOOTNOTE_OPEN = "#footnote["


def strip_footnotes(text):
    """Remove every #footnote[...] call, bracket-matched, so a footnote placed
    inside a quotation does not break the quotation's curly quotes. An unclosed
    call is removed to the end of the text."""
    out, i = [], 0
    while True:
        j = text.find(FOOTNOTE_OPEN, i)
        if j < 0:
            out.append(text[i:])
            return "".join(out)
        out.append(text[i:j])
        k, depth = j + len(FOOTNOTE_OPEN), 1
        while k < len(text) and depth:
            if text[k] == "[":
                depth += 1
            elif text[k] == "]":
                depth -= 1
            k += 1
        i = k


def compare_quote(quote, cite, th_books, anchor, refs, skipped):
    """Compare one quotation with its cited verses in the labelled version."""
    found = cites(cite, TH_CITE, th_books)
    if not found or found[0][1] is None or found[0][3] is None or isinstance(found[0][3], tuple):
        return
    name, code, ch, vv, label, raw = found[0]
    label = label or "THSV"
    verses = load_version(label, code)
    if verses is None:
        skipped.append(f"{raw} (not on disk)")
        return
    texts = [verses.get((ch, v)) for v in sorted(vv)]
    if any(t is None for t in texts):
        skipped.append(f"{raw} (verse not found in {label})")
        return
    expected = STRIP.sub("", "".join(texts))
    quote = TYPST_FN.sub("", quote)
    parts = [STRIP.sub("", p) for p in ELLIPSIS.split(quote) if STRIP.sub("", p)]
    pos, ok = 0, True
    for part in parts:
        i = expected.find(part, pos)
        if i < 0:
            ok = False
            break
        pos = i + len(part)
    if ok:
        return
    shown = " ".join(texts)
    refs.append(f"{{SC {anchor}}} REF quote: the quotation cited \"{raw}\" differs from {label}, which reads: {shown[:300]}")


def compare_paragraph(body, th_books, anchor, refs, skipped):
    """Pair each citation parenthesis with the quotations before it, in order."""
    pos = 0
    for m in CITE_PAREN.finditer(body):
        quotes = QUOTE.findall(strip_footnotes(body[pos:m.start()]))
        cites_ = [c.strip() for c in m.group(1).split(";")]
        pos = m.end()
        if not quotes:
            continue
        if len(quotes) == len(cites_):
            for q, c in zip(quotes, cites_):
                compare_quote(q, c, th_books, anchor, refs, skipped)
        elif len(cites_) == 1:
            compare_quote(quotes[-1], cites_[0], th_books, anchor, refs, skipped)
        else:
            skipped.append(f"({m.group(1)[:60]}) ({len(quotes)} quotations, {len(cites_)} citations)")


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
    refs, notes, skipped = [], [], []
    th_all = {p.anchor: cites(mask_markers(p.text), TH_CITE, th_books) for p in paras}
    order = [p.anchor for p in paras]

    def union(found, code, ch):
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
        body = mask_markers(p.text)
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
                notes.append(f"{{SC {p.anchor}}} NOTE extra: \"{raw}\" — the English paragraph does not cite {code} {ch}; translator's own apparatus")
                continue
            th_vs, th_loose = union(th, code, ch)
            if en_vs and th_vs and not en_loose and not th_loose and th_vs != en_vs:
                if th_vs > en_vs:
                    notes.append(f"{{SC {p.anchor}}} NOTE extra-verses: TH cites {code} {ch}{fmt_vv(th_vs)} — EN cites {code} {ch}{fmt_vv(en_vs)}")
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
        before = len(skipped)
        compare_paragraph(body, th_books, p.anchor, refs, skipped)
        skipped[before:] = [f"{{SC {p.anchor}}} {s}" for s in skipped[before:]]

    if skipped:
        notes.append("NOTE quotations not compared: " + "; ".join(skipped))
    for line in refs + notes:
        print(line)
    rel = chapter.resolve().relative_to(ROOT)
    n = sum(1 for p in paras if in_range(p.anchor, first, last))
    print(f"# {rel}: {len(refs)} REF finding(s), {len(notes)} note(s) in {n} paragraph(s)"
          + ("" if bounds else "; no WEB text in the Bible corpus, so chapter and verse bounds were not checked"))
    return 1 if refs else 0


if __name__ == "__main__":
    sys.exit(main())
