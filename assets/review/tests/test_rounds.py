"""Tests for what a reader's page loads and what the translator exports: only chapters open to the reader and the
reader's comments on them in the book's current review round; earlier rounds read-only through "My earlier
comments"; a closed chapter refuses adding, changing and deleting; the export of what changed since a time, of one
round, and the comments deleted since; and deleting one reader's comments between two times."""
import sqlite3
import unittest

from helpers import Site, sample_chapter

from server import db


class Base(unittest.TestCase):
    def setUp(self):
        self.site = Site(writes_per_minute=10000, limits={"comments_per_minute": 1000})
        self.addCleanup(self.site.close)
        for n in (1, 2):
            self.site.publish(sample_chapter(n))
        r = self.site.invite("Anan", ["SC01-02"])
        self.code, self.rid = r["code"], r["id"]
        self.other = self.site.invite("Mali", ["SC01"])["code"]

    def post(self, a="SC 101.1", ch="SC01", text="A note", code=None):
        r = self.site.comment(code or self.code, a, ch=ch, text=text)
        self.assertEqual(r.status, 201, r.body)
        return r.json

    def me(self):
        return self.site.call("GET", "/api/me", token=self.code).json

    def listed(self, query=""):
        return self.site.call("GET", "/api/comments" + query, token=self.code).json

    def start(self, name, book="SC"):
        r = self.site.admin_call("POST", "/api/admin/rounds", {"book": book, "name": name})
        self.assertEqual(r.status, 201, r.body)
        return r.json


class ClosedChapters(Base):
    def test_a_closed_chapter_leaves_the_page_with_the_readers_comments(self):
        keep = self.post()
        gone = self.post("SC 102.1", "SC02")
        # Closed for this reader: their own grants no longer hold SC02.
        self.site.admin_call("PATCH", f"/api/admin/readers/{self.rid}", {"grants": ["SC01"]})
        me = self.me()
        self.assertEqual([c["id"] for c in me["chapters"]], ["SC01"])
        self.assertEqual(me["comments_total"], 1)
        self.assertEqual([c["id"] for c in self.listed()["comments"]], [keep["id"]])
        self.assertEqual(self.listed("?book=SC&ch=SC02")["comments"], [])
        # Adding, changing and deleting are refused, and the comment stays on the site for the translator.
        for r in (self.site.comment(self.code, "SC 102.1", ch="SC02"),
                  self.site.call("PATCH", f"/api/comments/{gone['id']}", {"text": "x"}, token=self.code),
                  self.site.call("DELETE", f"/api/comments/{gone['id']}", token=self.code)):
            self.assertEqual((r.status, r.json["error"]), (404, "no_chapter"))
        exported = self.site.admin_call("GET", "/api/admin/export").json["comments"]
        self.assertIn(gone["id"], [c["id"] for c in exported])
        # Opened again, the chapter comes back with its comments.
        self.site.admin_call("PATCH", f"/api/admin/readers/{self.rid}", {"grants": ["SC01-02"]})
        self.assertEqual(sorted(c["id"] for c in self.listed()["comments"]), sorted([keep["id"], gone["id"]]))

    def test_a_withdrawn_chapter_leaves_every_readers_page(self):
        self.post("SC 102.1", "SC02")
        self.site.admin_call("DELETE", "/api/admin/chapters/SC/SC02")
        self.assertEqual(self.listed()["comments"], [])
        self.assertEqual(self.me()["comments_total"], 0)


