"""Build one book's web pages from its chapter files.

Usage, from the repository root:
    python3 websites/assets/scripts/build_book.py lo/GC

Reads the book's metadata.yaml and its chapters in 03_public/, and writes
one page per chapter into <site>/<BOOK>/chapters/, named from the chapter
number and English title (01_the_destruction_of_jerusalem.html). It also
rewrites the chapter list in <site>/<BOOK>/index.html, then runs
check_book.py on the result. For a Lao book, lao_words.py marks every word so
lines break only where the print dictionaries allow. The page header, footer and page words come
from the layout folder of the book's language, such as layout/lo/, and are
shared by every book in that language; the header opens every page with a
link to the site's home page. Exits 1 when the check finds a problem.
Needs the Python-Markdown library (python-markdown).
"""
import argparse
import hashlib
import os
import re
import sys

import markdown

ASSETS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(os.path.dirname(ASSETS), 'laoegw')
LAYOUT = os.path.join(ASSETS, 'layout')


def read_yaml(lines):
    """The simple YAML the books use: nested 'key: value' lines, read into
    dotted keys such as 'chapter.title.lo'."""
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
    """Split a chapter file into its front matter (as dotted keys) and body."""
    _, head, body = text.split('---', 2)
    return read_yaml(head.split('\n')), body


def clean_tex(text):
    """Remove the TeX the print build uses. \\p{} goes first, since it can
    sit inside \\lw{}, as in \\lw{ເລັກ\\p{200}ນ້ອຍ}."""
    text = re.sub(r'\\p\{-?\d+\}', '', text)
    text = re.sub(r'\\(lw|GCcode)\{(.*?)\}', r'\2', text)
    text = text.replace('\\newpage', '').replace('{\\;}', ' ').replace('{\\:}', ' ')
    return re.sub(r'\\[sS](?![A-Za-z])', '', text)


def prepare(body):
    """Markdown body ready for conversion: paragraph tags such as
    ## {GC 17.1} are navigation only and go, so ### subheadings become
    second level; the indented list in the introduction loses one level."""
    lines = []
    for line in body.split('\n'):
        if line.strip().startswith('## {'):
            continue
        if line.startswith('    '):
            line = line[4:]
        line = re.sub(r'^#(#{2,}) ', r'\1 ', line)
        lines.append(clean_tex(line))
    return '\n'.join(lines)


def to_html(text):
    html = markdown.markdown(text, extensions=['footnotes'], output_format='html',
                             extension_configs={'footnotes': {'BACKLINK_TITLE': '%d'}})
    html = re.sub(r'\\emph\{(.*?)\}', r'<em>\1</em>', html)
    html = re.sub(r'\\thai\{(.*?)\}', r'<span lang="th" class="thai">\1</span>', html)
    html = html.replace('\\nbsp', '&nbsp;')
    # a bare web address in the text, such as www.laoegw.com/GC, becomes a link
    html = re.sub(r'(?<![\w/.">])(www\.[A-Za-z0-9.-]+[A-Za-z0-9](?:/[^\s<.,;:)]*)?)',
                  r'<a href="https://\1">\1</a>', html)
    # a reference such as {GC 17.1} ends each paragraph; it names the
    # paragraph, so the page can be linked as ...html#GC17.1, and links to it
    html = re.sub(r'\{([A-Za-z]+) (\d+\.\d+)\}', r'<span class="egw">{\1 \2}</span>', html)
    return re.sub(
        r'<p>((?:(?!</?p>).)*?)<span class="egw">\{([A-Za-z]+) (\d+\.\d+)\}</span></p>',
        lambda m: (f'<p id="{m[2]}{m[3]}">{m[1]}<span class="egw">'
                   f'<a href="#{m[2]}{m[3]}">{{{m[2]} {m[3]}}}</a></span></p>'),
        html, flags=re.S)


def page_name(number, english_title):
    slug = re.sub(r'[^a-z0-9]+', '_', english_title.lower().replace("'", '').replace('’', ''))
    return f'{number:02d}_{slug.strip("_")}.html'


def stylesheet_version(site):
    """A version taken from the stylesheet's content, so a browser that saved
    an older copy fetches the new one when it changes."""
    with open(os.path.join(site, 'css', 'style.css'), 'rb') as f:
        return hashlib.sha1(f.read()).hexdigest()[:8]


def versioned(html, version):
    """Add ?v=version to every link to style.css."""
    return re.sub(r'(href="[^"]*css/style\.css)(\?v=[0-9a-f]+)?"', rf'\1?v={version}"', html)


