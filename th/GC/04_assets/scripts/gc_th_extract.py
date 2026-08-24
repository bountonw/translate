#!/usr/bin/env python3
"""Extract the Thai printed edition of The Great Controversy into Typst files.

The text comes out of the PDF's own glyph stream through the table in
browallia_cid_map.tsv, so nothing here is transcription: a character either
decodes or the run stops.  What this script adds is layout — reading the two
columns in the right order, dropping the running head, rejoining the lines of
a paragraph, restoring the spaces the typesetter set as kerns, composing the
SARA AM that the typesetting decomposed, and marking the italic runs.

It translates nothing and corrects no spelling.  Where the book is wrong, the
output is wrong in the same way.

Usage:
    python3 th/GC/04_assets/scripts/gc_th_extract.py QDF_PDF OUT_DIR [--report R]
"""

import argparse
import collections
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gc_th_pdf import Pdf, page_glyphs, load_cidmap  # noqa: E402

HEADER_Y = 575.0      # the running head sits at y=594; the body tops out at 563
GUTTER_X = 232.0      # the empty band between the two columns
DISPLAY_SIZE = 16.0   # chapter titles are set at 22.5 and 32.5
INDENT = 5.0          # a first line is indented about 14pt from the margin
SPACE_GAP = 0.10      # extra advance, in ems, that marks a kerned word space.
# Measuring every gap in the book puts real spaces at 0.15 and above, with
# 10,268 of them, eight more between 0.10 and 0.15, and nothing at all below
# 0.10, so the line sits at 0.10 and those eight are kept.

NIKHAHIT = "ํ"
SARA_AA = "า"
SARA_AM = "ำ"
TONE_MARKS = set("็่้๊๋์")
CLOSERS = set("”’)]")
OPENERS = set("“‘([")

# The 42 chapters open on these PDF pages, identified by the 32.5pt display
# type that appears on a chapter opening and nowhere else.
CHAPTER_PAGES = [
    18, 40, 50, 62, 78, 94, 116, 140, 164, 176, 188, 202, 228, 236,
    256, 278, 288, 306, 330, 342, 360, 376, 394, 408, 418, 434, 444,
    462, 474, 486, 492, 498, 510, 528, 538, 556, 566, 576, 586, 606,
    624, 632,
]
LAST_TEXT_PAGE = 648   # 649 and 650 are the covers
# Page 1 and pages 649-650 are the cover, a designed page whose words are set
# in scattered display type and which is not extracted.  Pages 2-7 are the
# title page, the imprint, the page of quotations
# and the two-page table of contents; pages 8-17 are the publisher's foreword
# and the Introduction, which is the part that carries {GC v.1} to {GC xii.2}.
FRONT_MATTER = (2, 7)
INTRODUCTION = (8, 17)


class Report:
    def __init__(self):
        self.lines = []
        self.counts = collections.Counter()

    def note(self, kind, where, detail):
        self.counts[kind] += 1
        self.lines.append(f"{kind}\t{where}\t{detail}")


# ─── page to lines ───────────────────────────────────────────────────────────


def cluster_lines(glyphs, tol=2.0):
    """Group glyphs into lines by baseline, keeping content-stream order."""
    keys = sorted({round(g.y, 1) for g in glyphs}, reverse=True)
    bands = []
    for y in keys:
        if bands and abs(bands[-1][0] - y) <= tol:
            bands[-1].append(y)
        else:
            bands.append([y])
    lookup = {}
    for band in bands:
        for y in band:
            lookup[y] = band[0]
    rows = collections.defaultdict(list)
    for g in glyphs:
        rows[lookup[round(g.y, 1)]].append(g)
    return rows