class Rounds(Base):
    def test_a_new_round_shows_only_the_comments_written_in_it(self):
        before = self.post(text="Before any round")
        first = self.start("first")
        self.assertEqual((first["book"], first["name"], first["current"], first["comments"]), ("SC", "first", True, 0))
        one = self.post(text="In the first round")
        self.assertEqual(one["round"], "first")
        self.assertEqual([c["id"] for c in self.listed()["comments"]], [one["id"]])
        book = self.me()["books"][0]
        self.assertEqual((book["round"]["name"], book["earlier"]), ("first", 1))
        self.assertEqual(self.me()["chapters"][0]["comments"], 1)
        self.start("second")
        two = self.post(text="In the second round")
        self.assertEqual([c["id"] for c in self.listed()["comments"]], [two["id"]])
        earlier = self.listed("?earlier=1")
        self.assertEqual([(c["id"], c["round"]) for c in earlier["comments"]],
                         [(before["id"], None), (one["id"], "first")])
        self.assertEqual([(r["name"], r["current"]) for r in earlier["rounds"]], [("first", False), ("second", True)])
        self.assertEqual(self.me()["books"][0]["earlier"], 2)
        # An earlier round can be read, not changed; the reader's own resend of an old comment answers it as it is.
        r = self.site.call("PATCH", f"/api/comments/{one['id']}", {"text": "x"}, token=self.code)
        self.assertEqual((r.status, r.json["error"]), (409, "round_closed"))
        resend = self.site.call("POST", "/api/comments", {"client_id": one["client_id"], "book": "SC", "ch": "SC01",
                                                          "a": "SC 101.1", "kind": "flag", "text": "x"}, token=self.code)
        self.assertEqual((resend.status, resend.json["round"]), (200, "first"))
        # The other reader's comments are theirs alone.
        self.assertEqual(self.site.call("GET", "/api/comments?earlier=1", token=self.other).json["comments"], [])

    def test_rounds_are_per_book_named_once_and_listed(self):
        self.site.publish(sample_chapter(1, book="QQ"), book="QQ")
        self.post()
        self.start("first")
        self.start("first", book="QQ")
        r = self.site.admin_call("POST", "/api/admin/rounds", {"book": "SC", "name": "FIRST"})
        self.assertEqual((r.status, r.json["error"]), (409, "round_taken"))
        for bad in ({"book": "SC", "name": "two words"}, {"book": "SC", "name": "-x"}, {"book": "sc", "name": "x"},
                    {"book": "SC"}):
            self.assertEqual(self.site.admin_call("POST", "/api/admin/rounds", bad).status, 400, bad)
        listed = self.site.admin_call("GET", "/api/admin/rounds").json
        self.assertEqual([(r["book"], r["name"], r["current"]) for r in listed["rounds"]],
                         [("QQ", "first", True), ("SC", "first", True)])
        self.assertEqual(listed["before"], {"SC": 1})

    def test_a_chapter_finished_before_the_round_is_to_be_read_again(self):
        self.site.call("PUT", "/api/finished", {"book": "SC", "ch": "SC01", "finished": True}, token=self.code)
        self.assertTrue(self.me()["chapters"][0]["finished"])
        con = sqlite3.connect(self.site.data / db.DB_NAME)
        con.execute("UPDATE finished SET at = '2026-01-01T00:00:00Z'")
        con.commit()
        con.close()
        self.start("second-reading")
        chapter = self.me()["chapters"][0]
        self.assertEqual((chapter["finished"], chapter["finished_at"]), (False, None))
        self.site.call("PUT", "/api/finished", {"book": "SC", "ch": "SC01", "finished": True}, token=self.code)
        self.assertTrue(self.me()["chapters"][0]["finished"])

    def test_the_export_of_one_round(self):
        self.post(text="Before")
        self.start("first")
        one = self.post(text="First")
        self.start("second")
        self.post(text="Second")
        got = self.site.admin_call("GET", "/api/admin/export?round=first").json
        self.assertEqual(([c["id"] for c in got["comments"]], got["round"]), ([one["id"]], "first"))
        self.assertEqual(got["comments"][0]["round"], "first")
        r = self.site.admin_call("GET", "/api/admin/export?round=none")
        self.assertEqual((r.status, r.json["error"]), (404, "no_round"))
        everything = self.site.admin_call("GET", "/api/admin/export").json["comments"]
        self.assertEqual([c["round"] for c in everything], [None, "first", "second"])

    def test_the_export_of_the_comments_before_the_first_round(self):
        before = self.post(text="Before")
        self.start("first")
        self.post(text="First")
        got = self.site.admin_call("GET", "/api/admin/export?before_first=1").json
        self.assertEqual(([c["id"] for c in got["comments"]], got["round"], got["before_first_round"]),
                         ([before["id"]], None, True))
        self.assertEqual(self.site.admin_call("GET", "/api/admin/export?before_first=1&book=GC").json["comments"], [])
        r = self.site.admin_call("GET", "/api/admin/export?before_first=1&round=first")
        self.assertEqual((r.status, r.json["error"]), (400, "bad_field"))
        # The deleted comments belong to the export of what changed only.
        self.assertEqual(self.site.admin_call(
            "GET", "/api/admin/export?before_first=1&since=2026-01-01T00:00:00Z").json["deleted"], [])


