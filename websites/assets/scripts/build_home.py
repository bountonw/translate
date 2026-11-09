"""Build the home page of www.laoegw.com from the list of books, the news and
the page's own words.

Usage, from the repository root:
    python3 websites/assets/scripts/build_home.py
    python3 websites/assets/scripts/build_home.py --release

Reads websites/books.yaml, the site's books in the order the page lists them,
and takes each book's title and author from its metadata.yaml, in the book's
own language. The layout, layout/lo/home.html, holds one card pattern, in a
<template class="book-card"> element, and one list for each language tab, such
as <ul class="book-list" data-lang="lo">. The build writes one card per book
into the list of the book's language, and leaves the pattern off the page.

The page's own words, such as {{books}}, come from the home: table of each
language's labels.txt, layout/lo, layout/th and layout/en. Each word is written
in every language, in a span with its lang and data-l; the language shown
without scripts, Lao, is visible and the others are hidden, and the page's
language buttons switch them. Every table has every word. A book's title
stays in the book's language; a book's title_in lines in websites/books.yaml
name it in other page languages, each shown under the title in its own
language's view only. Its author_in and first_printing_in lines give the author
and the first-printing line in other page languages; each view shows its own
language's line, or the book's own where it has none. The news entries of every language
in websites/news.yaml are listed the same way; a title in them may stand in
<i> and </i>, and every other < or & is shown as written.

The build versions the stylesheet the way build_book.py does, marks the Lao
words with lao_words.py, as the book pages are marked, so lines break only
where the Lao dictionaries allow, writes <site>/index.html, and then checks
every link on the page with check_book.py. A book's link leads to the web
folder the list gives it, so the book's pages must be built there first.
Exits 1 when the check finds a problem, and with --release, which the GitHub
check runs before a merge, also while a placeholder stands on the page: an
[OPEN note, in any language, or a {{field}} left unfilled.
"""
import argparse
import html
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_book import LAYOUT, SITE, read_yaml, stylesheet_version, versioned  # noqa: E402

WEBSITES = os.path.dirname(SITE)
REPO = os.path.dirname(WEBSITES)
BOOKS = os.path.join(WEBSITES, 'books.yaml')
NEWS = os.path.join(WEBSITES, 'news.yaml')
# the languages of the page's own words, in the order the page writes them,
# each with its table in layout/<lang>/labels.txt
LANGS = ('lo', 'th', 'en')
# the language the page shows without scripts; its layout folder holds home.html
LANG = 'lo'
# the home page's name in the Lao word cache, beside the book's chapters
HOME_ID = 'home'
FIELDS = ('web', 'lang', 'cover', 'description', 'first_printing')
# a book's lines in the page languages, each under its group, such as title_in.th
IN_LANGUAGE = ('title_in', 'author_in', 'first_printing_in')
# web: and cover: are plain paths inside the site: no ../, no web address,
# no spaces, quotation marks, & or colons
SAFE = re.compile(r'[A-Za-z0-9_][A-Za-z0-9_.-]*(?:/[A-Za-z0-9_][A-Za-z0-9_.-]*)*')
# a YAML block value (> or |), whose lines read_yaml does not join
BLOCK = re.compile(r'[>|][-+0-9]*')
# the layout's card pattern, with the comment line above it, its lists of
# books and its news list
CARD = re.compile(r'(?:\n[ \t]*<!--[^\n]*-->)?\n[ \t]*<template class="book-card">\n(.*?)\n[ \t]*</template>', re.S)
BOOK_LIST = re.compile(r'(<ul class="book-list" data-lang="([a-z]+)">)(.*?)(\n[ \t]*</ul>)', re.S)
NEWS_LIST = re.compile(r'(<ul class="news-list">)(.*?)(\n([ \t]*)</ul>)', re.S)
FIELD = re.compile(r'\{\{(\w+)\}\}')
LAO_LETTER = re.compile('[' + chr(0x0E80) + '-' + chr(0x0EFF) + ']')
THAI_LETTER = re.compile('[' + chr(0x0E00) + '-' + chr(0x0E7F) + ']')
# a placeholder that stops --release: an [OPEN note, with or without a space
# after it, or a {{field}} the build left unfilled
PLACEHOLDER = re.compile(r'\[OPEN\b|\{\{\w+\}\}')


