#!/usr/bin/env python3
"""Extract the printed Thai Desire of Ages into one Typst file per chapter.

The print, "ผู้พึงปรารถนาของปวงชน" (2023), was set in InDesign in two
columns. Its fonts map many vowel and tone glyphs to the wrong character, but
each such glyph sits inside a span whose ActualText gives the right one, so
the page is read glyph by glyph with each ActualText span standing in for the
glyphs it covers. Word spaces come only from the space characters the
typesetter set, never from gaps between glyphs, because justified lines are
letter-spaced. The typesetter ends every broken line with one space of its
own, so one space comes off each line end.

What the extraction changes in the text, and nothing else:
- a tone mark the stream puts before an upper vowel is put after it (ที่,
  not ท่ี), and the Thai private-use forms of shifted marks become the
  ordinary characters;
- the replacement character the fonts give for half of SARA AM is dropped;
- every kind of space becomes an ordinary space, and runs of spaces one;
- a hyphen at a line end between two Thai letters is dropped;
- the lines of a paragraph are joined, with a space after a line that stops
  short, such as a line of a poem.
- a mark set twice on one letter is set once (สู่่ becomes สู่), the one
  correction to the book's own text, since the reader sees one mark.
Spelling, wording and punctuation are otherwise the book's own.

The text is split at the {DA page.n} tags that close the paragraphs. Pull
quotes, which reprint a sentence of the text in a centred box, and the filler
quotations on a chapter's last page are left out. Each is written to the
report with its page, as is every dropped hyphen, every paragraph without a
tag, and every English tag the print does not carry.

Usage, from the repository root:
    qpdf --qdf --object-streams=disable --stream-data=uncompress IN.pdf QDF
    python3 th/DA/04_assets/scripts/da_th_extract.py QDF th/DA/04_assets/editions/print \
        --report th/DA/04_assets/editions/print/EXTRACTION-NOTES.tsv
    python3 th/DA/04_assets/scripts/da_th_extract.py QDF --dump 20 22

IN.pdf is "AW_ผู้พึงปรารถนาของปวงชน (72 res).pdf" from the zip in
th/DA/04_assets. The PDF reader is th/GC/04_assets/scripts/gc_th_pdf.py.
"""

import argparse
import collections
import glob
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, os.path.join(REPO, 'th', 'GC', '04_assets', 'scripts'))
from gc_th_pdf import Pdf, Lexer, Font, Ref, Name, mat_mul  # noqa: E402

SOURCE_DIR = os.path.join(REPO, 'th', 'DA', '00_source')
# A few glyphs map to the Thai private-use forms fonts use for a mark moved
# left or down to clear another (U+F700-F71A); each stands for the ordinary
# character.
PUA = {
    0xF700: 0x0E10,
    0xF701: 0x0E34,
    0xF702: 0x0E35,
    0xF703: 0x0E36,
    0xF704: 0x0E37,
    0xF705: 0x0E48,
    0xF706: 0x0E49,
    0xF707: 0x0E4A,
    0xF708: 0x0E4B,
    0xF709: 0x0E4C,
    0xF70A: 0x0E48,
    0xF70B: 0x0E49,
    0xF70C: 0x0E4A,
    0xF70D: 0x0E4B,
    0xF70E: 0x0E4C,
    0xF70F: 0x0E0D,
    0xF710: 0x0E31,
    0xF711: 0x0E4D,
    0xF712: 0x0E47,
    0xF713: 0x0E48,
    0xF714: 0x0E49,
    0xF715: 0x0E4A,
    0xF716: 0x0E4B,
    0xF717: 0x0E4C,
    0xF718: 0x0E38,
    0xF719: 0x0E39,
    0xF71A: 0x0E3A,
}

# The print misprints some tags: "(DA 21.2}", "{DA 61.1)", "{D 144.3}",
# "{D A 290.3}", "DA 593.3}", and "{DA 558.4" at a paragraph's end.
TAG_RE = re.compile(r'(?:[{(]\s*D\s*A?\s*(\d+)\s*\.\s*(\d+)\s*(?:[})]|$)'
                    r'|(?<![\w{(])DA\s*(\d+)\s*\.\s*(\d+)\s*[})])')
