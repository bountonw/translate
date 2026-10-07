#!/usr/bin/env python3
"""Mechanical sweep over a DA Thai chapter. Reads only; writes nothing.

    python3 th/DA/04_assets/scripts/da_punctcheck.py --chapter 12
    python3 th/DA/04_assets/scripts/da_punctcheck.py --chapter 12 --range 105.1 109.2
    python3 th/DA/04_assets/scripts/da_punctcheck.py --file PATH
    python3 th/DA/04_assets/scripts/da_punctcheck.py --list-checks

Every finding line is a defect, because every check here is mechanical; a NOTE
line is information and takes no marker. Intact [[ ]] markers are replaced by
their old side before checking, so a marker's English note is never flagged
while the paragraph around it still is. Exit status 1 when any finding was
printed. Chapter 0 is the preface.

DA conventions the sweep knows: a Typst block comment holding only a citation,
as /*ยอห์น 3:16*/, is the hidden citation of DA 3.D and prints as NOTE
hidden-citation, not as a typst-comment finding; a "=== " line between the
anchor comment and the prose is a subtitle; an editor's choice, ((A/B)) or
((original:A/B)), prints as NOTE editor-choice; a question or exclamation mark
outside direct speech prints as NOTE mark-narration for the editor (DA 3.G);
the #chapter header's basedon string is checked against DA 3.F.

No Lao or GC punctuation rule is applied: Thai sentences carry no final period,
and spaces mark phrase boundaries.
"""
import argparse
import re
import sys
import unicodedata

from pathlib import Path

from da_common import (chapter_path, parse_thai, mask_markers, in_range, anchor_key, load_books,
                       MARKER, OPEN_MARKER, ROOT, GLOSSARY, HIDDEN_CITE, EDITOR_CHOICE, SUBTITLE_LINE,
                       TAG_ANCHOR)

THAI_DIGIT = re.compile(r"[๐-๙]")
LAO_DIGIT = re.compile(r"[໐-໙]")
INVISIBLE = {
    "​": "ZERO WIDTH SPACE U+200B",
    "‌": "ZERO WIDTH NON-JOINER U+200C",
    "‍": "ZERO WIDTH JOINER U+200D",
    "⁠": "WORD JOINER U+2060",
    "﻿": "BYTE ORDER MARK U+FEFF",
    "­": "SOFT HYPHEN U+00AD",
    " ": "NO-BREAK SPACE U+00A0",
    " ": "NARROW NO-BREAK SPACE U+202F",
}
# Mai taikhu takes no tone mark; a tone mark follows its vowel, never precedes it.
MARK_ORDER = re.compile("็[่-๋]|[่-๋][ัิ-ฺ็]|ำ[่-๋]")
DOUBLE_SPACE = re.compile(r"(?<=\S)  +(?=\S)")
CITATION_PAREN = re.compile(r"\([^()]*\d+:\d+[^()]*\)")
FOOTNOTE = re.compile(r"#footnote\[(?:[^\[\]]|\[[^\]]*\])*\]")
EGW_TAG = re.compile(r"#EGW\[[^\]]*\]")
TYPST_CALL = re.compile(r"#[A-Za-z][A-Za-z0-9_-]*")
VERSION_LABEL = re.compile(r"\b(?:THSV|TNCV|TKJV|TH1940|TH1971|THA-ERV|ERV|TCV|NTV|TCL|TFB|KJV|RV|NIV|ESV)\b")
LATIN = re.compile(r"[A-Za-z]{2,}")
SPACE_BEFORE_CLOSE = re.compile(r" [”)\]]")
BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.S)
LINE_COMMENT = re.compile(r"(?<!:)//.*$", re.M)
ORIGINAL_TAG = re.compile(r"(?<=\(\()original:")
BARE_CITATION = re.compile(r"(?:[1-3]\s)?[฀-๿]+\s\d+:\d+")
QUOTED = re.compile(r"“[^“”]*”|‘[^‘’]*’")
NARRATION_MARK = re.compile(r"[?!]")
BASEDON_HEAD = re.compile(r'basedon:\s*"([^"]*)"')


