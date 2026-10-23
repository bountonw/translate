"""Tests for what the page relies on: every reason a reader's write is refused has its own code and status
(server.app.WRITE_ERRORS), /api/me carries the limits and the features, and the server's memory stays bounded."""
import json
import sqlite3
import unittest
from unittest import mock

from helpers import Site, sample_chapter

from server import app as app_module
from server import db


class RefusedWrites(unittest.TestCase):
    def setUp(self):
        self.site = Site(writes_per_minute=10000)
        self.addCleanup(self.site.close)
        self.site.publish(sample_chapter(1))
        self.site.publish(sample_chapter(2))
        r = self.site.invite("Reader", ["SC01-02"])
        self.code, self.rid = r["code"], r["id"]

    def post(self, **change):
        body = {"client_id": json.dumps(change)[:60].replace(" ", "").replace('"', "")[:60] or "c",
                "book": "SC", "ch": "SC01", "a": "SC 101.1", "kind": "flag", "quote": "", "text": "ok"}
        body.update(change)
        return self.site.call("POST", "/api/comments", body, token=self.code)

    def expect(self, r, code):
        self.assertEqual((r.status, r.json["error"]), (app_module.WRITE_ERRORS[code][0], code), r.body)
        self.assertTrue(r.json["message"])

    def test_each_reason_has_its_code(self):
        self.expect(self.post(client_id="a1", quote="", kind="wording"), "quote_required")
        self.expect(self.post(client_id="a2", quote="q" * 4001), "quote_too_long")
        self.expect(self.post(client_id="a3", text="   \u200b "), "text_required")
        self.expect(self.post(client_id="a4", text="t" * 8001), "text_too_long")
        self.expect(self.post(client_id="a5", a="SC 101.9"), "no_paragraph")
        self.expect(self.post(client_id="a6", ch="SC03"), "no_chapter")
        r = self.site.call("POST", "/api/comments", raw=json.dumps({"client_id": "a7", "book": "SC", "ch": "SC01",
                           "a": "SC 101.1", "kind": "flag", "text": "x" * 70000}).encode(), token=self.code)
        self.expect(r, "too_large")
        self.expect(self.site.call("PATCH", "/api/comments/nothing-here", {"text": "x"}, token=self.code),
                    "no_comment")
        # A comment of an earlier review round can be read but not changed.
        old = self.post(client_id="r1").json["id"]
        self.assertEqual(self.site.admin_call("POST", "/api/admin/rounds", {"book": "SC", "name": "two"}).status, 201)
        self.expect(self.site.call("PATCH", f"/api/comments/{old}", {"text": "x"}, token=self.code), "round_closed")
        self.expect(self.site.call("DELETE", f"/api/comments/{old}", token=self.code), "round_closed")
        self.assertNotIn("comment_limit", app_module.WRITE_ERRORS)

    def test_each_reason_to_refuse_a_reader_has_its_code(self):
        def expect(r, code):
            self.assertEqual((r.status, r.json["error"]), (app_module.ACCESS_ERRORS[code][0], code), r.body)
        expect(self.site.call("GET", "/api/me"), "no_code")
        expect(self.site.call("GET", "/api/me", token="x" * 32), "bad_code")
        expect(self.site.call("GET", "/api/me", token=self.code, headers={"X-Review-Device": None}), "no_device")
        expect(self.site.call("GET", "/api/me", token=self.code, headers={"X-Review-Device": "short"}), "no_device")
        for k in "23":
            self.site.call("GET", "/api/me", token=self.code, headers={"X-Review-Device": "another-device-000" + k})
        expect(self.site.call("GET", "/api/me", token=self.code, headers={"X-Review-Device": "another-device-0004"}),
               "device_waiting")

    def test_a_withdrawn_chapter_and_a_changed_paragraph(self):
        cid = self.post(client_id="w1", a="SC 101.3").json["id"]
        self.site.publish(sample_chapter(1, count=2, tag="v2"))
        self.expect(self.site.call("PUT", "/api/place", {"book": "SC", "ch": "SC01", "a": "SC 101.3"},
                                   token=self.code), "no_paragraph")
        self.site.admin_call("DELETE", "/api/admin/chapters/SC/SC01")
        self.expect(self.site.call("PATCH", f"/api/comments/{cid}", {"text": "x"}, token=self.code), "no_chapter")

    def test_slow_down(self):
        site = Site(writes_per_minute=2)
        self.addCleanup(site.close)
        site.publish(sample_chapter(1))
        code = site.invite("R", ["SC"])["code"]
        body = {"book": "SC", "ch": "SC01", "a": "SC 101.1"}
        site.call("PUT", "/api/place", body, token=code)
        site.call("PUT", "/api/place", body, token=code)
        r = site.call("PUT", "/api/place", body, token=code)
        self.expect(r, "slow_down")
        self.assertGreater(int(r.headers["retry-after"]), 0)

    def test_invisible_characters_are_removed_never_refused(self):
        r = self.post(client_id="inv", kind="wording", quote="a\u200bb", text="c\u2066d")
        self.assertEqual((r.status, r.json["quote"], r.json["text"]), (201, "ab", "cd"))

    def test_me_carries_limits_features_and_the_total(self):
        self.post(client_id="m1")
        self.post(client_id="m2", ch="SC02", a="SC 102.1")
        self.site.admin_call("DELETE", "/api/admin/chapters/SC/SC02")
        me = self.site.call("GET", "/api/me", token=self.code).json
        self.assertEqual(me["limits"], {"quote": 4000, "text": 8000, "comments_per_minute": 10,
                                        "comments_per_day": 1000, "writes_per_minute": 10000, "devices_per_link": 2})
        # Only the comments on chapters open now count: the page loads nothing of a closed chapter.
        self.assertEqual(me["comments_total"], 1)
        self.assertEqual(sum(c["comments"] for c in me["chapters"]), 1)
        self.assertEqual(me["id"], self.rid)
        self.assertEqual(me["features"]["english"], {"on": False})
        self.assertIs(me["english"], False)


