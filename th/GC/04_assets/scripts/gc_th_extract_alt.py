#!/usr/bin/env python3
"""Extract the other Thai edition of The Great Controversy into Typst files.

This edition is set in a single column in THSarabunPSK, and every font in it
carries a working Unicode table, so the characters need no decoding table of
their own.  Three things still have to be handled.  The SARA AM vowel is set as
a ligature whose Unicode table gives the replacement character, so ten thousand
of them arrive as U+FFFD followed by a SARA AA and have to be composed.  The
printed page number sits at the start of the last line of every page and has to
come off.  And the book carries a great deal of material the English original
does not have — a publisher's introduction, picture plates with captions, and
back matter — which is separated out by keeping only the paragraphs that end
with a {GC ###.#} tag.

Every paragraph that is dropped is written to the notes file with its page and
its opening words, so nothing disappears without a record.

The source PDF is not in this repository.  Set GC_ALT_PDF to a local copy of it
so that the picture plates can be found; without it every page is treated as
text, which is safe but leaves the plate pages in the notes file.

Usage:
    GC_ALT_PDF=/path/to/GC_alt_th.pdf \
        python3 th/GC/04_assets/scripts/gc_th_extract_alt.py QDF OUT_DIR [--report R]
"""

import argparse
import collections
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gc_th_pdf import Pdf, page_glyphs, load_cidmap  # noqa: E402
from gc_th_extract import (  # noqa: E402
    Report,
    cluster_lines,
    escape_typst,
    guard_calls,
    TAG_RE,
)

BODY_SIZE = (13.0, 20.0)   # the running text is set at 16pt
PAGE_OFFSET = 28           # printed page number = PDF page - 28
REPLACEMENT = "�"
SARA_AA = "า"
SARA_AM = "ำ"
TONE_MARKS = set("็่้๊๋์")
FIRST_TEXT_PAGE = 28
LAST_TEXT_PAGE = 763
SOURCE_PDF = os.path.expanduser(os.environ.get("GC_ALT_PDF", ""))


def source_chapters(source_dir):
    """Return {tag: chapter number} from the English source."""
    where = {}
    for path in sorted(glob.glob(os.path.join(source_dir, "GC*_en.md"))):
        m = re.search(r"GC(\d+)", os.path.basename(path))
        if not m or not m.group(1).isdigit():
            continue
        chapter = int(m.group(1))
        for tag in re.findall(r"\{GC ([^}]+)\}", open(path, encoding="utf-8").read()):
            where.setdefault(tag, chapter)
    return where


def line_text(row):
    """Render one line, composing SARA AM and marking bold and italic runs."""
    pieces = []
    i = 0
    n = len(row)
    while i < n:
        g = row[i]
        text = g.text
        step = 1
        if text == REPLACEMENT:
            nxt = row[i + 1] if i + 1 < n else None
            nxt2 = row[i + 2] if i + 2 < n else None
            if nxt is not None and nxt.text == SARA_AA:
                text, step = SARA_AM, 2
            elif nxt is not None and nxt.text == SARA_AM:
                text, step = SARA_AM, 2
            elif (
                nxt is not None
                and nxt.text in TONE_MARKS
                and nxt2 is not None
                and nxt2.text == SARA_AA
            ):
                text, step = nxt.text + SARA_AM, 3
            else:
                text, step = "", 1
        base = g.font.base
        style = "i" if "Italic" in base else ("b" if "Bold" in base else "")
        if pieces and pieces[-1][1] == style:
            pieces[-1][0].append(text)
        else:
            pieces.append([[text], style])
        i += step
    return [("".join(t), s) for t, s in pieces]


def page_lines(pdf, pageno, cidmap, cache, report):
    """Return the page's lines top to bottom, with the page number removed."""
    glyphs = [
        g for g in page_glyphs(pdf, pdf.pages[pageno - 1], cidmap, cache)
        if BODY_SIZE[0] <= g.size <= BODY_SIZE[1]
    ]
    if not glyphs:
        return []
    rows = cluster_lines(glyphs, tol=3.0)
    out = []
    for y in sorted(rows, reverse=True):
        out.append((y, rows[y]))
    if out:
        y, row = out[-1]
        pieces = line_text(row)
        joined = "".join(t for t, _ in pieces)
        m = re.match(r"\s*(\d+)\s", joined)
        if m and int(m.group(1)) == pageno - PAGE_OFFSET:
            cut = m.end()
            trimmed = []
            eaten = 0
            for text, style in pieces:
                if eaten >= cut:
                    trimmed.append((text, style))
                elif eaten + len(text) <= cut:
                    eaten += len(text)
                else:
                    trimmed.append((text[cut - eaten:], style))
                    eaten = cut
            out[-1] = (y, None)
            out[-1] = (y, trimmed)
        elif m:
            report.note("PAGE-NUMBER", f"p{pageno}",
                        f"the last line opens with {m.group(1)}, "
                        f"not the expected {pageno - PAGE_OFFSET}")
    margin = max(
        max(a.x + a.adv for a in rows[y]) for y in rows
    )
    result = []
    for y, r in out:
        glyphs = rows[y]
        full = max(a.x + a.adv for a in glyphs) >= margin - 12
        pieces = r if (isinstance(r, list) and r and isinstance(r[0], tuple)) else line_text(r)
        result.append((y, pieces, full))
    return result