def load_spelling(path=GLOSSARY):
    """(incorrect, correct) pairs from the glossary's spelling table.

    The table sits under the heading "## 3. Spelling" with the columns
    Word | Correct | Incorrect | Notes; "/" or ", " in the Incorrect cell
    separates several wrong forms. No file or no table means no spelling check.
    """
    pairs = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return pairs
    inside = False
    for line in lines:
        if line.startswith("## "):
            inside = "Spelling" in line
            continue
        if not inside or not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3 or cells[1] in ("Correct", "") or set(cells[1]) <= {"-"}:
            continue
        for wrong in re.split(r"/|,\s*", cells[2]):
            wrong = wrong.strip()
            if wrong:
                pairs.append((wrong, cells[1]))
    return pairs


SPELLING = load_spelling()

CHECKS = {
    "thai-digit": "a Thai digit U+0E50–U+0E59; Western digits only",
    "lao-digit": "a Lao digit U+0ED0–U+0ED9",
    "invisible": "a zero-width, joiner, BOM, soft-hyphen or no-break character",
    "double-space": "two or more spaces inside a paragraph",
    "quote-balance": "double quotation marks that do not pair within the paragraph",
    "single-quote-balance": "single quotation marks that do not pair within the paragraph",
    "space-before-close": "a space before a closing quotation mark, parenthesis or bracket",
    "anchor-tag": "the #EGW tag's anchor differs from the paragraph's comment anchor, or is missing or doubled",
    "anchor-order": "an anchor comment that does not ascend from the previous one",
    "latin": "Latin letters in the body outside a citation, a footnote, Typst markup or an editor's choice",
    "marker-open": "a [[ that does not open an intact marker",
    "combining-order": "a Thai combining mark with nothing to combine with",
    "mark-order": "a tone mark after mai taikhu (็่ ็้ ็๊ ็๋), or a tone mark typed before its vowel, or after sara am (ำ่)",
    "typst-comment": "a /* */ or // comment inside a paragraph that is not a hidden citation: a working note to resolve before print",
    "spelling": "a form the glossary's spelling table lists as incorrect; the finding names the correct form",
    "citation-bare": "a chapter:verse citation outside a parenthesis, a footnote and a hidden comment",
    "subtitle-position": "a === subtitle line that is not between the anchor comment and the prose",
    "basedon-format": "the #chapter basedon string breaks DA 3.F: บทที่ only for whole chapters, a space after the book name, an unspaced en dash for a range, และ for two chapters, \"; \" between other parts",
    "NOTE hidden-citation": "a citation inside /* */ (DA 3.D); information, no marker",
    "NOTE editor-choice": "an editor's choice ((A/B)) standing in the text; information, no marker",
    "NOTE mark-narration": "a ? or ! outside direct speech; the editor decides (DA 3.G)",
}


def strip_markup(body):
    body = FOOTNOTE.sub(" ", body)
    body = EGW_TAG.sub(" ", body)
    body = CITATION_PAREN.sub(" ", body)
    body = TYPST_CALL.sub(" ", body)
    body = VERSION_LABEL.sub(" ", body)
    body = ORIGINAL_TAG.sub("", body)
    return body


