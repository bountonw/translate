#!/usr/bin/env python3
"""Build an EPUB 3 of a Thai book written in Markdown, such as th/MB.

Usage, from the repository's top folder (the script writes only the file named by --out):
    python3 -B th/MB/assets/epub/build_mb_epub.py --out ~/MB_th.epub

Reads the book's metadata.yaml and its chapters in 03_public: "## {MB 1.1}" lines are
navigation only, "### " lines are subheadings, "> " lines are lines of a poem ("> > " an
indented line, a bare ">" a gap), "[^1]" a note. The translator field of metadata.yaml is
never read into the book, and the build stops if any word of it reaches a page.

Line breaks. Thai has no spaces between words, so each reading app needs a place to end a
line. Two things are added, neither a character:
- the words of th/assets/typeset/thai-breaks.txt stay whole, through the website's own
  websites/assets/scripts/thai_words.py, as on the web pages; the syllable breaks that print
  marks with a hyphen are left out, so a listed word never breaks;
- <wbr/> at every other word boundary that ICU (node's Intl.Segmenter, the word list of
  Chrome) finds between two Thai letters, for reading apps with no Thai word list of their own.

The cover is a JPEG or PNG file, or an EPUB whose cover picture is taken; a PNG is saved as
JPEG. The default is the cover picture of th/MB/04_pdf/MBTh v6.5.epub; with --text-cover,
the cover page is the title in text.
The same input gives the same file, byte for byte, so its hash can be published. MODIFIED
below is the time written into the file: change it for a new edition.
"""
import argparse
import html
import io
import json
import os
import re
import subprocess
import sys
import uuid
import zipfile
from xml.sax.saxutils import escape

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
# th/MB/assets/epub -> the repository's top folder
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
COVER = 'th/MB/04_pdf/MBTh v6.5.epub'
MODIFIED = '2026-11-12T00:00:00Z'

FONT_DIR = 'th/assets/fonts/saraban'
FONTS = [('Sarabun-Regular.ttf', 'normal', 'normal'), ('Sarabun-Bold.ttf', 'bold', 'normal'),
         ('Sarabun-Italic.ttf', 'normal', 'italic'), ('Sarabun-BoldItalic.ttf', 'bold', 'italic')]
BREAKS = 'th/assets/typeset/thai-breaks.txt'
EXTRAS = {'dedication': 'MB_00a_dedication_th.md', 'preface': 'MB_00c_preface_th.md'}
WORDS = {'toc': 'สารบัญ'}
LICENCE = 'https://creativecommons.org/licenses/by-nd/4.0/'

CSS = """{faces}
body {{ font-family: "Sarabun", serif; line-height: 1.7; margin: 0; padding: 0; }}
p {{ margin: 0 0 0.8em 0; text-align: left; }}
span.nb {{ white-space: nowrap; }}
h1 {{ font-size: 1.5em; line-height: 1.5; text-align: center; margin: 0.8em 0 1.2em 0; font-weight: bold; }}
h1 .chapter-number {{ display: block; font-size: 1.6em; font-weight: normal; line-height: 1.3; }}
h1 .chapter-name {{ display: block; }}
h2 {{ font-size: 1.1em; line-height: 1.6; font-weight: bold; margin: 1.4em 0 0.6em 0;
      page-break-after: avoid; break-after: avoid; }}
span.egw {{ font-size: 0.75em; color: #777777; white-space: nowrap; }}
sup {{ font-size: 0.75em; line-height: 0; }}
div.poem {{ margin: 0 0 0.8em 1.5em; }}
div.poem p {{ margin: 0; }}
div.poem p.in {{ margin-left: 2em; }}
div.poem p.gap {{ margin-top: 0.8em; }}
section.notes {{ margin-top: 2em; border-top: 1px solid #999999; padding-top: 0.6em; font-size: 0.9em; }}
aside p {{ margin: 0 0 0.6em 0; }}
section.titlepage, section.textcover {{ text-align: center; }}
p.book-title {{ font-size: 1.9em; font-weight: bold; line-height: 1.5; margin: 2em 0 0.3em 0; text-align: center; }}
p.book-title-en {{ font-size: 1.3em; margin-bottom: 2em; text-align: center; }}
p.author {{ font-size: 1.2em; margin-bottom: 0.2em; text-align: center; }}
p.author-en {{ font-style: italic; margin-bottom: 3em; text-align: center; }}
section.rights p {{ font-size: 0.85em; margin: 0 0 0.4em 0; }}
section.rights p.gap {{ margin-top: 1.2em; }}
section.dedication {{ padding-top: 20%; text-align: center; }}
section.dedication p {{ font-style: italic; font-size: 1.1em; text-align: center; }}
figure.cover {{ margin: 0; padding: 0; text-align: center; }}
figure.cover img {{ max-width: 100%; max-height: 100%; }}
nav#toc ol {{ list-style: none; margin: 0; padding: 0; }}
nav#toc li {{ margin: 0 0 0.5em 0; }}
"""

