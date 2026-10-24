"""Tests for parsers/sc_typst.py: SC01 to SC08 as they stand on main, and small made-up inputs."""
import re
import unittest

from helpers import REPO, SC_BOOK, SC_COUNTS, git_reader

import parsers
from parsers import sc_typst
from parsers.sc_typst import ParseError
from server.text import forbidden_char

EN = """---
book:
  title:
    en: Book
chapter:
  number: 1
  title:
    en: Sample Title
    indented: front matter line
---

## {SC 9.1}

First paragraph. {SC 9.1}

## {SC 9.2}

    Verse line one;
    Verse line two.
    Psalm 1:1. {SC 9.2}
"""

TH = """// Source-url: x
#import "../lib.typ": *
#show: apply-styles.with(proofing: true)

#chapter(
  number: 1,
    title: "Chapter title",
)

// {SC 9.1}

Text with #italic[slanted] and a note#footnote[See #italic[this] [nested]] and \\{braces\\}. #EGW[\\{SC 9.1\\}]

// {SC 9.2}

Second paragraph. #EGW[\\{SC 9.2\\}]
"""


def fake_reader(files):
    return lambda path: files.get(path)


def files_for(th, en=EN, n=1):
    nn = f"{n:02d}"
    return {f"th/SC/02_edit/SC{nn}_th.typ": th, f"th/SC/00_source/SC{nn}_en.md": en}


@unittest.skipIf(REPO is None, "the translation repository is not found; set REVIEW_REPO")
class MainChapters(unittest.TestCase):
    """SC01 to SC08 read from main."""

    @classmethod
    def setUpClass(cls):
        read = git_reader(REPO)
        cls.chapters = {n: sc_typst.load_chapter(SC_BOOK, n, read) for n in SC_COUNTS}

    def test_paragraph_counts(self):
        self.assertEqual({n: len(c["paragraphs"]) for n, c in self.chapters.items()}, SC_COUNTS)
        self.assertEqual(sum(len(c["paragraphs"]) for c in self.chapters.values()), 149)

    def test_ids_titles_and_sources(self):
        for n, c in self.chapters.items():
            self.assertEqual(c["id"], f"SC{n:02d}")
            self.assertTrue(c["title"] and c["title_en"])
            self.assertTrue(c["sources"][0].endswith(f"SC{n:02d}_th.typ"))
        self.assertEqual(self.chapters[1]["title_en"], "God’s Love for Man")

    def test_every_anchor_has_english(self):
        for c in self.chapters.values():
            for p in c["paragraphs"]:
                self.assertRegex(p["a"], r"^SC \d+\.\d+$")
                self.assertTrue(p["en"].startswith("<p"), p["a"])
                self.assertNotIn("{SC", p["en"])

    def test_anchors_unique_and_in_order(self):
        for c in self.chapters.values():
            anchors = [tuple(map(int, p["a"][3:].split("."))) for p in c["paragraphs"]]
            self.assertEqual(anchors, sorted(set(anchors)))

    def test_footnotes(self):
        notes = {n: sum(len(p["fn"]) for p in c["paragraphs"]) for n, c in self.chapters.items()}
        self.assertEqual(notes[1], 2)
        for c in self.chapters.values():
            for p in c["paragraphs"]:
                marks = re.findall(r'<sup class="fn">(\d+)</sup>', p["text"])
                self.assertEqual(len(marks), len(p["fn"]), p["a"])

    def test_italics(self):
        self.assertGreater(sum(p["text"].count("<em>") for p in self.chapters[6]["paragraphs"]), 0)
        for c in self.chapters.values():
            for p in c["paragraphs"]:
                self.assertEqual(p["text"].count("<em>"), p["text"].count("</em>"))

    def test_verse_lines_keep_breaks(self):
        p = next(p for p in self.chapters[1]["paragraphs"] if p["a"] == "SC 9.2")
        self.assertIn('<p class="verse">', p["en"])
        self.assertEqual(p["en"].count("<br>"), 4)

    def test_no_markup_left_and_no_forbidden_characters(self):
        for c in self.chapters.values():
            for p in c["paragraphs"]:
                for part in [p["text"], *p["fn"]]:
                    self.assertNotIn("#EGW", part)
                    self.assertNotIn("#italic", part)
                    self.assertIsNone(forbidden_char(part), p["a"])
                    self.assertNotIn("\\", part)


