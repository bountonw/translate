#!/usr/bin/env python3
"""Glossary sweep for one SC Thai chapter: the qa2 candidate file. Reads only.

    python3 th/SC/04_assets/scripts/sc_termcheck.py --chapter 01
    python3 th/SC/04_assets/scripts/sc_termcheck.py --chapter 01 --range 9.1 12.2 --out PATH

For every paragraph, finds each glossary head of sections 1 and 2 of
th/assets/translation_profile/thai-glossary.txt that the English paragraph
carries, and writes one line per head where:

    ABSENT  none of the Thai forms of any row of that head is in the Thai paragraph
    SENSE   the head has several rows, one per sense, and the Thai uses a form of
            one of them, so the sense is to be checked against the English

Rows of every tag are swept, [CHECK], [FLAG] and bare alike; the tag is
printed. Rows whose English differ only by number, as trial and trials, are one
head. A row whose Thai cell is a parenthesised instruction such as (free choice)
has no forms and is skipped. Spelling rows belong to sc_punctcheck.py. The
output is a shortlist for the qa2 auditor, who judges each line in its
sentence; nothing here is a finding. Writes
~/claude-sandbox/sc-audit/scNN-term-candidates-qa2.md unless --out is given.
"""
import argparse
import re
import sys
import unicodedata
from collections import OrderedDict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sc_common import (ROOT, SANDBOX, chapter_path, source_path, parse_thai,  # noqa: E402
                       parse_english, mask_markers, in_range)

GLOSSARY = ROOT / "th" / "assets" / "translation_profile" / "thai-glossary.txt"
THAI = re.compile(r"[฀-๿]")
PAREN = re.compile(r"\([^)]*\)")
SPLIT_EN = re.compile(r",\s*(?![^()]*\))")
ARTICLE = re.compile(r"^(?:the|a|an)\s+", re.I)
STOP = {"the", "a", "an", "his", "her", "its", "their", "our", "your", "my", "of", "and", "great"}
DIVINE = {"god", "christ", "jesus", "lord", "him", "his"}
# Heads that collide with a function word: the English must read as the noun.
NOUN_ONLY = {"will": r"(?:the|his|her|our|your|their|my|its|own|human|free|of|a)\s+"}
EXCERPT_PAD = 60


class Row:
    def __init__(self, en, th, notes, line_no):
        self.label = en.strip()
        self.notes = notes.strip()
        self.line_no = line_no
        self.en_variants = []
        for i, part in enumerate(SPLIT_EN.split(en)):
            v = ARTICLE.sub("", PAREN.sub("", part).strip().strip('"“”')).strip()
            if not v or v.lower() in STOP or len(v) < 3:
                continue
            # "in sympathy with God, Christ": a divine name after the comma is
            # part of the phrase, not a head of its own.
            if i > 0 and v.lower() in DIVINE:
                continue
            self.en_variants.append(v)
        self.th_forms = []
        for part in th.split("/"):
            f = PAREN.sub("", part).strip().strip('"“”')
            if f and THAI.search(f):
                self.th_forms.append(f)

    @property
    def tag(self):
        up = self.notes.upper()
        if "[FLAG]" in up:
            return "FLAG"
        if "[CHECK]" in up:
            return "CHECK"
        return "bare"

    @property
    def usable(self):
        return bool(self.en_variants and self.th_forms)


def form_in(form, text):
    """True where the form occurs other than as the tail of a longer divine
    title: บุตรของพระเจ้า inside พระบุตรของพระเจ้า, the Son, is not a site."""
    i = text.find(form)
    while i >= 0:
        if not (form.startswith("บุตร") and text[max(0, i - 3):i] == "พระ"):
            return True
        i = text.find(form, i + 1)
    return False


def parse_glossary(path):
    """Rows of sections 1 and 2; the spelling section is not read."""
    rows, section = [], 0
    for n, line in enumerate(path.read_text(encoding="utf-8").split("\n"), 1):
        s = line.strip()
        if s.startswith("## "):
            section += 1
            continue
        if section > 2 or not s.startswith("|") or re.match(r"^\|[\s:|-]+\|$", s):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 2 or not cells[0] or cells[0].lower() == "english":
            continue
        row = Row(cells[0], cells[1], cells[2] if len(cells) > 2 else "", n)
        if row.usable:
            rows.append(row)
    return rows


def fold(text):
    text = text.replace("’", "'").replace("‘", "'")
    norm = unicodedata.normalize("NFKD", text)
    return "".join(c for c in norm if not unicodedata.combining(c))


def head_key(variant):
    k = fold(variant).lower()
    if len(k) > 4 and k.endswith("s") and not k.endswith("ss"):
        k = k[:-1]
    return k