# Thai letters that may stand on either side of a line break: the consonants and the vowels
# written before them. A sign written above, below or after a letter, ๆ and ฯ never start a line.
THAI_START = re.compile('[ก-ฮเ-ไ]')
THAI_LETTER = re.compile('[ก-ฮะ-ฺๅ็-๎]')
# a letter made silent by ์ (U+0E4C) belongs to the syllable before it
SILENT = re.compile('[ก-ฮ][ัิ-ฺ็-๋]*์')
SEGMENTER = """
const s = new Intl.Segmenter('th', {granularity: 'word'});
let data = ''; process.stdin.on('data', d => data += d);
process.stdin.on('end', () => {
  const out = JSON.parse(data).map(t => {
    const cuts = []; let n = 0;
    for (const p of s.segment(t)) { n += [...p.segment].length; cuts.push(n); }
    return cuts;
  });
  process.stdout.write(JSON.stringify(out));
});
"""


def read_yaml(lines):
    """The simple YAML the books use: nested 'key: value' lines, read into dotted keys."""
    values, path = {}, []
    for line in lines:
        if not line.strip() or line.strip() in ('---', '...') or line.lstrip().startswith('#'):
            continue
        indent = len(line) - len(line.lstrip())
        key, _, value = line.strip().partition(':')
        path = [(i, k) for i, k in path if i < indent] + [(indent, key.strip())]
        if value.strip():
            values['.'.join(k for _, k in path)] = value.strip()
    return values


def front_matter(text):
    _, head, body = text.split('---', 2)
    return read_yaml(head.split('\n')), body


def inline(text, code, notes):
    """One line of Markdown text as XHTML: *emphasis*, [^n] notes, {MB 1.1} references."""
    text = escape(text.strip())
    text = re.sub(r'\*(\S(?:[^*]*\S)?)\*', r'<em>\1</em>', text)
    text = re.sub(r'\[\^(\w+)\]', lambda m: (notes.setdefault(m[1], len(notes) + 1) and
                  f'<sup><a epub:type="noteref" role="doc-noteref" id="nr{notes[m[1]]}" href="#fn{notes[m[1]]}">{notes[m[1]]}</a></sup>'), text)
    return re.sub(r'\{(%s [^}]+)\}' % code, r'<span class="egw">{\1}</span>', text)


def para_id(text, code):
    m = re.search(r'\{%s ([^}]+)\}\s*$' % code, text)
    return f' id="{code}{m[1]}"' if m else ''


