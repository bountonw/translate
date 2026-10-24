"""Tests for chapter versions: every published version is kept, the version a reader last opened is recorded,
/api/me says which paragraphs changed since, a reader's comment says whether its paragraph changed, the earlier
wording can be read, and the export gives the paragraph as the reader saw it."""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from helpers import Site, sample_chapter

from server import app as app_module
from server import db


def changed_chapter(tag="v2", drop_last=False, add=False, commit="def5678"):
    """Chapter 1 with paragraph 2 reworded, and optionally paragraph 3 removed or paragraph 4 added."""
    ch = sample_chapter(1, count=4 if add else 3)
    ch["paragraphs"][1]["text"] = f"Paragraph 2 reworded ({tag})"
    if drop_last:
        ch["paragraphs"] = ch["paragraphs"][:2]
    ch["commit"] = commit
    return ch


class Base(unittest.TestCase):
    def setUp(self):
        self.site = Site(limits={"comments_per_minute": 1000})
        self.addCleanup(self.site.close)
        self.v1 = self.site.publish(sample_chapter(1))["version"]
        r = self.site.invite("Reader", ["SC"], english=True)
        self.code = r["code"]

    def me_chapter(self):
        return self.site.call("GET", "/api/me", token=self.code).json["chapters"][0]

    def opened(self, version):
        r = self.site.call("PUT", "/api/opened", {"book": "SC", "ch": "SC01", "version": version}, token=self.code)
        self.assertEqual(r.status, 200, r.body)
        return r.json


class KeptVersions(Base):
    def test_every_version_is_kept_and_publish_says_what_changed(self):
        res = self.site.publish(changed_chapter(drop_last=True))
        self.assertEqual((res["previous"], res["paragraphs_changed"], res["paragraphs_removed"]), (self.v1, 1, 1))
        con = sqlite3.connect(self.site.data / db.DB_NAME)
        self.addCleanup(con.close)
        rows = con.execute("SELECT version, seq FROM chapter_version WHERE ch = 'SC01' ORDER BY seq").fetchall()
        self.assertEqual([r[0] for r in rows], [self.v1, res["version"]])
        self.assertEqual([r[1] for r in rows], [1, 2])
        chapters = self.site.admin_call("GET", "/api/admin/chapters").json["chapters"]
        self.assertEqual(chapters[0]["versions"], 2)
        # The same text again keeps its version and adds none; an earlier text published again goes last.
        again = self.site.publish(changed_chapter(drop_last=True))
        self.assertFalse(again["changed"])
        back = self.site.publish(sample_chapter(1))
        self.assertEqual(back["version"], self.v1)
        rows = con.execute("SELECT version, seq FROM chapter_version WHERE ch = 'SC01' ORDER BY seq").fetchall()
        self.assertEqual([r[0] for r in rows], [res["version"], self.v1])

    def test_a_span_alone_changes_no_paragraph(self):
        ch = sample_chapter(1)
        ch["paragraphs"][0]["text"] = ch["paragraphs"][0]["text"].replace(
            "Paragraph", '<span data-kind="bible" data-value="John 3:16">Paragraph</span>')
        ch["commit"] = "fff0000"
        res = self.site.publish(ch)
        self.assertTrue(res["changed"])
        self.assertEqual(res["paragraphs_changed"], 0)