def find_gutter(body, lo=200.0, hi=270.0, need=5.0):
    """Return the x to split two columns at, or None if the page sets one column.

    The gutter is the widest band of the page that no glyph paints over.  A
    fixed threshold is not enough: a vowel or a tone mark carries no advance
    and sits a little to the right of the letter it belongs to, so on a page
    whose left column runs long the marks alone reach into a fixed band and
    make a two-column page look like one.
    """
    spans = sorted(
        (g.x, g.x + max(g.adv, 0.0)) for g in body if lo - 40 <= g.x <= hi + 40
    )
    if not spans:
        return None
    best = (0.0, None)
    edge = lo
    for start, end in spans:
        if start > edge:
            width = min(start, hi) - edge
            if width > best[0]:
                best = (width, edge + width / 2)
        edge = max(edge, end)
        if edge >= hi:
            break
    if edge < hi and hi - edge > best[0]:
        best = (hi - edge, edge + (hi - edge) / 2)
    return best[1] if best[0] >= need else None


def page_rows(pdf, page, cidmap, font_cache):
    """Return the page's lines as (order_key, column, baseline, glyphs)."""
    glyphs = [g for g in page_glyphs(pdf, page, cidmap, font_cache) if g.y <= HEADER_Y]
    display = [g for g in glyphs if g.size > DISPLAY_SIZE]
    body = [g for g in glyphs if g.size <= DISPLAY_SIZE]

    out = []
    for y, row in cluster_lines(display).items():
        out.append((0, -1, -y, y, row))

    body_rows = cluster_lines(body)
    split = find_gutter(body)
    two_col = split is not None
    for y, row in body_rows.items():
        if two_col:
            left = [g for g in row if g.x < split]
            right = [g for g in row if g.x >= split]
            if left:
                out.append((1, 0, -y, y, left))
            if right:
                out.append((1, 1, -y, y, right))
        else:
            out.append((1, 0, -y, y, row))
    out.sort(key=lambda r: (r[0], r[1], r[2]))
    return [(col, y, row) for _, col, _, y, row in out], two_col


# ─── line to text ────────────────────────────────────────────────────────────