class MadeUpInputs(unittest.TestCase):
    def load(self, th, en=EN):
        """Through parsers.load_chapter, which runs the format module and then the checks for every book."""
        return parsers.load_chapter(SC_BOOK, 1, fake_reader(files_for(th, en)))

    def test_inline_markup(self):
        c = self.load(TH)
        self.assertEqual(c["title"], "Chapter title")
        self.assertEqual(c["title_en"], "Sample Title")
        p = c["paragraphs"][0]
        self.assertEqual(p["text"], 'Text with <em>slanted</em> and a note<sup class="fn">1</sup> and {braces}.')
        self.assertEqual(p["fn"], ["See <em>this</em> [nested]"])
        self.assertEqual(c["paragraphs"][1]["en"],
                         '<p class="verse">Verse line one;<br>Verse line two.<br>Psalm 1:1.</p>')
        self.assertEqual(c["paragraphs"][0]["en"], "<p>First paragraph.</p>")

    def test_block_comments_are_left_out_as_typst_leaves_them_out(self):
        # A Typst block comment never prints, so readers never see it, as in {SC 64.1}.
        c = self.load(TH.replace("Second paragraph.", "Second/*health of our countenance from Psalm 43:5*/ "
                                 "paragraph /* a /* nested */ note */ ends#footnote[A note/*hidden]*/.]."))
        p = c["paragraphs"][1]
        self.assertEqual(p["text"], 'Second paragraph ends<sup class="fn">1</sup>.')
        self.assertEqual(p["fn"], ["A note."])
        self.assertNotIn("Psalm", p["text"])
        c = self.load(TH.replace("Second paragraph.", "Ends with a comment./*see Psalm 43:5*/"))
        self.assertEqual(c["paragraphs"][1]["text"], "Ends with a comment.")
        # An escaped slash is text, and a comment left open is refused.
        self.assertEqual(self.load(TH.replace("Second paragraph.", "a \\/* b"))["paragraphs"][1]["text"], "a /* b")
        with self.assertRaisesRegex(ParseError, "unclosed comment"):
            self.load(TH.replace("Second paragraph.", "a /* b"))

    def test_stage_order(self):
        files = files_for(TH)
        files["th/SC/03_public/SC01_th.typ"] = TH.replace("Second paragraph.", "Public text.")
        c = sc_typst.load_chapter(SC_BOOK, 1, fake_reader(files))
        self.assertEqual(c["paragraphs"][1]["text"], "Public text.")
        self.assertEqual(c["sources"][0], "th/SC/03_public/SC01_th.typ")

    def test_refuses_marker_and_choice(self):
        for bad in ("[[ marker ]]", "((a|b))"):
            with self.assertRaisesRegex(ParseError, "marker"):
                self.load(TH.replace("Second paragraph.", bad))

    def test_refuses_missing_english(self):
        with self.assertRaisesRegex(ParseError, "no English for SC 9.2"):
            self.load(TH, EN.split("## {SC 9.2}")[0])

    def test_refuses_mismatched_mark(self):
        with self.assertRaisesRegex(ParseError, "ends with the mark"):
            self.load(TH.replace("#EGW[\\{SC 9.2\\}]", "#EGW[\\{SC 9.3\\}]"))

    def test_refuses_unknown_call_and_text_before_anchor(self):
        with self.assertRaisesRegex(ParseError, "unknown Typst call"):
            self.load(TH.replace("Second paragraph.", "#strong[x]"))
        with self.assertRaisesRegex(ParseError, "before the first anchor"):
            self.load(TH.replace("// {SC 9.1}\n", ""))

    def test_refuses_thai_digit_and_invisible_characters(self):
        for ch in ("\u0e51", "\u0ed1", "\u200b", "\U000e0041", "\u2066", "\ufe0f", "\U000e0100", "\u034f",
                   "\u180e", "\u3164", "\u00ad"):
            with self.assertRaisesRegex(ParseError, f"U\\+{ord(ch):04X}"):
                self.load(TH.replace("Second paragraph.", f"Second{ch} paragraph."))
        with self.assertRaisesRegex(ParseError, "title holds the character U\\+2069"):
            self.load(TH.replace("Chapter title", "Chapter\u2069 title"))

    def test_file_names_from_the_names_map(self):
        book = dict(SC_BOOK, id="DA", source="th/DA/{stage}/{name}_th.typ", english="th/DA/00_source/{name}_en.md",
                    names={"0": "DA00_preface"})
        self.assertEqual(sc_typst.chapter_paths(book, 0, "01_raw"),
                         ("th/DA/01_raw/DA00_preface_th.typ", "th/DA/00_source/DA00_preface_en.md"))
        self.assertEqual(sc_typst.chapter_paths(book, 3, "01_raw"),
                         ("th/DA/01_raw/DA03_th.typ", "th/DA/00_source/DA03_en.md"))
        self.assertEqual(sc_typst.chapter_paths(SC_BOOK, 9, "02_edit"),
                         ("th/SC/02_edit/SC09_th.typ", "th/SC/00_source/SC09_en.md"))

    def test_missing_file(self):
        with self.assertRaisesRegex(ParseError, "not found"):
            sc_typst.load_chapter(SC_BOOK, 2, fake_reader(files_for(TH)))


if __name__ == "__main__":
    unittest.main()


class EnglishCommentTest(unittest.TestCase):
    def test_markdown_comment_is_dropped(self):
        from parsers.sc_typst import english_chapter
        text = "---\nchapter:\n  title:\n    en: Test\n---\n\n## {SC 9.1}\n\nNature <!-- a note for the translator --> speaks. {SC 9.1}\n"
        title, en = english_chapter(text, "SC01")
        self.assertNotIn("note for the translator", str(en))
        self.assertIn("speaks", str(en))
