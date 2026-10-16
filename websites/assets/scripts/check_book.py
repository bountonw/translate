"""Check one book's web pages against its chapter files.

Usage, from the repository root:
    python3 websites/assets/scripts/check_book.py lo/GC

build_book.py runs this check after every build. For every chapter in the
book's 03_public folder it checks that the page exists, that every link on
it leads to a file, that no TeX command is left, and that the text and the
footnotes hold the same letters and digits, in the same order, as the
chapter file. The chapter side is cleaned by this script's own rules, not
the converter's, so a converter fault shows up as a difference.
Exits 1 when it finds a problem.
"""
import os
import re
import sys
from html.parser import HTMLParser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_book import SITE, front_matter, page_name  # noqa: E402


class Text(HTMLParser):
    """Visible text and links, without the title and footnote numbers."""
    def __init__(self):
        super().__init__()
        self.out, self.links, self.skip = [], [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ('title', 'script', 'style', 'sup'):
            self.skip += 1
        href = dict(attrs).get('href')
        if tag == 'a' and href:
            self.links.append(href)

    def handle_endtag(self, tag):
        if tag in ('title', 'script', 'style', 'sup'):
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            self.out.append(data)


def visible(html):
    html = re.sub(r'<p class="chapter-url">.*?</p>', '', html, flags=re.S)
    parser = Text()
    parser.feed(html)
    return ''.join(parser.out), parser.links


KEEP = re.compile(r'[\u0E00-\u0EFFA-Za-z0-9]')


def letters(text):
    """Thai, Lao and Latin letters and digits, in order."""
    return ''.join(KEEP.findall(text))


def clean_md(text):
    text = re.sub(r'\\p\{-?\d+\}', '', text)
    for _ in range(3):
        text = re.sub(r'\\(lw|GCcode|emph|thai)\{([^{}]*)\}', r'\2', text)
    text = re.sub(r'\\(newpage|nbsp|s|S)(?![A-Za-z])', '', text)
    text = text.replace('{\\;}', ' ').replace('{\\:}', ' ')
    return re.sub(r'\[\^\d+\]:?', '', text)


def md_parts(body):
    lines = [line for line in body.split('\n') if not line.strip().startswith('## {')]
    main = '\n'.join(line for line in lines if not line.startswith('[^'))
    notes = '\n'.join(line for line in lines if line.startswith('[^'))
    return clean_md(main), clean_md(notes)


def first_difference(a, b):
    i = next((k for k in range(min(len(a), len(b))) if a[k] != b[k]), min(len(a), len(b)))
    return i, a[max(0, i - 25):i + 25], b[max(0, i - 25):i + 25]


def check(book, site=SITE):
    """Print every problem on the book's pages and return how many there are."""
    book = book.rstrip('/')
    folder = os.path.join(site, os.path.basename(book))
    chapters = os.path.join(book, '03_public')
    problems = pages = 0
    for name in sorted(os.listdir(chapters)):
        if not name.endswith('.md'):
            continue
        head, body = front_matter(open(os.path.join(chapters, name), encoding='utf-8').read())
        number = int(head['chapter.number'])
        rel = 'chapters/' + page_name(number, head['chapter.title.en'])
        page = os.path.join(folder, rel)
        pages += 1
        if not os.path.exists(page):
            print('MISSING page', rel)
            problems += 1
            continue
        raw = open(page, encoding='utf-8').read()
        for href in visible(raw)[1]:
            if href.startswith(('http', '#', 'mailto')):
                continue
            target = os.path.normpath(os.path.join(os.path.dirname(page), href.split('#')[0]))
            if not os.path.exists(target):
                print('BROKEN link', rel, '->', href)
                problems += 1
        if re.search(r'\\[A-Za-z]', raw):
            print('TeX left on', rel, re.findall(r'\\[A-Za-z]+', raw)[:5])
            problems += 1
        text = raw.split('</h1>', 1)[1].split('<nav class="chapter-nav bottom">', 1)[0]
        text, _, notes = text.partition('<div class="footnote">')
        md_main, md_notes = md_parts(body)
        for label, a, b in (('TEXT', md_main, visible(text)[0]), ('FOOTNOTES', md_notes, visible(notes)[0])):
            a, b = letters(a), letters(b)
            if a != b:
                i, x, y = first_difference(a, b)
                print(f'{label} differs on {rel} at letter {i}')
                print('   chapter file:', x)
                print('   page        :', y)
                problems += 1
    print(f'{os.path.basename(book)}: {pages} pages checked, {problems} problems')
    return problems


if __name__ == '__main__':
    sys.exit(1 if check(sys.argv[1], *sys.argv[2:3]) else 0)