TONE = '\u0e48\u0e49\u0e4a\u0e4b\u0e4c'
UPPER = '\u0e31\u0e34\u0e35\u0e36\u0e37\u0e47'
THAI = re.compile(r'[\u0e01-\u0e4e]')
REPLACEMENT = '\ufffd'
MARKS = re.compile(r'[\u0e31\u0e34-\u0e3a\u0e47-\u0e4e]+')
ESCAPE = str.maketrans({c: '\\' + c for c in '\\[]#@*_$<>`'})


class Glyph:
    __slots__ = ('x', 'y', 'size', 'text', 'n', 'code', 'end')

    def __init__(self, x, y, size, text, n, code=None, end=None):
        self.x, self.y, self.size, self.text, self.n, self.code = x, y, size, text, n, code
        self.end = x if end is None else end


def decode_text(v):
    if isinstance(v, str):
        v = v.encode('latin-1')
    if v.startswith(b'\xfe\xff'):
        return v[2:].decode('utf-16-be', 'replace')
    return v.decode('latin-1')


def page_glyphs(pdf, page, font_cache):
    """Return the page's glyphs in stream order, each ActualText span as one glyph."""
    res = pdf.get(page, 'Resources') or {}
    fonts = {}
    for key, ref in (pdf.get(res, 'Font') or {}).items():
        cache_key = ref.num if isinstance(ref, Ref) else (id(page), key)
        if cache_key not in font_cache:
            font_cache[cache_key] = Font(pdf, pdf.resolve(ref), {})
        fonts[key] = font_cache[cache_key]

    content = pdf.page_content(page)
    lex = Lexer(content, 0)
    stack = []
    ctm = (1, 0, 0, 1, 0, 0)
    tm = tlm = (1, 0, 0, 1, 0, 0)
    font, size = None, 0.0
    tc = tw = ts = tl = 0.0
    th = 1.0
    operands = []
    out = []
    marked = []          # one entry per open BDC/BMC: None, or [text, first position]

    def position():
        trm = mat_mul((size * th, 0, 0, size, 0, ts), mat_mul(tm, ctm))
        return trm[4], trm[5], (trm[2] ** 2 + trm[3] ** 2) ** 0.5

    def actual():
        for m in marked:
            if m is not None:
                return m
        return None

    def show(raw):
        nonlocal tm
        if font is None:
            return
        for code in font.codes(raw):
            text, _ = font.decode(code)
            x, y, eff = position()
            w0 = font.width(code) / 1000.0
            adv = (w0 * size + tc + (tw if (code == 32 and not font.two_byte) else 0)) * th
            tm = mat_mul((1, 0, 0, 1, adv, 0), tm)
            end = position()[0]
            span = actual()
            if span is not None:
                if span[1] is None:
                    span[1] = (x, y, eff)
                span[2] = end
            elif text:
                out.append(Glyph(x, y, eff, text.translate(PUA), len(out), code, end))

    n = len(content)
    while lex.i < n:
        val, is_kw = lex.parse()
        if val is None and not is_kw:
            if lex.i >= n:
                break
            continue
        if not is_kw:
            operands.append(val)
            if len(operands) > 32:
                del operands[:-32]
            continue
        op = val
        try:
            if op == 'q':
                stack.append(ctm)
            elif op == 'Q':
                if stack:
                    ctm = stack.pop()
            elif op == 'cm' and len(operands) >= 6:
                ctm = mat_mul(tuple(float(x) for x in operands[-6:]), ctm)
            elif op == 'BT':
                tm = tlm = (1, 0, 0, 1, 0, 0)
            elif op == 'Tf' and len(operands) >= 2:
                font = fonts.get(str(operands[-2]))
                size = float(operands[-1])
            elif op == 'Td' and len(operands) >= 2:
                tlm = mat_mul((1, 0, 0, 1, float(operands[-2]), float(operands[-1])), tlm)
                tm = tlm
            elif op == 'TD' and len(operands) >= 2:
                tl = -float(operands[-1])
                tlm = mat_mul((1, 0, 0, 1, float(operands[-2]), float(operands[-1])), tlm)
                tm = tlm
            elif op == 'Tm' and len(operands) >= 6:
                tm = tlm = tuple(float(x) for x in operands[-6:])
            elif op == 'T*':
                tlm = mat_mul((1, 0, 0, 1, 0, -tl), tlm)
                tm = tlm
            elif op == 'TL' and operands:
                tl = float(operands[-1])
            elif op == 'Tc' and operands:
                tc = float(operands[-1])
            elif op == 'Tw' and operands:
                tw = float(operands[-1])
            elif op == 'Tz' and operands:
                th = float(operands[-1]) / 100.0
            elif op == 'Ts' and operands:
                ts = float(operands[-1])
            elif op == 'Tj' and operands:
                show(operands[-1])
            elif op == "'" and operands:
                tlm = mat_mul((1, 0, 0, 1, 0, -tl), tlm)
                tm = tlm
                show(operands[-1])
            elif op == '"' and len(operands) >= 3:
                tw, tc = float(operands[-3]), float(operands[-2])
                tlm = mat_mul((1, 0, 0, 1, 0, -tl), tlm)
                tm = tlm
                show(operands[-1])
            elif op == 'TJ' and operands and isinstance(operands[-1], list):
                for item in operands[-1]:
                    if isinstance(item, (bytes, str)):
                        show(item)
                    elif isinstance(item, (int, float)):
                        tm = mat_mul((1, 0, 0, 1, -item / 1000.0 * size * th, 0), tm)
            elif op == 'BMC':
                marked.append(None)
            elif op == 'BDC':
                props = operands[-1] if operands else None
                if isinstance(props, dict) and 'ActualText' in props:
                    marked.append([decode_text(props['ActualText']), None, None])
                else:
                    marked.append(None)
            elif op == 'EMC':
                if marked:
                    m = marked.pop()
                    if m is not None and actual() is None:
                        x, y, eff = m[1] if m[1] else position()
                        out.append(Glyph(x, y, eff, m[0].translate(PUA), len(out), None, m[2]))
        except (TypeError, ValueError, IndexError):
            pass
        operands = []
    return out


