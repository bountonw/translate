"""Tests for build_home.py, the home page layout, its per-language word tables,
its language switch and the home page link check in check_book.py.

Run from the repository root:
    python3 -m pytest websites/assets/scripts/test_build_home.py

Each test builds in its own temporary folder, with its own Lao word cache;
only the real list of books, the real news file, the real layout and word
tables, the real stylesheet, the real Lao dictionaries and the real
metadata.yaml are read, and nothing in the repository is written. The test of
the language switch runs the page's script with node, and is skipped where
node is missing.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
from html.parser import HTMLParser

import pytest

import build_home
import check_book
from build_book import LAYOUT, SITE, stylesheet_version, versioned
from check_book import check_home

HOME_LAYOUT = os.path.join(LAYOUT, 'lo', 'home.html')
WORDS = build_home.read_words()
BOOK_FIELDS = {'lang', 'web', 'title', 'author', 'cover', 'description', 'first_printing', 'title_in'}
# Thai and Lao digits, and the invisible characters: zero-width space, joiners,
# word joiner, byte order mark and soft hyphen
FORBIDDEN = re.compile('[' + ''.join(f'{chr(first)}-{chr(last)}' for first, last in (
    (0x0E50, 0x0E59), (0x0ED0, 0x0ED9), (0x200B, 0x200D), (0x2060, 0x2060), (0xFEFF, 0xFEFF), (0x00AD, 0x00AD))) + ']')
LAO = re.compile('[' + chr(0x0E80) + '-' + chr(0x0EFF) + ']')

METADATA = """---
lang: en-US
author:
  en: First Author
  lo: Author in lo
book:
  title:
    en: First Book
    lo: Title in lo
...
"""

LIST = """# a comment line
xx/AB:
  web: AB
  lang: lo
  cover:
  description: A short line about the book.
  first_printing:
xx/CD:
  web: en/CD
  lang: en
  cover: images/cover.jpg
  first_printing: Printed once.
"""

NEWS = """# a comment line
lo:
  - Newest & last added.
  - Oldest.
th:
  - An entry for the Thai page.
"""


@pytest.fixture
def setup(tmp_path):
    """A repository with a Lao book, an English book and a news file, and a
    site whose stylesheet and book folders exist. The Thai tab lists no book.
    Returns (site, books_path, repo)."""
    repo = tmp_path / 'repo'
    for folder, lang, title in (('xx/AB', 'lo-LA', 'First Book'), ('xx/CD', 'en-US', 'Second Book')):
        (repo / folder).mkdir(parents=True)
        (repo / folder / 'metadata.yaml').write_text(
            METADATA.replace('First Book', title).replace('en-US', lang), encoding='utf-8')
    books = repo / 'books.yaml'
    books.write_text(LIST, encoding='utf-8')
    (repo / 'news.yaml').write_text(NEWS, encoding='utf-8')
    site = tmp_path / 'site'
    (site / 'css').mkdir(parents=True)
    (site / 'css' / 'style.css').write_text('body { margin: 0; }\n', encoding='utf-8')
    for web in ('AB', 'en/CD'):
        (site / web / 'images').mkdir(parents=True)
        (site / web / 'index.html').write_text('<!DOCTYPE html>\n', encoding='utf-8')
    (site / 'en/CD/images/cover.jpg').write_bytes(b'')
    return str(site), str(books), str(repo)


def built(setup, shown=build_home.LANG):
    """Build in the setup's folders, with a word cache of their own, and return the page."""
    site, books_path, repo = setup
    build_home.build(site, LAYOUT, books_path, repo, os.path.join(repo, 'news.yaml'),
                     os.path.join(repo, 'words.json'), shown)
    return open(os.path.join(site, 'index.html'), encoding='utf-8').read()


def unmarked(page):
    """The page without the Lao word marks of lao_words.py."""
    return re.sub(r'<span class="w">([^<]*)</span>|<wbr\n>|&shy;', lambda m: m[1] or '', page)


def book_list(page, lang):
    return page.split(f'<ul class="book-list" data-lang="{lang}">', 1)[1].split('</ul>', 1)[0]


def word(key, shown='lo'):
    """The word as the build writes it, in every language, unmarked."""
    return build_home.in_every_language({lang: table[key] for lang, table in WORDS.items()}, shown)


def test_list_is_read_in_order_with_title_and_author_from_metadata(setup):
    _, books_path, repo = setup
    books = build_home.read_books(books_path, repo)
    assert [b['folder'] for b in books] == ['xx/AB', 'xx/CD']
    # each in the book's own language
    assert [b['title'] for b in books] == ['Title in lo', 'Second Book']
    assert [b['author'] for b in books] == ['Author in lo', 'First Author']
    assert books[0]['web'] == 'AB' and books[1]['web'] == 'en/CD'
    # an optional field left empty is absent
    assert 'cover' not in books[0] and books[1]['cover'] == 'images/cover.jpg'


def test_real_list_takes_gc_title_and_author_from_its_metadata():
    books = build_home.read_books()
    gc = next(b for b in books if b['folder'] == 'lo/GC')
    assert gc['web'] == 'GC' and gc['lang'] == 'lo'
    meta = open(os.path.join(build_home.REPO, 'lo', 'GC', 'metadata.yaml'), encoding='utf-8').read()
    assert f'lo: {gc["title"]}\n' in meta
    assert f'lo: {gc["author"]}\n' in meta


