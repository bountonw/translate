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
"""
import importlib
import re

from server.content import plain, safe_html
from server.languages import REGISTRY
from server.text import forbidden_char


class ParseError(ValueError):
    """The chapter cannot be published as it stands."""


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
    bad = forbidden_char(chapter["title_th"], language) or forbidden_char(chapter.get("title_en", ""))
    if bad:
        raise ParseError(f"{cid}: the title holds the character U+{ord(bad):04X}")
    if any(m in chapter["title_th"] for m in MARKERS):
        raise ParseError(f"{cid}: the title holds a marker or an editor's choice; resolve it first")
    for p in chapter["paragraphs"]:
        for part in [p["th"], *p["fn"], p.get("en", "")]:
            if not safe_html(part):
                raise ParseError(f"{cid}: {{{p['a']}}} holds HTML outside the content model (server/content.py)")
        if any(m in part for part in [p["th"], *p["fn"]] for m in MARKERS):
            raise ParseError(f"{cid}: {{{p['a']}}} holds a marker or an editor's choice; resolve it first")
        # The English is checked by the rules for every book: no invisible character, no Thai or Lao digit.
        bad = forbidden_char(p["th"] + "".join(p["fn"]), language) or forbidden_char(p.get("en", ""))
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


def words(p):
    """A paragraph's text without its HTML, which an annotator must leave as it found it."""
    return [plain(x) for x in (p["th"], *p["fn"], p.get("en", ""))]