def page_lines(pdf, pageno, cache):
    """Return the lines of one page as (column, y, size, text, x, end), in reading order."""
    key = ('lines', pageno)
    if key not in cache:
        cache[key] = _page_lines(pdf, pageno, cache)
    return cache[key]


def _page_lines(pdf, pageno, cache):
    page = pdf.pages[pageno - 1]
    box = pdf.get(page, 'MediaBox') or [0, 0, 411, 595]
    mid = (float(box[0]) + float(box[2])) / 2
    # The stream draws each printed line in one run, so a line is a run of
    # glyphs at one height; a mark or space at the end of a left-column line
    # can sit past the middle of the page and still belongs to that line.
    runs = []
    for g in page_glyphs(pdf, page, cache):
        last = runs[-1][-1] if runs else None
        # A tone mark can be set a few points above its line.
        tol = 6 if MARKS.fullmatch(g.text) or not g.text.replace(REPLACEMENT, '').strip() else 2.5
        if last is None or abs(g.y - runs[-1][0].y) > tol or g.x < last.x - 30 or g.x > last.x + 40:
            runs.append([g])
        else:
            runs[-1].append(g)
    lines = []
    for gs in runs:
        # The typesetter ends every broken line with one space of its own,
        # whether or not the break falls between words (code 32 up to PDF page
        # 209, code 3 after it). Where the break falls at a word space the line
        # ends in two spaces, so exactly one comes off and the other stays.
        if gs and not gs[-1].text.strip():
            gs.pop()
        if not gs:
            continue
        start = next((g.x for g in gs if g.text.strip()), gs[0].x)
        col = 0 if start < mid - 2 else 1
        lines.append((col, gs[0].y, max(g.size for g in gs), ''.join(g.text for g in gs), start,
                      max(g.end for g in gs)))
    # A block set across both columns, such as a quoted psalm, is read after
    # the text of both columns above it and before the text of both below it.
    text_lines = [l for l in lines if 14.5 <= l[2] <= 18.5]
    if text_lines:
        centre = (min(l[4] for l in text_lines) + max(l[5] for l in text_lines)) / 2
        span = sorted((l for l in text_lines if l[4] < centre - 15 and l[5] > centre + 15), key=lambda l: -l[1])
        # The first line of a block can be too short to cross the gutter; it
        # starts at the block's left edge, one line above it, after a gap.
        grown = True
        while grown:
            grown = False
            for l in text_lines:
                if l in span:
                    continue
                below = [b for b in span if 0 < l[1] - b[1] <= 21 and abs(b[4] - l[4]) < 1]
                above = [a for a in text_lines if a[0] == l[0] and a is not l and 0 < a[1] - l[1] <= 21]
                if below and not above:
                    span.append(l)
                    grown = True
        span.sort(key=lambda l: -l[1])
        tops, prev = [], None
        for l in span:
            if prev is None or prev - l[1] > 30:
                tops.append(l[1])
            prev = l[1]

        def band(l):
            above = sum(1 for t in tops if t > l[1] + 1)
            if l in span:
                return 2 * above + 1 if any(abs(t - l[1]) < 1 for t in tops) else 2 * above - 1
            return 2 * above
        lines.sort(key=lambda l: (band(l), l[0] if l not in span else 0, -l[1]))
    return lines