def test_real_list_gives_gc_its_cover_and_the_first_printing_of_its_title_page():
    gc = next(b for b in build_home.read_books() if b['folder'] == 'lo/GC')
    assert gc['cover'] == 'images/cover.jpg'
    assert os.path.exists(os.path.join(SITE, gc['web'], gc['cover']))
    title_page = os.path.join(build_home.REPO, 'lo', 'GC', '04_assets', 'scripts', 'tex', 'title_page.tex')
    assert '\\textbf{' + gc['first_printing'] + '}' in open(title_page, encoding='utf-8').read()


def test_word_tables_hold_the_same_words_in_lao_thai_and_english():
    assert list(WORDS) == ['lo', 'th', 'en']
    keys = set(WORDS['lo'])
    assert all(set(table) == keys for table in WORDS.values())
    # every word in double braces in the layout, other than a book field, is a word of the tables, and back
    layout = open(HOME_LAYOUT, encoding='utf-8').read()
    assert set(re.findall(r'\{\{(\w+)\}\}', layout)) - BOOK_FIELDS == keys | {'empty_tab_lo'}
    # each empty-tab line is in the tables for the tabs that list no book
    langs = {book['lang'] for book in build_home.read_books()}
    for lang in re.findall(r'<ul class="book-list" data-lang="(\w+)">', layout):
        assert lang in langs or f'empty_tab_{lang}' in keys, lang
    # the layout holds no Lao or Thai word but the names on the language buttons; the tables hold the rest
    runs = set(re.findall('[' + chr(0x0E00) + '-' + chr(0x0EFF) + ']+', layout))
    assert runs == {WORDS['lo']['lang_lo'], WORDS['th']['lang_th']}


def test_a_word_missing_from_one_table_stops_the_build(tmp_path):
    for lang in build_home.LANGS:
        (tmp_path / lang).mkdir()
        shutil.copy(os.path.join(LAYOUT, lang, 'labels.txt'), tmp_path / lang)
    path = tmp_path / 'th' / 'labels.txt'
    text = path.read_text(encoding='utf-8')
    path.write_text(re.sub(r'\n  books: [^\n]*', '', text), encoding='utf-8')
    with pytest.raises(SystemExit, match=r'th/labels.txt has no home.books'):
        build_home.read_words(str(tmp_path))


def test_page_shows_lao_and_holds_every_word_in_thai_and_english_hidden(setup):
    page = unmarked(built(setup))
    assert '<html lang="lo">' in page
    for key in WORDS['lo']:
        if key != 'empty_tab_en':  # the English tab lists a book here
            assert word(key) in page, key
    variants = re.findall(r'<(span|li) lang="(\w+)" data-l="(\w+)"( hidden)?>', page)
    assert variants
    for _, _, belongs, hidden in variants:
        assert (belongs == 'lo') == (not hidden)
    counts = {lang: sum(1 for v in variants if v[2] == lang) for lang in build_home.LANGS}
    # each word stands in every language; the fixture's news has two Lao entries and one Thai
    assert counts['lo'] - 2 == counts['th'] - 1 == counts['en']


def test_each_word_is_marked_with_the_language_it_is_written_in(setup):
    page = unmarked(built(setup))
    spans = re.findall(r'<span lang="(\w+)" data-l="(\w+)"(?: hidden)?>([^<]*)</span>', page)
    assert spans
    for lang, _, text in spans:
        assert lang == build_home.written_in(text)
    assert build_home.written_in('[OPEN a question]') == 'en'
    assert build_home.written_in(WORDS['lo']['books']) == 'lo'
    assert build_home.written_in(WORDS['th']['books']) == 'th'


def test_a_page_built_to_show_thai_shows_the_thai_words(setup):
    page = unmarked(built(setup, 'th'))
    assert '<html lang="th">' in page
    assert word('books', 'th') in page
    assert re.search(r'<span lang="th" data-l="th">', page) and re.search(r'<span lang="lo" data-l="lo" hidden>', page)


