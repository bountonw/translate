#!/usr/bin/env python3
"""fb_check.py — the mechanical check of one Lao statement of the 28 Fundamental Beliefs (lo/FB/CLAUDE.md 5.A and 6.A).

Usage: python3 fb_check.py --belief 07 [--dry-run] [--file PATH]

The statement file is found in lo/FB/01_raw, 02_edit or 03_public unless --file names it. The checks are:
the file shape (heading "== N — title", the text, a blank line, the reference line); the orthography of
lao-profile.txt section 2 (ພຣະ, ເຊິ່ງ, ຫຼ, ຣາຊ without a linking ະ, the ຳ ligature); the Correct/Incorrect
spelling tables of GC-glossary.txt, taking only the rows whose Incorrect form is a spelling variant of the
Correct form; Lao and Thai digits; Thai letters; invisible characters; straight quotation marks; the en dash
between digits in a range (profile 5.A); spaces around ແລະ; double and trailing spaces; and the reference line
against the English source and the book rows of lao-glossary.txt section 2. A standing [[ marker ends the check.

Every mechanical fix is applied to the file itself, with no marker, and printed as "fixed"; --dry-run prints
the fixes without writing. Fixes are applied in passes until none is left, so two defects in one word are both
fixed. What the script cannot fix (shape, Thai letters, a book without a glossary row, a reference list of a
different length) is printed as "note". Exit status 0 means no note is left; 1 means notes,
or fixes not written because of --dry-run.
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
STAGES = ("01_raw", "02_edit", "03_public")
LAO_GLOSSARY = ROOT / "lo/assets/translation_profile/lao-glossary.txt"
GC_GLOSSARY = ROOT / "lo/GC/04_assets/translation_profile/GC-glossary.txt"

INVISIBLE = {"​": "U+200B zero-width space", "‌": "U+200C zero-width non-joiner",
             "‍": "U+200D zero-width joiner", "﻿": "U+FEFF byte-order mark",
             "­": "U+00AD soft hyphen", "⁠": "U+2060 word joiner"}
LAO_DIGITS = str.maketrans("໐໑໒໓໔໕໖໗໘໙", "0123456789")
THAI_DIGITS = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")
# ພະ before one of these heads is the honorific prefix without its ຣ (profile 2.A); elsewhere ພະ is a syllable.
DIVINE_HEADS = ("ເຈົ້າ", "ອົງ", "ຄຳ", "ທຳ", "ຄຣິ", "ຄລິ", "ວິນຍານ", "ບິດາ", "ບຸດ", "ເຢຊູ", "ຜູ້", "ນິມິດ", "ລັກສະນະ",
                "ຣາຊ", "ລາຊ", "ສັນຍາ", "ບັນຍັດ", "ໄທ", "ພັກ", "ພອນ", "ນາມ", "ກຽດ", "ກາຍ", "ຫັດ", "ບາດ", "ຄຸນ", "ເມດຕາ", "ປະສົງ")
ABBR = {"Gen.": "Genesis", "Exod.": "Exodus", "Ex.": "Exodus", "Lev.": "Leviticus", "Num.": "Numbers", "Deut.": "Deuteronomy",
        "Josh.": "Joshua", "Judg.": "Judges", "Ruth": "Ruth", "1 Sam.": "1 Samuel", "2 Sam.": "2 Samuel",
        "1 Kings": "1 Kings", "2 Kings": "2 Kings", "1 Chron.": "1 Chronicles", "2 Chron.": "2 Chronicles",
        "Ezra": "Ezra", "Neh.": "Nehemiah", "Esther": "Esther", "Job": "Job", "Ps.": "Psalms", "Prov.": "Proverbs",
        "Eccl.": "Ecclesiastes", "Song of Sol.": "Song of Solomon", "Isa.": "Isaiah", "Jer.": "Jeremiah",
        "Lam.": "Lamentations", "Ezek.": "Ezekiel", "Dan.": "Daniel", "Hosea": "Hosea", "Joel": "Joel", "Amos": "Amos",
        "Obad.": "Obadiah", "Jonah": "Jonah", "Mic.": "Micah", "Nahum": "Nahum", "Hab.": "Habakkuk", "Zeph.": "Zephaniah",
        "Haggai": "Haggai", "Hag.": "Haggai", "Zech.": "Zechariah", "Mal.": "Malachi", "Matt.": "Matthew", "Mark": "Mark",
        "Luke": "Luke", "John": "John", "Acts": "Acts", "Rom.": "Romans", "1 Cor.": "1 Corinthians", "2 Cor.": "2 Corinthians",
        "Gal.": "Galatians", "Eph.": "Ephesians", "Phil.": "Philippians", "Col.": "Colossians",
        "1 Thess.": "1 Thessalonians", "2 Thess.": "2 Thessalonians", "1 Tim.": "1 Timothy", "2 Tim.": "2 Timothy",
        "Titus": "Titus", "Philemon": "Philemon", "Heb.": "Hebrews", "James": "James", "1 Peter": "1 Peter",
        "2 Peter": "2 Peter", "1 John": "1 John", "2 John": "2 John", "3 John": "3 John", "Jude": "Jude", "Rev.": "Revelation"}


class Finding:
    """A defect at line[i:j], replaced by new_sub; the marker spans line[a:b]. A note-only finding has i None."""

    def __init__(self, line, note, i=None, j=None, new_sub=None, a=None, b=None):
        self.line, self.note, self.i, self.j, self.new_sub, self.a, self.b = line, note, i, j, new_sub, a, b


def rel(path):
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def levenshtein(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def spelling_rows():
    """(incorrect, correct) pairs from every Correct/Incorrect table of the GC glossary, spelling variants only."""
    pairs = []
    if not GC_GLOSSARY.exists():
        return pairs
    in_table = False
    for line in GC_GLOSSARY.read_text(encoding="utf-8").splitlines():
        if line.startswith("| Word | Correct | Incorrect"):
            in_table = True
            continue
        if line.startswith("|---"):
            continue
        if not line.startswith("| ") or line.startswith("| English"):
            in_table = False
            continue
        if not in_table:
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 3:
            continue
        correct = cells[1].split(" / ")[0].strip()
        for bad in [b.strip() for b in cells[2].split(" / ") if b.strip()]:
            same_word = bad[:2] == correct[:2] or bad[-2:] == correct[-2:]
            if len(bad) >= 3 and same_word and levenshtein(bad, correct) <= 4 and bad != correct:
                pairs.append((bad, correct))
    return pairs


def book_rows():
    """English head -> Lao name from lao-glossary.txt section 2, the parenthesis dropped, the first alternative taken."""
    rows = {}
    if not LAO_GLOSSARY.exists():
        return rows
    section = False
    for line in LAO_GLOSSARY.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            section = "Proper nouns" in line
            continue
        if section and line.startswith("| ") and not line.startswith("| English") and not line.startswith("|---"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) >= 2:
                head = re.sub(r"\s*\(.*?\)", "", cells[0]).strip()
                rows[head] = cells[1].split(" / ")[0].strip()
    return rows


def find_file(n, explicit):
    if explicit:
        return Path(explicit)
    hits = [ROOT / "lo/FB" / s / f"FB{n:02d}_lo.typ" for s in STAGES if (ROOT / "lo/FB" / s / f"FB{n:02d}_lo.typ").exists()]
    if len(hits) != 1:
        sys.exit(f"FB{n:02d}_lo.typ: {len(hits)} files in the stage directories; expected one")
    return hits[0]


def english_refs(n):
    src = ROOT / "lo/FB/00_source" / f"FB{n:02d}_en.md"
    m = re.search(r"\(([^()]+)\.\)\s*\{FB \d+\.\d+\}\s*$", src.read_text(encoding="utf-8").strip())
    return m.group(1) if m else None


def parse_refs(body):
    """[(book or None, refs)] from the text inside the parentheses, split on ';'."""
    items = []
    for item in [i.strip() for i in body.split(";") if i.strip()]:
        m = re.match(r"^((?:[123] )?[^\d]+?)\s+(\d.*)$", item)
        items.append((m.group(1).strip(), m.group(2).strip()) if m else (None, item))
    return items


def norm_refs(s):
    return re.sub(r"\s+", " ", s.replace("–", "-").replace("—", "-")).strip()


def token_span(line, i, j):
    """The space-delimited token that holds line[i:j]."""
    a = line.rfind(" ", 0, i) + 1
    b = line.find(" ", j)
    return a, (len(line) if b == -1 else b)


def check_line(idx, line, findings, spelling):
    def add(i, j, new_sub, note):
        a, b = token_span(line, i, j)
        findings.append(Finding(idx, note, i, j, new_sub, a, b))

    for m in re.finditer(r"[໐-໙]+", line):
        add(m.start(), m.end(), m.group().translate(LAO_DIGITS), "Lao digits become Western digits (profile 6.A)")
    for m in re.finditer(r"[๐-๙]+", line):
        add(m.start(), m.end(), m.group().translate(THAI_DIGITS), "Thai digits become Western digits (profile 6.A)")
    for m in re.finditer(r"[ก-๏๚๛]+", line):
        findings.append(Finding(idx, f"Thai letters {m.group()!r} at column {m.start()}; no replacement is proposed"))
    for m in re.finditer("[" + "".join(INVISIBLE) + "]", line):
        add(m.start(), m.end(), "", f"the token holds {INVISIBLE[m.group()]}, removed; the two sides differ only by that character (profile 6.B)")
    for m in re.finditer("ໍາ", line):
        add(m.start(), m.end(), "ຳ", "ໍ + າ becomes the single ຳ; the two sides look alike (profile 2.G)")
    for m in re.finditer("ພະ(?=" + "|".join(DIVINE_HEADS) + ")", line):
        add(m.start(), m.end(), "ພຣະ", "ພຣະ not ພະ (profile 2.A)")
    for m in re.finditer("ຊຶ່ງ", line):
        add(m.start(), m.end(), "ເຊິ່ງ", "ເຊິ່ງ not ຊຶ່ງ (profile 2.B)")
    for m in re.finditer("ຫລ", line):
        add(m.start(), m.end(), "ຫຼ", "ຫຼ not ຫລ (profile 2.C)")
    for m in re.finditer("ຣາຊະ", line):
        add(m.start(), m.end(), "ຣາຊ", "ຣາຊ compounds take no linking ະ (profile 2.F)")
    for m in re.finditer("ພຣະລາຊ", line):
        add(m.start(), m.end(), "ພຣະຣາຊ", "ຣາຊ keeps its ຣ (profile 2.E)")
    for m in re.finditer("ນິລະມິດ", line):
        add(m.start(), m.end(), "ນິຣະມິດ", "ນິຣະມິດ keeps its ຣ (profile 2.E)")
    for bad, good in spelling:
        for m in re.finditer(re.escape(bad), line):
            add(m.start(), m.end(), good, f"{good} not {bad} (GC-glossary.txt spelling table)")
    quotes = 0
    for m in re.finditer('"', line):
        quotes += 1
        add(m.start(), m.end(), "“" if quotes % 2 else "”", "straight quotation mark becomes “ ” (profile 4.A)")
    for m in re.finditer(r"(?<=\d)[-—](?=\d)", line):
        add(m.start(), m.end(), "–", "a range takes an en dash, not a hyphen or em dash (profile 5.A)")
    for m in re.finditer("ແລະ", line):
        i, j = m.start(), m.end()
        if "ເຊິ່ງກັນແລະກັນ" in line[max(0, i - 12):j + 6]:
            continue
        left_ok = i == 0 or line[i - 1] == " "
        right_ok = j == len(line) or line[j] == " "
        if not (left_ok and right_ok):
            add(i, j, ("" if left_ok else " ") + "ແລະ" + ("" if right_ok else " "), "spaces around ແລະ (profile 3.D)")
    for m in re.finditer("  +", line):
        a = line.rfind(" ", 0, m.start()) + 1
        b = line.find(" ", m.end())
        b = len(line) if b == -1 else b
        findings.append(Finding(idx, "double space becomes one space; the two sides differ only by the space", m.start(), m.end(), " ", a, b))
    if line.endswith(" "):
        i = len(line.rstrip(" "))
        findings.append(Finding(idx, "trailing space at the end of the line removed", i, len(line), "", i, len(line)))


def check_reference_line(n, line, findings, books):
    m = re.match(r"^\(ສຶກສາເພີ່ມເຕີມ: (.+)\)\.$", line)
    if not m:
        findings.append(Finding(3, "the reference line is not of the form (ສຶກສາເພີ່ມເຕີມ: ...). with the period after the parenthesis (profile 5.A)"))
        return
    en = english_refs(n)
    if en is None:
        findings.append(Finding(3, "no reference list found in the English source"))
        return
    en_items, lo_items = parse_refs(en), parse_refs(m.group(1))
    if len(en_items) != len(lo_items):
        findings.append(Finding(3, f"the English list has {len(en_items)} items and the Lao list {len(lo_items)}: EN {en!r}"))
        return
    pos = line.index(m.group(1))
    for (eb, er), (lb, lr), raw in zip(en_items, lo_items, [i.strip() for i in m.group(1).split(";") if i.strip()]):
        start = line.index(raw, pos)
        pos = start + len(raw)
        head = ABBR.get(eb) if eb else None
        if eb and head is None:
            findings.append(Finding(3, f"the English abbreviation {eb!r} is not in the script's table; add it"))
            continue
        if eb and head not in books:
            findings.append(Finding(3, f"no glossary row for the book {head}; the Lao writes {lb!r} (profile 5.B)"))
        elif eb and lb != books[head]:
            findings.append(Finding(3, f"the book {head} is {books[head]} in the glossary; EN {eb} {er}", start, start + len(lb), books[head], start, start + len(raw)))
        elif (eb is None) != (lb is None):
            findings.append(Finding(3, f"item {raw!r} carries a book name where the English does not, or the reverse; EN {(eb or '') + ' ' + er}".replace("EN  ", "EN ")))
        if norm_refs(er) != norm_refs(lr):
            i = start + (len(lb) + 1 if lb else 0)
            findings.append(Finding(3, f"the numbers differ from the English; EN {(eb or '') + ' ' + er}".replace("EN  ", "EN "), i, i + len(lr), er, start, start + len(raw)))


def collect(belief, lines, spelling, books):
    findings = []
    if len(lines) != 4 or lines[2] != "":
        findings.append(Finding(None, f"the file has {len(lines)} lines; expected the heading, the text, a blank line and the reference line (CLAUDE.md 2.B)"))
    h = re.match(r"^== (\d+) — (.+)$", lines[0]) if lines else None
    if not h:
        findings.append(Finding(0, "the heading is not of the form == N — title (profile 3.E)"))
    elif h.group(1) != str(belief):
        findings.append(Finding(0, f"the heading number is {h.group(1)!r}; expected {belief}"))
    for idx, line in enumerate(lines):
        check_line(idx, line, findings, spelling)
    if len(lines) >= 4:
        check_reference_line(belief, lines[3], findings, books)
    return findings


def where(idx):
    return "file" if idx is None else ("heading" if idx == 0 else "text" if idx == 1 else "reference line" if idx == 3 else f"line {idx + 1}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--belief", required=True, type=int)
    ap.add_argument("--file")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    path = find_file(a.belief, a.file)
    text = path.read_text(encoding="utf-8")
    standing = text.count("[[")
    if standing:
        print(f"note [file]: {standing} standing [[ marker(s) in {rel(path)}; resolve them first, the check stops here (CLAUDE.md 6.A)")
        return 1
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    spelling, books = spelling_rows(), book_rows()
    fixed = []
    for _ in range(10):
        fixes = [f for f in collect(a.belief, lines, spelling, books) if f.i is not None]
        if not fixes:
            break
        for idx in sorted({f.line for f in fixes}):
            line, taken = lines[idx], []
            for f in sorted([f for f in fixes if f.line == idx], key=lambda f: -f.i):
                if any(f.i < j and f.j > i for i, j in taken) or line[f.i:f.j] == f.new_sub:
                    continue
                token_before = line[f.a:f.b]
                line = line[:f.i] + f.new_sub + line[f.j:]
                taken.append((f.i, f.i + len(f.new_sub)))
                fixed.append((idx, token_before, f.note))
            lines[idx] = line
    notes = [f for f in collect(a.belief, lines, spelling, books) if f.i is None]
    for idx, token, note in fixed:
        print(f"fixed [{where(idx)}]: {token!r}: {note}")
    for f in notes:
        print(f"note [{where(f.line)}]: {f.note}")
    if fixed and not a.dry_run:
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"{len(fixed)} fix(es) written to {rel(path)}")
    elif fixed:
        print(f"{len(fixed)} fix(es) not written (dry run)")
    if not fixed and not notes:
        print(f"PASS: {rel(path)} has no finding")
    return 1 if notes or (fixed and a.dry_run) else 0


if __name__ == "__main__":
    sys.exit(main())