def normalise(text):
    text = text.replace('\ufffd', '')
    text = re.sub(f'([{TONE}])([{UPPER}])', r'\2\1', text)
    return text


# A mark the print sets twice on one letter, or SARA II set over SARA I; the
# glyphs overlap on the page, so the reader sees one mark, and one is kept.
# This is the one correction the extraction makes to the book's own text.
DOUBLED = re.compile(r'([\u0e31\u0e34-\u0e3a\u0e47-\u0e4e])\1|\u0e35\u0e34')
PREFACE = (7, 10)        # บทนำ, the publishers' preface, in PDF pages
CHAPTERS = (16, 1097)    # from the opening of chapter 1 to the end of the text
BODY = (14.5, 17.5)      # body sizes: 15 in the preface, 16 and 17 in the chapters
CHAPTER_NO, TITLE = 72.0, 24.0
MARGINS = (34.0, 45.4, 62.2, 62.4, 73.7)   # body line starts: margin and paragraph indent, verso and recto
INDENTS = (28.3, 24.2)   # paragraph indent in the chapters and in the preface
BASEDON = re.compile(r'^(บทนี้)?อ้างอิงจาก')
SPACES = re.compile(r'[\u2000-\u200a\u00a0 ]+')


class Report:
    def __init__(self):
        self.rows = []

    def note(self, kind, where, text):
        self.rows.append((kind, where, text))

    def write(self, path):
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write('kind\twhere\ttext\n')
            for row in self.rows:
                fh.write('\t'.join(row) + '\n')


def source_tags():
    """Return {'DA 19.1': chapter number} from the English source, in book order."""
    where = {}
    for path in sorted(glob.glob(os.path.join(SOURCE_DIR, 'DA*_en.md'))):
        number = int(re.match(r'DA(\d+)', os.path.basename(path)).group(1))
        for m in re.finditer(r'^## \{(DA [\d.]+)\}', open(path, encoding='utf-8').read(), re.M):
            where[m.group(1)] = number
    return where


def tag_text(m):
    return f'DA {m.group(1) or m.group(3)}.{m.group(2) or m.group(4)}'


# No line of the book starts with a closing bracket, so a tag at a line end
# that lacks one, "{DA 558.4", still ends its paragraph.
TAG_END = re.compile(r'(?:[{(]\s*D\s*A?|(?<![\w{(])DA)\s*\d+\s*\.\s*\d+\s*[})]?\s*$')


def squeeze(text):
    return re.sub(r'[\s\u2000-\u200a\u00a0“”‘’"\'.]+', '', text)