def run_switch(page, actions):
    """Run the page's script in node on a stand-in for the browser made from
    the page's elements, do the actions, and return the state after each."""
    class Elements(HTMLParser):
        def __init__(self):
            super().__init__()
            self.found, self.open = [], []

        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            element = None
            if attrs.get('id') or 'data-l' in attrs or 'data-lang' in attrs:
                element = {'tag': tag, 'attrs': {k: v or '' for k, v in attrs.items()}, 'text': ''}
                self.found.append(element)
            if tag not in ('wbr', 'img', 'br', 'input', 'meta', 'link'):
                self.open.append(element)

        def handle_endtag(self, tag):
            if self.open:
                self.open.pop()

        def handle_data(self, data):
            for element in reversed(self.open):
                if element is not None and 'data-l' in element['attrs']:
                    element['text'] += data
                    break

    parser = Elements()
    parser.feed(page.split('<body>', 1)[1])
    script = re.findall(r'<script>(.*?)</script>', page, re.S)[-1]
    lang = re.search(r'<html lang="(\w+)">', page)[1]
    stand_in = """
const elements = %s, actions = %s, out = [];
function make(d) {
  const e = { tag: d.tag, attrs: Object.assign({}, d.attrs), listeners: {}, children: [], text: d.text || '' };
  e.id = e.attrs.id || '';
  e.hidden = 'hidden' in e.attrs;
  e.tabIndex = e.attrs.tabindex === undefined ? 0 : Number(e.attrs.tabindex);
  const classes = new Set((e.attrs['class'] || '').split(' ').filter(Boolean));
  e.classList = { toggle: (c, on) => { if (on) classes.add(c); else classes.delete(c); }, has: c => classes.has(c) };
  e.getAttribute = k => (k in e.attrs ? e.attrs[k] : null);
  e.setAttribute = (k, v) => { e.attrs[k] = String(v); };
  e.addEventListener = (t, f) => { (e.listeners[t] = e.listeners[t] || []).push(f); };
  e.fire = (t, extra) => (e.listeners[t] || []).forEach(f => f(Object.assign({ preventDefault() {} }, extra || {})));
  e.focus = () => {};
  e.scrollIntoView = () => {};
  e.appendChild = c => { e.children.push(c); };
  e.textContent = '';
  return e;
}
const all = elements.map(make);
global.document = {
  documentElement: { lang: %s, className: 'js' },
  getElementById: id => all.find(e => e.id === id) || null,
  createElement: () => make({ tag: 'a', attrs: {} }),
  querySelectorAll: sel => ({
    '.tabs [role="tab"]': all.filter(e => e.attrs.role === 'tab'),
    '.langs button': all.filter(e => e.tag === 'button' && 'aria-pressed' in e.attrs),
    '[data-l]': all.filter(e => 'data-l' in e.attrs),
  })[sel] || [],
};
eval(%s);
function state() {
  const shown = [...new Set(all.filter(e => 'data-l' in e.attrs && !e.hidden).map(e => e.attrs['data-l']))];
  return {
    lang: document.documentElement.lang, shown,
    pressed: all.filter(e => e.attrs['aria-pressed'] === 'true').map(e => e.attrs['data-lang']),
    tab: all.filter(e => e.attrs['aria-selected'] === 'true').map(e => e.attrs['data-lang']),
    panels: all.filter(e => e.classList.has('shown')).map(e => e.id),
    mail: document.getElementById('mail').children.map(c => c.attrs.href),
    texts: all.filter(e => 'data-l' in e.attrs && !e.hidden).map(e => e.text),
  };
}
out.push(state());
for (const [kind, lang] of actions) {
  const target = all.find(e => e.attrs['data-lang'] === lang && (kind === 'tab') === (e.attrs.role === 'tab'));
  target.fire('click');
  out.push(state());
}
console.log(JSON.stringify(out));
""" % (json.dumps(parser.found), json.dumps(actions), json.dumps(lang), json.dumps(script))
    done = subprocess.run(['node', '-e', stand_in], capture_output=True, text=True, timeout=60)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


@pytest.mark.skipif(not shutil.which('node'), reason='node is not installed')
def test_language_buttons_switch_every_word_and_tabs_switch_only_the_books(setup):
    page = built(setup)
    states = run_switch(page, [['button', 'th'], ['tab', 'en'], ['button', 'en'], ['button', 'lo']])
    start, thai, english_tab, english, lao = states
    assert {key: value for key, value in start.items() if key != 'texts'} == {
        'lang': 'lo', 'shown': ['lo'], 'pressed': ['lo'], 'tab': ['lo'], 'panels': ['books-lo'],
        'mail': ['mailto:laoegw@proton.me']}
    # a language button shows its words, presses itself and selects its tab
    assert (thai['lang'], thai['shown'], thai['pressed'], thai['tab']) == ('th', ['th'], ['th'], ['th'])
    # a tab selects its books and leaves the words as they are
    assert (english_tab['shown'], english_tab['pressed'], english_tab['tab']) == (['th'], ['th'], ['en'])
    assert (english['lang'], english['shown'], english['pressed']) == ('en', ['en'], ['en'])
    assert (lao['lang'], lao['shown'], lao['pressed'], lao['panels']) == ('lo', ['lo'], ['lo'], ['books-lo'])


def with_lines_in_other_languages(setup):
    """Give the setup's Lao book a first-printing line, a Thai author line, and
    Thai and English first-printing lines; it has no English author line."""
    books_path = setup[1]
    text = open(books_path, encoding='utf-8').read()
    open(books_path, 'w', encoding='utf-8').write(text.replace(
        '  first_printing:\nxx/CD:', '  first_printing: Printed in Lao.\n  author_in:\n    th: Author, Thai view\n'
        '  first_printing_in:\n    th: Printed, Thai view\n    en: Printed, English view\nxx/CD:', 1))


def visible_in(card, cls):
    """The visible text of a card line: its span not hidden, or its plain text."""
    line = re.search(rf'<p class="{cls}">(.*?)</p>', card)[1]
    shown = re.findall(r'<span lang="\w+" data-l="\w+">([^<]*)</span>', line)
    return shown if '<span' in line else [line]


