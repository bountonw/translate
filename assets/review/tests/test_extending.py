"""Tests for the extension places: the language registry, the content model with its marked spans,
and annotators."""
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path

from helpers import SC_BOOK, Site, sample_chapter
from test_parser import EN, TH, fake_reader, files_for

import parsers
from server import content, languages, text


class LanguageRegistry(unittest.TestCase):
    def test_thai_is_registered_and_the_project_ban_stays(self):
        reg = languages.REGISTRY
        self.assertIn("th", reg.codes)
        self.assertEqual(reg.data["languages"]["th"]["font"]["family"], "Sarabun")
        for code, entry in reg.data["languages"].items():
            font = entry["font"]
            for f in font["files"] + [{"src": font["license"]}]:
                self.assertTrue((languages.PATH.parent / f["src"]).is_file(), (code, f["src"]))
        # Thai and Lao digits are refused in every book, with or without a language entry.
        for lang in (None, "th", "lo"):
            self.assertEqual(text.forbidden_char("abc \u0e51", lang), "\u0e51")
            self.assertEqual(text.forbidden_char("abc \u0ed1", lang), "\u0ed1")
            self.assertIsNone(text.forbidden_char("abc 1 \u0e19\u0e49\u0e33", lang))
        # Reader text: every refused digit becomes a Western digit.
        self.assertEqual("\u0e50\u0e59\u0ed3".translate(text.DIGITS), "093")

    def test_a_language_entry_adds_its_own_characters(self):
        data = json.loads(languages.PATH.read_text())
        data["languages"]["xx"] = {"name": "Test", "font": {"family": "F", "files": []},
                                   "refuse": [{"range": "U+00AA"}, {"range": "U+0660-U+0669"}]}
        reg = languages.Registry(data)
        self.assertTrue(reg.refused("\u00aa", "xx"))
        self.assertFalse(reg.refused("\u00aa", "th"))
        self.assertTrue(reg.refused("\u0ed5", "xx"))
        self.assertEqual(reg.digits()[0x0663], "3")
        self.assertNotIn(0x00AA, reg.digits())

    def test_a_broken_registry_is_refused(self):
        good = json.loads(languages.PATH.read_text())
        for change in (lambda d: d.update(languages={}),
                       lambda d: d["languages"]["th"].update(name=""),
                       lambda d: d["languages"]["th"].pop("font"),
                       lambda d: d["languages"]["th"].update(refuse=[{"range": "0E50"}]),
                       lambda d: d["languages"]["th"].update(refuse=[{"range": "U+0E59-U+0E50"}]),
                       lambda d: d["languages"].update({"Thai!": d["languages"]["th"]})):
            d = json.loads(json.dumps(good))
            change(d)
            with self.assertRaises(languages.RegistryError):
                languages.Registry(d)
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "x.json").write_text("{")
            with self.assertRaises(languages.RegistryError):
                languages.load(Path(tmp) / "x.json")

    def test_publish_names_a_registered_language(self):
        site = Site()
        self.addCleanup(site.close)
        ch = sample_chapter(1)
        for bad in ("qaa", "xx", 5):        # qaa is a code reserved for local use, never registered
            r = site.admin_call("PUT", "/api/admin/chapters/SC/SC01", dict(ch, language=bad))
            self.assertEqual((r.status, r.json["error"]), (400, "unknown_language"), bad)
        r = site.admin_call("PUT", "/api/admin/chapters/SC/SC01", {k: v for k, v in ch.items() if k != "language"})
        self.assertEqual((r.status, r.json["error"]), (400, "unknown_language"))
        site.publish(ch)
        # A book already known keeps its language when publish leaves it out.
        r = site.admin_call("PUT", "/api/admin/chapters/SC/SC02", {k: v for k, v in sample_chapter(2).items()
                                                                     if k != "language"})
        self.assertEqual(r.status, 200, r.body)

    def test_parser_refuses_a_book_whose_language_is_not_registered(self):
        with self.assertRaisesRegex(parsers.ParseError, "not in web/languages.json"):
            parsers.load_chapter(dict(SC_BOOK, language="qaa"), 1, fake_reader(files_for(TH)))
        with self.assertRaisesRegex(parsers.ParseError, "does not exist"):
            parsers.load_chapter(dict(SC_BOOK, parser="no_such_format"), 1, fake_reader(files_for(TH)))