def check_para(p, out, note):
    raw = p.text
    body = mask_markers(raw)

    # Marker integrity is checked on the raw text, before masking.
    intact = [m.span() for m in MARKER.finditer(raw)]
    for m in OPEN_MARKER.finditer(raw):
        if not any(s <= m.start() < e for s, e in intact):
            out(p, "marker-open", raw[m.start():m.start() + 60])

    for m in THAI_DIGIT.finditer(body):
        out(p, "thai-digit", context(body, m.start()))
    for m in LAO_DIGIT.finditer(body):
        out(p, "lao-digit", context(body, m.start()))
    for ch, name in INVISIBLE.items():
        for i in [i for i, c in enumerate(body) if c == ch]:
            out(p, "invisible", f"{name} at: {context(body, i)}")
    for m in DOUBLE_SPACE.finditer(body):
        out(p, "double-space", context(body, m.start()))
    for m in SPACE_BEFORE_CLOSE.finditer(body):
        out(p, "space-before-close", context(body, m.start()))

    hidden = [m for m in HIDDEN_CITE.finditer(body)]
    for m in hidden:
        note(p, "hidden-citation", m.group(0))
    no_hidden = HIDDEN_CITE.sub(" ", body)
    bare = CITATION_PAREN.sub(" ", FOOTNOTE.sub(" ", no_hidden))
    for m in BARE_CITATION.finditer(bare):
        out(p, "citation-bare", context(bare, m.start()))

    opens, closes = body.count("“"), body.count("”")
    if opens != closes:
        out(p, "quote-balance", f"{opens} opening and {closes} closing double quotation marks")
    sopen, sclose = body.count("‘"), body.count("’")
    if sopen != sclose:
        out(p, "single-quote-balance", f"{sopen} opening and {sclose} closing single quotation marks")

    # A Thai combining mark (vowel above or below, tone mark) must follow a base letter.
    prev = " "
    for i, c in enumerate(body):
        if unicodedata.category(c) == "Mn" and "฀" <= c <= "๿":
            if not ("฀" <= prev <= "๿"):
                out(p, "combining-order", f"{unicodedata.name(c, hex(ord(c)))} at: {context(body, i)}")
        prev = c
    for m in MARK_ORDER.finditer(body):
        out(p, "mark-order", context(body, m.start()))

    for wrong, right in SPELLING:
        for m in re.finditer(re.escape(wrong), body):
            out(p, "spelling", f"{wrong} -> {right}: {context(body, m.start())}")

    for m in BLOCK_COMMENT.finditer(no_hidden):
        out(p, "typst-comment", m.group(0)[:80])
    for m in LINE_COMMENT.finditer(no_hidden):
        out(p, "typst-comment", m.group(0)[:80])
    stripped = strip_markup(LINE_COMMENT.sub(" ", BLOCK_COMMENT.sub(" ", no_hidden)))
    latin_src = EDITOR_CHOICE.sub(lambda m: " " * len(m.group(0)), stripped)  # Latin inside ((...)) is ignored
    for m in LATIN.finditer(latin_src):
        out(p, "latin", context(stripped, m.start()))

    # Question and exclamation marks outside direct speech, for the editor (DA 3.G).
    narration = QUOTED.sub(lambda m: " " * len(m.group(0)), FOOTNOTE.sub(" ", LINE_COMMENT.sub(" ", BLOCK_COMMENT.sub(" ", body))))
    narration = EDITOR_CHOICE.sub(lambda m: " " * len(m.group(0)), narration)
    for m in NARRATION_MARK.finditer(narration):
        note(p, "mark-narration", context(narration, m.start()))

    # A subtitle line sits between the anchor comment and the prose, before any other text.
    lines = [l for l in p.lines]
    seen_prose = False
    for l in lines:
        if SUBTITLE_LINE.match(l):
            if seen_prose:
                out(p, "subtitle-position", l[:80])
        elif l.strip():
            seen_prose = True

    if not p.tags:
        out(p, "anchor-tag", "no #EGW tag in the paragraph")
    elif len(p.tags) > 1:
        out(p, "anchor-tag", f"{len(p.tags)} #EGW tags: {', '.join(p.tags)}")
    elif p.tags[0] != p.anchor:
        out(p, "anchor-tag", f"comment {{DA {p.anchor}}} but tag {{DA {p.tags[0]}}}")


