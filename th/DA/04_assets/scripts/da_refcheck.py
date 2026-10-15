#!/usr/bin/env python3
"""Scripture-citation check for a DA Thai chapter. Reads only; writes nothing.

    python3 th/DA/04_assets/scripts/da_refcheck.py --chapter 12
    python3 th/DA/04_assets/scripts/da_refcheck.py --chapter 12 --range 105.1 109.2
    python3 th/DA/04_assets/scripts/da_refcheck.py --chapter 12 --file PATH

For every paragraph in range, every citation in the Thai (inline, in a
parenthesis, inside a #footnote, or hidden in a /* */ comment) is set beside
every citation in the English paragraph of the same anchor, and a quotation
followed by its citation is compared word for word with the cited version from
the offline Bible corpus, all ten Thai versions and every book (path in
da_common.py). Chapter and verse bounds come from the WEB text. A chapter-only
citation after a semicolon takes the book cited before it. English tails such
as "R. V." and "margin" are ignored. The based-on passage of the chapter comes
from the English header; the verse picks of pass 1, when
~/claude-sandbox/da-audit/DANN-verses.tsv exists, are cross-checked.

    REF   a finding that takes a marker: a book name not in th_books.txt, a
          chapter or verse beyond the book, an unknown version label, a
          citation the English has and the Thai lacks, the same chapter cited
          with fewer verses than the English, a quotation that differs from
          its version (the version's text is printed), a quotation from the
          based-on passage with neither a printed nor a hidden citation
          (uncited), a hidden citation outside the based-on passage
          (hidden-outside), a hidden citation with a label other than THSV, or
          a verse pick of pass 1 whose paragraph carries no citation of it.
    NOTE  not a marker: a citation the Thai carries beyond the English (DA 3.C
          allows it), extra verses, a THSV quotation from the based-on passage
          with a printed citation (DA 3.D wants it hidden), a quotation that
          could not be compared.

Exit status 1 when any REF line was printed. Chapter 0 is the preface.
"""
import argparse
import re
import sys
from pathlib import Path

from da_common import (chapter_path, source_path, parse_thai, parse_english, english_words,
                       mask_markers, in_range, ROOT, load_books, load_bounds, load_version,
                       based_on, in_based_on, HIDDEN_CITE, KNOWN_LABELS, DEFAULT_VERSION, VERSIONS,
                       load_verse_picks, parse_ref_code)

THAI = "฀-๿"
VERSES = r"\d+(?:\s*[-–]\s*\d+)?(?:,\s*\d+(?:\s*[-–]\s*\d+)?)*"
TH_CITE = re.compile(
    rf"(?P<book>(?:[1-3]\s)?[{THAI}]+)\s+(?P<ch>\d+)(?![{THAI}\d])(?![\s]*[{THAI}])(?::(?P<vv>{VERSES}))?"
    rf"(?:\s*[-–]\s*(?P<ch2>\d+):(?P<v2>\d+))?(?:\s+(?P<label>[A-Z][A-Z0-9-]+))?")
EN_CITE = re.compile(
    r"(?P<book>(?:[1-3]\s)?[A-Z][a-z]+(?:\s(?:of\s)?[A-Z][a-z]+)?)\s+(?P<ch>\d+)(?::(?P<vv>" + VERSES + r"))?"
    r"(?:\s*[-–]\s*(?P<ch2>\d+):(?P<v2>\d+))?")