def book_index(pdf, first, last, cache):
    """Return the book's text without spaces, and a count of every tag it prints."""
    text = ''.join(normalise(l[3]) for p in range(first, last + 1) for l in page_lines(pdf, p, cache))
    return squeeze(text), collections.Counter(tag_text(m) for m in TAG_RE.finditer(text))


def read_pages(pdf, first, last, cache, report, index=None, order=None):
    """Return the blocks of a page range in reading order.

    A block is ('chapter', text), ('title', text), ('basedon', text) or
    ('para', text, first page). A paragraph runs to the next {DA} tag; a line
    that stops short of the column's right edge, such as a line of a poem,
    ends in a forced break, and the next line is joined to it with a space.
    """
    blocks = []
    buf, start_page = [], None
    order = order or {}
    last_pos = -1

    def flush(page):
        nonlocal buf, start_page, last_pos
        if buf:
            text = join_lines(buf, page, report)
            blocks.append(('para', text, start_page))
            tags = [tag_text(m) for m in TAG_RE.finditer(text)]
            if tags and tags[-1] in order:
                last_pos = max(last_pos, order[tags[-1]])
        buf, start_page = [], None

    for page in range(first, last + 1):
        lines = page_lines(pdf, page, cache)
        # Chapter numbers, titles and "based on" lines are centred, so some
        # fall in the right-hand column; they head the page, so they go first.
        ornament = any(l[2] == CHAPTER_NO and 'บทที่' not in l[3] for l in lines)
        heads = [l for l in lines if l[2] in (CHAPTER_NO, TITLE) or BASEDON.match(normalise(l[3]).strip())]
        heads.sort(key=lambda l: -l[1])
        body = [l for l in lines if l not in heads]
        # A line stops short when it ends well before its column's right edge,
        # or, for a line set across both columns, before the text's right edge.
        sized = [l for l in body if BODY[0] <= l[2] <= BODY[1]]
        centre = (min(l[4] for l in sized) + max(l[5] for l in sized)) / 2 if sized else 0

        def spans(l):
            return l[4] < centre - 15 and l[5] > centre + 15
        right = {}
        for l in sized:
            if not spans(l):
                right[l[0]] = max(right.get(l[0], l[5]), l[5])
        frame = max((l[5] for l in sized), default=0)
        # A pull quote reprints a sentence of the text in a centred box that
        # crosses the gutter; it is left out of the chapters and reported.
        text_lines = [l for l in lines if 15.5 <= l[2] <= 18.5] or lines
        mid = (min(l[4] for l in text_lines) + max(l[5] for l in text_lines)) / 2 if lines else 205
        quote = [l for l in body if 15.5 <= l[2] <= 18.5 and l[4] < mid - 20 and l[5] > mid + 20
                 and (abs((l[4] + l[5]) / 2 - mid) < 8 or all(abs(l[4] - m) > 0.6 for m in MARGINS))]
        # A Bible passage the text quotes can be centred too. A pull quote is
        # told from it by its tag, which a paragraph of the text also carries,
        # or, where it has no tag, by words the text prints elsewhere or by
        # standing alone on its page.
        if quote:
            # The box's short lines, such as its tag, need not cross the gutter.
            lo, hi = min(l[1] for l in quote) - 25, max(l[1] for l in quote) + 25
            centre = sum((l[4] + l[5]) / 2 for l in quote) / len(quote)
            quote += [l for l in body if l not in quote and lo <= l[1] <= hi and 15.5 <= l[2] <= 18.5
                      and abs((l[4] + l[5]) / 2 - centre) < 6]
            quote.sort(key=lambda l: -l[1])
        if quote and index is not None:
            joined = ''.join(normalise(l[3]) for l in quote)
            tags = [tag_text(m) for m in TAG_RE.finditer(joined)]
            if tags and order and tags[-1] not in order:
                pull = True     # the English has no such paragraph
            elif tags:
                pull = index[1][tags[-1]] >= 2 or order.get(tags[-1], 1e9) < last_pos
            else:
                # A psalm the text quotes twice is still text, so a centred
                # block without a tag is a pull quote only on a page of its own.
                pull = ornament or len(quote) == len([l for l in body if l[2] > 13])
            if not pull:
                quote = []
        if quote:
            report.note('PULL-QUOTE', f'p{page}', SPACES.sub(' ', ' '.join(normalise(l[3]) for l in quote)).strip())
            body = [l for l in body if l not in quote]
        base = {}
        for col, y, size, text, x, end in body:
            if BODY[0] <= size <= BODY[1]:
                base[col] = min(base.get(col, x), x)
        # On a chapter's opening page, centred lines between the title and the
        # first paragraph give the passages the chapter is based on.
        pending = None
        if any(l[2] == TITLE for l in heads):
            first = max((l[1] for l in body if any(abs(l[4] - base.get(l[0], 0) - i) < 3 for i in INDENTS)),
                        default=None)
            lead = [l for l in body if first is not None and l[1] > first + 1]
            if lead:
                text = SPACES.sub(' ', ' '.join(normalise(l[3]) for l in lead)).strip()
                prior = [SPACES.sub(' ', normalise(h[3])).strip() for h in heads if BASEDON.match(normalise(h[3]).strip())]
                heads = [h for h in heads if not BASEDON.match(normalise(h[3]).strip())]
                pending = ('basedon', ' '.join(prior + [text]))
                body = [l for l in body if l not in lead]
        for line in heads + [None] + body:
            if line is None:
                # The "based on" line follows the chapter number and title.
                if pending:
                    blocks.append(pending)
                continue
            col, y, size, text, x, end = line
            text = normalise(text)
            if not text.strip():
                continue
            if size == CHAPTER_NO and 'บทที่' not in text:
                continue        # the ❝ ❞ ornaments of a pull-quote page
            if size == CHAPTER_NO:
                # The last page of a chapter can carry a quotation the
                # publisher set as filler, with no tag; it is not the text.
                if buf and not TAG_END.search(''.join(t for t, _ in buf)):
                    report.note('FILLER', f'p{start_page}', join_lines(buf, page, report))
                    buf, start_page = [], None
                flush(page)
                blocks.append(('chapter', SPACES.sub(' ', text).strip()))
            elif size == TITLE:
                flush(page)
                blocks.append(('title', SPACES.sub(' ', text).strip()))
            elif BASEDON.match(text.strip()) and not buf:
                blocks.append(('basedon', SPACES.sub(' ', text).strip()))
            elif BODY[0] <= size <= BODY[1]:
                if not buf:
                    start_page = page
                edge = frame if spans((col, y, size, text, x, end)) else right.get(col, end)
                buf.append((text, end < edge - 12))
                if TAG_END.search(''.join(t for t, _ in buf[-2:])):
                    flush(page)
            elif size != 12.0:
                report.note('SKIPPED', f'p{page}', f'{size}pt {text[:60]}')
    if buf:
        report.note('NO-TAG', f'p{start_page}', join_lines(buf, last, report)[:80])
    flush(last)
    return blocks


