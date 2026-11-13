#!/usr/bin/env python3
"""Write the English source of The Story of Jesus, one file per chapter.

    python3 th/SJ/04_assets/scripts/sj_source_extract.py
    python3 th/SJ/04_assets/scripts/sj_source_extract.py --book PATH --zip PATH --out DIR

The text is the EGW Writings app's book 144, The Story of Jesus (1896, 1900),
as egw_extract.py writes it from the app's download: one Markdown file whose
paragraphs open with their codes, as "{SJ 13.1} In the little town ...", and
whose italics are *words*. Make that file with

    python3 ~/claude-sandbox/egw/egw_extract.py ZIPS_DIR OUT_DIR

where ZIPS_DIR is the app's "Application Support/zips" folder; the default
--book is ~/claude-sandbox/egw/extracted/en/SJ.md. The chapter links come from
the table of contents in the app's own zip, en/2/4/144.zip, read-only; without
the zip the url line is left empty.

Writes th/SJ/00_source/SJNN_en.md for the preface (SJ00) and chapters 1 to 32
in the shape of th/SC/00_source: front matter, then per paragraph

    ## {SJ 13.1}

    paragraph text {SJ 13.1}

A paragraph of several lines, a poem, is written with each line indented four
spaces and the code after its last line. A paragraph the book leaves without a
code, as the preface's closing lines, is written indented after the paragraph
before it, with no code, as SC00 writes its signature. The text is the book's
own; nothing is corrected. Contacts no server.
"""
import argparse
import json
import os
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BOOK = Path(os.path.expanduser(os.environ.get("EGW_SJ_MD", "~/claude-sandbox/egw/extracted/en/SJ.md")))
ZIP = Path(os.path.expanduser(
    "~/programming/bible/egw-download/egw-data/PWBRSPX93T.com.whiteestate.library/"
    "Application Support/zips/en/2/4/144.zip"))
HEADING = re.compile(r"^###\s+(?:Chapter (\d+)\s*[—-]\s*(.+?)|(Preface))\s*\{SJ \d+\}\s*$")
PARA = re.compile(r"^\{SJ (\d+\.\d+)\}\s*(.*)$", re.S)


def toc_links(zpath):
    """chapter number -> egwwritings.org link to its heading paragraph."""
    try:
        toc = json.loads(zipfile.ZipFile(zpath).read("toc.json"))
    except (OSError, KeyError, zipfile.BadZipFile):
        return {}
    links = {}
    for t in toc:
        m = re.match(r"Chapter (\d+)\s*[—-]", t.get("title", ""))
        n = int(m.group(1)) if m else 0 if t.get("title") == "Preface" else None
        if n is not None:
            links[n] = "https://egwwritings.org/read?panels=p" + t["para_id"]
    return links


def front(number, title, url, book):
    return "\n".join([
        "---", "book:", "  title:", f"    en: {book}", "chapter:",
        f"  number:{' ' + str(number) if number else ''}", "  title:", f"    en: {title}",
        f"  url: {url}", "author:", "  en: Ellen White", "---", ""])


def block(lines, code=None):
    tail = f" {{SJ {code}}}" if code else ""
    if len(lines) == 1 and code:
        return lines[0] + tail
    return "\n".join("    " + ln for ln in lines) + tail


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--book", default=str(BOOK))
    ap.add_argument("--zip", default=str(ZIP))
    ap.add_argument("--out", default=str(ROOT / "th" / "SJ" / "00_source"))
    a = ap.parse_args()
    text = Path(a.book).read_text(encoding="utf-8")
    m = re.search(r'^title: "(.*)"$', text, re.M)
    book = m.group(1) if m else "The Story of Jesus"
    links = toc_links(a.zip)
    chapters, cur = {}, None
    for raw in re.split(r"\n\s*\n", text.split("\n---\n", 1)[-1]):
        lines = [ln.rstrip() for ln in raw.strip().split("\n") if ln.strip()]
        if not lines:
            continue
        h = HEADING.match(lines[0])
        if h:
            n, title = (int(h.group(1)), h.group(2).strip()) if h.group(1) else (0, "Preface")
            cur = chapters[n] = {"head": front(n, title, links.get(n, ""), book), "parts": []}
            continue
        if cur is None or lines[0].startswith("#"):
            continue
        p = PARA.match(lines[0])
        if p:
            lines[0] = p.group(2)
            cur["parts"].append(f"## {{SJ {p.group(1)}}}\n\n{block(lines, p.group(1))}")
        elif cur["parts"]:
            cur["parts"][-1] += "\n\n" + block(lines)
    if not chapters:
        sys.exit(f"no chapter headings in {a.book}")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for n, ch in sorted(chapters.items()):
        p = out / f"SJ{n:02d}_en.md"
        p.write_text(ch["head"] + "\n" + "\n\n".join(ch["parts"]) + "\n", encoding="utf-8")
        print(f"{p.name}: {len(ch['parts'])} paragraphs")
    print(f"written {len(chapters)} files to {out}" + ("" if links else "; no zip, so the url lines are empty"))


if __name__ == "__main__":
    main()