EN_TAIL = re.compile(r",?\s*(?:A\.\s?R\.\s?V\.|R\.\s?V\.|margin|A\.\s?V\.)")
ONE_CHAPTER = {"OBA", "PHM", "2JN", "3JN", "JUD"}
TH_BOOK = re.compile(rf"(?:[1-3]\s)?[{THAI}]+(?=\s+\d+)")
EN_BOOK = re.compile(r"(?:[1-3]\s)?[A-Z][a-z]+(?:\s(?:of\s)?[A-Z][a-z]+)?(?=\s+\d+)")
CONT_CITE = re.compile(r";\s*(?=\d+:\d)")
STRIP = re.compile(r"[\s​‌‍﻿ “”‘’\"'.,;:!?()\[\]<>…\-–—]")
ELLIPSIS = re.compile(r"…|\.\.\.|\. \. \.")
# Typst function markup inside a quotation, as "#italic[", is not Scripture.
TYPST_FN = re.compile(r"#[A-Za-z_][\w.]*(?:\([^()]*\))?\[")
QUOTE = re.compile(r"“([^“”]{12,})”")
# A citation parenthesis "(ยอห์น 3:16 TNCV)" or a hidden citation "/*ยอห์น 3:16*/".
CITE_SLOT = re.compile(r"\(([^()]*\d+:\d+[^()]*)\)|/\*\s*([^*]*?\d+(?::[\d,\s–-]+)?(?:\s+[A-Z][A-Z0-9-]+)?)\s*\*/")
FOOTNOTE_OPEN = "#footnote["


def expand(vv):
    out = set()
    for part in re.split(r",\s*", vv):
        if re.search(r"[-–]", part):
            lo, hi = re.split(r"\s*[-–]\s*", part)
            out.update(range(int(lo), int(hi) + 1))
        else:
            out.add(int(part))
    return out


def carry_books(text, book_re):
    """A chapter-only citation after a semicolon takes the book cited before it:
    "(ยอห์น 5:19 TNCV; 14:10 THSV)" is read as ยอห์น 14:10 THSV and the English
    "John 14:17; 16:7" as John 16:7, so its label and verses are checked."""
    def fill(m):
        last = None
        for b in book_re.finditer(text, 0, m.start()):
            last = b
        return f"; {last.group(0)} " if last else m.group(0)
    return CONT_CITE.sub(fill, text)


def cites(text, regex, books):
    """Every citation in text as (name, code_or_None, chapter, verses_or_None, label, raw)."""
    text = carry_books(text, TH_BOOK if regex is TH_CITE else EN_BOOK)
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


def strip_footnotes(text):
    """Remove every #footnote[...] call, bracket-matched."""
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


def quote_matches(quote, label, code, ch, vv):
    """True, False, or None when the version or a verse is not on disk."""
    verses = load_version(label, code)
    if verses is None:
        return None
    texts = [verses.get((ch, v)) for v in sorted(vv)]
    if any(t is None for t in texts):
        return None
    expected = STRIP.sub("", "".join(texts))
    quote = TYPST_FN.sub("", quote)
    parts = [STRIP.sub("", p) for p in ELLIPSIS.split(quote) if STRIP.sub("", p)]
    pos = 0
    for part in parts:
        i = expected.find(part, pos)
        if i < 0:
            return False
        pos = i + len(part)
    return True


def compare_quote(quote, cite, hidden, th_books, anchor, refs, notes, skipped, basedon):
    """Compare one quotation with its cited verses in the labelled version and
    apply the DA rules on hidden and printed citations."""
    found = cites(cite, TH_CITE, th_books)
    if not found or found[0][1] is None or found[0][3] is None or isinstance(found[0][3], tuple):
        return
    name, code, ch, vv, label, raw = found[0]
    label = label or DEFAULT_VERSION
    inside = all(in_based_on(basedon, code, ch, v) for v in vv) if basedon else False
    if hidden and not inside:
        refs.append(f"{{DA {anchor}}} REF hidden-outside: the hidden citation /*{raw}*/ is not in the chapter's based-on passage; DA 3.D hides only based-on THSV quotations")
    if hidden and label != DEFAULT_VERSION:
        refs.append(f"{{DA {anchor}}} REF hidden-label: /*{raw}*/ carries {label}; a quotation in any version but THSV is cited and labelled in print")
    if not hidden and inside and label == DEFAULT_VERSION:
        notes.append(f"{{DA {anchor}}} NOTE based-on-cited: \"{raw}\" prints a citation for a THSV quotation from the based-on passage; DA 3.D hides it as /*{raw}*/")
    ok = quote_matches(quote, label, code, ch, vv)
    if ok is None:
        verses = load_version(label, code)
        skipped.append(f"{raw} ({'version not on disk' if verses is None else 'verse not found in ' + label})")
        return
    if ok:
        return
    verses = load_version(label, code)
    shown = " ".join(verses.get((ch, v), "") for v in sorted(vv))
    refs.append(f"{{DA {anchor}}} REF quote: the quotation cited \"{raw}\" differs from {label}, which reads: {shown[:300]}")


