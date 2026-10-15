#!/usr/bin/env python3
"""Extract the printed Thai Steps to Christ into one Typst file per chapter.

The print, "เคล็ดลับแห่งความสุข" (สำนักพิมพ์ข่าวประเสริฐ), is on the EGW
Writings app as book 14099, code ThSC: a zip holding one JSON file per
chapter, each a list of paragraph objects whose "content" is the paragraph's
HTML and, on nearly every paragraph, the English code "{SC page.n}" at its
end. That code places the paragraph against th/SC/00_source.

What the extraction changes in the text, and nothing else:
- the "{SC page.n}" code at the end of a paragraph becomes the "// {SC page.n}"
  comment above it and the "#EGW[\\{SC page.n\\}]" tag at its end;
- a page-break span is dropped and its page recorded in the report;
- the <br /> line ends of a poem become spaces, and a poem's source line
  joins the poem as one paragraph, since the English sets both under one code;
- runs of spaces become one space, and a paragraph's leading and trailing
  spaces go;
- a character Typst would read as markup is escaped with a backslash and
  recorded; the data holds none.
Spelling, wording and punctuation are the book's own.

A paragraph whose code is missing, repeated or displaced in the data takes
its code from RENUMBERED.tsv, which records each paragraph's printed code,
the action and the code it became; each line of that file was checked by
reading the Thai against the English paragraph. A paragraph the data leaves
without a code and the table does not cover is written under
"// no tag in the print" with no closing tag.

Usage, from the repository root:
    python3 th/SC/04_assets/scripts/sc_print_extract.py th/SC/04_assets/editions/print \\
        --renumber th/SC/04_assets/editions/print/RENUMBERED.tsv \\
        --report th/SC/04_assets/editions/print/EXTRACTION-NOTES.tsv [--zip ZIP]

ZIP defaults to the EGW Writings download under ~/programming/bible/egw-download.
The script ends by comparing each file's codes with the English source's
anchors and prints one line per chapter.
"""

import argparse
import csv
import json
import os
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "th" / "SC" / "00_source"
DEFAULT_ZIP = os.path.expanduser(
    "~/programming/bible/egw-download/egw-data/PWBRSPX93T.com.whiteestate.library/"
    "Application Support/zips/th/1099/14099.zip")
BOOK = "14099"
CODE_AT_END = re.compile(r"\s*\{SC (\d+\.\d+)\}\s*$")
CODE_INSIDE = re.compile(r"\{SC \d+\.\d+\}")
PAGE_BREAK = re.compile(r'<span class="page-break" data-page="(\d+)"></span>')
TAG = re.compile(r"<[^>]+>")
TYPST_SPECIAL = set("#*_`$@<>[]\\")