class ContentModel(unittest.TestCase):
    def test_tags(self):
        ok = ["<em>a</em>", '<sup class="fn">1</sup>', '<p class="verse">a<br>b</p>', "<br/>",
              '<span data-kind="bible" data-value="John 3:16">x</span>',
              '<span class="term" data-kind="glossary" data-value="grace &amp; truth">x</span>',
              '<span data-kind="name">x</span>']
        bad = ["<script>x</script>", '<p onclick="x">a</p>', '<span data-kind="Bible">x</span>',
               '<span data-value="x" data-kind="bible">x</span>', '<span data-kind="b" data-value="a"b">x</span>',
               '<span data-kind="b" data-value="a & b">x</span>', '<span data-kind="b" data-value="<x>">x</span>',
               '<span data-kind="b" style="x">x</span>', '<a href="x">x</a>', "a < b", '<span id="x">x</span>']
        for t in ok:
            self.assertTrue(content.safe_html(t), t)
        for t in bad:
            self.assertFalse(content.safe_html(t), t)
        self.assertEqual(content.marks('<span data-kind="bible" data-value="A &amp; B">x</span> <em>y</em>'),
                         [("bible", "A & B")])

    def test_the_server_accepts_marked_spans_and_the_export_shows_the_words(self):
        site = Site()
        self.addCleanup(site.close)
        ch = sample_chapter(1)
        ch["paragraphs"][0]["th"] = 'See <span data-kind="bible" data-value="John 3:16">John 3:16</span> here'
        site.publish(ch)
        code = site.invite("R", ["SC"])["code"]
        body = site.call("GET", "/api/chapter/SC/SC01", token=code).json
        self.assertIn('data-kind="bible"', body["paragraphs"][0]["th"])
        site.comment(code, "SC 101.1", kind="wording", quote="John 3:16", text="x")
        row = site.admin_call("GET", "/api/admin/export").json["comments"][0]
        self.assertEqual((row["th"], row["quote_found"]), ("See John 3:16 here", True))
        ch["paragraphs"][0]["th"] = '<span data-kind="bible" onclick="x">x</span>'
        r = site.admin_call("PUT", "/api/admin/chapters/SC/SC01", ch)
        self.assertEqual((r.status, r.json["error"]), (400, "unsafe_html"))


class EveryFormat(unittest.TestCase):
    """The checks of parsers.check_chapter hold for any format module, not only sc_typst."""

    def fmt(self, title="Title", th="Text", fn=(), en="<p>English</p>"):
        m = types.ModuleType("parsers.test_format")
        m.load_chapter = lambda book, n, read: {
            "id": f"{book['id']}{n:02d}", "n": n, "title_th": title, "title_en": "English title",
            "paragraphs": [{"a": "XX 1.1", "th": "Fine", "fn": [], "en": "<p>x</p>"},
                           {"a": "XX 1.2", "th": th, "fn": list(fn), "en": en}], "sources": []}
        sys.modules[m.__name__] = m
        self.addCleanup(sys.modules.pop, m.__name__, None)
        return parsers.load_chapter({"id": "XX", "language": "th", "parser": "test_format"}, 1, None)

    def test_markers_are_refused_in_any_format(self):
        self.assertEqual(len(self.fmt()["paragraphs"]), 2)
        for kw in (dict(th="Text [[marker: check this]]"), dict(th="((a | b)) choice"), dict(fn=["note [[x]]"]),
                   dict(title="Title ((a | b))")):
            with self.assertRaisesRegex(parsers.ParseError, "marker or an editor's choice", msg=kw):
                self.fmt(**kw)

    def test_the_english_is_checked_for_invisible_characters_and_digits(self):
        for bad in ("\u202e", "\u200b", "\u0e51"):
            with self.assertRaisesRegex(parsers.ParseError, f"U\\+{ord(bad):04X}"):
                self.fmt(en=f"<p>English{bad}</p>")


class Annotators(unittest.TestCase):
    def install(self, name, annotate):
        m = types.ModuleType(f"parsers.annotators.{name}")
        m.annotate = annotate
        sys.modules[m.__name__] = m
        self.addCleanup(sys.modules.pop, m.__name__)

    def test_the_list_is_empty_for_sc(self):
        books = json.loads((Path(parsers.__file__).parents[1] / "books.json").read_text())
        self.assertEqual(books["SC"]["annotators"], [])

    def test_annotators_run_in_order_and_may_not_change_words(self):
        def mark(p, book):
            return dict(p, th=p["th"].replace("Second", '<span data-kind="test" data-value="2">Second</span>'))

        def wrap(p, book):
            return dict(p, th=p["th"].replace("paragraph", "<em>paragraph</em>"))

        self.install("mark_two", mark)
        self.install("wrap", wrap)
        book = dict(SC_BOOK, annotators=["mark_two", "wrap"])
        ch = parsers.load_chapter(book, 1, fake_reader(files_for(TH, EN)))
        self.assertEqual(ch["paragraphs"][1]["th"], '<span data-kind="test" data-value="2">Second</span> '
                                                    "<em>paragraph</em>.")
        self.install("rewrite", lambda p, book: dict(p, th="Other words"))
        with self.assertRaisesRegex(parsers.ParseError, "changed the words"):
            parsers.load_chapter(dict(SC_BOOK, annotators=["rewrite"]), 1, fake_reader(files_for(TH, EN)))
        self.install("unsafe", lambda p, book: dict(p, th=p["th"].replace("Second", '<b onclick="x">Second</b>')))
        with self.assertRaisesRegex(parsers.ParseError, "content model"):
            parsers.load_chapter(dict(SC_BOOK, annotators=["unsafe"]), 1, fake_reader(files_for(TH, EN)))
        with self.assertRaisesRegex(parsers.ParseError, "does not exist"):
            parsers.load_chapter(dict(SC_BOOK, annotators=["missing_one"]), 1, fake_reader(files_for(TH, EN)))


if __name__ == "__main__":
    unittest.main()