def join_lines(lines, page, report):
    out = ''
    short = False
    for line, line_short in lines:
        if short and out and not out.endswith(' '):
            out += ' '
        elif out.endswith('-') and THAI.match(out[-2:-1] or '') and THAI.match(line[:1]):
            report.note('HYPHEN', f'p{page}', out[-12:] + line[:12])
            out = out[:-1]
        out += line
        short = line_short
    out = TAG_RE.sub(lambda m: '{' + tag_text(m) + '}', out)
    return SPACES.sub(' ', out).strip()


TOC = (11, 15)           # สารบัญ, the table of contents, in PDF pages


def toc_titles(pdf, cache):
    """Return {chapter number: title} from the table of contents.

    Five chapter openings set their titles in a display font whose glyphs map
    to no text, so the titles are taken from the contents pages for every
    chapter, where each sits on one line as tab, number, tab, title.
    """
    titles = {}
    for p in range(TOC[0], TOC[1] + 1):
        for l in page_lines(pdf, p, cache):
            m = re.match(r'^\t?(\d+)\t(.+?)(\t\d+)?$', normalise(l[3]).rstrip())
            if m:
                titles[int(m.group(1))] = SPACES.sub(' ', m.group(2)).strip()
    return titles


def renumber(chapters, path, report):
    """Apply the corrections in RENUMBERED.tsv to the printed codes.

    Each row names the chapter file, a code (with #1 or #2 where the print
    carries it twice), the action and the code or codes it becomes:
    RECODE gives the paragraph another code; SPLIT gives, for each new
    paragraph after the first, the words it begins with, each searched for
    after the one before; EMPTY puts an empty paragraph with the new code
    after the named one, for an English paragraph the Thai does not render.
    A line beginning with # starts a new stage: the rows after it name the
    codes as the stages before left them.
    """
    stages = [[]]
    for line in list(open(path, encoding='utf-8'))[1:]:
        if line.startswith('#'):
            stages.append([])
        elif line.strip():
            stages[-1].append(line.rstrip('\n').split('\t'))
    for rows in stages:
        for f, printed, action, codes, splits in rows:
            number = 0 if f == 'DA00' else int(f[2:])
            paras = chapters[number]['paras']
            tag, _, nth = printed.partition('#')
            hits = [i for i, (t, _) in enumerate(paras) if t == tag]
            if not hits:
                sys.exit(f'RENUMBERED.tsv: {f} has no paragraph {printed}')
            i = hits[int(nth) - 1 if nth else 0]
            codes = codes.split('|')
            if action == 'RECODE':
                paras[i] = ('!' + codes[0], paras[i][1])
            elif action == 'SPLIT':
                text, parts, at = paras[i][1], [], 0
                for word in splits.split('|'):
                    cut = text.find(word, at + 1)
                    if cut < 0:
                        sys.exit(f'RENUMBERED.tsv: {f} {printed} has no "{word}" to split at')
                    parts.append(text[at:cut].strip())
                    at = cut
                parts.append(text[at:].strip())
                paras[i:i + 1] = [('!' + c, t) for c, t in zip(codes, parts)]
            elif action == 'EMPTY':
                paras.insert(i + 1, ('!' + codes[0], ''))
            report.note('RENUMBERED', f, f'{printed} {action} {" + ".join(codes)}')
        for ch in chapters.values():
            ch['paras'] = [(t[1:] if t and t.startswith('!') else t, x) for t, x in ch['paras']]