def caption_pages(pdf, cidmap, cache, first, last):
    """Return the body pages that carry a picture and no paragraph tag.

    Twenty-seven pages inside the body are picture plates: a portrait or an
    English quotation graphic with a Thai caption written by this edition's
    editors.  None of them carries a {GC ###.#} tag, and eleven other pages
    carry both a picture and tagged text, so the presence of a picture alone
    is not enough to set a page aside.
    """
    import subprocess
    try:
        listing = subprocess.run(
            ["pdfimages", "-list", "-"], input=open(SOURCE_PDF, "rb").read(),
            capture_output=True,
        ).stdout.decode("utf-8", "replace")
    except (OSError, TypeError):
        return set()
    with_image = set()
    for line in listing.splitlines()[2:]:
        head = line.split()
        if head and head[0].isdigit():
            with_image.add(int(head[0]))
    skip = set()
    for pageno in sorted(p for p in with_image if first <= p <= last):
        text = "".join(
            t for _y, pieces, _full in page_lines(pdf, pageno, cidmap, cache, Report())
            for t, _s in pieces
        )
        if not TAG_RE.search(text):
            skip.add(pageno)
    return skip


def build(pdf, cidmap, cache, report, skip=()):
    """Walk the body pages and return every paragraph with its page.

    The paragraph boundary is the {GC ###.#} tag itself, not the indent.  This
    edition indents some continuation lines and breaks some lines short of the
    measure in the middle of a sentence, so neither the leading space nor the
    right margin marks a paragraph reliably, while the tag marks the end of one
    by definition.
    """
    paragraphs = []
    current = {"pieces": [], "page": FIRST_TEXT_PAGE, "lines": []}
    paragraphs.append(current)
    for pageno in range(FIRST_TEXT_PAGE, LAST_TEXT_PAGE + 1):
        if pageno in skip:
            for _y, pieces, _full in page_lines(pdf, pageno, cidmap, cache, report):
                caption = "".join(t for t, _ in pieces).strip()
                if caption:
                    report.note("PICTURE-CAPTION", f"p{pageno}", caption[:70])
            continue
        for _y, pieces, full in page_lines(pdf, pageno, cidmap, cache, report):
            joined = "".join(t for t, _ in pieces)
            if not joined.strip():
                continue
            if current["pieces"]:
                tail = current["pieces"][-1][0]
                head = joined.lstrip()
                if tail.endswith("-") and head[:1] and "ก" <= head[0] <= "๛":
                    current["pieces"][-1] = (tail[:-1], current["pieces"][-1][1])
                    report.note("LINE-HYPHEN", f"p{pageno}",
                                tail[-24:] + " | " + head[:24])
            current["lines"].append((pieces, full))
            for text, style in pieces:
                if not current["pieces"]:
                    text = text.lstrip()
                if current["pieces"] and current["pieces"][-1][1] == style:
                    current["pieces"][-1] = (current["pieces"][-1][0] + text, style)
                else:
                    current["pieces"].append((text, style))
            if TAG_RE.search("".join(t for t, _ in current["pieces"])):
                current = {"pieces": [], "page": pageno, "lines": []}
                paragraphs.append(current)
    return paragraphs



def trim_opening(paragraph, report):
    """Drop a chapter opener from the front of the chapter's first paragraph.

    Between the last tagged paragraph of one chapter and the first of the next,
    this edition sets a chapter title, a date line and often a page of the
    editors' own comment, none of which the English book has.  Because the
    paragraph boundary here is the tag, all of that arrives fused to the front
    of the first tagged paragraph.  Every one of those opening lines stops well
    short of the measure, and the body paragraph that follows runs full width,
    so the cut goes after the last short line that still has a full line after
    it.
    """
    lines = paragraph.get("lines") or []
    cut = 0
    for i, (_pieces, full) in enumerate(lines):
        if not full and any(f for _p, f in lines[i + 1:]):
            cut = i + 1
    if not cut:
        return paragraph
    dropped = "".join(
        t for pieces, _f in lines[:cut] for t, _s in pieces
    ).strip()
    if dropped:
        report.note("CHAPTER-OPENER", f"p{paragraph['page']}", dropped[:70])
    kept = []
    for pieces, _f in lines[cut:]:
        for text, style in pieces:
            if not kept:
                text = text.lstrip()
            if kept and kept[-1][1] == style:
                kept[-1] = (kept[-1][0] + text, style)
            else:
                kept.append((text, style))
    paragraph["pieces"] = kept
    return paragraph