def convert(body, code):
    """The chapter body as a list of XHTML blocks, and its notes."""
    notes, defs, blocks = {}, {}, []
    for block in re.split(r'\n\s*\n', body.strip()):
        lines = [l for l in block.split('\n') if l.strip()]
        if not lines:
            continue
        first = lines[0].strip()
        if re.fullmatch(r'## \{[^}]+\}', first) and len(lines) == 1:
            continue
        if first.startswith('## {'):
            lines = lines[1:]
            first = lines[0].strip()
        if first.startswith('### '):
            blocks.append(('h2', f'<h2>{inline(first[4:], code, notes)}</h2>'))
            lines = lines[1:]
            if not lines:
                continue
            first = lines[0].strip()
        m = re.match(r'\[\^(\w+)\]:\s*(.*)', first)
        if m:
            defs[m[1]] = ' '.join([m[2]] + [l.strip() for l in lines[1:]])
            continue
        if first.startswith('>'):
            out, gap = [], False
            for l in lines:
                l = l.strip()
                if not l.startswith('>'):
                    raise SystemExit(f'a poem line without ">": {l[:60]}')
                rest = l[1:].strip()
                if not rest:
                    gap = True
                    continue
                cls = 'in' if rest.startswith('>') else ''
                rest = rest.lstrip('>').strip()
                cls = ' '.join(c for c in (cls, 'gap' if gap else '') if c)
                out.append(f'<p class="{cls}">' if cls else '<p>')
                out[-1] += inline(rest, code, notes) + '</p>'
                gap = False
            blocks.append(('poem', f'<div class="poem"{para_id(lines[-1], code)}>\n' + '\n'.join(out) + '\n</div>'))
            continue
        if any(l.lstrip().startswith(('#', '- ', '* ', '|')) for l in lines):
            raise SystemExit(f'a Markdown form the build does not know: {first[:60]}')
        text = ' '.join(l.strip() for l in lines)
        blocks.append(('p', f'<p{para_id(text, code)}>{inline(text, code, notes)}</p>'))
    if set(notes) != set(defs):
        raise SystemExit(f'notes and their texts differ: {sorted(notes)} {sorted(defs)}')
    note_html = [(notes[k], inline(defs[k], code, {})) for k in sorted(defs, key=lambda k: notes[k])]
    return blocks, note_html


def segment(texts):
    """ICU's word ends in each text, as character counts from its start."""
    run = subprocess.run(['node', '-e', SEGMENTER], input=json.dumps(texts), capture_output=True,
                         text=True, check=True)
    return json.loads(run.stdout)


TAG = re.compile(r'(<[^>]*>)')


def add_breaks(fragment, cuts_of, stats):
    """<wbr/> at each ICU word end between two Thai letters, outside the words kept whole."""
    parts = TAG.split(fragment)
    plain = ''.join(html.unescape(p) for p in parts if not p.startswith('<'))
    cuts = set(cuts_of(plain))
    out, pos, in_nb = [], 0, False
    for p in parts:
        if p.startswith('<'):
            if p == '<span class="nb">':
                in_nb = 'first'
            elif p == '</span>' and in_nb:
                in_nb = False
            out.append(p)
            continue
        text = html.unescape(p)
        piece = []
        for i, ch in enumerate(text):
            at = pos + i
            if (at in cuts and at > 0 and THAI_START.match(ch) and THAI_LETTER.match(plain[at - 1])
                    and not 'เ' <= plain[at - 1] <= 'ไ' and not SILENT.match(plain, at)):
                if in_nb == 'first' and i == 0:
                    out.insert(len(out) - 1, '<wbr/>')
                    stats['wbr_word'] += 1
                elif not in_nb:
                    piece.append('<wbr/>')
                    stats['wbr_word'] += 1
            piece.append(escape(ch))
        if in_nb == 'first':
            in_nb = True
        out.append(''.join(piece))
        pos += len(text)
    return re.sub(r'(<wbr/>)+', '<wbr/>', ''.join(out))


def page(title, body):
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE html>\n'
            '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" '
            'lang="th" xml:lang="th">\n<head>\n<meta charset="utf-8"/>\n'
            f'<title>{escape(title)}</title>\n'
            '<link rel="stylesheet" type="text/css" href="../css/book.css"/>\n</head>\n<body>\n'
            f'{body}\n</body>\n</html>\n')