class WhatChanged(Base):
    def test_since_brings_new_and_changed_comments_and_names_the_deleted(self):
        old = self.post(text="Old")
        edited = self.post(text="To be edited")
        deleted = self.post(text="To be deleted")
        con = sqlite3.connect(self.site.data / db.DB_NAME)
        con.execute("UPDATE comment SET created = '2026-01-01T00:00:00Z', updated = '2026-01-01T00:00:00Z'")
        con.commit()
        con.close()
        since = "2026-02-01T00:00:00Z"
        self.assertEqual(self.site.admin_call("GET", f"/api/admin/export?since={since}").json["comments"], [])
        self.site.call("PATCH", f"/api/comments/{edited['id']}", {"text": "Edited"}, token=self.code)
        self.site.call("DELETE", f"/api/comments/{deleted['id']}", token=self.code)
        new = self.post(text="New", code=self.other)
        got = self.site.admin_call("GET", f"/api/admin/export?since={since}").json
        self.assertEqual([c["id"] for c in got["comments"]], [edited["id"], new["id"]])
        self.assertEqual([(d["id"], d["reader"], d["ch"]) for d in got["deleted"]], [(deleted["id"], "Anan", "SC01")])
        self.assertEqual(got["since"], since)
        self.assertLessEqual(got["exported"], db.now())
        mine = self.site.admin_call("GET", f"/api/admin/export?since={since}&reader=Mali").json
        self.assertEqual(([c["id"] for c in mine["comments"]], mine["deleted"]), ([new["id"]], []))
        everything = self.site.admin_call("GET", "/api/admin/export").json
        self.assertEqual((len(everything["comments"]), everything["deleted"]), (3, []))
        self.assertNotIn(old["id"], [c["id"] for c in got["comments"]])
        r = self.site.admin_call("GET", "/api/admin/export?since=yesterday")
        self.assertEqual((r.status, r.json["error"]), (400, "bad_field"))


class CommentTimes(Base):
    def test_a_comment_that_waits_for_the_write_lock_gets_the_time_it_is_saved(self):
        """A comment's time is taken once it holds the write lock, so an export of what changed taken while it
        waited never has a later time than the comment and yet misses it."""
        import threading
        import time
        hold = db.connect(self.site.data / db.DB_NAME)
        self.addCleanup(hold.close)
        hold.execute("BEGIN IMMEDIATE")
        out = {}
        worker = threading.Thread(target=lambda: out.setdefault("r", self.site.comment(self.code, "SC 101.1")))
        worker.start()
        time.sleep(1.2)
        exported = self.site.admin_call("GET", "/api/admin/export").json
        self.assertEqual(exported["comments"], [])
        hold.execute("COMMIT")
        worker.join(10)
        self.assertEqual(out["r"].status, 201, out["r"].body)
        self.assertGreaterEqual(out["r"].json["created"], exported["exported"])
        since = self.site.admin_call("GET", f"/api/admin/export?since={exported['exported']}").json
        self.assertEqual([c["id"] for c in since["comments"]], [out["r"].json["id"]])


class GoneParagraphs(Base):
    def test_comments_on_paragraphs_taken_out_stand_together_in_the_order_of_their_paragraphs(self):
        site = self.site
        site.publish(sample_chapter(3, count=5))
        site.admin_call("PATCH", f"/api/admin/readers/{self.rid}", {"grants": ["SC"]})
        mali = self.site.invite("Boon", ["SC"])["code"]
        ids = []
        for a, code in (("SC 103.4", self.code), ("SC 103.3", mali), ("SC 103.4", mali), ("SC 103.3", self.code),
                        ("SC 103.1", self.code)):
            r = site.comment(code, a, ch="SC03")
            self.assertEqual(r.status, 201, r.body)
            ids.append(r.json["id"])
        site.publish(sample_chapter(3, count=2, tag="v2"))
        got = [(c["anchor"], c["id"], c["anchor_missing"])
               for c in site.admin_call("GET", "/api/admin/export?ch=SC03").json["comments"]]
        self.assertEqual(got, [("SC 103.1", ids[4], False), ("SC 103.3", ids[1], True), ("SC 103.3", ids[3], True),
                               ("SC 103.4", ids[0], True), ("SC 103.4", ids[2], True)])


