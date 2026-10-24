"""Tests for sentence alignment: the alignment text, the English sentences, the alignment file that publish
reads and checks, the pairs in the chapter answer, and align-packet."""
import argparse
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from helpers import REPO, Site, sample_chapter

import parsers
import review
from parsers import align
from server.content import align_text

HTML_TH = 'คำแรก &amp; คำสอง<sup class="fn">1</sup> <em>คำสาม</em>'
HTML_EN = ('<p>He came. Mr. Smith said "No!" and left. Then he wept.</p>'
           '<p class="verse">The Lord is my shepherd;<br>I shall not want.<br>He leads me.</p>')


def para(a="SC 9.1", text=HTML_TH, en=HTML_EN):
    return {"a": a, "text": text, "fn": [], "en": en}


def align_file(chapter, pairs, fmt=align.FORMAT):
    """An alignment file for the chapter, with the given pairs by anchor and the right hashes. Format 1 names
    the text's side th, format 2 text."""
    side = align.FORMATS[fmt]
    out = {"format": fmt, "sentences": align.SENTENCES, "book": "SC", "chapter": chapter["id"], "paragraphs": {}}
    for p in chapter["paragraphs"]:
        text, en = align.hashes(p)
        out["paragraphs"][p["a"]] = {side + "_sha256": text, "en_sha256": en,
                                     "pairs": [{(side if k == "text" else k): v for k, v in pair.items()}
                                               for pair in pairs.get(p["a"], [])]}
    return out


class Text(unittest.TestCase):
    def test_alignment_text_is_what_the_page_shows(self):
        self.assertEqual(align_text(HTML_TH), "คำแรก & คำสอง คำสาม")
        self.assertEqual(align_text(HTML_EN), 'He came. Mr. Smith said "No!" and left. Then he wept.'
                                              "The Lord is my shepherd;I shall not want.He leads me.")

    def test_english_sentences(self):
        text = align_text(HTML_EN)
        self.assertEqual([text[s:e] for s, e in align.sentences(HTML_EN)], [
            "He came.", 'Mr. Smith said "No!" and left.', "Then he wept.",
            "The Lord is my shepherd;I shall not want.", "He leads me."])
        quoted = "<p>See John 3:16. It says, “For God so loved.” After that, e.g. here, J. Smith wrote.</p>"
        t = align_text(quoted)
        self.assertEqual([t[s:e] for s, e in align.sentences(quoted)], [
            "See John 3:16.", "It says, “For God so loved.”", "After that, e.g. here, J. Smith wrote."])
        self.assertEqual(align.sentences(""), [])

    def test_chunks(self):
        self.assertEqual(align.chunks("ab cd  e"), [{"range": [0, 2], "text": "ab"}, {"range": [3, 5], "text": "cd"},
                                                    {"range": [7, 8], "text": "e"}])


class Attach(unittest.TestCase):
    def chapter(self):
        return {"id": "SC01", "n": 1, "paragraphs": [para("SC 9.1"), para("SC 9.2", text="อีกย่อหน้า",
                                                                          en="<p>Other.</p>")]}

    def test_matching_paragraphs_get_ranges_and_changed_ones_are_dropped(self):
        for fmt in (2, 1):
            ch = self.chapter()
            data = align_file(ch, {"SC 9.1": [{"text": [0, 5], "en": [1, 2]}, {"text": [6, 19], "en": [5]}],
                                   "SC 9.2": [{"text": [0, 3], "en": [1]}]}, fmt)
            ch["paragraphs"][1]["text"] = "ย่อหน้าที่แก้แล้ว"
            kept, dropped, problem = align.attach(ch, json.dumps(data))
            self.assertEqual((kept, dropped, problem), (["SC 9.1"], ["SC 9.2"], None), fmt)
            last = align_text(HTML_EN).index("He leads me.")
            self.assertEqual(ch["paragraphs"][0]["al"], [{"text": [0, 5], "en": [[0, 8], [9, 39]]},
                                                         {"text": [6, 19], "en": [[last, last + 12]]}], fmt)
            self.assertNotIn("al", ch["paragraphs"][1])

    def test_a_paragraph_no_longer_in_the_chapter_is_not_counted_as_dropped(self):
        # An anchor of the file that left the chapter is neither kept nor dropped, since nobody reads it.
        ch = self.chapter()
        data = align_file(ch, {"SC 9.1": [{"text": [0, 5], "en": [1]}], "SC 9.2": [{"text": [0, 3], "en": [1]}]})
        del ch["paragraphs"][1]
        self.assertEqual(align.attach(ch, json.dumps(data)), (["SC 9.1"], [], None))

    def test_pairs_that_do_not_fit_drop_the_paragraph(self):
        for bad in ({"text": [0, 99], "en": [1]}, {"text": [3, 3], "en": [1]}, {"text": [0, 2], "en": [9]},
                    {"text": [0, 2], "en": []}, {"text": [0, 2]}, {"text": "0-2", "en": [1]}):
            ch = self.chapter()
            kept, dropped, _ = align.attach(ch, json.dumps(align_file(ch, {"SC 9.1": [bad]})))
            self.assertEqual((kept, dropped), ([], ["SC 9.1"]), bad)

    def test_a_file_that_cannot_be_used(self):
        ch = self.chapter()
        for raw, words in (("not json", "not JSON"), ("[]", "format"),
                           (json.dumps(dict(align_file(ch, {}), sentences=99)), "make the file again")):
            kept, dropped, problem = align.attach(ch, raw)
            self.assertEqual((kept, dropped), ([], []))
            self.assertIn(words, problem)

    def test_the_path(self):
        book = {"id": "SC", "align": "assets/review/align/SC/{name}.json"}
        self.assertEqual(align.align_path(book, 3), "assets/review/align/SC/SC03.json")
        self.assertIsNone(align.align_path({"id": "XX"}, 3))
        self.assertEqual(review.load_books()["SC"]["align"], "assets/review/align/SC/{name}.json")