def cover_jpeg(path):
    """The cover as JPEG bytes, from a picture file or from an EPUB's cover picture."""
    if path.endswith('.epub'):
        with zipfile.ZipFile(path) as z:
            opf_name = re.search(r'full-path="([^"]+)"', z.read('META-INF/container.xml').decode()).group(1)
            opf = z.read(opf_name).decode('utf-8')
            item = re.search(r'<item [^>]*properties="cover-image"[^>]*>', opf).group()
            href = html.unescape(re.search(r'href="([^"]+)"', item).group(1))
            data = z.read(os.path.normpath(os.path.join(os.path.dirname(opf_name), href)).replace(os.sep, '/'))
    else:
        data = open(path, 'rb').read()
    if data[:3] == b'\xff\xd8\xff':
        return data
    from PIL import Image
    buf = io.BytesIO()
    Image.open(io.BytesIO(data)).convert('RGB').save(buf, 'JPEG', quality=88, optimize=True)
    return buf.getvalue()


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--repo', default=REPO, help='the repository; default the one holding this script')
    parser.add_argument('--book', default='th/MB')
    parser.add_argument('--out', required=True)
    parser.add_argument('--cover', default=COVER,
                        help='JPEG, PNG, or an EPUB whose cover picture is taken; a path inside the repository')
    parser.add_argument('--text-cover', action='store_true', help='a cover page of the title in text, no picture')
    parser.add_argument('--extras', default='', help='front pages from the book\'s assets: dedication,preface')
    parser.add_argument('--modified', default=MODIFIED, help='the time written into the file, as 2026-11-09T00:00:00Z')
    args = parser.parse_args()

    repo = os.path.abspath(args.repo)
    if args.text_cover:
        args.cover = None
    elif args.cover:
        args.cover = os.path.join(repo, args.cover)
    sys.path.insert(0, os.path.join(repo, 'websites', 'assets', 'scripts'))
    try:
        import thai_words
    except ImportError:
        raise SystemExit('websites/assets/scripts/thai_words.py is missing; it comes with the Thai pages of the website')
    book_dir = os.path.join(repo, args.book)
    code = os.path.basename(args.book.rstrip('/'))
    meta = read_yaml(open(os.path.join(book_dir, 'metadata.yaml'), encoding='utf-8'))
    title, title_en = meta['book.title.th'], meta['book.title.en']
    author, author_en = meta['author.th'], meta['author.en']
    withheld = [w for k, v in meta.items() if k.startswith('translator.') for w in v.split() if len(w) > 2]
    tree = thai_words.word_tree(open(os.path.join(repo, BREAKS), encoding='utf-8').read(), code, BREAKS)

    modified = args.modified
    date_time = tuple(int(x) for x in re.findall(r'\d+', modified)[:6])
    identifier = 'urn:uuid:' + str(uuid.uuid5(uuid.NAMESPACE_URL, f'{args.book}#epub'))
    stats = dict(wbr_word=0, wbr_listed=0, kept=0)

    # chapters, then the front pages the book's assets hold
    chapters = []
    folder = os.path.join(book_dir, '03_public')
    for name in sorted(os.listdir(folder)):
        if name.endswith('.md'):
            head, body = front_matter(open(os.path.join(folder, name), encoding='utf-8').read())
            n = int(head['chapter.number'])
            blocks, notes = convert(body, code)
            chapters.append(dict(n=n, file=f'{code}{n:02d}.xhtml', name=head['chapter.title.th'],
                                 blocks=blocks, notes=notes))
    chapters.sort(key=lambda c: c['n'])
    extras = {}
    for key in [k for k in args.extras.split(',') if k]:
        head, body = front_matter(open(os.path.join(book_dir, 'assets', EXTRAS[key]), encoding='utf-8').read())
        blocks, notes = convert(body, code)
        extras[key] = dict(file=f'{key}.xhtml', name=head['chapter.title.th'], blocks=blocks, notes=notes)

    # the copyright line, address, licence and Bible notices of the print's credits page;
    # the people it names, from the line "Translated from" on, stay out
    credits = open(os.path.join(book_dir, 'assets', 'MB_000a_CreditsPage_th.txt'), encoding='utf-8').read().split('\n')
    start = next(i for i, l in enumerate(credits) if l.startswith('สงวนลิขสิทธิ์ ©'))
    end = next(i for i, l in enumerate(credits) if i > start and l.startswith('Translated from'))
    rights = credits[start:end]
    start = next(i for i, l in enumerate(credits) if l.startswith('พระคัมภีร์ที่ใช้เป็นหลัก'))
    end = next(i for i, l in enumerate(credits) if i > start and l.startswith('Printed'))
    rights += [''] + credits[start:end]
    lines, gap = [], False
    for l in rights:
        if not l.strip():
            gap = True
            continue
        text = escape(l.strip()).replace(LICENCE, f'<a href="{LICENCE}">{LICENCE}</a>')
        lines.append(('p', f'<p class="gap">{text}</p>' if gap else f'<p>{text}</p>'))
        gap = False
    front = dict(name=escape(title), blocks=lines, notes=[])

    # every Thai text the reader sees, kept whole where listed, then ICU's word ends
    def fragments():
        for doc in chapters + list(extras.values()) + [front]:
            yield doc, 'name', None
            for i in range(len(doc['blocks'])):
                yield doc, 'blocks', i
            for i in range(len(doc['notes'])):
                yield doc, 'notes', i
    marked = []
    for doc, field, i in fragments():
        value = doc[field] if i is None else doc[field][i][1]
        # the website marks a kept word <span class="w">; the EPUB's stylesheet names it nb
        kept = thai_words.keep_whole(value, tree).replace(thai_words.OPEN, '<span class="nb">')
        stats['kept'] += kept.count('<span class="nb">')
        # print breaks a listed word at its syllables with a hyphen; a reading app would break
        # there with no hyphen, so in the EPUB a listed word stays whole in one span
        stats['wbr_listed'] += kept.count('</span>&shy;<span class="nb">')
        kept = kept.replace('</span>&shy;<span class="nb">', '')
        if '&shy;' in kept:
            raise SystemExit(f'a soft hyphen the build does not know: {kept[:80]}')
        marked.append((doc, field, i, kept))
    plains = [''.join(html.unescape(p) for p in TAG.split(k) if not p.startswith('<')) for *_, k in marked]
    cut_lists = dict(zip(plains, segment(plains)))
    for doc, field, i, kept in marked:
        value = add_breaks(kept, lambda t: cut_lists[t], stats)
        if i is None:
            doc['marked_name'] = value
        else:
            doc[field][i] = (doc[field][i][0], value)

    def body_of(doc, kind, heading):
        notes = ''
        if doc['notes']:
            notes = (f'<section class="notes" epub:type="footnotes" role="doc-endnotes">\n' + '\n'.join(
                f'<aside epub:type="footnote" role="doc-footnote" id="fn{k}"><p><a href="#nr{k}">{k}</a> {t}</p></aside>'
                for k, t in doc['notes']) + '\n</section>')
        return (f'<section {kind}>\n{heading}\n' + '\n'.join(b for _, b in doc['blocks']) + f'\n{notes}\n</section>')

    files = {}
    faces = '\n'.join(f'@font-face {{ font-family: "Sarabun"; font-weight: {w}; font-style: {s}; '
                      f'src: url("../fonts/{f}"); }}' for f, w, s in FONTS)
    files['OEBPS/css/book.css'] = CSS.format(faces=faces).encode('utf-8')
    for f, _, _ in FONTS:
        files[f'OEBPS/fonts/{f}'] = open(os.path.join(repo, FONT_DIR, f), 'rb').read()

    def add(name, doc_title, body):
        files[f'OEBPS/text/{name}'] = page(doc_title, body).encode('utf-8')

    spine, manifest = [], []
    if args.cover:
        files['OEBPS/images/cover.jpg'] = cover_jpeg(args.cover)
        add('cover.xhtml', title, f'<section epub:type="cover"><figure class="cover"><img src="../images/cover.jpg" '
                                  f'alt="{escape(title)}" role="doc-cover"/></figure></section>')
        manifest.append('<item id="cover-image" href="images/cover.jpg" media-type="image/jpeg" properties="cover-image"/>')
    else:
        add('cover.xhtml', title, f'<section class="textcover" epub:type="cover">\n<p class="book-title">{front["marked_name"]}</p>\n'
                                  f'<p class="author">{author}</p>\n</section>')
    spine.append('cover')
    add('title.xhtml', title,
        f'<section class="titlepage" epub:type="titlepage">\n<p class="book-title">{front["marked_name"]}</p>\n'
        f'<p class="book-title-en" lang="en" xml:lang="en">{title_en}</p>\n<p class="author">{author}</p>\n'
        f'<p class="author-en" lang="en" xml:lang="en">{author_en}</p>\n</section>')
    spine.append('title')
    rights_html = '\n'.join(b for _, b in front['blocks'])
    if f'<a href="{LICENCE}">' not in rights_html:
        raise SystemExit('the licence address was not found on the rights page')
    add('rights.xhtml', title, '<section class="rights" epub:type="copyright-page">\n' + rights_html + '\n</section>')
    spine.append('rights')

    toc = []
    if 'dedication' in extras:
        d = extras['dedication']
        add(d['file'], d['name'], '<section class="dedication" epub:type="dedication" role="doc-dedication">\n'
            + '\n'.join(b for _, b in d['blocks']) + '\n</section>')
        spine.append('dedication')
    spine.append('nav')
    if 'preface' in extras:
        d = extras['preface']
        add(d['file'], d['name'], body_of(d, 'epub:type="preface" role="doc-preface"',
                                          f'<h1><span class="chapter-name">{d["marked_name"]}</span></h1>'))
        spine.append('preface')
        toc.append((d['file'], d['name'], d['marked_name']))
    for c in chapters:
        add(c['file'], f'{c["n"]}. {c["name"]}', body_of(
            c, 'epub:type="chapter" role="doc-chapter"',
            f'<h1><span class="chapter-number">{c["n"]}</span> <span class="chapter-name">{c["marked_name"]}</span></h1>'))
        spine.append(f'ch{c["n"]:02d}')
        toc.append((c['file'], f'{c["n"]}. {c["name"]}', f'{c["n"]}. {c["marked_name"]}'))
    first = chapters[0]
    add('nav.xhtml', WORDS['toc'],
        f'<nav epub:type="toc" id="toc" role="doc-toc">\n<h1>{WORDS["toc"]}</h1>\n<ol>\n'
        + '\n'.join(f'<li><a href="{f}">{m}</a></li>' for f, _, m in toc) + '\n</ol>\n</nav>\n'
        f'<nav epub:type="landmarks" hidden="hidden"><ol>\n<li><a epub:type="cover" href="cover.xhtml">{title}</a></li>\n'
        f'<li><a epub:type="toc" href="nav.xhtml">{WORDS["toc"]}</a></li>\n'
        f'<li><a epub:type="bodymatter" href="{first["file"]}">{first["n"]}. {first["name"]}</a></li>\n</ol></nav>')
    files['OEBPS/toc.ncx'] = (
        '<?xml version="1.0" encoding="UTF-8"?>\n<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1" xml:lang="th">\n'
        f'<head><meta name="dtb:uid" content="{identifier}"/></head>\n<docTitle><text>{title}</text></docTitle>\n<navMap>\n'
        + '\n'.join(f'<navPoint id="n{i}" playOrder="{i}"><navLabel><text>{escape(t)}</text></navLabel>'
                    f'<content src="text/{f}"/></navPoint>' for i, (f, t, _) in enumerate(toc, 1))
        + '\n</navMap>\n</ncx>\n').encode('utf-8')

    ids = {'cover': 'cover.xhtml', 'title': 'title.xhtml', 'rights': 'rights.xhtml', 'nav': 'nav.xhtml'}
    ids.update({k: v['file'] for k, v in extras.items()})
    ids.update({f'ch{c["n"]:02d}': c['file'] for c in chapters})
    manifest = (['<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>',
                 '<item id="css" href="css/book.css" media-type="text/css"/>'] + manifest
                + [f'<item id="{k}" href="text/{v}" media-type="application/xhtml+xml"'
                   + (' properties="nav"' if k == 'nav' else '') + '/>' for k, v in ids.items()]
                + [f'<item id="font{i}" href="fonts/{f}" media-type="font/ttf"/>' for i, (f, _, _) in enumerate(FONTS)])
    given, _, surname = author_en.rpartition(' ')
    nl = '\n'
    files['OEBPS/package.opf'] = f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="book-id" xml:lang="th" prefix="ibooks: http://vocabulary.itunes.apple.com/rdf/ibooks/vocabulary-extensions-1.0/">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:identifier id="book-id">{identifier}</dc:identifier>