class ResentAfterDelete(Base):
    def test_a_comment_sent_again_after_it_was_deleted_stays_deleted(self):
        first = self.site.comment(self.code, "SC 101.1", client_id="phone-1", text="Once")
        self.assertEqual(first.status, 201)
        self.assertEqual(self.site.call("DELETE", "/api/comments/phone-1", token=self.code).status, 200)
        again = self.site.comment(self.code, "SC 101.1", client_id="phone-1", text="Once")
        self.assertEqual((again.status, again.json["error"]), (404, "no_comment"))
        self.assertEqual(self.site.admin_call("GET", "/api/admin/export").json["comments"], [])
        # Another reader may use the same client_id, and so may a comment deleted with delete-comments.
        self.assertEqual(self.site.comment(self.other, "SC 101.1", client_id="phone-1").status, 201)
        self.site.comment(self.code, "SC 101.1", client_id="phone-2")
        self.site.admin_call("POST", f"/api/admin/readers/{self.rid}/delete-comments",
                             {"from": "2026-01-01T00:00:00Z", "to": "2099-01-01T00:00:00Z", "delete": True})
        self.assertEqual(self.site.comment(self.code, "SC 101.1", client_id="phone-2").status, 404)


class DeleteBetweenTimes(Base):
    def test_the_delete_removes_only_the_comments_counted(self):
        self.post(text="Junk 1")
        self.post(text="Junk 2")
        path = f"/api/admin/readers/{self.rid}/delete-comments"
        span = {"from": "2026-01-01T00:00:00Z", "to": "2099-01-01T00:00:00Z"}
        counted = self.site.admin_call("POST", path, span).json
        self.assertEqual(counted["comments"], 2)
        later = self.post(text="Written after the count")
        done = self.site.admin_call("POST", path, dict(span, delete=True, upto=counted["last"])).json
        self.assertEqual((done["deleted"], done["last"]), (2, counted["last"]))
        left = [c["id"] for c in self.site.admin_call("GET", "/api/admin/export?reader=Anan").json["comments"]]
        self.assertEqual(left, [later["id"]])
        self.assertIsNone(self.site.admin_call("POST", path, dict(span, upto=1)).json["last"])
        self.assertEqual(self.site.admin_call("POST", path, dict(span, upto="7")).status, 400)

    def test_one_readers_comments_between_two_times(self):
        early, late = self.post(text="Early"), self.post(text="Junk")
        mine = self.post(text="Not junk", code=self.other)
        con = sqlite3.connect(self.site.data / db.DB_NAME)
        con.execute("UPDATE comment SET created = '2026-10-01T05:00:00Z' WHERE id = ?", (early["id"],))
        con.execute("UPDATE comment SET created = '2026-10-21T05:00:00Z' WHERE id IN (?, ?)", (late["id"], mine["id"]))
        con.commit()
        con.close()
        path = f"/api/admin/readers/{self.rid}/delete-comments"
        span = {"from": "2026-10-20T17:00:00Z", "to": "2026-10-22T17:00:00Z"}
        counted = self.site.admin_call("POST", path, span).json
        self.assertEqual((counted["comments"], counted["deleted"], counted["chapters"], counted["name"]),
                         (1, 0, {"SC01": 1}, "Anan"))
        self.assertEqual(len(self.site.admin_call("GET", "/api/admin/export").json["comments"]), 3)
        done = self.site.admin_call("POST", path, dict(span, delete=True)).json
        self.assertEqual((done["comments"], done["deleted"]), (1, 1))
        left = [c["id"] for c in self.site.admin_call("GET", "/api/admin/export").json["comments"]]
        self.assertEqual(sorted(left), sorted([early["id"], mine["id"]]))
        gone = self.site.admin_call("GET", "/api/admin/export?since=2026-01-01T00:00:00Z").json["deleted"]
        self.assertEqual([d["id"] for d in gone], [late["id"]])
        for bad in ({"from": "2026-10-22T17:00:00Z", "to": "2026-10-20T17:00:00Z"}, {"from": "2026-10-20", "to": "x"},
                    dict(span, delete="yes")):
            self.assertEqual(self.site.admin_call("POST", path, bad).status, 400, bad)
        self.assertEqual(self.site.admin_call("POST", "/api/admin/readers/999/delete-comments", span).status, 404)


if __name__ == "__main__":
    unittest.main()