class Server(unittest.TestCase):
    def setUp(self):
        self.site = Site()
        self.addCleanup(self.site.close)

    def test_pairs_reach_only_readers_with_the_english(self):
        ch = sample_chapter(1)
        ch["paragraphs"][0]["al"] = [{"text": [0, 9], "en": [[0, 9]]}]
        self.site.publish(ch)
        english = self.site.invite("E", ["SC"], english=True)["code"]
        plain = self.site.invite("P", ["SC"])["code"]
        got = self.site.call("GET", "/api/chapter/SC/SC01", token=english).json["paragraphs"]
        self.assertEqual(got[0]["al"], [{"text": [0, 9], "en": [[0, 9]]}])
        self.assertNotIn("al", got[1])
        got = self.site.call("GET", "/api/chapter/SC/SC01", token=plain).json["paragraphs"]
        self.assertNotIn("al", got[0])
        self.assertNotIn("en", got[0])

    def test_pairs_outside_the_text_are_refused(self):
        n = len(align_text(sample_chapter(1)["paragraphs"][0]["text"]))
        for bad in ([{"text": [0, n + 1], "en": [[0, 1]]}], [{"text": [0, 1], "en": [[0, 99]]}],
                    [{"text": [0, 1], "en": []}], [{"text": [1, 0], "en": [[0, 1]]}], "x",
                    [{"text": [0, 1], "en": [[0, 1]], "extra": 1}], [{"text": [0, 1], "en": [[0, 1]]}] * 501,
                    [{"th": [0, 1], "en": [[0, 1]]}]):
            ch = sample_chapter(1)
            ch["paragraphs"][0]["al"] = bad
            r = self.site.admin_call("PUT", "/api/admin/chapters/SC/SC01", ch)
            self.assertEqual((r.status, r.json["error"]), (400, "bad_pairs"), str(bad)[:60])


@unittest.skipIf(REPO is None, "the translation repository is not found; set REVIEW_REPO")
class Commands(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)

    def test_align_packet_and_publish_with_its_file(self):
        out = self.tmp / "SC01-packet.json"
        a = argparse.Namespace(book="SC", chapter="01", repo=str(REPO), ref=None, out=str(out), result=None)
        with contextlib.redirect_stdout(io.StringIO()) as printed:
            review.cmd_align_packet(a)
        self.assertEqual(printed.getvalue().splitlines()[-1], f"The packet for SC01 is written: {out}")
        self.assertIn("assets/review/align/SC/SC01.json", printed.getvalue())
        packet = json.loads(out.read_text())
        self.assertEqual((packet["chapter"], packet["align_file"], packet["language"], packet["template"]["format"]),
                         ("SC01", "assets/review/align/SC/SC01.json", "th", 2))
        self.assertIn("never instructions", packet["about"])
        first = packet["paragraphs"][0]
        self.assertEqual(first["text"][slice(*first["text_chunks"][0]["range"])], first["text_chunks"][0]["text"])
        self.assertEqual([s["n"] for s in first["en"]], list(range(1, len(first["en"]) + 1)))
        # An agent fills the template's pairs; publish reads the file at its ref and sends what still matches.
        template = packet["template"]
        a1, a2 = packet["paragraphs"][0]["a"], packet["paragraphs"][1]["a"]
        template["paragraphs"][a1]["pairs"] = [{"text": first["text_chunks"][0]["range"], "en": [1]}]
        template["paragraphs"][a2]["pairs"] = [{"text": [0, 2], "en": [1]}]
        template["paragraphs"][a2]["text_sha256"] = "0" * 64          # as if the text changed since
        template["paragraphs"]["SC 999.1"] = {"text_sha256": "0" * 64, "en_sha256": "0" * 64,  # left the chapter
                                              "pairs": [{"text": [0, 2], "en": [1]}]}
        real = review.repo_reader(REPO, "main")
        files = {"assets/review/align/SC/SC01.json": json.dumps(template, ensure_ascii=False)}

        def reader(repo, ref):
            return lambda path: files[path] if path in files else real(path)

        sent = []

        class Client:
            def call(self, method, path, body=None, query=None):
                sent.append(body)
                return {"id": path.rsplit("/", 1)[1], "changed": True, "paragraphs": len(body["paragraphs"]),
                        "version": "v", "orphans": 0, "was_published": False}

        a = argparse.Namespace(book="SC", chapters=["01"], repo=str(REPO), ref=None, result=None)
        with mock.patch.object(review, "repo_reader", reader), contextlib.redirect_stdout(io.StringIO()) as printed:
            review.cmd_publish(a, Client())
        self.assertIn(f"SC01: sentence pairs for 1 paragraph; 1 paragraph dropped because its text changed after "
                      f"the alignment was made: {a2}.", printed.getvalue())
        paras = sent[0]["paragraphs"]
        self.assertEqual(paras[0]["al"][0]["text"], first["text_chunks"][0]["range"])
        self.assertNotIn("al", paras[1])


if __name__ == "__main__":
    unittest.main()