def test_author_and_first_printing_follow_the_page_language_and_the_lao_view_keeps_the_books_own(setup):
    with_lines_in_other_languages(setup)
    books = build_home.read_books(setup[1], setup[2])
    assert books[0]['author_in'] == {'th': 'Author, Thai view'}
    assert books[0]['first_printing_in'] == {'th': 'Printed, Thai view', 'en': 'Printed, English view'}
    expected = {'lo': ('Author in lo', 'Printed in Lao.'), 'th': ('Author, Thai view', 'Printed, Thai view'),
                'en': ('Author in lo', 'Printed, English view')}
    for shown, (author, printing) in expected.items():
        card = book_list(unmarked(built(setup, shown)), 'lo')
        assert visible_in(card, 'author') == [author], shown
        assert visible_in(card, 'first-printing') == [printing], shown
        # every view holds every language's line, one visible
        assert card.count('data-l=') == 3 + 6  # the start button, the author and the first-printing line
    # the title stays the book's own in every view
    for shown in build_home.LANGS:
        assert '<h3 class="title">Title in lo</h3>' in unmarked(built(setup, shown))
    # a book with no lines in other languages keeps its plain lines
    english = book_list(unmarked(built(setup)), 'en')
    assert '<p class="author">First Author</p>' in english


@pytest.mark.skipif(not shutil.which('node'), reason='node is not installed')
def test_language_buttons_switch_the_author_and_first_printing_lines(setup):
    with_lines_in_other_languages(setup)
    states = run_switch(built(setup), [['button', 'th'], ['button', 'en'], ['button', 'lo']])
    lao, thai, english, back = (set(state['texts']) for state in states)
    assert {'Author in lo', 'Printed in Lao.'} <= lao and not {'Author, Thai view', 'Printed, Thai view'} & lao
    assert {'Author, Thai view', 'Printed, Thai view'} <= thai and not {'Author in lo', 'Printed in Lao.'} & thai
    assert {'Author in lo', 'Printed, English view'} <= english and 'Printed, Thai view' not in english
    assert back == lao


def test_real_gc_card_shows_its_lao_author_and_printing_in_the_lao_view():
    gc = next(b for b in build_home.read_books() if b['folder'] == 'lo/GC')
    assert set(gc['author_in']) == set(gc['first_printing_in']) == {'th', 'en'}
    layout = open(HOME_LAYOUT, encoding='utf-8').read()
    news = {lang: build_home.read_news(lang=lang) for lang in WORDS}
    for shown in build_home.LANGS:
        page = build_home.fill(layout, build_home.read_books(), news, WORDS, shown)
        card = book_list(page, 'lo')
        own = shown == 'lo'
        assert visible_in(card, 'author') == [gc['author'] if own else gc['author_in'][shown]]
        assert visible_in(card, 'first-printing') == [gc['first_printing'] if own else gc['first_printing_in'][shown]]
        # the title stays Lao, with the line naming it in the view's language under it
        assert f'<h3 class="title">{gc["title"]}</h3>' in card
    # with no script the page is the Lao view
    static = build_home.fill(layout, build_home.read_books(), news, WORDS)
    assert visible_in(book_list(static, 'lo'), 'author') == [gc['author']]


def test_a_line_in_a_language_the_page_lacks_stops_the_build(setup):
    books_path = setup[1]
    text = open(books_path, encoding='utf-8').read()
    open(books_path, 'w', encoding='utf-8').write(text.replace(
        '  first_printing:\nxx/CD:', '  first_printing:\n  author_in:\n    fr: Auteur\nxx/CD:', 1))
    with pytest.raises(SystemExit, match='author_in.fr is not one of the fields'):
        build_home.read_books(books_path, setup[2])


def test_thai_text_never_ends_with_a_full_stop():
    thai = [text for text in WORDS['th'].values() if build_home.written_in(text) == 'th']
    thai += build_home.read_news(lang='th')
    for book in build_home.read_books():
        for group in build_home.IN_LANGUAGE:
            thai += [text for text in book[group].values() if build_home.written_in(text) == 'th']
    assert len(thai) >= 12
    assert [text for text in thai if text.endswith('.')] == []


def test_language_buttons_name_each_language_in_its_own_words_in_every_view(setup):
    names = {'lo': WORDS['lo']['lang_lo'], 'th': WORDS['th']['lang_th'], 'en': WORDS['en']['lang_en']}
    for shown in build_home.LANGS:
        page = unmarked(built(setup, shown))
        header = page.split('<header class="home-header">', 1)[1].split('</header>', 1)[0]
        for lang, name in names.items():
            assert re.search(rf'<button type="button" data-lang="{lang}" aria-pressed="\w+"><svg[^>]*><use[^>]*></use></svg>'
                             rf'<span lang="{lang}">{name}</span></button>', header), (shown, lang)
        assert 'data-l=' not in header


def test_title_in_lines_name_the_book_in_the_thai_and_english_views_only(setup):
    site, books_path, repo = setup
    text = open(books_path, encoding='utf-8').read()
    open(books_path, 'w', encoding='utf-8').write(text.replace(
        '  first_printing:\nxx/CD:', '  first_printing:\n  title_in:\n    th: Named for the Thai view\n'
        '    en: Named for the English view\nxx/CD:', 1))
    books = build_home.read_books(books_path, repo)
    assert books[0]['title_in'] == {'th': 'Named for the Thai view', 'en': 'Named for the English view'}
    assert books[1]['title_in'] == {}
    for shown in build_home.LANGS:
        card = book_list(unmarked(built(setup, shown)), 'lo')
        lines = re.findall(r'<p class="title-in" lang="\w+" data-l="(\w+)"( hidden)?>([^<]*)</p>', card)
        assert [(lang, text) for lang, _, text in lines] == [('th', 'Named for the Thai view'),
                                                           ('en', 'Named for the English view')]
        # the Lao view shows no extra line; the Thai and English views show their own
        assert [lang for lang, hidden, _ in lines if not hidden] == ([] if shown == 'lo' else [shown])
        # the line stands under the title
        assert card.index('<h3 class="title">') < card.index('<p class="title-in"') < card.index('<p class="author">')
    assert 'title-in' not in book_list(unmarked(built(setup)), 'en')


