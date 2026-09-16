#!/usr/bin/env python3
"""Mechanical sweep over an SC Thai chapter. Reads only; writes nothing.

    python3 th/SC/04_assets/scripts/sc_punctcheck.py --chapter 12
    python3 th/SC/04_assets/scripts/sc_punctcheck.py --chapter 12 --range 105.1 109.2
    python3 th/SC/04_assets/scripts/sc_punctcheck.py --list-checks

Every line printed is a finding and not a candidate, because every check here
is mechanical. A batch auditor passes --range with its own batch so consecutive
batches do not report the same finding twice. Intact [[ ]] markers are replaced
by their old side before checking, so a marker's English note is never flagged
while the paragraph around it still is. Exit status 1 when anything was found.

No Lao or GC punctuation rule is applied: Thai sentences carry no final period,
questions usually carry no question mark, and spaces mark phrase boundaries.
"""
import argparse
import re
import sys
import unicodedata

from pathlib import Path

from sc_common import (chapter_path, parse_thai, mask_markers, in_range, anchor_key,
                       MARKER, OPEN_MARKER, ROOT)

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
DOUBLE_SPACE = re.compile(r"(?<=\S)  +(?=\S)")
CITATION_PAREN = re.compile(r"\([^()]*\d+:\d+[^()]*\)")
FOOTNOTE = re.compile(r"#footnote\[(?:[^\[\]]|\[[^\]]*\])*\]")
EGW_TAG = re.compile(r"#EGW\[[^\]]*\]")
TYPST_CALL = re.compile(r"#[A-Za-z][A-Za-z0-9_-]*")
VERSION_LABEL = re.compile(r"\b(?:THSV|TNCV|TKJV|TH1940|TH1971|THA-ERV|ERV|TCV|NTV|TFB|KJV|NIV|ESV)\b")
LATIN = re.compile(r"[A-Za-z]{2,}")
SPACE_BEFORE_CLOSE = re.compile(r" [”)\]]")
BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.S)
LINE_COMMENT = re.compile(r"(?<!:)//.*$", re.M)

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
    "latin": "Latin letters in the body outside a citation, a footnote or Typst markup",
    "marker-open": "a [[ that does not open an intact marker",
    "combining-order": "a Thai combining mark with nothing to combine with",
    "typst-comment": "a /* */ or // comment inside a paragraph: a translator's working note that must be resolved before print",
}


def strip_markup(body):
    body = FOOTNOTE.sub(" ", body)
    body = EGW_TAG.sub(" ", body)
    body = CITATION_PAREN.sub(" ", body)
    body = TYPST_CALL.sub(" ", body)
    body = VERSION_LABEL.sub(" ", body)
    return body


def check_para(p, out):
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

    for m in BLOCK_COMMENT.finditer(body):
        out(p, "typst-comment", m.group(0)[:80])
    for m in LINE_COMMENT.finditer(body):
        out(p, "typst-comment", m.group(0)[:80])
    stripped = strip_markup(LINE_COMMENT.sub(" ", BLOCK_COMMENT.sub(" ", body)))
    for m in LATIN.finditer(stripped):
        out(p, "latin", context(stripped, m.start()))

    if not p.tags:
        out(p, "anchor-tag", "no #EGW tag in the paragraph")
    elif len(p.tags) > 1:
        out(p, "anchor-tag", f"{len(p.tags)} #EGW tags: {', '.join(p.tags)}")
    elif p.tags[0] != p.anchor:
        out(p, "anchor-tag", f"comment {{SC {p.anchor}}} but tag {{SC {p.tags[0]}}}")


def context(text, i, width=28):
    s = max(0, i - width)
    e = min(len(text), i + width)
    return text[s:e].replace("\n", " ")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--chapter", type=int)
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
    elif a.chapter:
        path = chapter_path(a.chapter)
    else:
        ap.error("--chapter NN or --file PATH")
    first, last = a.range if a.range else (None, None)
    text = path.read_text(encoding="utf-8")
    head, paras = parse_thai(text)
    findings = []

    def out(p, check, what):
        findings.append(f"{{SC {p.anchor}}} {check}: {what}")

    prev = None
    for p in paras:
        if not in_range(p.anchor, first, last):
            prev = p.anchor
            continue
        check_para(p, out)
        if prev and anchor_key(p.anchor) <= anchor_key(prev):
            out(p, "anchor-order", f"follows {{SC {prev}}}")
        prev = p.anchor

    if not paras:
        print(f"{path}: no anchor comments found; is this a chapter file?")
        return 1
    for f in findings:
        print(f)
    try:
        rel = path.resolve().relative_to(ROOT)
    except ValueError:
        rel = path
    print(f"# {rel}: {len(findings)} finding(s) in {sum(1 for p in paras if in_range(p.anchor, first, last))} paragraph(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