def numbered(number, title):
    """'1. Title' as on the printed contents page; the introduction (0) has no number."""
    return f'{number}. {title}' if number > 0 else title


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('book', help='the book folder, such as lo/GC')
    parser.add_argument('--site', default=SITE)
    parser.add_argument('--layout', default=LAYOUT)
    args = parser.parse_args()

    code = os.path.basename(os.path.normpath(args.book))
    meta = read_yaml(open(os.path.join(args.book, 'metadata.yaml'), encoding='utf-8'))
    lang = meta['lang'].split('-')[0]
    # each language has its own header, footer and page words
    layout = os.path.join(args.layout, lang)
    labels = read_yaml(open(os.path.join(layout, 'labels.txt'), encoding='utf-8'))
    book_title = meta[f'book.title.{lang}']

    chapters = {}
    folder = os.path.join(args.book, '03_public')
    for name in sorted(os.listdir(folder)):
        if not name.endswith('.md'):
            continue
        head, body = front_matter(open(os.path.join(folder, name), encoding='utf-8').read())
        number = int(head['chapter.number'])
        chapters[number] = {
            'id': name.rsplit('_', 1)[0],  # GC01, GC00_introduction: names the chapter's dictionary
            'number': number,
            'name': clean_tex(head[f'chapter.title.{lang}']),
            'title': numbered(number, clean_tex(head[f'chapter.title.{lang}'])),
            'short': f'{labels["chapter"]} {number}' if number > 0 else clean_tex(head[f'chapter.title.{lang}']),
            'page': page_name(number, head['chapter.title.en']),
            'url': head.get('chapter.url'),
            'body': body,
        }

    header = open(os.path.join(layout, 'chapter_header.html'), encoding='utf-8').read()
    css_version = stylesheet_version(args.site)
    header = versioned(header, css_version)
    footer = open(os.path.join(layout, 'chapter_footer.html'), encoding='utf-8').read()
    out_folder = os.path.join(args.site, code, 'chapters')
    os.makedirs(out_folder, exist_ok=True)
    numbers = sorted(chapters)
    pages = {}
    for i, number in enumerate(numbers):
        ch = chapters[number]
        prev = chapters[numbers[i - 1]] if i > 0 else None
        nxt = chapters[numbers[i + 1]] if i + 1 < len(numbers) else None

        def nav(position, prev_text, next_text):
            left = f'<a href="{prev["page"]}">‹ {prev_text}</a>' if prev else ''
            right = f'<a href="{nxt["page"]}">{next_text} ›</a>' if nxt else ''
            return (f'<nav class="chapter-nav {position}"><span class="nav-prev">{left}</span>'
                    f'<a class="nav-toc" href="../index.html">{labels["toc"]}</a>'
                    f'<span class="nav-next">{right}</span></nav>\n')

        page = header
        for key, value in (('lang', lang), ('book', code), ('book_title', book_title), ('title', ch['title'])):
            page = page.replace('{{' + key + '}}', value)
        page += nav('top', prev and prev['short'], nxt and nxt['short'])
        # as in the print: the number centred on its own line, the title below it
        number_line = f'<span class="chapter-number">{number}</span> ' if number > 0 else ''
        page += f'<h1>{number_line}<span class="chapter-name">{ch["name"]}</span></h1>\n'
        if ch['url']:
            page += f'<p class="chapter-url"><a target="_blank" href="{ch["url"]}">{labels["english"]}</a></p>\n'
        page += to_html(prepare(ch['body'])) + '\n'
        page += nav('bottom', prev and prev['title'], nxt and nxt['title'])
        page += footer
        pages[ch['id']] = page

    # Lao: lines break only where the print dictionaries allow
    if lang == 'lo':
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from lao_words import mark
        pages = mark(pages, code)
    for number in numbers:
        with open(os.path.join(out_folder, chapters[number]['page']), 'w', encoding='utf-8') as f:
            f.write(pages[chapters[number]['id']])

    # the chapter list on the book's contents page
    index_path = os.path.join(args.site, code, 'index.html')
    index = versioned(open(index_path, encoding='utf-8').read(), css_version)
    items = ''.join(f'\n            <li>\n                <a href="chapters/{chapters[n]["page"]}">{chapters[n]["title"]}</a>\n            </li>'
                    for n in numbers)
    index, count = re.subn(r'(<nav class="toc">\s*<ol>).*?(\s*</ol>)', lambda m: m[1] + items + m[2], index, flags=re.S)
    if not count:
        raise SystemExit(f'{index_path} has no <nav class="toc"><ol> list')
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(index)
    print(f'{code}: {len(numbers)} pages and the contents list written')

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from check_book import check
    sys.exit(1 if check(args.book, args.site) else 0)


if __name__ == '__main__':
    main()