def uncited_quotes(quotes, th_books, anchor, refs, basedon):
    """A quotation with no citation slot after it: REF uncited when it matches a
    verse of the based-on passage in any version; otherwise it is speech, not Scripture."""
    for q in quotes:
        hit = None
        for code, ch, vv in basedon:
            verses_all = vv if vv is not None else None
            for label in VERSIONS:
                verses = load_version(label, code)
                if not verses:
                    continue
                for (c, v), t in verses.items():
                    if c != ch or (verses_all is not None and v not in verses_all):
                        continue
                    if quote_matches(q, label, code, ch, {v}):
                        hit = (label, code, ch, v)
                        break
                if hit:
                    break
            if hit:
                break
        if hit:
            label, code, ch, v = hit
            refs.append(f"{{DA {anchor}}} REF uncited: the quotation “{q[:60]}…” matches {label} {code} {ch}:{v} of the based-on passage and carries no citation, printed or hidden")


def compare_paragraph(body, th_books, anchor, refs, notes, skipped, basedon):
    """Pair each citation slot, printed or hidden, with the quotations before it, in order."""
    pos = 0
    text = strip_footnotes(body)
    for m in CITE_SLOT.finditer(text):
        hidden = m.group(2) is not None
        inner = m.group(1) if m.group(1) is not None else m.group(2)
        quotes = QUOTE.findall(text[pos:m.start()])
        cites_ = [c.strip() for c in carry_books(inner, TH_BOOK).split(";")]
        pos = m.end()
        if not quotes:
            continue
        if len(quotes) == len(cites_):
            for q, c in zip(quotes, cites_):
                compare_quote(q, c, hidden, th_books, anchor, refs, notes, skipped, basedon)
        elif len(cites_) == 1:
            compare_quote(quotes[-1], cites_[0], hidden, th_books, anchor, refs, notes, skipped, basedon)
            uncited_quotes(quotes[:-1], th_books, anchor, refs, basedon)
        else:
            skipped.append(f"({inner[:60]}) ({len(quotes)} quotations, {len(cites_)} citations)")
    uncited_quotes(QUOTE.findall(text[pos:]), th_books, anchor, refs, basedon)