<dc:title id="book-title">{title}</dc:title>
<meta refines="#book-title" property="alternate-script" xml:lang="en">{title_en}</meta>
<dc:creator id="creator">{author}</dc:creator>
<meta refines="#creator" property="role" scheme="marc:relators">aut</meta>
<meta refines="#creator" property="alternate-script" xml:lang="en">{author_en}</meta>
<meta refines="#creator" property="file-as" xml:lang="en">{surname}, {given}</meta>
<dc:language>th</dc:language>
<dc:date>{modified[:10]}</dc:date>
<dc:rights>CC BY-ND 4.0 https://creativecommons.org/licenses/by-nd/4.0/</dc:rights>
<dc:source>{title_en}</dc:source>
<meta property="dcterms:modified">{modified}</meta>
<meta property="ibooks:specified-fonts">true</meta>
{'<meta name="cover" content="cover-image"/>' if args.cover else ''}
</metadata>
<manifest>
{nl.join(manifest)}
</manifest>
<spine toc="ncx">
{nl.join(f'<itemref idref="{s}"/>' for s in spine)}
</spine>
</package>
""".encode('utf-8')
    files['META-INF/container.xml'] = (
        '<?xml version="1.0" encoding="UTF-8"?>\n<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n'
        '<rootfiles><rootfile full-path="OEBPS/package.opf" media-type="application/oebps-package+xml"/></rootfiles>\n</container>\n').encode('utf-8')

    for name, data in files.items():
        if name.endswith(('.xhtml', '.opf', '.ncx')):
            text = data.decode('utf-8')
            hit = [w for w in withheld if w in text]
            if hit:
                raise SystemExit(f'{name} holds a word of the translator field of metadata.yaml; nothing written')
            if re.search('[\u0e50-\u0e59\u00ad\u200b-\u200d\u2060\ufeff]', text):
                raise SystemExit(f'{name} holds a Thai digit or an invisible character; nothing written')

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with zipfile.ZipFile(args.out, 'w') as z:
        def put(name, data, method):
            info = zipfile.ZipInfo(name, date_time=date_time)
            info.compress_type = method
            info.external_attr = 0o644 << 16
            info.create_system = 3
            z.writestr(info, data, compresslevel=9 if method == zipfile.ZIP_DEFLATED else None)
        put('mimetype', b'application/epub+zip', zipfile.ZIP_STORED)
        for name in sorted(files):
            put(name, files[name], zipfile.ZIP_DEFLATED)
    print(f'{args.out}: {os.path.getsize(args.out)} bytes, {len(chapters)} chapters, extras {sorted(extras) or "none"}, '
          f'cover {"picture" if args.cover else "text"}, modified {modified}')
    print(f'words kept whole {stats["kept"]}; syllable breaks of listed words joined {stats["wbr_listed"]}; '
          f'<wbr/> at ICU word ends {stats["wbr_word"]}')


if __name__ == '__main__':
    main()