def read_books(path=BOOKS, repo=REPO):
    """The listed books in order. Each is a dict of its fields in the list,
    its repository folder, and the title and author from its metadata.yaml."""
    entries = {}
    for key, value in read_yaml(open(path, encoding='utf-8')).items():
        folder, _, field = key.partition('.')
        group, _, lang = field.partition('.')
        if field not in FIELDS and not (group in IN_LANGUAGE and lang in LANGS):
            raise SystemExit(f'{path}: {key} is not one of the fields {", ".join(FIELDS)}, '
                             f'or {", ".join(IN_LANGUAGE)} with a language of {", ".join(LANGS)}')
        if BLOCK.fullmatch(value):
            raise SystemExit(f'{path}: {key} must stand on one line; a value of > or | is not read')
        entries.setdefault(folder, {})[field] = value
    books = []
    for folder, entry in entries.items():
        for field in ('web', 'lang'):
            if field not in entry:
                raise SystemExit(f'{path}: {folder} has no {field}')
        for field, value in (('web', entry['web'].strip('/')), ('cover', entry.get('cover'))):
            if value is not None and not SAFE.fullmatch(value):
                raise SystemExit(f'{path}: {folder} {field} {entry[field]} must be a plain path inside the site')
        meta_path = os.path.join(repo, folder, 'metadata.yaml')
        meta = read_yaml(open(meta_path, encoding='utf-8'))
        lang = entry['lang']
        if meta.get('lang', '').split('-')[0] != lang:
            raise SystemExit(f'{path}: {folder} has lang {lang}, but {meta_path} has {meta.get("lang")}')
        for key in (f'book.title.{lang}', f'author.{lang}'):
            if key not in meta:
                raise SystemExit(f'{meta_path} has no {key}')
        book = {key: value for key, value in entry.items() if '.' not in key}
        for group in IN_LANGUAGE:
            book[group] = {key.split('.', 1)[1]: value for key, value in entry.items() if key.startswith(group + '.')}
        books.append(dict(book, folder=folder, title=meta[f'book.title.{lang}'], author=meta[f'author.{lang}']))
    return books


def read_news(path=NEWS, lang=LANG):
    """The entries of one language in the news file, in the file's order.
    A language starts a group, as "lo:"; each entry under it is one line
    starting with "- "."""
    groups, group = {}, None
    for number, line in enumerate(open(path, encoding='utf-8'), 1):
        text = line.strip()
        if not text or text.startswith('#'):
            continue
        if not line[0].isspace():
            key, colon, rest = text.partition(':')
            if not colon or rest.strip():
                raise SystemExit(f'{path}:{number}: a language stands alone on its line, as "lo:"')
            group = groups.setdefault(key.strip(), [])
        elif group is not None and text.startswith('- ') and text[2:].strip():
            if BLOCK.fullmatch(text[2:].strip()):
                raise SystemExit(f'{path}:{number}: an entry must stand on one line; a value of > or | is not read')
            group.append(text[2:].strip())
        else:
            raise SystemExit(f'{path}:{number}: an entry is one line starting with "- ", under its language')
    return groups.get(lang, [])


def read_words(layout=LAYOUT, langs=LANGS):
    """The page's own words, {lang: {word: text}}, from the home: table of
    each language's labels.txt. Every table must hold every word."""
    words = {}
    for lang in langs:
        path = os.path.join(layout, lang, 'labels.txt')
        labels = read_yaml(open(path, encoding='utf-8'))
        words[lang] = {key.split('.', 1)[1]: value for key, value in labels.items() if key.startswith('home.')}
        if not words[lang]:
            raise SystemExit(f'{path} has no home: table')
    every = set().union(*(table.keys() for table in words.values()))
    for lang, table in words.items():
        missing = sorted(every - table.keys())
        if missing:
            raise SystemExit(f'{os.path.join(layout, lang, "labels.txt")} has no home.{", home.".join(missing)}')
    return words


def written_in(text):
    """The language a text is written in, by its letters: lo for Lao, th for
    Thai, and en for any other, such as English or an [OPEN note."""
    if LAO_LETTER.search(text):
        return 'lo'
    return 'th' if THAI_LETTER.search(text) else 'en'


def in_every_language(texts, shown):
    """One word or line in every language, {lang: text}: each in a span whose
    data-l names the page language it belongs to and whose lang names the
    language it is written in, escaped; only the shown language is visible."""
    return ''.join(f'<span lang="{written_in(text)}" data-l="{lang}"{"" if lang == shown else " hidden"}>'
                   f'{html.escape(text)}</span>' for lang, text in texts.items())


def card(pattern, book, shown=LANG):
    """One book's card from the layout's pattern: each {{field}} of the book
    filled with the book's value, escaped. {{title_in}} becomes one line per
    page language that names the book in it, visible in that language's view
    only. Where author_in or first_printing_in gives lines, {{author}} and
    {{first_printing}} are written in every page language, the book's own
    where a language has no line, and each view shows its own. A line whose
    field the list leaves empty is left out; any other {{name}} is left as it
    stands."""
    web = book['web'].strip('/')
    values = {'lang': book['lang'], 'web': web, 'title': book['title'], 'author': book['author'],
              'cover': f'{web}/{book["cover"]}' if book.get('cover') else '',
              'description': book.get('description', ''),
              'first_printing': book.get('first_printing', '')}
    values = {key: html.escape(value) for key, value in values.items()}
    values['title_in'] = ''.join(
        f'<p class="title-in" lang="{written_in(text)}" data-l="{lang}"{"" if lang == shown else " hidden"}>'
        f'{html.escape(text)}</p>' for lang, text in (book.get('title_in') or {}).items())
    for field in ('author', 'first_printing'):
        own, lines_in = book.get(field, ''), book.get(f'{field}_in') or {}
        if own and lines_in:
            values[field] = in_every_language({lang: lines_in.get(lang, own) for lang in LANGS}, shown)
    lines = []
    for line in pattern.split('\n'):
        fields = [field for field in FIELD.findall(line) if field in values]
        if all(values[field] for field in fields):
            lines.append(FIELD.sub(lambda m: values.get(m[1], m[0]), line))
    return ''.join('\n' + line for line in lines)


