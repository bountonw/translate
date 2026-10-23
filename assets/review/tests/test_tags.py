"""Tests for paragraph tags: a source with text but no tags stops publish with a plain message, and the
markers of a chapter file are found by the tag that stands before them."""
import argparse
import contextlib
import io
import unittest
from unittest import mock

from helpers import REPO, SC_BOOK
from test_parser import EN, TH, fake_reader, files_for

import parsers
import review

UNTAGGED = """#import "../lib.typ": *
#chapter(
  number: 1,
    title: "Chapter title",
)

First paragraph, with no tag before it.

Second paragraph.
"""


class NoTags(unittest.TestCase):
    def test_thai_without_tags(self):
        with self.assertRaises(parsers.NoTags) as e:
            parsers.load_chapter(SC_BOOK, 1, fake_reader(files_for(UNTAGGED)))
        message = str(e.exception)
        self.assertTrue(message.startswith("The book SC has no paragraph tags: SC01 has text in its Thai file "
                                           "th/SC/02_edit/SC01_th.typ but no tag such as {SC 1.1}"), message)
        self.assertIn("never by its place in the chapter", message)

    def test_english_without_tags(self):
        en = EN.replace("## {SC 9.1}", "## One").replace("## {SC 9.2}", "## Two")
        with self.assertRaisesRegex(parsers.NoTags, r"English file th/SC/00_source/SC01_en.md but no tag such as "
                                                    r"## \{SC 1.1\}"):
            parsers.load_chapter(SC_BOOK, 1, fake_reader(files_for(TH, en)))

    def test_one_missing_tag_is_another_fault(self):
        with self.assertRaises(parsers.ParseError) as e:
            parsers.load_chapter(SC_BOOK, 1, fake_reader(files_for(TH.replace("// {SC 9.1}\n", ""))))
        self.assertNotIsInstance(e.exception, parsers.NoTags)

    @unittest.skipIf(REPO is None, "the translation repository is not found; set REVIEW_REPO")
    def test_publish_stops_before_anything_is_sent(self):
        real = review.repo_reader(REPO, "main")
        files = {"th/SC/03_public/SC02_th.typ": UNTAGGED}

        def reader(repo, ref):
            return lambda path: files[path] if path in files else real(path)

        sent = []

        class Client:
            def call(self, *args, **kw):
                sent.append(args)
                return {}

        a = argparse.Namespace(book="SC", chapters=["01-02"], repo=str(REPO), ref=None, result=None)
        with mock.patch.object(review, "repo_reader", reader), self.assertRaises(review.CLIError) as e, \
                contextlib.redirect_stdout(io.StringIO()):
            review.cmd_publish(a, Client())
        self.assertIn("The book SC has no paragraph tags: SC02", str(e.exception))
        self.assertTrue(str(e.exception).endswith("Nothing was published."))
        self.assertEqual(sent, [])


class Markers(unittest.TestCase):
    def test_each_marker_belongs_to_the_tag_before_it(self):
        text = ("// {SC 9.1}\nFirst [[FACT MED #1|a -> b|EN \"x\"; see {SC 3.2}]] text "
                "[[GRAM LOW #2|c -> d|note]] #EGW[\\{SC 9.1\\}]\n\n// {SC 9.2}\nSecond. #EGW[\\{SC 9.2\\}]\n\n"
                "// {SC 9.3}\nThird [[STYLE LOW #3|e -> f|multi\nline]] end #EGW[\\{SC 9.3\\}]\n")
        found = parsers.markers(text)
        self.assertEqual(sorted(found), ["SC 9.1", "SC 9.3"])
        self.assertEqual([m[:14] for m in found["SC 9.1"]], ["[[FACT MED #1|", "[[GRAM LOW #2|"])
        self.assertTrue(found["SC 9.3"][0].endswith("multi\nline]]"))
        self.assertEqual(parsers.markers("No markers here {SC 1.1}."), {})
        self.assertEqual(parsers.markers("[[before any tag]]"), {"": ["[[before any tag]]"]})

    def test_markdown_headings_count_as_tags(self):
        text = "## {GC 17.2}\n\nText [[FACT HIGH #4|x -> y|z]].\n"
        self.assertEqual(parsers.markers(text), {"GC 17.2": ["[[FACT HIGH #4|x -> y|z]]"]})


if __name__ == "__main__":
    unittest.main()