def test_real_list_names_gc_in_thai_and_english_and_the_lao_view_hides_both():
    gc = next(b for b in build_home.read_books() if b['folder'] == 'lo/GC')
    assert set(gc['title_in']) == {'th', 'en'}
    assert build_home.written_in(gc['title_in']['th']) == 'th' and build_home.written_in(gc['title_in']['en']) == 'en'
    layout = open(HOME_LAYOUT, encoding='utf-8').read()
    # the names are the book's data, not the layout's
    assert '{{title_in}}' in layout and gc['title_in']['en'] not in layout and gc['title_in']['th'] not in layout
    news = {lang: build_home.read_news(lang=lang) for lang in WORDS}
    for shown in build_home.LANGS:
        page = build_home.fill(layout, build_home.read_books(), news, WORDS, shown)
        for lang, text in gc['title_in'].items():
            hidden = '' if lang == shown else ' hidden'
            assert f'<p class="title-in" lang="{lang}" data-l="{lang}"{hidden}>{text}</p>' in page


def test_news_keeps_italics_for_a_title_and_escapes_everything_else():
    assert build_home.news_html('A <i>Title</i> & <b>bold</b> <script>') == (
        'A <i>Title</i> &amp; &lt;b&gt;bold&lt;/b&gt; &lt;script&gt;')
    assert build_home.news_html('<i>One</i> and <i>two</i>.') == '<i>One</i> and <i>two</i>.'
    for entry in ('<i>open', 'close</i>', '<i><i>twice</i></i>', '</i>back<i>'):
        with pytest.raises(SystemExit, match='<i>'):
            build_home.news_html(entry)


def test_real_news_lines_carry_their_titles_in_italics():
    news = {lang: build_home.read_news(lang=lang) for lang in WORDS}
    page = build_home.fill(open(HOME_LAYOUT, encoding='utf-8').read(), build_home.read_books(), news, WORDS)
    for lang in ('th', 'en'):
        assert re.search(rf'<li lang="{lang}" data-l="{lang}" hidden>[^<]*<i>[^<]+</i>[^<]*</li>', page), lang
    assert '&lt;i&gt;' not in page


def test_each_book_goes_in_the_list_of_its_language(setup):
    page = unmarked(built(setup))
    assert book_list(page, 'lo').count('<li class="book" lang="lo">') == 1
    assert book_list(page, 'en').count('<li class="book" lang="en">') == 1
    assert '<li class="book"' not in book_list(page, 'th')
    # the card pattern is left off the page
    assert '<template' not in page and '{{' not in page
    # a second build gives the same page
    assert unmarked(built(setup)) == page


def test_a_tab_with_no_book_shows_its_line_in_every_language(setup):
    page = unmarked(built(setup))
    assert book_list(page, 'th').strip() == f'<li class="empty"><p>{word("empty_tab_th")}</p></li>'
    assert 'class="empty"' not in book_list(page, 'lo') + book_list(page, 'en')


def test_card_shows_cover_title_author_first_printing_and_the_start_button(setup):
    page = unmarked(built(setup))
    lao, english = book_list(page, 'lo'), book_list(page, 'en')
    assert '<h3 class="title">Title in lo</h3>' in lao
    assert '<p class="author">Author in lo</p>' in lao
    assert '<p class="description">A short line about the book.</p>' in lao
    assert f'<a class="read" href="AB/">{word("start_reading")}</a>' in lao
    assert '<h3 class="title">Second Book</h3>' in english
    assert '<p class="author">First Author</p>' in english
    assert '<img class="cover" src="en/CD/images/cover.jpg" alt="">' in english
    assert '<p class="first-printing">Printed once.</p>' in english
    assert f'<a class="read" href="en/CD/">{word("start_reading")}</a>' in english
    # an empty optional field leaves its line off the card
    assert '<img' not in lao and 'first-printing' not in lao
    assert 'class="description"' not in english


def test_card_leaves_out_a_line_whose_field_is_empty_and_leaves_any_other_name():
    pattern = '<li lang="{{lang}}">\n<img src="{{cover}}">\n<p>{{title}}, {{author}}</p>\n<p>{{description}}</p>\n</li>'
    book = {'lang': 'lo', 'web': 'AB/', 'title': 'T', 'author': 'A', 'cover': 'c.jpg', 'description': ''}
    assert build_home.card(pattern, book) == '\n<li lang="lo">\n<img src="AB/c.jpg">\n<p>T, A</p>\n</li>'
    # a name that is not a book field is left for --release to find
    assert build_home.card('<p>{{subtitle}}</p>', book) == '\n<p>{{subtitle}}</p>'