def render(paragraph):
    parts = []
    for text, style in paragraph["pieces"]:
        text = escape_typst(re.sub(r"\s{2,}", " ", text))
        if not text:
            continue
        if style in ("i", "b"):
            stripped = text.strip()
            if stripped:
                lead = " " if text[:1] == " " else ""
                trail = " " if text[-1:] == " " else ""
                fn = "italic" if style == "i" else "strong"
                parts.append(f"{lead}#{fn}[{stripped}]{trail}")
                continue
        parts.append(text)
    return re.sub(r"\s{2,}", " ", "".join(parts)).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("qdf")
    ap.add_argument("outdir")
    ap.add_argument("--report", default=None)
    ap.add_argument("--source", default="lo/GC/00_source")
    args = ap.parse_args()

    pdf = Pdf(args.qdf)
    cidmap = load_cidmap(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "browallia_cid_map.tsv")
    )
    report = Report()
    chapter_of = source_chapters(args.source)
    os.makedirs(args.outdir, exist_ok=True)

    cache = {}
    skip = caption_pages(pdf, cidmap, cache, FIRST_TEXT_PAGE, LAST_TEXT_PAGE)
    print(f"picture pages set aside: {len(skip)}")
    paragraphs = build(pdf, cidmap, cache, report, skip)

    chapters = collections.defaultdict(list)
    kept = dropped = 0
    seen_chapter = set()
    for para in paragraphs:
        preview = render(para)
        tags_preview = [f"{m.group(1)}.{m.group(2)}" for m in TAG_RE.finditer(preview)]
        if tags_preview:
            chapter_preview = chapter_of.get(tags_preview[-1])
            if chapter_preview is not None and chapter_preview not in seen_chapter:
                para = trim_opening(para, report)
        body = render(para)
        if not body:
            continue
        tags = [f"{m.group(1)}.{m.group(2)}" for m in TAG_RE.finditer(body)]
        body = re.sub(r"\s{2,}", " ", TAG_RE.sub("", body)).strip()
        if not tags:
            dropped += 1
            report.note("DROPPED", f"p{para['page']}", body[:70])
            continue
        if not body:
            dropped += 1
            report.note("EMPTY-AFTER-TRIM", f"p{para['page']}",
                        f"{tags[-1]} carried only a chapter opening")
            continue
        chapter = chapter_of.get(tags[-1])
        if chapter is None:
            dropped += 1
            report.note("UNKNOWN-TAG", f"p{para['page']}", f"{tags[-1]}: {body[:50]}")
            continue
        kept += 1
        seen_chapter.add(chapter)
        chapters[chapter].append((body, tags))

    for chapter, blocks in sorted(chapters.items()):
        name = f"GC{chapter:02d}_alt_th.typ"
        lines = [
            "// The other Thai edition of The Great Controversy, from "
            "GC_th_alt-original.pdf.",
            "// Extracted from the print, not translated or edited. Only the "
            "paragraphs the",
            "// book tags with a {GC ###.#} number are kept; the publisher's own "
            "material is",
            "// listed in EXTRACTION-NOTES-ALT.tsv.",
            "",
        ]
        for body, tags in blocks:
            tag = tags[-1]
            lines.append(f"// {{GC {tag}}}")
            lines.append("")
            extra = "".join(f" #EGW[\\{{GC {t}\\}}]" for t in tags[:-1])
            lines.append(guard_calls(f"{body}{extra}") + f" #EGW[\\{{GC {tag}\\}}]")
            lines.append("")
        with open(os.path.join(args.outdir, name), "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines).rstrip() + "\n")
        print(f"{name}: paragraphs {len(blocks)}")

    if args.report:
        with open(args.report, "w", encoding="utf-8") as fh:
            fh.write("# kind\twhere\tdetail\n")
            fh.write("\n".join(report.lines) + "\n")
    print(f"kept {kept} tagged paragraphs, set aside {dropped}")
    print("report counts:", dict(report.counts))


if __name__ == "__main__":
    main()
