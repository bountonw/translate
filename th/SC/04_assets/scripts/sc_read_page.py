#!/usr/bin/env python3
"""Reading page for the SC read-through (th/SC/CLAUDE.md section 10). Reads
the chapters and the English as they stand on main; writes one HTML page
under ~/claude-sandbox/sc-read/ for publishing as a claude.ai artifact.

    python3 th/SC/04_assets/scripts/sc_read_page.py --chapters 01-08
    python3 th/SC/04_assets/scripts/sc_read_page.py --chapters 01-08 10 --ref main --out PATH

Each chapter is read with git show from --ref (default main), under
th/SC/03_public, 02_edit or 01_raw, and its English from th/SC/00_source.
Every paragraph keeps its anchor, so the page saves notes, the reader's
place and each chapter's finished state by anchor in the artifact's
database; the template beside this script, sc_read_page.html, holds the
page and its code. A chapter holding a [[ marker or a (( choice is refused.
Republish to the same artifact after a chapter changes on main: the notes
stay, keyed by anchor.
"""
import argparse
import html
import itertools
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TEMPLATE = Path(__file__).with_name("sc_read_page.html")
STAGES = ("03_public", "02_edit", "01_raw")
OUT = Path.home() / "claude-sandbox" / "sc-read" / "sc-read.html"


def git_show(ref, path):
    r = subprocess.run(["git", "-C", str(ROOT), "show", f"{ref}:{path}"],
                       capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def chapter_list(args):
    out = []
    for a in args:
        if "-" in a:
            lo, hi = (int(x) for x in a.split("-"))
            out.extend(range(lo, hi + 1))
        else:
            out.append(int(a))
    return [f"{n:02d}" for n in out]


def match_bracket(s, i):
    """Index of the ] closing the [ at s[i], skipping escaped brackets."""
    depth = 0
    while i < len(s):
        c = s[i]
        if c == "\\":
            i += 2
            continue
        if c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise ValueError("unclosed bracket")


def typst_inline(s, notes):
    """Typst paragraph text to HTML; footnotes go to notes, #EGW is dropped."""
    out, i = [], 0
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s):
            out.append(html.escape(s[i + 1]))
            i += 2
            continue
        m = re.match(r"#(italic|footnote|EGW)\[", s[i:])
        if m:
            start = i + len(m.group(0)) - 1
            end = match_bracket(s, start)
            inner = s[start + 1:end]
            if m.group(1) == "italic":
                out.append("<em>" + typst_inline(inner, notes) + "</em>")
            elif m.group(1) == "footnote":
                notes.append(typst_inline(inner, notes))
                out.append(f'<sup class="fn">{len(notes)}</sup>')
            i = end + 1
            continue
        if s[i] == "#":
            raise ValueError(f"unknown Typst call: {s[i:i + 30]}")
        out.append(html.escape(s[i]))
        i += 1
    return "".join(out).strip()


def thai_chapter(text, nn):
    if "[[" in text or "((" in text:
        sys.exit(f"SC{nn}: the chapter holds a marker or an editor's choice; resolve it first")
    title = re.search(r'title:\s*"([^"]*)"', text).group(1)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)  # Typst block comments are the translator's, never the reader's
    paras, anchor = [], None
    for line in text.splitlines():
        m = re.match(r"// \{SC (\d+\.\d+)\}", line)
        if m:
            anchor = "SC " + m.group(1)
            continue
        if not line.strip() or line.startswith(("//", "#import", "#show", "#chapter", " ", ")")):
            continue
        if anchor is None:
            sys.exit(f"SC{nn}: text before the first anchor: {line[:60]}")
        notes = []
        paras.append({"a": anchor, "th": typst_inline(line, notes), "fn": notes})
        anchor = None
    return title, paras


def english_chapter(text):
    title = re.search(r"^\s*title:\s*\n\s*en:\s*(.+)$", text.split("chapter:", 1)[1], re.M).group(1).strip()
    en = {}
    for block in re.split(r"^## ", text, flags=re.M)[1:]:
        head, _, body = block.partition("\n")
        a = re.match(r"\{(SC \d+\.\d+)\}", head).group(1)
        body = re.sub(r"\s*\{SC \d+\.\d+\}\s*$", "", body.strip("\n").rstrip())
        parts = []
        for chunk in re.split(r"\n\s*\n", body):
            # Lines indented four spaces are verse and keep their breaks; other lines are prose.
            for verse, run in itertools.groupby(chunk.split("\n"), key=lambda l: l.startswith("    ")):
                run = [html.escape(l.strip()) for l in run if l.strip()]
                if run:
                    parts.append('<p class="verse">' + "<br>".join(run) + "</p>" if verse else "<p>" + " ".join(run) + "</p>")
        en[a] = "".join(parts)
    return title, en


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--chapters", nargs="+", required=True, help="01-08, or 01 02 05")
    p.add_argument("--ref", default="main")
    p.add_argument("--out", type=Path, default=OUT)
    a = p.parse_args()

    book = []
    for nn in chapter_list(a.chapters):
        th = next((t for st in STAGES if (t := git_show(a.ref, f"th/SC/{st}/SC{nn}_th.typ"))), None)
        en = git_show(a.ref, f"th/SC/00_source/SC{nn}_en.md")
        if th is None or en is None:
            sys.exit(f"SC{nn}: not found on {a.ref}")
        th_title, paras = thai_chapter(th, nn)
        en_title, en_paras = english_chapter(en)
        missing = [x["a"] for x in paras if x["a"] not in en_paras]
        if missing:
            sys.exit(f"SC{nn}: no English for {', '.join(missing)}")
        for x in paras:
            x["en"] = en_paras[x["a"]]
        book.append({"id": f"SC{nn}", "n": int(nn), "th": th_title, "en": en_title, "paras": paras})

    commit = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", a.ref],
                            capture_output=True, text=True).stdout.strip()
    data = json.dumps({"ref": a.ref, "commit": commit, "chapters": book}, ensure_ascii=False)
    page = TEMPLATE.read_text().replace("/*BOOK_DATA*/null", data.replace("</", "<\\/"))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(page)
    n = sum(len(c["paras"]) for c in book)
    print(f"{a.out}: {len(book)} chapters, {n} paragraphs, from {a.ref} at {commit}")


if __name__ == "__main__":
    main()