class Answers(unittest.TestCase):
    def setUp(self):
        self.site = Site(writes_per_minute=10000)
        self.addCleanup(self.site.close)
        self.site.publish(sample_chapter(1))
        r = self.site.invite("Reader", ["SC"])
        self.code = r["code"]

    def test_a_change_that_meets_a_delete_answers_no_comment(self):
        """A delete from another tab may land between the change's read and its write: 404, not 500."""
        cid = self.site.comment(self.code, "SC 101.1").json["id"]
        real = self.site.app.access

        def access_then_delete(req, book, ch):
            entry = real(req, book, ch)
            req.conn.execute("DELETE FROM comment WHERE id = ?", (cid,))
            return entry

        with mock.patch.object(self.site.app, "access", access_then_delete):
            r = self.site.call("PATCH", f"/api/comments/{cid}", {"text": "changed"}, token=self.code)
        self.assertEqual((r.status, r.json["error"]), (404, "no_comment"))

    def test_a_place_on_a_paragraph_that_is_gone_is_null(self):
        put = {"book": "SC", "ch": "SC01", "a": "SC 101.3"}
        self.assertEqual(self.site.call("PUT", "/api/place", put, token=self.code).status, 200)
        place = lambda: self.site.call("GET", "/api/me", token=self.code).json["chapters"][0]["place"]  # noqa: E731
        self.assertEqual(place(), "SC 101.3")
        self.site.publish(sample_chapter(1, count=2, tag="v2"))
        self.assertIsNone(place())

    def test_each_book_carries_its_title_in_its_own_language(self):
        books = lambda: self.site.call("GET", "/api/me", token=self.code).json["books"]  # noqa: E731
        self.assertEqual(books()[0]["title"], "")
        self.site.publish(dict(sample_chapter(1), book_title="Book title in its language"))
        self.assertEqual((books()[0]["title"], books()[0]["language"]), ("Book title in its language", "th"))
        # Publishing without it keeps the title; a forbidden character is refused.
        self.site.publish(sample_chapter(1, tag="v3"))
        self.assertEqual(books()[0]["title"], "Book title in its language")
        r = self.site.admin_call("PUT", "/api/admin/chapters/SC/SC01", dict(sample_chapter(1), book_title="x\u0e51"))
        self.assertEqual((r.status, r.json["error"]), (400, "bad_field"))

    def test_the_english_is_checked_for_invisible_characters_and_digits(self):
        for bad in ("\u202e", "\u200b", "\u0e51", "\u0ed1"):
            ch = sample_chapter(1)
            ch["paragraphs"][1]["en"] = f"<p>English{bad} text</p>"
            r = self.site.admin_call("PUT", "/api/admin/chapters/SC/SC01", ch)
            self.assertEqual((r.status, r.json["error"]), (400, "forbidden_character"), hex(ord(bad)))
        r = self.site.admin_call("PUT", "/api/admin/chapters/SC/SC01", dict(sample_chapter(1), title_en="Title\u200b"))
        self.assertEqual((r.status, r.json["error"]), (400, "bad_field"))

    def test_processed_names_its_limit(self):
        r = self.site.admin_call("POST", "/api/admin/processed", {"ids": list(range(1, 10002))})
        self.assertEqual(r.status, 400)
        self.assertIn("10000", r.json["message"])
        self.assertEqual(self.site.admin_call("POST", "/api/admin/processed", {"ids": list(range(1, 10001))}).status,
                         200)