def clean(html):
    """The paragraph's text and the pages that break inside it."""
    pages = PAGE_BREAK.findall(html)
    t = PAGE_BREAK.sub(" ", html)
    t = re.sub(r"<br\s*/?>\r?\n?", " ", t)
    t = TAG.sub("", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t, pages


def escape(text, notes, where):
    out = []
    for ch in text:
        if ch in TYPST_SPECIAL:
            notes.append(("ESCAPED", where, ch))
            out.append("\\" + ch)
        else:
            out.append(ch)
    s = "".join(out)
    if s[:1] in "=-+/" :
        notes.append(("ESCAPED", where, s[0]))
        s = "\\" + s
    return s


def read_renumber(path):
    table = {}
    if not path:
        return table
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            table[row["para"]] = row
    return table


def english_codes():
    codes = {}
    for n in range(1, 14):
        text = (SOURCE / f"SC{n:02d}_en.md").read_text(encoding="utf-8")
        seen = []
        for c in re.findall(r"\{SC (\d+\.\d+)\}", text):
            if c not in seen:
                seen.append(c)
        codes[n] = seen
    return codes


def chapters(zf):
    """(chapter number or 0, title, file name) from toc.json, in book order."""
    out = []
    for entry in json.loads(zf.read("toc.json")):
        if entry["heading_level"] != 3:
            continue
        m = re.match(r"(\d+)\. ", entry["title"])
        n = int(m.group(1)) if m else 0
        pid = entry["dup"] or entry["para_id"]
        out.append((n, entry["title"], f"{pid}.json"))
    return out


def paragraphs(items, table, notes, label):
    """Merge poems with their source lines and apply JOIN; yield (ids, code, text, pages, title)."""
    held = None      # a poem waiting for its source line, or a JOIN paragraph
    for p in items:
        kind = p["element_type"]
        sub = p.get("element_subtype") or ""
        text, pages = clean(p["content"])
        if kind == "h1":
            continue
        if kind == "h3":
            yield ([p["para_id"]], None, text, pages, True)
            continue
        m = CODE_AT_END.search(text)
        code = m.group(1) if m else None
        if m:
            text = text[:m.start()].rstrip()
        if CODE_INSIDE.search(text):
            notes.append(("CODE-INSIDE", f"{label} {p['para_id']}", text[:60]))
        ids = [p["para_id"]]
        if held:
            hid, hcode, htext, hpages, hkind = held
            if hkind == "poem" and sub != "poem-source":
                notes.append(("POEM-ALONE", f"{label} {hid[0]}", htext[:60]))
                yield (hid, hcode, htext, hpages, False)
            else:
                ids = hid + ids
                text = htext + " " + text
                pages = hpages + pages
                code = code or hcode
                notes.append(("POEM" if hkind == "poem" else "JOIN", f"{label} {hid[0]}+{p['para_id']}", text[:60]))
            held = None
        row = table.get(p["para_id"])
        if row and row["action"] == "JOIN":
            held = (ids, code, text, pages, "join")
            continue
        if row is None:
            row = next((table[i] for i in ids if i in table and table[i]["action"] != "JOIN"), None)
        if sub == "poem-noindent":
            held = (ids, code, text, pages, "poem")
            continue
        if row:
            action = row["action"]
            if action in ("RECODE", "SUPPLY"):
                if (row["printed"] or None) != (f"SC {code}" if code else None):
                    notes.append(("TABLE-MISMATCH", f"{label} {row['para']}", f"data has {code}, table says {row['printed']}"))
                notes.append((action, f"{label} {row['para']}", f"{row['printed'] or '-'} -> {row['code']}"))
                code = row["code"].replace("SC ", "")
            elif action == "UNTAG":
                notes.append(("UNTAG", f"{label} {row['para']}", f"{row['printed']} dropped"))
                code = None
        yield (ids, code, text, pages, False)
    if held:
        hid, hcode, htext, hpages, hkind = held
        yield (hid, hcode, htext, hpages, False)


def write_chapter(zf, n, title, fname, outdir, table, notes, en):
    items = json.loads(zf.read(fname))
    label = f"SC{n:02d}"
    out = outdir / (f"{label}_preface_print_th.typ" if n == 0 else f"{label}_print_th.typ")
    pages = sorted({int(p["refcode_short"].split()[1].split(".")[0]) for p in items if p.get("refcode_short")})
    lines = [
        f"// Thai printed edition, เคล็ดลับแห่งความสุข (ThSC), pages {pages[0]}-{pages[-1]} of the print, "
        f"from the EGW Writings data file {fname}.",
        "// Extracted from the data, not translated or edited.",
        "",
    ]
    codes = []
    for ids, code, text, brk, is_title in paragraphs(items, table, notes, label):
        if is_title:
            lines += [f"// TITLE: {text}", ""]
            continue
        where = f"{label} {{SC {code}}}" if code else f"{label} {ids[0]}"
        for pg in brk:
            notes.append(("PAGE", where, pg))
        body = escape(text, notes, where)
        if code:
            codes.append(code)
            lines += [f"// {{SC {code}}}", "", f"{body} #EGW[\\{{SC {code}\\}}]", ""]
        else:
            notes.append(("NO-TAG", f"{label} {ids[0]}", text[:60]))
            lines += ["// no tag in the print", "", body, ""]
    out.write_text("\n".join(lines).rstrip("\n") + "\n", encoding="utf-8")
    if n == 0:
        return f"{label}: {len(codes)} codes, written to {out}"
    want = en[n]
    missing = [c for c in want if c not in codes]
    extra = [c for c in codes if c not in want]
    dup = sorted({c for c in codes if codes.count(c) > 1})
    order = [c for c in codes if c in want] == [c for c in want if c in codes]
    state = "matches the English" if not (missing or extra or dup) and order else \
        f"missing {missing} extra {extra} repeated {dup} order {'kept' if order else 'BROKEN'}"
    return f"{label}: {len(codes)} of {len(want)} codes, {state}"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("outdir")
    ap.add_argument("--zip", default=DEFAULT_ZIP)
    ap.add_argument("--renumber", help="RENUMBERED.tsv: para, printed, action, code, note")
    ap.add_argument("--report", help="EXTRACTION-NOTES.tsv to write")
    a = ap.parse_args()
    outdir = Path(a.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    table = read_renumber(a.renumber)
    notes = []
    en = english_codes()
    with zipfile.ZipFile(a.zip) as zf:
        for n, title, fname in chapters(zf):
            print(write_chapter(zf, n, title, fname, outdir, table, notes, en))
    if a.report:
        with open(a.report, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, delimiter="\t", lineterminator="\n")
            w.writerow(["kind", "where", "text"])
            w.writerows(notes)
        print(f"{len(notes)} notes written to {a.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