def test_lao_words_are_marked_as_on_the_book_pages(setup):
    site, books_path, repo = setup
    page = built(setup)
    head, body = page.split('<body>', 1)
    # every Lao letter of the body stands in a word mark, and the head is not marked
    text = ''.join(part for part in re.split(r'(<[^>]+>)', re.sub(r'<span class="w">[^<]*</span>', '', body))
                   if not part.startswith('<'))
    assert not LAO.search(text)
    assert '<span class="w">' in body and '<span class="w">' not in head
    # without its marks, the page is the filled layout
    layout = open(HOME_LAYOUT, encoding='utf-8').read()
    news = {lang: build_home.read_news(os.path.join(repo, 'news.yaml'), lang) for lang in WORDS}
    filled = build_home.fill(versioned(layout, stylesheet_version(site)), build_home.read_books(books_path, repo),
                             news, WORDS)
    assert unmarked(page) == filled


def test_news_lists_the_entries_of_every_language_in_order(setup):
    page = built(setup)
    region = page.split('<ul class="news-list">', 1)[1].split('</ul>', 1)[0]
    assert [line.strip() for line in region.strip().split('\n')] == [
        '<li lang="en" data-l="lo">Newest &amp; last added.</li>', '<li lang="en" data-l="lo">Oldest.</li>',
        '<li lang="en" data-l="th" hidden>An entry for the Thai page.</li>']


def test_real_news_file_lists_its_entries_in_every_language():
    news = {lang: build_home.read_news(lang=lang) for lang in WORDS}
    assert all(news.values())
    page = build_home.fill(open(HOME_LAYOUT, encoding='utf-8').read(), build_home.read_books(), news, WORDS)
    for lang, entries in news.items():
        for entry in entries:
            assert re.search(rf'<li lang="\w+" data-l="{lang}"( hidden)?>{re.escape(entry)}</li>', page)


def test_news_text_is_nine_tenths_of_the_reading_size_and_its_heading_is_not():
    layout = open(HOME_LAYOUT, encoding='utf-8').read()
    assert re.search(r'\.news-list \{[^}]*font-size: 0\.9em;', open(os.path.join(SITE, 'css', 'style.css'), encoding='utf-8').read())
    assert not re.search(r'(\.news h2|#news-heading)[^{]*\{', layout)


@pytest.mark.parametrize('text, message', [
    ('lo: an entry\n', 'stands alone on its line'),
    ('  - an entry before any language\n', 'an entry is one line'),
    ('lo:\n  an entry without its dash\n', 'an entry is one line'),
    ('lo:\n  -\n', 'an entry is one line'),
    ('lo:\n  - >\n', 'must stand on one line'),
])
def test_news_file_errors_stop_the_build(tmp_path, text, message):
    path = tmp_path / 'news.yaml'
    path.write_text(text, encoding='utf-8')
    with pytest.raises(SystemExit, match=message):
        build_home.read_news(str(path))


def test_page_source_holds_no_mail_address(setup):
    page = built(setup)
    assert not re.search(r'[\w.+-]+@[\w-]+\.[A-Za-z]', page)
    assert 'mailto:laoegw' not in page
    # where the script does not run, the address stands in a form robots do not
    # read as one; the script replaces it with the link
    assert '<span id="mail">laoegw [at] proton.me</span>' in page
    assert "getElementById('mail')" in page


def test_footer_labels_the_short_licence_line_and_the_book_pages_keep_theirs(setup):
    page = unmarked(built(setup))
    footer = page.split('<footer class="site-footer">', 1)[1].split('</footer>', 1)[0]
    assert (f'<p>{word("licence")}: <a rel="license" href="https://creativecommons.org/licenses/by-nd/4.0/">'
            'CC BY-ND 4.0</a></p>') in footer
    assert f'<p>{word("contact")}: <span id="mail">' in footer
    chapter_footer = open(os.path.join(LAYOUT, 'lo', 'chapter_footer.html'), encoding='utf-8').read()
    assert ('<a rel="license" href="https://creativecommons.org/licenses/by-nd/4.0/">Creative Commons '
            'Attribution-NoDerivatives 4.0 International (CC BY-ND 4.0)</a>') in chapter_footer


def test_stylesheet_is_versioned_by_its_content(setup):
    site = setup[0]
    css = os.path.join(site, 'css', 'style.css')
    for content in (b'body { margin: 0; }\n', b'body { margin: 1em; }\n'):
        with open(css, 'wb') as f:
            f.write(content)
        page = built(setup)
        version = hashlib.sha1(content).hexdigest()[:8]
        assert page.count(f'href="css/style.css?v={version}"') == 1


def test_every_tab_has_its_panel_its_list_and_its_language_button():
    layout = open(HOME_LAYOUT, encoding='utf-8').read()
    tabs = re.findall(r'role="tab" id="tab-(\w+)" data-lang="(\w+)" aria-controls="books-(\w+)"', layout)
    assert [tab[0] for tab in tabs] == ['lo', 'th', 'en']
    for tab_id, lang, panel in tabs:
        assert tab_id == lang == panel
        assert f'id="books-{lang}"' in layout
        assert f'<ul class="book-list" data-lang="{lang}">' in layout
    buttons = re.findall(r'<button type="button" data-lang="(\w+)" aria-pressed="(true|false)"', layout)
    assert buttons == [('lo', 'true'), ('th', 'false'), ('en', 'false')]
    assert [lang for lang, _ in buttons] == list(build_home.LANGS)
    # the Lao tab is selected and the only tab in the keyboard's tab order
    tags = re.findall(r'<button[^>]* role="tab"[^>]*>', layout)
    assert [('aria-selected="true"' in tag, 'tabindex="-1"' in tag) for tag in tags] == [
        (True, False), (False, True), (False, True)]
    assert '<div class="panel shown" id="books-lo">' in layout