def write_chapter(path, header, title, basedon, paras):
    out = header + ['', f'// TITLE: {title}']
    if basedon:
        # The preface's line under its title says where it comes from.
        label = 'SUBTITLE' if title == 'บทนำ' else 'BASEDON'
        out.append(f'// {label}: {basedon}')
    for tag, text in paras:
        body = TAG_RE.sub('', text).strip().translate(ESCAPE) if tag else text.translate(ESCAPE)
        if tag and not body:
            # An English paragraph the Thai does not render keeps its place.
            out += ['', f'// {{{tag}}}', '', f'#EGW[\\{{{tag}\\}}]']
        elif tag:
            out += ['', f'// {{{tag}}}', '', body + f' #EGW[\\{{{tag}\\}}]']
        else:
            out += ['', '// no tag in the print', '', body]
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(out) + '\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('qdf')
    ap.add_argument('out', nargs='?')
    ap.add_argument('--report')
    ap.add_argument('--renumber', help='RENUMBERED.tsv: corrections to the printed codes')
    ap.add_argument('--pdf-name', default='AW_ผู้พึงปรารถนาของปวงชน (72 res).pdf')
    ap.add_argument('--dump', nargs=2, type=int, metavar=('FIRST', 'LAST'))
    args = ap.parse_args()
    pdf = Pdf(args.qdf)
    cache = {}
    if args.dump:
        for p in range(args.dump[0], args.dump[1] + 1):
            print(f'=== page {p}')
            for col, y, size, text, x, end in page_lines(pdf, p, cache):
                print(f'{col} {y:6.1f} {size:5.1f} {x:6.1f} {end:6.1f} |{normalise(text)}|')
        return

    report = Report()
    where = source_tags()
    seen = collections.Counter()
    chapters = collections.OrderedDict()   # number -> dict(title, basedon, paras, pages)

    def take(blocks, number, title_parts):
        ch = chapters.setdefault(number, {'title': [], 'basedon': None, 'paras': [], 'pages': []})
        ch['title'] += title_parts
        for b in blocks:
            if b[0] == 'basedon':
                ch['basedon'] = b[1]
            elif b[0] == 'para':
                tags = [tag_text(m) for m in TAG_RE.finditer(b[1])]
                tag = tags[-1] if tags else None
                if len(tags) > 1:
                    report.note('MULTI-TAG', f'p{b[2]}', ' '.join(tags))
                if tag:
                    seen[tag] += 1
                    if tag not in where:
                        report.note('UNKNOWN-TAG', f'p{b[2]}', tag)
                    elif where[tag] != number:
                        report.note('WRONG-CHAPTER', f'p{b[2]}', f'{tag} is in English chapter {where[tag]}, print chapter {number}')
                for m in DOUBLED.finditer(b[1]):
                    report.note('DOUBLED-MARK', f'p{b[2]}', b[1][max(0, m.start() - 10):m.end() + 10]
                                + ' -> one ' + m.group(0)[0])
                ch['paras'].append((tag, DOUBLED.sub(lambda m: m.group(0)[0], b[1])))
                ch['pages'].append(b[2])

    index = book_index(pdf, CHAPTERS[0], CHAPTERS[1], cache)
    pre = read_pages(pdf, PREFACE[0], PREFACE[1], cache, report)
    take([b for b in pre if b[0] in ('para', 'basedon')], 0, [b[1] for b in pre if b[0] == 'title'])
    number = None
    pending_title = []
    order = {t: i for i, t in enumerate(where)}
    for b in read_pages(pdf, CHAPTERS[0], CHAPTERS[1], cache, report, index, order):
        if b[0] == 'chapter':
            m = re.search(r'(\d+)', b[1])
            if m:
                number = int(m.group(1))
                pending_title = []
            continue
        if b[0] == 'title':
            take([], number, [b[1]])
            continue
        take([b], number, [])

    for tag, n in seen.items():
        if n > 1:
            report.note('DUPLICATE-TAG', tag, str(n))
    for tag in where:
        if tag not in seen:
            report.note('MISSING-TAG', tag, f'English chapter {where[tag]}')

    if args.renumber:
        renumber(chapters, args.renumber, report)
    toc = toc_titles(pdf, cache)
    if args.out:
        os.makedirs(args.out, exist_ok=True)
        for number, ch in chapters.items():
            name = 'DA00_preface_print_th.typ' if number == 0 else f'DA{number:02d}_print_th.typ'
            pages = ch['pages']
            header = [f'// Thai printed edition, ผู้พึงปรารถนาของปวงชน (2023), PDF pages {min(pages)}-{max(pages)} of {args.pdf_name}.',
                      '// Extracted from the print, not translated or edited.']
            title = ' '.join(ch['title'])
            if number:
                # The opening page is followed unless its title is in the display
                # font that maps to no text; the contents has typos of its own.
                if len(re.findall('[\u0e01-\u0e2e]', title)) < 2 and number in toc:
                    report.note('TITLE', f'chapter {number}', f'taken from the contents: {toc[number]}')
                    title = toc[number]
                elif squeeze(toc.get(number, '')) != squeeze(title):
                    report.note('TITLE', f'chapter {number}', f'contents: {toc.get(number)} | opening page: {title}')
                title = f'{number} {title}'
            write_chapter(os.path.join(args.out, name), header, title, ch['basedon'], ch['paras'])
    if args.report:
        report.write(args.report)
    kinds = collections.Counter(r[0] for r in report.rows)
    print(f'{len(chapters)} chapters, {sum(len(c["paras"]) for c in chapters.values())} paragraphs, '
          f'{len(seen)} distinct tags of {len(where)} in the English source; report: {dict(kinds)}')


if __name__ == '__main__':
    main()