class Bounded(unittest.TestCase):
    def test_write_counter_forgets_quiet_readers(self):
        site = Site(writes_per_minute=1000)
        self.addCleanup(site.close)
        site.publish(sample_chapter(1))
        made = site.admin_call("POST", "/api/admin/readers/batch", {"readers": [
            {"name": f"R{i}", "grants": ["SC"]} for i in range(50)]}).json["readers"]
        clock = [1000.0]
        with mock.patch.object(app_module.time, "monotonic", lambda: clock[0]):
            site.app.swept = clock[0]
            for r in made:
                site.call("PUT", "/api/place", {"book": "SC", "ch": "SC01", "a": "SC 101.1"}, token=r["code"])
            self.assertEqual(len(site.app.writes), 50)
            clock[0] += 61
            site.call("PUT", "/api/place", {"book": "SC", "ch": "SC01", "a": "SC 101.1"}, token=made[0]["code"])
            self.assertEqual(len(site.app.writes), 1)

    def test_chapter_cache_has_a_ceiling(self):
        site = Site()
        self.addCleanup(site.close)
        with mock.patch.object(app_module, "CACHE_MOST", 3):
            for n in range(1, 6):
                site.publish(sample_chapter(n))
            code = site.invite("R", ["SC"])["code"]
            for n in range(1, 6):
                self.assertEqual(site.call("GET", f"/api/chapter/SC/SC{n:02d}", token=code).status, 200)
            self.assertEqual(len(site.app.cache), 3)
            self.assertEqual([k[1] for k in site.app.cache], ["SC03", "SC04", "SC05"])
            site.call("GET", "/api/chapter/SC/SC03", token=code)
            site.call("GET", "/api/chapter/SC/SC01", token=code)
            self.assertEqual([k[1] for k in site.app.cache], ["SC05", "SC03", "SC01"])


class QueryPlans(unittest.TestCase):
    """The per-request queries use indexes, so their cost does not grow with the number of readers."""

    def test_no_full_scan_of_reader_tables(self):
        site = Site()
        self.addCleanup(site.close)
        con = sqlite3.connect(site.data / db.DB_NAME)
        self.addCleanup(con.close)
        args = {"book": "SC", "ch": "SC01", "r": 1}
        for sql in (app_module.ACCESS_SQL, app_module.OPEN_SQL):
            plan = " ".join(r[3] for r in con.execute("EXPLAIN QUERY PLAN " + sql, args))
            for table in ("grant", "group_member", "group_grant", "reader_group"):
                self.assertNotRegex(plan, rf"SCAN (\"?{table}\"?|{table[0]}{{1,2}}\b)(?! USING)", plan)
        for sql, a in (("SELECT * FROM reader WHERE code_hash = ?", ("x",)),
                       ("SELECT COUNT(*) FROM comment WHERE reader = ?", (1,)),
                       ("SELECT * FROM comment WHERE reader = ? AND client_id = ?", (1, "c")),
                       ("SELECT id, state, last_seen FROM reader_device WHERE reader = ? AND link = ? AND device = ?",
                        (1, "l", "d")),
                       ("SELECT COUNT(*) FROM reader_device WHERE reader = ? AND link = ?", (1, "l")),
                       ("SELECT s.name, s.value FROM group_member m JOIN reader_group t ON t.id = m.grp AND "
                        "t.active = 1 JOIN group_setting s ON s.grp = m.grp WHERE m.reader = ?", (1,))):
            plan = " ".join(r[3] for r in con.execute("EXPLAIN QUERY PLAN " + sql, a))
            self.assertIn("USING", plan, sql)
            self.assertNotRegex(plan, r"SCAN (reader|comment|m|reader_device)\b(?! USING)", sql)


if __name__ == "__main__":
    unittest.main()