def check_picks(nn, th_all, hidden_all, refs, notes, in_scope):
    """Each verse pick of pass 1 should be cited, printed or hidden, in its paragraph."""
    for row in load_verse_picks(nn):
        anchor = row.get("anchor", "")
        if not anchor or not in_scope(anchor):
            continue
        parsed = parse_ref_code(row.get("ref", ""))
        if not parsed:
            continue
        code, ch, vv = parsed
        cited = any(t[1] == code and t[2] == ch for t in th_all.get(anchor, []) + hidden_all.get(anchor, []))
        if not cited and row.get("kind", "quotation") == "quotation":
            refs.append(f"{{DA {anchor}}} REF pick-uncited: pass 1 picked {row['ref']} {row.get('version', '')} for “{row.get('english', '')[:50]}” and the paragraph cites no {code} {ch}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--chapter", type=int, required=True, help="chapter number; 0 is the preface")
    ap.add_argument("--file", help="a chapter file to check in place of the chapter's own file")
    ap.add_argument("--range", nargs=2, metavar=("FIRST", "LAST"))
    a = ap.parse_args()
    first, last = a.range if a.range else (None, None)
    th_books, en_books = load_books()
    bounds = load_bounds()
    chapter = Path(a.file) if a.file else chapter_path(a.chapter)
    source = source_path(a.chapter)
    basedon = based_on(a.chapter)
    _, paras = parse_thai(chapter.read_text(encoding="utf-8"))
    english = parse_english(source.read_text(encoding="utf-8"))
    refs, notes, skipped = [], [], []
    th_all = {p.anchor: cites(HIDDEN_CITE.sub(" ", mask_markers(p.text)), TH_CITE, th_books) for p in paras}
    hidden_all = {p.anchor: [c for m in HIDDEN_CITE.finditer(mask_markers(p.text)) for c in cites(m.group("cite"), TH_CITE, th_books)] for p in paras}
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
        th = th_all[p.anchor] + hidden_all[p.anchor]
        en = cites(EN_TAIL.sub("", english_words(english.get(p.anchor, ""))), EN_CITE, en_books)
        if p.anchor not in english:
            refs.append(f"{{DA {p.anchor}}} REF align: no English paragraph carries this anchor")
        seen_pairs = set()
        for name, code, ch, vv, label, raw in th:
            if code is None:
                refs.append(f"{{DA {p.anchor}}} REF unknown-book: \"{raw}\" — {name} is not in th_books.txt")
                continue
            if label and label not in KNOWN_LABELS:
                refs.append(f"{{DA {p.anchor}}} REF label: \"{raw}\" — {label} is not a known version label")
            if label == DEFAULT_VERSION:
                notes.append(f"{{DA {p.anchor}}} NOTE thsv-label: \"{raw}\" — THSV is the default and carries no label (DA 3.B)")
            b = bounds.get(code)
            if b:
                if ch not in b:
                    refs.append(f"{{DA {p.anchor}}} REF bounds: \"{raw}\" — {code} has {max(b)} chapters")
                elif vv and not isinstance(vv, tuple) and max(vv) > b[ch]:
                    refs.append(f"{{DA {p.anchor}}} REF bounds: \"{raw}\" — {code} {ch} has {b[ch]} verses")
            if (code, ch) in seen_pairs:
                continue
            seen_pairs.add((code, ch))
            en_vs, en_loose = union(en, code, ch)
            if not en_vs and not en_loose:
                notes.append(f"{{DA {p.anchor}}} NOTE extra: \"{raw}\" — the English paragraph does not cite {code} {ch}; a citation the English leaves out (DA 3.C) or the translator's own apparatus")
                continue
            th_vs, th_loose = union(th, code, ch)
            if en_vs and th_vs and not en_loose and not th_loose and th_vs != en_vs:
                if th_vs > en_vs:
                    notes.append(f"{{DA {p.anchor}}} NOTE extra-verses: TH cites {code} {ch}{fmt_vv(th_vs)} — EN cites {code} {ch}{fmt_vv(en_vs)}")
                else:
                    refs.append(f"{{DA {p.anchor}}} REF verses: TH cites {code} {ch}{fmt_vv(th_vs)} — EN cites {code} {ch}{fmt_vv(en_vs)}")
        for name, code, ch, vv, label, raw in en:
            if any(t[1] == code and t[2] == ch for t in th):
                continue
            near = [order[j] for j in (i - 1, i + 1) if 0 <= j < len(order)
                    and any(t[1] == code and t[2] == ch for t in th_all[order[j]] + hidden_all[order[j]])]
            if near:
                notes.append(f"{{DA {p.anchor}}} NOTE moved: EN \"{raw}\" is cited in the Thai at {{DA {near[0]}}} instead")
            else:
                refs.append(f"{{DA {p.anchor}}} REF missing: EN \"{raw}\" — no Thai citation of {code} {ch} in the paragraph")
        before = len(skipped)
        compare_paragraph(body, th_books, p.anchor, refs, notes, skipped, basedon)
        skipped[before:] = [f"{{DA {p.anchor}}} {s}" for s in skipped[before:]]

    check_picks(a.chapter, th_all, hidden_all, refs, notes, lambda anc: in_range(anc, first, last))

    if skipped:
        notes.append("NOTE quotations not compared: " + "; ".join(skipped))
    for line in refs + notes:
        print(line)
    try:
        rel = chapter.resolve().relative_to(ROOT)
    except ValueError:
        rel = chapter
    n = sum(1 for p in paras if in_range(p.anchor, first, last))
    print(f"# {rel}: {len(refs)} REF finding(s), {len(notes)} note(s) in {n} paragraph(s)"
          + (f"; based on {', '.join(f'{c} {ch}' for c, ch, _ in basedon)}" if basedon else "; no based-on passage")
          + ("" if bounds else "; no WEB text in the Bible corpus, so chapter and verse bounds were not checked"))
    return 1 if refs else 0


if __name__ == "__main__":
    sys.exit(main())