def en_pattern(variant):
    """Whole words, any inflection of the last word; a head written in capitals,
    as I AM, matches only in capitals; a NOUN_ONLY head needs its determiner."""
    words = fold(variant).split()
    parts = [re.escape(w) for w in words[:-1]]
    last = words[-1]
    if last.endswith("y"):
        tail = f"(?:{re.escape(last)}|{re.escape(last[:-1])}ies)"
    else:
        tail = re.escape(last) + r"(?:s|es|ed|d|ing)?"
    parts.append(tail)
    lead = NOUN_ONLY.get(variant.lower(), "")
    flags = 0 if variant.isupper() else re.I
    return re.compile(r"(?<![A-Za-z])" + lead + r"\s+".join(parts) + r"(?![A-Za-z])", flags)


def group_rows(rows):
    """head key -> {"rows": [Row], "patterns": {variant: regex}}"""
    groups = OrderedDict()
    for row in rows:
        for v in row.en_variants:
            g = groups.setdefault(head_key(v), {"rows": [], "patterns": OrderedDict()})
            if row not in g["rows"]:
                g["rows"].append(row)
            g["patterns"].setdefault(v, en_pattern(v))
    return groups


def excerpt(text, m):
    s, e = m.start(), m.end()
    a, b = max(0, s - EXCERPT_PAD), min(len(text), e + EXCERPT_PAD)
    out = text[a:s] + "**" + text[s:e] + "**" + text[e:b]
    out = " ".join(out.split())
    return ("..." if a > 0 else "") + out + ("..." if b < len(text) else "")


def sweep(en_text, th_text, groups):
    absent, sense = [], []
    for key, g in groups.items():
        match = None
        for pat in g["patterns"].values():
            match = pat.search(en_text)
            if match:
                break
        if not match:
            continue
        present = [(row, f) for row in g["rows"] for f in row.th_forms if form_in(f, th_text)]
        if not present:
            absent.append((g["rows"], excerpt(en_text, match)))
        elif len(g["rows"]) > 1:
            used = OrderedDict()
            for row, f in present:
                used.setdefault(row, f)
            others = [r for r in g["rows"] if r not in used]
            sense.append((used, others, excerpt(en_text, match)))
    return absent, sense


def row_desc(row):
    return f"\"{row.label}\" [{row.tag}] {' / '.join(row.th_forms)}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--chapter", required=True)
    ap.add_argument("--range", nargs=2, metavar=("FIRST", "LAST"))
    ap.add_argument("--out")
    args = ap.parse_args()
    nn = f"{int(args.chapter):02d}"
    first, last = args.range if args.range else (None, None)

    chapter = chapter_path(nn)
    _, paras = parse_thai(chapter.read_text(encoding="utf-8"))
    english = parse_english(source_path(nn).read_text(encoding="utf-8"))
    groups = group_rows(parse_glossary(GLOSSARY))

    out_path = Path(args.out).expanduser() if args.out else SANDBOX / f"sc{nn}-term-candidates-qa2.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [f"# SC{nn} qa2 term candidates — {chapter.relative_to(ROOT)} — shortlist, not findings", ""]
    n_paras = n_absent = n_sense = 0
    by_tag = {"CHECK": 0, "FLAG": 0, "bare": 0}
    for para in paras:
        if not in_range(para.anchor, first, last):
            continue
        en_text = english.get(para.anchor)
        if en_text is None:
            lines += [f"## {{SC {para.anchor}}}", "", "NO ENGLISH PARAGRAPH at this anchor", ""]
            continue
        n_paras += 1
        th_text = mask_markers(para.text)
        absent, sense = sweep(en_text, th_text, groups)
        if not absent and not sense:
            continue
        lines += [f"## {{SC {para.anchor}}}", ""]
        for rows, ex in absent:
            n_absent += 1
            for r in rows:
                by_tag[r.tag] += 1
            lines.append("ABSENT " + "; ".join(row_desc(r) for r in rows) + f" | EN \"{ex}\"")
            lines.append("")
        for used, others, ex in sense:
            n_sense += 1
            has = "; ".join(f"Thai has {f} of \"{r.label}\" [{r.tag}]" for r, f in used.items())
            oth = "; ".join(row_desc(r) for r in others)
            lines.append(f"SENSE {has} | other senses: {oth} | EN \"{ex}\"")
            lines.append("")
    summary = (f"paragraphs swept {n_paras}; ABSENT heads {n_absent} "
               f"(rows: CHECK {by_tag['CHECK']}, FLAG {by_tag['FLAG']}, bare {by_tag['bare']}); SENSE heads {n_sense}")
    lines += ["## Summary", "", summary, ""]
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(summary)
    print(f"written {out_path}")


if __name__ == "__main__":
    main()