def test_layout_takes_its_colours_and_dark_mode_from_the_book_stylesheet():
    layout = open(HOME_LAYOUT, encoding='utf-8').read()
    stylesheet = open(os.path.join(SITE, 'css', 'style.css'), encoding='utf-8').read()
    defined = set(re.findall(r'(--[\w-]+):', stylesheet))
    used = set(re.findall(r'var\((--[\w-]+)\)', layout))
    assert used - defined == set()
    style = ''.join(re.findall(r'<style>(.*?)</style>', layout, re.S))
    assert not re.search(r'#[0-9a-fA-F]{3,6}\b', style)
    assert 'prefers-color-scheme' not in layout
    assert '<link rel="stylesheet" href="css/style.css">' in layout


def test_site_name_font_is_set_in_one_place_and_served_by_the_site():
    stylesheet = open(os.path.join(SITE, 'css', 'style.css'), encoding='utf-8').read()
    assert stylesheet.count('--brand-family: "Lora", serif;') == 1
    assert stylesheet.count('var(--brand-family)') == 2
    for name in ('lo/home.html', 'lo/chapter_header.html'):
        layout = open(os.path.join(os.path.dirname(HOME_LAYOUT), '..', name), encoding='utf-8').read()
        assert 'fonts.googleapis' not in layout and 'fonts.gstatic' not in layout and '<style' not in layout
    for url in re.findall(r'url\("\.\./fonts/([^"]+)"\)', stylesheet):
        assert os.path.isfile(os.path.join(SITE, 'fonts', url)), url


def test_no_thai_or_lao_digits_and_no_invisible_characters(setup):
    paths = [HOME_LAYOUT, build_home.BOOKS, build_home.NEWS]
    paths += [os.path.join(LAYOUT, lang, 'labels.txt') for lang in build_home.LANGS]
    texts = [open(path, encoding='utf-8').read() for path in paths]
    texts.append(built(setup))
    for text in texts:
        assert not FORBIDDEN.search(text)


def test_link_check_passes_when_every_target_exists(setup):
    built(setup)
    assert check_home(setup[0]) == 0


def test_link_check_finds_a_book_not_built_and_a_missing_cover(setup, capsys):
    site, books_path, repo = setup
    # a third book whose pages and cover are not on the site
    os.makedirs(os.path.join(repo, 'xx', 'EF'))
    shutil.copy(os.path.join(repo, 'xx', 'CD', 'metadata.yaml'), os.path.join(repo, 'xx', 'EF'))
    with open(books_path, 'a', encoding='utf-8') as f:
        f.write('xx/EF:\n  web: EF\n  lang: en\n  cover: images/cover.jpg\n')
    built(setup)
    capsys.readouterr()
    assert check_home(site) == 2
    printed = capsys.readouterr().out.splitlines()
    assert 'BROKEN link index.html -> EF/' in printed
    assert 'BROKEN link index.html -> EF/images/cover.jpg' in printed


def test_link_check_follows_the_stylesheet_and_folder_links(tmp_path):
    page = str(tmp_path / 'index.html')
    (tmp_path / 'GC').mkdir()
    hrefs = ['css/style.css?v=21b6620d', 'GC/', 'GC', 'http-notes.html',
             'http://example.org/', 'https://example.org/', 'mailto:a@b.c', '#top']
    # a folder link needs index.html with or without the final slash, and
    # only http://, https://, mailto: and # are left unfollowed
    assert check_book.broken_links(page, hrefs) == ['css/style.css?v=21b6620d', 'GC/', 'GC', 'http-notes.html']
    (tmp_path / 'css').mkdir()
    (tmp_path / 'css' / 'style.css').write_text('', encoding='utf-8')
    (tmp_path / 'GC' / 'index.html').write_text('', encoding='utf-8')
    assert check_book.broken_links(page, hrefs) == ['http-notes.html']


def test_link_check_reads_escaped_links_as_a_browser_does(tmp_path):
    (tmp_path / 'index.html').write_text('<a href="a&amp;b.html">x</a>\n', encoding='utf-8')
    (tmp_path / 'a&b.html').write_text('', encoding='utf-8')
    assert check_home(str(tmp_path)) == 0


def test_language_must_match_the_metadata(setup):
    _, books_path, repo = setup
    with open(books_path, encoding='utf-8') as f:
        text = f.read()
    with open(books_path, 'w', encoding='utf-8') as f:
        f.write(text.replace('lang: lo', 'lang: en', 1))
    # the metadata holds a title and author in en, so only the language stops it
    with pytest.raises(SystemExit, match='has lang en'):
        build_home.read_books(books_path, repo)


def test_a_book_in_a_language_without_a_list_stops_the_build():
    book = {'folder': 'xx/FR', 'web': 'FR', 'lang': 'fr', 'title': 'T', 'author': 'A'}
    with pytest.raises(SystemExit, match='no list of books for it'):
        build_home.fill(open(HOME_LAYOUT, encoding='utf-8').read(), [book], {}, WORDS)


def test_title_and_author_are_escaped(setup):
    repo = setup[2]
    meta = os.path.join(repo, 'xx', 'AB', 'metadata.yaml')
    with open(meta, 'w', encoding='utf-8') as f:
        f.write(METADATA.replace('en-US', 'lo-LA').replace('Title in lo', '<b>&"').replace('Author in lo', '<i>'))
    page = built(setup)
    assert '<h3 class="title">&lt;b&gt;&amp;&quot;</h3>' in page
    assert '<p class="author">&lt;i&gt;</p>' in page
    assert '<b>' not in page and '<i>' not in page