def news_html(entry):
    """A news entry, escaped, with <i> and </i> kept for a title."""
    text = html.escape(entry).replace('&lt;i&gt;', '<i>').replace('&lt;/i&gt;', '</i>')
    if not re.fullmatch(r'[^<]*(?:<i>[^<]*</i>[^<]*)*', text):
        raise SystemExit(f'the news entry "{entry}" opens an <i> it does not close, or closes one it did not open')
    return text


def fill(page, books, news=None, words=None, shown=LANG):
    """The page with its own words written in every language, shown in one,
    one card per book in the list of the book's language, the news entries of
    every language in the news list, and the card pattern left off. A {{name}}
    that is neither a word nor a book field is left as it stands."""
    words, news = words or {}, news or {}
    if words and shown not in words:
        raise SystemExit(f'the page cannot show {shown}: the languages of its words are {", ".join(words)}')
    found = CARD.search(page)
    if not found:
        raise SystemExit('the home page layout has no <template class="book-card"> card pattern')
    page = page[:found.start()] + page[found.end():]
    own = {key: {lang: table[key] for lang, table in words.items()} for key in (words.get(shown) or {})}
    for key in own:
        if key in ('lang', 'web', 'title', 'author', 'cover', 'description', 'first_printing', 'title_in'):
            raise SystemExit(f'the word {key} has the name of a book field')

    def own_word(m):
        return in_every_language(own[m[1]], shown) if m[1] in own else m[0]
    pattern = FIELD.sub(own_word, found[1])
    page = FIELD.sub(own_word, page)
    page = re.sub(r'<html lang="[a-z]+">', f'<html lang="{shown}">', page, count=1)

    tabs = [m[2] for m in BOOK_LIST.finditer(page)]
    if not tabs:
        raise SystemExit('the home page layout has no <ul class="book-list" data-lang="..."> list')
    for book in books:
        if book['lang'] not in tabs:
            raise SystemExit(f'{book.get("folder", book["web"])} has lang {book["lang"]}, '
                             f'and the home page layout has no list of books for it')

    def books_of(m):
        cards = ''.join(card(pattern, book, shown) for book in books if book['lang'] == m[2])
        return m[1] + (cards or m[3]) + m[4]

    def news_of(m):
        return m[1] + ''.join(
            f'\n{m[4]}    <li lang="{written_in(entry)}" data-l="{lang}"{"" if lang == shown else " hidden"}>'
            f'{news_html(entry)}</li>'
            for lang, entries in news.items() for entry in entries) + m[3]

    page = BOOK_LIST.sub(books_of, page)
    page, count = NEWS_LIST.subn(news_of, page)
    if not count:
        raise SystemExit('the home page layout has no <ul class="news-list"> list')
    return page


def build(site=SITE, layout=LAYOUT, books_path=BOOKS, repo=REPO, news_path=NEWS, words_cache=None, shown=LANG):
    """Write <site>/index.html and return the books it lists. words_cache is
    the Lao word cache, lao_words.py's own when None; shown is the language
    the page shows without scripts."""
    from lao_words import CACHE, mark
    books = read_books(books_path, repo)
    words = read_words(layout)
    news = {lang: read_news(news_path, lang) for lang in words}
    page = open(os.path.join(layout, LANG, 'home.html'), encoding='utf-8').read()
    page = fill(versioned(page, stylesheet_version(site)), books, news, words, shown)
    # the home page belongs to no book, so the Lao dictionaries alone split it
    page = mark({HOME_ID: page}, None, words_cache or CACHE)[HOME_ID]
    with open(os.path.join(site, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(page)
    return books


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--site', default=SITE)
    parser.add_argument('--layout', default=LAYOUT)
    parser.add_argument('--books', default=BOOKS, help='the list of books')
    parser.add_argument('--news', default=NEWS, help='the news file')
    parser.add_argument('--lang', default=LANG, choices=LANGS, help='the language the page shows without scripts')
    parser.add_argument('--words-cache', help="the Lao word cache, if not lao_words.py's own")
    parser.add_argument('--release', action='store_true',
                        help='also exit 1 while a placeholder, [OPEN or an unfilled {{field}}, stands')
    args = parser.parse_args(argv)

    books = build(args.site, args.layout, args.books, news_path=args.news, words_cache=args.words_cache,
                  shown=args.lang)
    print(f'home page: index.html written, books listed: {len(books)}')
    page = open(os.path.join(args.site, 'index.html'), encoding='utf-8').read()
    open_choices = len(PLACEHOLDER.findall(page))
    if open_choices:
        print(f'home page: placeholders standing ([OPEN or an unfilled {{{{field}}}}): {open_choices}; '
              f'the page is not ready for the server')

    from check_book import check_home
    problems = check_home(args.site)
    sys.exit(1 if problems or (args.release and open_choices) else 0)


if __name__ == '__main__':
    main()