def line_text(row, report, where):
    """Render one line, restoring kerned spaces, composing SARA AM, marking italics."""
    gaps = []
    for a, b in zip(row, row[1:]):
        if a.text == " " or b.text == " " or a.size <= 0:
            continue
        gaps.append((b.x - (a.x + a.adv)) / a.size)
    gaps.sort()
    base = gaps[len(gaps) // 2] if gaps else 0.0

    pieces = []          # (text, style) with style in "", "i", "b"
    i = 0
    n = len(row)
    while i < n:
        g = row[i]
        text = g.text
        step = 1
        if g.code == 300 and g.font.is_cid_thai:
            nxt = row[i + 1] if i + 1 < n else None
            nxt2 = row[i + 2] if i + 2 < n else None
            if nxt is not None and nxt.text == SARA_AA:
                text, step = SARA_AM, 2
            elif (
                nxt is not None
                and nxt.text in TONE_MARKS
                and nxt2 is not None
                and nxt2.text == SARA_AA
            ):
                text, step = nxt.text + SARA_AM, 3
            else:
                report.note("LONE-NIKHAHIT", where, "".join(x.text for x in row))
        style = "i" if "Italic" in g.font.base else ("b" if "Bold" in g.font.base else "")
        if pieces and pieces[-1][1] == style:
            pieces[-1][0].append(text)
        else:
            pieces.append([[text], style])

        if i + step < n:
            last = row[i + step - 1]
            nxt = row[i + step]
            end = last.x + last.adv
            if (
                text != " "
                and nxt.text != " "
                and last.size > 0
                and (nxt.x - end) / last.size - base >= SPACE_GAP
            ):
                pieces[-1][0].append(" ")
        i += step
    return [("".join(t), s) for t, s in pieces]


def join_pieces(pieces):
    return "".join(t for t, _ in pieces)


# ─── paragraph assembly ──────────────────────────────────────────────────────


def build_paragraphs(pdf, first_page, last_page, cidmap, font_cache, report):
    """Walk a page range and return its paragraphs as piece lists."""
    paras = []
    current = None
    for pno in range(first_page, last_page + 1):
        rows, _ = page_rows(pdf, pdf.pages[pno - 1], cidmap, font_cache)
        margins = {}
        for col, _y, row in rows:
            x0 = min(g.x for g in row)
            margins[col] = min(margins.get(col, x0), x0)
        for col, y, row in rows:
            where = f"p{pno}"
            pieces = line_text(row, report, where)
            if not join_pieces(pieces).strip():
                continue
            display = max(g.size for g in row) > DISPLAY_SIZE
            starts = display or min(g.x for g in row) > margins[col] + INDENT
            if starts or current is None:
                current = {"pieces": [], "display": display, "page": pno}
                paras.append(current)
            elif current["display"] != display:
                current = {"pieces": [], "display": display, "page": pno}
                paras.append(current)
            if current["pieces"]:
                tail = current["pieces"][-1][0]
                head = join_pieces(pieces)
                if tail.endswith("-") and head[:1] and "ก" <= head[0] <= "๛":
                    current["pieces"][-1] = (tail[:-1], current["pieces"][-1][1])
                    report.note("LINE-HYPHEN", where, tail[-24:] + " | " + head[:24])
                elif tail[-1:] in CLOSERS or head[:1] in OPENERS:
                    # Within a line this book always sets a space on the outside
                    # of a quotation mark or a bracket, so a break falling there
                    # has swallowed one.  Every insertion is recorded.
                    if not tail.endswith(" ") and not head.startswith(" "):
                        current["pieces"][-1] = (tail + " ", current["pieces"][-1][1])
                        report.note("JOIN-SPACE", where, tail[-12:] + " | " + head[:12])
            for text, style in pieces:
                if current["pieces"] and current["pieces"][-1][1] == style:
                    current["pieces"][-1] = (
                        current["pieces"][-1][0] + text,
                        style,
                    )
                else:
                    current["pieces"].append((text, style))
    return paras


# ─── Typst output ────────────────────────────────────────────────────────────

# The book prints one tag without its opening brace, reading "GC 335.2}" on
# page 322, so the brace is optional here and that tag is recognised too.
TAG_RE = re.compile(r"\{?\s*GC\s*([ivxlcdm]+|\d+)\.(\d+)\s*\}", re.I)


ESCAPE = str.maketrans(
    {c: "\\" + c for c in "\\[]#@*_$<>`"}
)


def escape_typst(text):
    """Escape the characters Typst reads as markup.

    The print uses square brackets for the translators' explanatory notes, and
    at {GC 640.2} it carries a stray closing bracket with no opening one, which
    Typst refuses to compile.  Escaping every literal bracket keeps the file
    valid whatever the print does, and renders the character unchanged.
    """
    return text.translate(ESCAPE)


def to_typst(paras, report, where):
    """Render paragraphs as th/SC-style Typst body text."""
    out = []
    for para in paras:
        text_parts = []
        for text, style in para["pieces"]:
            text = escape_typst(text.replace("  ", " "))
            if not text:
                continue
            if style == "i":
                stripped = text.strip()
                if stripped:
                    lead = " " if text[:1] == " " else ""
                    trail = " " if text[-1:] == " " else ""
                    text_parts.append(f"{lead}#italic[{stripped}]{trail}")
                    continue
            text_parts.append(text)
        body = "".join(text_parts).strip()
        if not body:
            continue

        tags = [f"{m.group(1)}.{m.group(2)}" for m in TAG_RE.finditer(body)]
        body = TAG_RE.sub("", body).strip()
        body = re.sub(r"\s{2,}", " ", body)
        if para["display"]:
            out.append(("display", body, tags))
        else:
            out.append(("para", body, tags))
        if not tags and not para["display"]:
            report.note("NO-TAG", f"{where} p{para['page']}", body[:60])
        if len(tags) > 1:
            report.note("MULTI-TAG", f"{where} p{para['page']}", " ".join(tags))
    return out


# After a Typst call such as #italic[...], a following period or open bracket
# reads as a field access or a second argument rather than as text, so it has
# to be escaped.  The print does this constantly, in references of the form
# "#italic[Ibid].เล่มที่ 2".
TRAILING = re.compile(r"(?<!\\)\](?=[.(])")


def guard_calls(line):
    return TRAILING.sub(lambda m: "]" + chr(92), line)



def merge_titles(blocks):
    """Join the lines of a chapter title and put the chapter number first.

    A chapter title set over two lines arrives as three display blocks, because
    the boxed chapter number stands to the left of the two lines with its
    baseline between them and so is read second.  They are one title, and the
    number belongs at its head.
    """
    out = []
    run = []
    for block in blocks:
        if block[0] == "display":
            run.append(block[1])
            continue
        if run:
            out.append(("display", one_title(run), []))
            run = []
        out.append(block)
    if run:
        out.append(("display", one_title(run), []))
    return out


def one_title(parts):
    numbers = [p for p in parts if p.strip().isdigit()]
    words = [p for p in parts if not p.strip().isdigit()]
    return " ".join(numbers + words).strip()



def write_file(path, blocks, header_comment):
    blocks = merge_titles(blocks)
    lines = [header_comment, ""]
    for kind, body, tags in blocks:
        if kind == "display":
            lines.append(f"// TITLE: {body}")
            lines.append("")
            continue
        tag = tags[-1] if tags else None
        if tag:
            lines.append(f"// {{GC {tag}}}")
            lines.append("")
        extra = "".join(f" #EGW[\\{{GC {t}\\}}]" for t in tags[:-1])
        if tag:
            lines.append(
                guard_calls(f"{body}{extra}") + f" #EGW[\\{{GC {tag}\\}}]"
            )
        else:
            lines.append(guard_calls(body))
        lines.append("")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines).rstrip() + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("qdf")
    ap.add_argument("outdir")
    ap.add_argument("--report", default=None)
    ap.add_argument("--only", default=None, help="chapter number, or 0 for the front matter")
    args = ap.parse_args()

    pdf = Pdf(args.qdf)
    cidmap = load_cidmap(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "browallia_cid_map.tsv")
    )
    font_cache = {}
    report = Report()
    os.makedirs(args.outdir, exist_ok=True)

    jobs = []
    jobs.append((None, FRONT_MATTER[0], FRONT_MATTER[1], "GC00_front_print_th.typ"))
    jobs.append((0, INTRODUCTION[0], INTRODUCTION[1], "GC00_intro_print_th.typ"))
    for idx, start in enumerate(CHAPTER_PAGES):
        end = (CHAPTER_PAGES[idx + 1] - 1) if idx + 1 < len(CHAPTER_PAGES) else LAST_TEXT_PAGE
        jobs.append((idx + 1, start, end, f"GC{idx + 1:02d}_print_th.typ"))

    for num, first, last, name in jobs:
        if args.only is not None and (num is None or int(args.only) != num):
            continue
        paras = build_paragraphs(pdf, first, last, cidmap, font_cache, report)
        blocks = to_typst(paras, report, name)
        header = (
            f"// Thai printed edition, Great Hope (Full Version), pages {first}-{last} "
            f"of Great-Hope-01-01-2017.pdf.\n"
            f"// Extracted from the print, not translated or edited."
        )
        write_file(os.path.join(args.outdir, name), blocks, header)
        tags = [t for _, _, ts in blocks for t in ts]
        print(f"{name}: pages {first}-{last}  paragraphs {len(blocks)}  tags {len(tags)}")

    if args.report:
        with open(args.report, "w", encoding="utf-8") as fh:
            fh.write("# kind\twhere\tdetail\n")
            fh.write("\n".join(report.lines) + "\n")
    print("report counts:", dict(report.counts))


if __name__ == "__main__":
    main()