@pytest.mark.parametrize('old, new, message', [
    ('web: AB', 'web: ../x', 'must be a plain path inside the site'),
    ('web: AB', 'web: https://x', 'must be a plain path inside the site'),
    ('cover: images/cover.jpg', 'cover: ../../x.jpg', 'must be a plain path inside the site'),
    ('description: A short line about the book.', 'description: >', 'must stand on one line'),
])
def test_unsafe_or_unread_values_stop_the_build(setup, old, new, message):
    _, books_path, _ = setup
    with open(books_path, encoding='utf-8') as f:
        text = f.read()
    assert old in text
    with open(books_path, 'w', encoding='utf-8') as f:
        f.write(text.replace(old, new, 1))
    with pytest.raises(SystemExit, match=message):
        built(setup)


@pytest.fixture
def release_run(tmp_path):
    """A site the real list of books can be built into, a copy of the layout
    whose word tables hold a plain word for every [OPEN note, and a news file
    with no note. Returns the arguments that build there."""
    site = tmp_path / 'site'
    (site / 'css').mkdir(parents=True)
    (site / 'css' / 'style.css').write_text('', encoding='utf-8')
    (site / 'GC' / 'images').mkdir(parents=True)
    (site / 'GC' / 'index.html').write_text('', encoding='utf-8')
    (site / 'GC' / 'images' / 'cover.jpg').write_bytes(b'')
    layout = tmp_path / 'layout'
    for lang in build_home.LANGS:
        (layout / lang).mkdir(parents=True)
        text = open(os.path.join(LAYOUT, lang, 'labels.txt'), encoding='utf-8').read()
        (layout / lang / 'labels.txt').write_text(re.sub(r'\[OPEN[^\]]*\]', 'word', text), encoding='utf-8')
    shutil.copy(HOME_LAYOUT, layout / 'lo')
    news = tmp_path / 'news.yaml'
    news.write_text('lo:\n  - An entry.\nth:\n  - An entry.\nen:\n  - An entry.\n', encoding='utf-8')
    return ['--site', str(site), '--words-cache', str(tmp_path / 'words.json'),
            '--layout', str(layout), '--news', str(news)]


def test_release_passes_the_real_page(release_run, capsys):
    run = release_run[:4]  # the real layout, word tables and news
    for argv in (run, run + ['--release']):
        with pytest.raises(SystemExit) as stop:
            build_home.main(argv)
        assert stop.value.code == 0
    page = open(os.path.join(release_run[1], 'index.html'), encoding='utf-8').read()
    assert not build_home.PLACEHOLDER.search(page)
    assert 'placeholders standing' not in capsys.readouterr().out


def test_release_passes_a_page_with_no_placeholder(release_run):
    for argv in (release_run, release_run + ['--release']):
        with pytest.raises(SystemExit) as stop:
            build_home.main(argv)
        assert stop.value.code == 0
    page = open(os.path.join(release_run[1], 'index.html'), encoding='utf-8').read()
    assert not build_home.PLACEHOLDER.search(page)


@pytest.mark.parametrize('where, placeholder', [
    ('layout', '<p>[OPEN a question still open]</p>'),
    ('layout', '<p>[OPEN: a question still open]</p>'),
    ('layout', '<h2>{{news_heading}}</h2>'),
    ('news', '[OPEN: news line to write]'),
    ('words', '[OPEN: a word to rule]'),
])
def test_release_refuses_an_open_note_or_an_unfilled_field(release_run, capsys, where, placeholder):
    layout, news = release_run[5], release_run[7]
    if where == 'layout':
        home = os.path.join(layout, 'lo', 'home.html')
        text = open(home, encoding='utf-8').read()
        open(home, 'w', encoding='utf-8').write(text.replace('<main>', '<main>\n' + placeholder, 1))
    elif where == 'news':
        open(news, 'a', encoding='utf-8').write(f'  - {placeholder}\n')
    else:
        labels = os.path.join(layout, 'th', 'labels.txt')
        text = open(labels, encoding='utf-8').read()
        open(labels, 'w', encoding='utf-8').write(re.sub(r'\n  contact: [^\n]*', f'\n  contact: {placeholder}', text))
    # the placeholder stops --release, and only --release
    for argv, code in ((release_run, 0), (release_run + ['--release'], 1)):
        with pytest.raises(SystemExit) as stop:
            build_home.main(argv)
        assert stop.value.code == code
    assert 'placeholders standing ([OPEN or an unfilled {{field}}): 1;' in capsys.readouterr().out


@pytest.mark.parametrize('layout, message', [
    ('<body></body>', 'card pattern'),
    ('<template class="book-card">\n<li>{{title}}</li>\n</template>\n<ul class="news-list">\n</ul>', 'no <ul class="book-list"'),
    ('<template class="book-card">\n<li>{{title}}</li>\n</template>\n<ul class="book-list" data-lang="lo">\n</ul>', 'no <ul class="news-list">'),
])
def test_layout_without_its_pattern_or_lists_is_refused(layout, message):
    with pytest.raises(SystemExit, match=message):
        build_home.fill('\n' + layout, [])
