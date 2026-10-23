"""Book parsers: one module per source format, each offering load_chapter(book, n, read).

load_chapter here is what review.py calls. It picks the format module the
book's books.json entry names ("parser"), runs the book's annotators over
every paragraph ("annotators", a list of module names in parsers/annotators/,
empty for every book now), and checks the result: every paragraph must keep to
the content model (server/content.py), no text may hold a character the
language registry refuses for the book's language (web/languages.json), and
no title, paragraph or footnote may hold a marker [[ or an editor's choice ((.
These checks hold for every format. EXTENDING.md says how to add a format or
an annotator.

A chapter is {"id", "n", "title", "title_en", "paragraphs", "sources"}, and each
paragraph {"a", "text", "fn", "en"}: title and text hold the book's own
language, whatever it is (books.json "language"); the _en fields the English.
"""
import importlib
import re

from server.content import plain, safe_html
from server.languages import REGISTRY
from server.text import forbidden_char


class ParseError(ValueError):
    """The chapter cannot be published as it stands."""


class NoTags(ParseError):
    """The source has text but no paragraph tags, such as {SC 9.1}, so no paragraph can be named. A paragraph
    is always named by the tag written into the source, never by its position, so publish stops."""


def no_tags(book_id, cid, where, example):
    """The NoTags error for a chapter whose source (where: "Thai" or "English", with its path) has text but no tag."""
    return NoTags(f"The book {book_id} has no paragraph tags: {cid} has text in its {where} but no tag such as "
                  f"{example} before each paragraph. A paragraph is named only by its tag, never by its place in "
                  "the chapter, so the tags are written into the book's source once, before anything is published.")


NAME_RE = re.compile(r"[a-z][a-z0-9_]{0,40}")


def module(kind, name):
    if not isinstance(name, str) or not NAME_RE.fullmatch(name):
        raise ParseError(f"books.json names the {kind} {name!r}; write the name of a module in parsers/")
    package = "parsers" if kind == "parser" else "parsers.annotators"
    try:
        return importlib.import_module(f"{package}.{name}")
    except ModuleNotFoundError:
        raise ParseError(f"books.json names the {kind} {name}, but {package.replace('.', '/')}/{name}.py does not exist")


def check_language(book):
    language = book.get("language")
    if language not in REGISTRY.refuse:
        raise ParseError(f"book {book.get('id')}: the language {language!r} is not in web/languages.json "
                         f"(it lists {', '.join(REGISTRY.codes)})")
    return language


MARKERS = ("[[", "((")


def check_chapter(chapter, language):
    """Refuse a chapter whose HTML leaves the content model, whose text holds a refused character, or whose
    title, paragraphs or footnotes hold a marker [[ or an editor's choice ((, whatever its format."""
    cid = chapter["id"]
    if not chapter.get("paragraphs"):
        raise ParseError(f"{cid}: no paragraphs")
    bad = forbidden_char(chapter["title"], language) or forbidden_char(chapter.get("title_en", ""))
    if bad:
        raise ParseError(f"{cid}: the title holds the character U+{ord(bad):04X}")
    if any(m in chapter["title"] for m in MARKERS):
        raise ParseError(f"{cid}: the title holds a marker or an editor's choice; resolve it first")
    for p in chapter["paragraphs"]:
        for part in [p["text"], *p["fn"], p.get("en", "")]:
            if not safe_html(part):
                raise ParseError(f"{cid}: {{{p['a']}}} holds HTML outside the content model (server/content.py)")
        if any(m in part for part in [p["text"], *p["fn"]] for m in MARKERS):
            raise ParseError(f"{cid}: {{{p['a']}}} holds a marker or an editor's choice; resolve it first")
        # The English is checked by the rules for every book: no invisible character, no Thai or Lao digit.
        bad = forbidden_char(p["text"] + "".join(p["fn"]), language) or forbidden_char(p.get("en", ""))
        if bad:
            raise ParseError(f"{cid}: {{{p['a']}}} holds the character U+{ord(bad):04X}")


def load_chapter(book, n, read):
    """Chapter n of book, parsed by the book's format module, annotated and checked."""
    language = check_language(book)
    annotators = [module("annotator", name) for name in book.get("annotators", [])]
    chapter = module("parser", book.get("parser")).load_chapter(book, n, read)
    for a in annotators:
        out = []
        for p in chapter["paragraphs"]:
            q = a.annotate(dict(p, fn=list(p["fn"])), book)
            if words(q) != words(p):
                raise ParseError(f"{chapter['id']}: the annotator {a.__name__} changed the words of {{{p['a']}}}")
            out.append(q)
        chapter["paragraphs"] = out
    check_chapter(chapter, language)
    return chapter


# A marker in a chapter file, [[TYPE ...|old -> new|note]], and a paragraph tag as a source writes it: {SC 9.1}
# in a comment line or a heading, or \{SC 9.1\} inside a Typst call.
MARKER_RE = re.compile(r"\[\[.*?\]\]", re.S)
TAG_RE = re.compile(r"\\?\{([A-Za-z]{1,10} \d{1,4}\.\d{1,4})\\?\}")


def markers(text):
    """The markers [[...]] of a chapter file, by the paragraph tag that stands nearest before each:
    {"SC 9.1": ["[[FACT MED #1|...]]"]}. Tags quoted inside a marker do not count. Works for any format whose
    paragraphs follow their tags, as SC's Typst chapters and GC's Markdown chapters do."""
    found = list(MARKER_RE.finditer(text))
    masked = list(text)
    for m in found:
        masked[m.start():m.end()] = " " * (m.end() - m.start())
    tags = [(t.start(), t.group(1)) for t in TAG_RE.finditer("".join(masked))]
    out = {}
    for m in found:
        before = [a for pos, a in tags if pos < m.start()]
        out.setdefault(before[-1] if before else "", []).append(m.group(0))
    return out


def words(p):
    """A paragraph's text without its HTML, which an annotator must leave as it found it."""
    return [plain(x) for x in (p["text"], *p["fn"], p.get("en", ""))]