class Opened(Base):
    def test_never_opened_means_no_change_to_show(self):
        c = self.me_chapter()
        self.assertEqual((c["opened"], c["changed"]), (None, None))
        self.site.publish(changed_chapter())
        self.assertEqual(self.me_chapter()["changed"], None)

    def test_changed_paragraphs_since_the_version_opened(self):
        self.assertTrue(self.opened(self.v1)["recorded"])
        v2 = self.site.publish(changed_chapter(add=True))["version"]
        c = self.me_chapter()
        self.assertEqual((c["version"], c["opened"]), (v2, self.v1))
        ch = c["changed"]
        self.assertEqual(ch["since"], self.v1)
        self.assertEqual([(p["a"], p["new"]) for p in ch["paragraphs"]], [("SC 101.2", False), ("SC 101.4", True)])
        self.assertEqual(ch["removed"], [])
        self.assertRegex(ch["at"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        # A third version that removes a paragraph: the list runs from the version opened to now.
        self.site.publish(changed_chapter(add=True, drop_last=False, commit="aaa0001") | {
            "paragraphs": changed_chapter(add=True)["paragraphs"][:2] + changed_chapter(add=True)["paragraphs"][3:]})
        ch = self.me_chapter()["changed"]
        self.assertEqual([p["a"] for p in ch["paragraphs"]], ["SC 101.2", "SC 101.4"])
        self.assertEqual([p["a"] for p in ch["removed"]], ["SC 101.3"])
        # Opening the current version clears the list.
        self.opened(self.me_chapter()["version"])
        self.assertIsNone(self.me_chapter()["changed"])

    def test_a_paragraph_changed_and_changed_back_is_not_listed(self):
        self.opened(self.v1)
        self.site.publish(changed_chapter())
        back = sample_chapter(1)
        back["commit"] = "bbb0002"
        self.site.publish(back)
        self.assertIsNone(self.me_chapter()["changed"])

    def test_the_record_only_moves_forward(self):
        v2 = self.site.publish(changed_chapter())["version"]
        self.assertTrue(self.opened(v2)["recorded"])
        late = self.opened(self.v1)          # sent late from another device
        self.assertEqual((late["recorded"], late["opened"]), (False, v2))
        unknown = self.opened("abc-not-kept")
        self.assertEqual((unknown["recorded"], unknown["opened"]), (False, v2))
        self.assertEqual(self.me_chapter()["opened"], v2)
        # An earlier text published again is a newer version in the history.
        back = self.site.publish(sample_chapter(1))
        self.assertEqual(back["version"], self.v1)
        self.assertTrue(self.opened(self.v1)["recorded"])

    def test_opened_needs_an_open_chapter_and_counts_as_a_write(self):
        r = self.site.call("PUT", "/api/opened", {"book": "SC", "ch": "SC09", "version": "x"}, token=self.code)
        self.assertEqual((r.status, r.json["error"]), (404, "no_chapter"))
        r = self.site.call("PUT", "/api/opened", {"book": "SC", "ch": "SC01", "version": 5}, token=self.code)
        self.assertEqual((r.status, r.json["error"]), (400, "bad_field"))
        site = Site(writes_per_minute=2)
        self.addCleanup(site.close)
        v = site.publish(sample_chapter(1))["version"]
        code = site.invite("R", ["SC"])["code"]
        body = {"book": "SC", "ch": "SC01", "version": v}
        statuses = [site.call("PUT", "/api/opened", body, token=code).status for _ in range(3)]
        self.assertEqual(statuses, [200, 200, 429])


class Earlier(Base):
    def test_the_wording_in_the_version_last_opened(self):
        self.opened(self.v1)
        self.site.publish(changed_chapter(add=True))
        r = self.site.call("GET", "/api/earlier/SC/SC01?a=SC%20101.2", token=self.code)
        self.assertEqual(r.status, 200, r.body)
        self.assertEqual((r.json["version"], r.json["same"]), (self.v1, False))
        self.assertEqual((r.json["text"], r.json["language"]), ("Paragraph 2 of chapter 1 (v1) <em>word</em>", "th"))
        self.assertEqual(r.json["fn"], [])
        unchanged = self.site.call("GET", "/api/earlier/SC/SC01?a=SC%20101.1", token=self.code).json
        self.assertTrue(unchanged["same"])
        self.assertEqual(unchanged["fn"], ["Note 1"])
        new = self.site.call("GET", "/api/earlier/SC/SC01?a=SC%20101.4", token=self.code)
        self.assertEqual((new.status, new.json["error"]), (404, "no_earlier"))

    def test_a_version_named_and_the_refusals(self):
        v2 = self.site.publish(changed_chapter())["version"]
        r = self.site.call("GET", f"/api/earlier/SC/SC01?a=SC%20101.2&version={self.v1}", token=self.code)
        self.assertEqual((r.status, r.json["version"]), (200, self.v1))
        for query in ("a=SC%20101.2", f"a=SC%20101.2&version={v2}", "a=SC%20101.2&version=nothing"):
            r = self.site.call("GET", f"/api/earlier/SC/SC01?{query}", token=self.code)
            self.assertEqual((r.status, r.json["error"]), (404, "no_earlier"), query)
        r = self.site.call("GET", "/api/earlier/SC/SC01?a=bad", token=self.code)
        self.assertEqual((r.status, r.json["error"]), (400, "bad_field"))
        other = self.site.invite("Other", ["SC02"])["code"]
        r = self.site.call("GET", f"/api/earlier/SC/SC01?a=SC%20101.2&version={self.v1}", token=other)
        self.assertEqual((r.status, r.json["error"]), (404, "no_chapter"))


class CommentsAndExport(Base):
    def test_a_comment_says_whether_its_paragraph_changed(self):
        on2 = self.site.comment(self.code, "SC 101.2", text="On paragraph two").json
        on1 = self.site.comment(self.code, "SC 101.1", text="On paragraph one").json
        on3 = self.site.comment(self.code, "SC 101.3", text="On paragraph three").json
        self.assertEqual((on2["version"], on2["para_changed"], on2["para_changed_at"]), (self.v1, False, None))
        self.site.publish(changed_chapter(drop_last=True))
        mine = {c["id"]: c for c in self.site.call("GET", "/api/comments", token=self.code).json["comments"]}
        self.assertTrue(mine[on2["id"]]["para_changed"])
        self.assertRegex(mine[on2["id"]]["para_changed_at"], r"Z$")
        self.assertFalse(mine[on1["id"]]["para_changed"])
        self.assertTrue(mine[on3["id"]]["para_changed"])      # its paragraph left the chapter
        # A change by the reader moves the comment to the current version.
        r = self.site.call("PATCH", f"/api/comments/{on2['id']}", {"text": "Read again"}, token=self.code)
        self.assertEqual((r.json["para_changed"], r.json["version"]), (False, self.me_chapter()["version"]))

    def test_a_version_the_site_does_not_keep_is_unknown(self):
        c = self.site.comment(self.code, "SC 101.2").json
        con = sqlite3.connect(self.site.data / db.DB_NAME)
        con.execute("UPDATE comment SET version = 'older-than-the-site' WHERE id = ?", (c["id"],))
        con.commit()
        con.close()
        mine = self.site.call("GET", "/api/comments", token=self.code).json["comments"]
        self.assertEqual((mine[0]["para_changed"], mine[0]["para_changed_at"]), (None, None))
        exported = self.site.admin_call("GET", "/api/admin/export").json["comments"][0]
        self.assertEqual((exported["changed"], exported["paragraph_seen"]), (None, None))

    def test_the_export_gives_the_paragraph_as_the_reader_saw_it(self):
        c = self.site.comment(self.code, "SC 101.2", kind="wording", quote="Paragraph 2", text="Better").json
        self.site.publish(changed_chapter())
        ex = self.site.admin_call("GET", "/api/admin/export").json["comments"]
        e = next(x for x in ex if x["id"] == c["id"])
        self.assertEqual(e["paragraph_seen"], "Paragraph 2 of chapter 1 (v1) word")
        self.assertEqual(e["paragraph"], "Paragraph 2 reworded (v2)")
        self.assertEqual((e["changed"], e["footnotes_seen"], e["en"]), (True, [], "English 2"))
        self.assertNotEqual(e["version_seen"], e["version_now"])


def database_at(path, version):
    """A database made by the code of that version: the schema and the migrations up to it."""
    with mock.patch.object(db, "MIGRATIONS", [m for m in db.MIGRATIONS if m[0] <= version]):
        db.init_db(path, features=[])
    con = sqlite3.connect(path)
    assert con.execute("PRAGMA user_version").fetchone()[0] == version
    return con


V4_PARAS = [{"a": "SC 101.1", "th": "One <em>word</em>", "fn": ["Note"], "en": "<p>One.</p>",
             "al": [{"th": [0, 3], "en": [[0, 4]]}]},
            {"a": "SC 101.2", "th": "Two", "fn": [], "en": "<p>Two.</p>"}]


class Migration5(unittest.TestCase):
    def test_a_version_4_database_keeps_its_chapters_as_their_first_versions(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / db.DB_NAME
        con = database_at(path, 4)
        con.execute("INSERT INTO book (id, title_en, language, title_th) VALUES ('SC', 'Book', 'th', '')")
        con.execute("INSERT INTO chapter (book, id, n, title_th, title_en, version, content_hash, count, paragraphs,"
                    " updated, source_th, source_en, source_commit) VALUES ('SC', 'SC01', 1, 'Title', 'English',"
                    " 'v4', 'old', 2, ?, '2026-10-01T00:00:00Z', 'th/SC/02_edit/SC01_th.typ', 'en.md', 'abc')",
                    (json.dumps(V4_PARAS, ensure_ascii=False),))
        con.execute("INSERT INTO reader (name, code_hash, created) VALUES ('R', 'x', 'now')")
        con.execute("INSERT INTO comment (client_id, reader, book, ch, a, kind, text, version, created, updated)"
                    " VALUES ('c1', 1, 'SC', 'SC01', 'SC 101.1', 'flag', 'kept', 'v4', 'now', 'now')")
        con.commit()
        con.close()
        db.init_db(path)
        con = sqlite3.connect(path)
        self.addCleanup(con.close)
        self.assertEqual(con.execute("PRAGMA user_version").fetchone()[0], db.MIGRATIONS[-1][0])
        self.assertEqual(con.execute("SELECT version, seq FROM chapter_version").fetchall(), [("v4", 1)])
        self.assertEqual(con.execute("SELECT text, reply, reply_at, round FROM comment").fetchall(),
                         [("kept", "", None, None)])


class Migration6(unittest.TestCase):
    """Version 6 gives the translation's text neutral names, and adds rounds, devices and deleted comments."""

    def test_a_version_5_database_keeps_every_row_and_its_versions(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        data = Path(tmp.name)
        token, _ = db.setup(data / "made-for-the-token")
        path = data / db.DB_NAME
        con = database_at(path, 5)
        stored = json.dumps(V4_PARAS, ensure_ascii=False)
        con.execute("INSERT INTO book (id, title_en, language, title_th) VALUES ('SC', 'Book', 'th', 'Book title')")
        con.execute("INSERT INTO chapter (book, id, n, title_th, title_en, version, content_hash, count, paragraphs,"
                    " updated, source_th, source_en, source_commit) VALUES ('SC', 'SC01', 1, 'Title', 'English',"
                    " 'abc-v5', 'old', 2, ?, '2026-10-01T00:00:00Z', 'th/SC/02_edit/SC01_th.typ', 'en.md', 'abc')",
                    (stored,))
        con.execute("INSERT INTO chapter_version (book, ch, version, title_th, title_en, paragraphs, source_commit,"
                    " published, seq) VALUES ('SC', 'SC01', 'abc-v5', 'Title', 'English', ?, 'abc', 'now', 1)",
                    (stored,))
        con.execute("INSERT INTO reader (name, code_hash, created) VALUES ('R', 'x', 'now')")
        con.execute("INSERT INTO comment (client_id, reader, book, ch, a, kind, text, version, created, updated)"
                    " VALUES ('c1', 1, 'SC', 'SC01', 'SC 101.1', 'flag', 'kept', 'abc-v5', 'now', 'now')")
        con.commit()
        counts = {t: con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for t in
                  ("book", "chapter", "chapter_version", "reader", "comment", "grant", "place", "finished")}
        con.close()
        db.init_db(path)
        con = sqlite3.connect(path)
        self.addCleanup(con.close)
        self.assertEqual(con.execute("PRAGMA user_version").fetchone()[0], db.MIGRATIONS[-1][0])
        for t, n in counts.items():
            self.assertEqual(con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0], n, t)
        self.assertEqual(con.execute("SELECT title FROM book").fetchone()[0], "Book title")
        title, source, paras, digest = con.execute("SELECT title, source, paragraphs, content_hash FROM chapter").fetchone()
        self.assertEqual((title, source), ("Title", "th/SC/02_edit/SC01_th.typ"))
        paras = json.loads(paras)
        self.assertEqual([list(p) for p in paras], [["a", "text", "fn", "en", "al"], ["a", "text", "fn", "en"]])
        self.assertEqual(paras[0]["al"], [{"text": [0, 3], "en": [[0, 4]]}])
        self.assertEqual(digest, db.content_hash("Title", "English", paras))
        kept = json.loads(con.execute("SELECT paragraphs FROM chapter_version").fetchone()[0])
        self.assertEqual(kept, paras)
        self.assertEqual(con.execute("SELECT round FROM comment").fetchall(), [(None,)])
        for table in ("review_round", "reader_device", "comment_gone"):
            self.assertEqual(con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0], 0)
        self.assertEqual(con.execute("PRAGMA integrity_check").fetchone()[0], "ok")
        self.assertEqual(con.execute("PRAGMA foreign_key_check").fetchall(), [])
        # Publishing the same text again keeps the version, so readers download nothing new.
        (data / db.TOKEN_HASH).write_text((data / "made-for-the-token" / db.TOKEN_HASH).read_text())
        app = app_module.App(data)
        site = Site.__new__(Site)
        site.app, site.admin = app, token.read_text().strip()
        again = site.publish({"n": 1, "title": "Title", "title_en": "English", "paragraphs": paras, "commit": "def5678",
                              "language": "th"})
        self.assertEqual((again["changed"], again["version"]), (False, "abc-v5"))
        db.init_db(path)    # a second start changes nothing
        self.assertEqual(con.execute("PRAGMA user_version").fetchone()[0], db.MIGRATIONS[-1][0])


class Migration7(unittest.TestCase):
    """Version 7 records the client_id of each comment deleted; a database newer than the code is refused."""

    def test_a_version_6_database_keeps_its_deleted_comments(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / db.DB_NAME
        con = database_at(path, 6)
        con.execute("INSERT INTO comment_gone (id, reader, book, ch, at) VALUES (4, 1, 'SC', 'SC01', 'now')")
        con.commit()
        con.close()
        db.init_db(path)
        con = sqlite3.connect(path)
        self.addCleanup(con.close)
        self.assertEqual(con.execute("PRAGMA user_version").fetchone()[0], db.MIGRATIONS[-1][0])
        self.assertEqual(con.execute("SELECT id, reader, ch, client_id FROM comment_gone").fetchall(),
                         [(4, 1, "SC01", None)])

    def test_code_older_than_the_database_refuses_it(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / db.DB_NAME
        db.init_db(path)
        con = sqlite3.connect(path)
        con.execute(f"PRAGMA user_version = {db.MIGRATIONS[-1][0] + 1}")
        con.close()
        with self.assertRaises(db.TooNew) as e:
            db.init_db(path)
        self.assertIn("Rolling back", str(e.exception))
        # It is a ValueError, which serve --dev turns into one plain message.
        self.assertIsInstance(e.exception, ValueError)


class QuotePlace(Base):
    """A comment records where its quoted words start in the paragraph's reading text (`at`), which the reader
    routes and the export give back; the site keeps no place for a comment without quoted words."""

    def test_a_comment_keeps_where_its_quoted_words_start(self):
        # In "Paragraph 2 of chapter 1 (v1) <em>word</em>" the reading text drops the tag, so "word" starts at 30.
        c = self.site.comment(self.code, "SC 101.2", quote="word", text="Twice?", at=30)
        self.assertEqual(c.status, 201, c.body)
        self.assertEqual(c.json["at"], 30)
        listed = self.site.call("GET", "/api/comments?book=SC&ch=SC01", token=self.code).json["comments"]
        self.assertEqual([x["at"] for x in listed], [30])
        ex = self.site.admin_call("GET", "/api/admin/export").json["comments"]
        self.assertEqual(ex[0]["at"], 30)
        self.assertEqual(ex[0]["quote"], "word")
        # Without quoted words there is no place, whatever the page sent; without `at` the place is not known.
        bare = self.site.comment(self.code, "SC 101.1", text="No quote", at=4).json
        self.assertIsNone(bare["at"])
        older = self.site.comment(self.code, "SC 101.3", quote="Paragraph", text="From an older page").json
        self.assertIsNone(older["at"])

    def test_a_place_that_is_not_a_whole_number_is_refused(self):
        for bad in (-1, 1.5, "3", True, 100_001, [2]):
            r = self.site.comment(self.code, "SC 101.2", quote="word", text="x", at=bad)
            self.assertEqual((r.status, r.json["error"]), (400, "bad_at"), bad)
        self.assertEqual(self.site.comment(self.code, "SC 101.2", quote="word", text="x", at=None).status, 201)
        self.assertEqual(self.site.comment(self.code, "SC 101.2", quote="word", text="x", at=100_000).status, 201)

    def test_new_quoted_words_without_a_place_have_none(self):
        c = self.site.comment(self.code, "SC 101.2", quote="word", text="x", at=30).json
        path = f"/api/comments/{c['id']}"
        # A change of the text alone keeps the place.
        r = self.site.call("PATCH", path, {"text": "y"}, token=self.code)
        self.assertEqual((r.status, r.json["at"]), (200, 30))
        # New quoted words with their place take it; new words without one have none.
        r = self.site.call("PATCH", path, {"quote": "Paragraph 2", "at": 0}, token=self.code)
        self.assertEqual((r.json["quote"], r.json["at"]), ("Paragraph 2", 0))
        r = self.site.call("PATCH", path, {"quote": "chapter"}, token=self.code)
        self.assertEqual((r.json["quote"], r.json["at"]), ("chapter", None))
        # A place alone is a change, and clears the processed mark as any change does.
        self.site.admin_call("POST", "/api/admin/processed", {"ids": [c["id"]]})
        r = self.site.call("PATCH", path, {"at": 15}, token=self.code)
        self.assertEqual((r.json["at"], r.json["processed"]), (15, False))
        r = self.site.call("PATCH", path, {"at": "15"}, token=self.code)
        self.assertEqual((r.status, r.json["error"]), (400, "bad_at"))

    def test_a_place_where_the_quoted_words_do_not_stand_is_not_kept(self):
        """The site keeps `at` only where the quoted words stand in the reading text of
        the version it records with the comment, and never at white space."""
        # "Paragraph 2 of chapter 1 (v1) word": "word" starts at 30; 29 is the space before it, 31 inside it.
        for at, kept in ((30, 30), (29, None), (31, None), (0, None)):
            c = self.site.comment(self.code, "SC 101.2", quote="word", text="Where?", at=at)
            self.assertEqual((c.status, c.json["at"]), (201, kept), at)
        # White space in the quote counts as one space, as on the page.
        c = self.site.comment(self.code, "SC 101.2", quote="of  chapter", text="Spaces", at=12)
        self.assertEqual(c.json["at"], 12)

    def test_a_place_counted_in_an_earlier_version_is_dropped(self):
        """A new version puts five letters before the words; a change, a draft or a new
        comment that still sends the old place gets none, and the new place is kept."""
        c = self.site.comment(self.code, "SC 101.2", quote="word", text="Before", at=30).json
        ch = sample_chapter(1)
        ch["paragraphs"][1]["text"] = "Intro " + ch["paragraphs"][1]["text"]
        ch["commit"] = "abc0002"
        v2 = self.site.publish(ch)["version"]
        path = f"/api/comments/{c['id']}"
        # A change of the text alone moves the comment to version 2, where "word" starts at 36, not 30.
        r = self.site.call("PATCH", path, {"text": "After"}, token=self.code)
        self.assertEqual((r.status, r.json["version"], r.json["at"]), (200, v2, None))
        r = self.site.call("PATCH", path, {"at": 36}, token=self.code)
        self.assertEqual(r.json["at"], 36)
        r = self.site.call("PATCH", path, {"text": "Again", "at": 30}, token=self.code)
        self.assertEqual(r.json["at"], None)
        old = self.site.comment(self.code, "SC 101.2", quote="word", text="Old place", at=30).json
        new = self.site.comment(self.code, "SC 101.2", quote="word", text="New place", at=36).json
        self.assertEqual((old["at"], new["at"]), (None, 36))
        ex = {x["text"]: x["at"] for x in self.site.admin_call("GET", "/api/admin/export").json["comments"]}
        self.assertEqual((ex["Old place"], ex["New place"]), (None, 36))

    def test_the_export_gives_at_as_a_place_in_the_paragraph_it_shows(self):
        """paragraph_seen has a line break for each <br> and its ends trimmed, which the
        reading text has not; the export's `at` is a place in paragraph_seen, from which the quote starts, while
        the reader routes keep the place in the reading text."""
        ch = sample_chapter(1)
        ch["paragraphs"][1]["text"] = "  first twice<br>twice <em>again</em> &amp; twice"
        ch["commit"] = "abc0003"
        self.site.publish(ch)
        # The reading text is "  first twicetwice again & twice": the second "twice" starts at 13.
        c = self.site.comment(self.code, "SC 101.2", quote="twice", text="The second one", at=13).json
        self.assertEqual(c["at"], 13)
        listed = self.site.call("GET", "/api/comments?book=SC&ch=SC01", token=self.code).json["comments"]
        self.assertEqual([x["at"] for x in listed], [13])
        third = self.site.comment(self.code, "SC 101.2", quote="twice", text="The third one", at=27).json
        self.assertEqual(third["at"], 27)

        def exported():
            return {x["text"]: x for x in self.site.admin_call("GET", "/api/admin/export").json["comments"]}

        ex = exported()
        for text in ("The second one", "The third one"):
            x = ex[text]
            self.assertEqual(x["paragraph_seen"], "first twice\ntwice again & twice")
            self.assertTrue(x["paragraph_seen"][x["at"]:].startswith("twice"), text)
        self.assertEqual((ex["The second one"]["at"], ex["The third one"]["at"]), (12, 26))
        # After a new version, the place still counts in the paragraph as the reader saw it.
        ch["paragraphs"][1]["text"] = "Changed now"
        ch["commit"] = "abc0004"
        self.site.publish(ch)
        x = exported()["The second one"]
        self.assertNotEqual(x["version_seen"], x["version_now"])
        self.assertEqual((x["paragraph"], x["paragraph_seen"], x["at"]), ("Changed now", "first twice\ntwice again & twice", 12))


class Migration9(unittest.TestCase):
    """Version 9 adds where a comment's quoted words start; the comments of a version 8 database have none."""

    def test_a_version_8_database_keeps_its_comments_without_a_place(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / db.DB_NAME
        con = database_at(path, 8)
        con.execute("INSERT INTO book (id) VALUES ('SC')")
        con.execute("INSERT INTO chapter (book, id, n, title, title_en, version, content_hash, count, paragraphs,"
                    " updated) VALUES ('SC', 'SC01', 1, 'T', 'T', 'v1', 'h', 0, '[]', 'now')")
        con.execute("INSERT INTO reader (name, code_hash, created) VALUES ('R', 'x', 'now')")
        con.execute("INSERT INTO comment (client_id, reader, book, ch, a, kind, quote, text, created, updated)"
                    " VALUES ('c1', 1, 'SC', 'SC01', 'SC 101.1', 'flag', 'word', 'A note', 'now', 'now')")
        con.commit()
        con.close()
        db.init_db(path)
        con = sqlite3.connect(path)
        self.addCleanup(con.close)
        self.assertEqual(con.execute("PRAGMA user_version").fetchone()[0], db.MIGRATIONS[-1][0])
        self.assertEqual(con.execute("SELECT client_id, quote, quote_at FROM comment").fetchall(), [("c1", "word", None)])
        self.assertEqual(con.execute("PRAGMA integrity_check").fetchone()[0], "ok")


class Caches(unittest.TestCase):
    def test_comparisons_are_bounded_and_forgotten_when_the_chapter_changes(self):
        site = Site()
        self.addCleanup(site.close)
        v1 = site.publish(sample_chapter(1))["version"]
        v2 = site.publish(changed_chapter())["version"]
        conn = db.connect(site.data / db.DB_NAME)
        self.addCleanup(conn.close)
        with mock.patch.object(app_module, "CHANGES_MOST", 1):
            site.app.changes(conn, "SC", "SC01", v1, v2)
            site.app.changes(conn, "SC", "SC01", v2, v2)
            self.assertEqual(len(site.app.compared), 1)
        site.publish(changed_chapter(tag="v3", commit="ccc0003"))
        self.assertEqual([k for k in site.app.compared if k[:2] == ("SC", "SC01")], [])


if __name__ == "__main__":
    unittest.main()