def check_basedon(head_lines, th_books):
    """Findings on the #chapter basedon string against DA 3.F; [] when clean or absent."""
    m = BASEDON_HEAD.search("\n".join(head_lines))
    if not m or not m.group(1).strip():
        return []
    s = m.group(1).strip()
    found = []
    if "-" in s:
        found.append("a hyphen; a range takes an en dash (–)")
    if re.search(r"\s–|–\s", s):
        found.append("a spaced en dash; a range takes an unspaced en dash")
    if re.search(r";\S", s):
        found.append('a semicolon without a following space; parts are joined by "; "')
    # Parts are joined by "; ". A part opening with a book name starts a book
    # segment, as "อพยพ บทที่ 25–40"; a part opening with a digit continues the
    # book before it, as the "6; 7" of "โยชูวา 5:13–15; 6; 7". บทที่ is written
    # once, after the book name, and only when every part of the string is a
    # whole chapter; และ joins two whole chapters; a comma separates verses.
    parts = [x.strip() for x in s.split(";")]
    versed_any = ":" in s
    for x in parts:
        bm = re.match(r"^((?:[1-3] )?[฀-๿]+)(\s?)(.*)$", x)
        if bm:
            book, space, rest = bm.groups()
            if rest and not space:
                found.append(f'"{x}": no space after the book name')
            if book not in th_books:
                found.append(f'"{x}": {book} is not a book name in th_books.txt')
            if versed_any and "บทที่" in x:
                found.append(f'"{x}": บทที่ is written only when every part is a whole chapter')
            if not versed_any and "บทที่" not in x:
                found.append(f'"{x}": a whole-chapter part without บทที่')
        elif re.match(r"^\d", x):
            if "บทที่" in x:
                found.append(f'"{x}": บทที่ is written once, after the book name')
        else:
            found.append(f'"{x}" opens with neither a book name nor a chapter number')
        if not versed_any and "," in x:
            found.append(f'"{x}": two chapters take และ, more take "; "')
        if versed_any and "และ" in x:
            found.append(f'"{x}": และ joins whole chapters only')
    return [f"basedon \"{s}\": {f}" for f in found]


def context(text, i, width=28):
    s = max(0, i - width)
    e = min(len(text), i + width)
    return text[s:e].replace("\n", " ")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--chapter", type=int, help="chapter number; 0 is the preface")
    ap.add_argument("--file", help="a chapter file, instead of --chapter")
    ap.add_argument("--range", nargs=2, metavar=("FIRST", "LAST"), help="anchors, e.g. 105.1 109.2")
    ap.add_argument("--list-checks", action="store_true")
    a = ap.parse_args()
    if a.list_checks:
        for k, v in CHECKS.items():
            print(f"{k:22} {v}")
        return 0
    if a.file:
        path = Path(a.file)
    elif a.chapter is not None:
        path = chapter_path(a.chapter)
    else:
        ap.error("--chapter NN or --file PATH")
    first, last = a.range if a.range else (None, None)
    text = path.read_text(encoding="utf-8")
    head, paras = parse_thai(text)
    findings, notes = [], []

    def out(p, check, what):
        findings.append(f"{{DA {p.anchor}}} {check}: {what}")

    def note(p, check, what):
        notes.append(f"{{DA {p.anchor}}} NOTE {check}: {what}")

    th_books, _ = load_books()
    for f in check_basedon(head, th_books):
        findings.append(f"header basedon-format: {f}")

    prev = None
    for p in paras:
        if not in_range(p.anchor, first, last):
            prev = p.anchor
            continue
        check_para(p, out, note)
        if prev and anchor_key(p.anchor) <= anchor_key(prev):
            out(p, "anchor-order", f"follows {{DA {prev}}}")
        prev = p.anchor
        for m in EDITOR_CHOICE.finditer(p.text):
            note(p, "editor-choice", m.group(0)[:80])

    if not paras:
        print(f"{path}: no anchor comments found; is this a chapter file, or a chapter not yet drafted?")
        return 1
    for n in notes:
        print(n)
    for f in findings:
        print(f)
    try:
        rel = path.resolve().relative_to(ROOT)
    except ValueError:
        rel = path
    print(f"# {rel}: {len(findings)} finding(s), {len(notes)} note(s) in {sum(1 for p in paras if in_range(p.anchor, first, last))} paragraph(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
