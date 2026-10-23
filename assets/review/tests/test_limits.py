"""Tests for the limits a reader writes under: new comments a minute and a day (midnight to midnight Thailand
time), other changes a minute, the lengths of the quote and the comment, the devices a link works on unasked, all
settings in config.json that /api/me carries. There is no limit on the comments a reader keeps."""
import json
import sqlite3
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest import mock

from helpers import Site, sample_chapter

from server import app as app_module
from server import common, db


class Settings(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.data = Path(tmp.name)

    def config(self, limits):
        (self.data / db.CONFIG).write_text(json.dumps({"public_url": "https://x.example", "limits": limits}))

    def test_the_ruled_defaults(self):
        self.assertEqual(common.load_limits(self.data), {
            "quote": 4000, "text": 8000, "comments_per_minute": 10, "comments_per_day": 1000,
            "writes_per_minute": 60, "devices_per_link": 2})

    def test_a_config_that_still_names_the_retired_total_starts(self):
        # The lifetime limit of 5,000 comments is gone; a config.json written for it still starts the site.
        self.config({"comments": 5000, "comments_per_day": 300})
        got = common.load_limits(self.data)
        self.assertNotIn("comments", got)
        self.assertEqual(got["comments_per_day"], 300)

    def test_config_json_sets_them_and_a_caller_overrides(self):
        self.config({"comments_per_day": 200, "text": 6000})
        got = common.load_limits(self.data, {"text": 7000, "quote": None})
        self.assertEqual((got["comments_per_day"], got["text"], got["quote"]), (200, 7000, 4000))

    def test_a_wrong_setting_stops_the_start_before_the_database_is_touched(self):
        for limits, words in (({"comment_per_day": 5}, "no limit named comment_per_day"),
                              ({"quote": 0}, "at least 1"), ({"text": "8000"}, "whole number"),
                              ({"text": True}, "whole number"), ({"text": 16000}, "at most 16128"),
                              ("1000", "must be an object")):
            with self.subTest(limits=limits):
                self.config(limits)
                with self.assertRaisesRegex(ValueError, words):
                    app_module.App(self.data)
                self.assertFalse((self.data / db.DB_NAME).exists())

    def test_the_largest_comment_fits_one_request(self):
        most = common.load_limits(self.data)
        body = json.dumps({"client_id": "c" * 64, "book": "SC", "ch": "SC01", "a": "SC 101.1", "kind": "wording",
                           "quote": "\U0001F600" * most["quote"], "text": "\U0001F600" * most["text"]},
                          ensure_ascii=False).encode()
        self.assertLess(len(body), common.BODY_LIMIT)


class NewComments(unittest.TestCase):
    def setUp(self):
        self.site = Site(limits={"comments_per_minute": 3, "comments_per_day": 5})
        self.addCleanup(self.site.close)
        self.site.publish(sample_chapter(1))
        self.code = self.site.invite("Reader", ["SC"])["code"]

    def post(self, client_id):
        return self.site.comment(self.code, "SC 101.1", client_id=client_id)

    def test_a_minute_counts_new_comments_only(self):
        self.assertEqual([self.post(f"m{i}").status for i in range(3)], [201, 201, 201])
        r = self.post("m3")
        self.assertEqual((r.status, r.json["error"]), (429, "slow_down"))
        self.assertGreater(int(r.headers["retry-after"]), 0)
        # A comment sent again answers as before and counts for nothing; places, edits and deletes go on.
        self.assertEqual(self.post("m0").status, 200)
        cid = self.site.call("GET", "/api/comments", token=self.code).json["comments"][0]["id"]
        self.assertEqual(self.site.call("PATCH", f"/api/comments/{cid}", {"text": "x"}, token=self.code).status, 200)
        self.assertEqual(self.site.call("PUT", "/api/place", {"book": "SC", "ch": "SC01", "a": "SC 101.1"},
                                        token=self.code).status, 200)
        self.assertEqual(self.site.call("DELETE", f"/api/comments/{cid}", token=self.code).status, 200)

    def test_a_refused_comment_takes_no_place_in_the_minute(self):
        for i in range(3):
            r = self.site.call("POST", "/api/comments", {"client_id": f"bad{i}", "book": "SC", "ch": "SC01",
                                                         "a": "SC 101.1", "kind": "flag", "text": ""}, token=self.code)
            self.assertEqual(r.json["error"], "text_required")
        self.assertEqual([self.post(f"ok{i}").status for i in range(3)], [201, 201, 201])

    def test_the_day_has_its_own_code_and_a_delete_gives_nothing_back(self):
        clock = [1000.0]
        with mock.patch.object(app_module.time, "monotonic", lambda: clock[0]):
            for i in range(5):
                if i == 3:
                    clock[0] += 61          # a new minute
                self.assertEqual(self.post(f"d{i}").status, 201, i)
            cid = self.site.call("GET", "/api/comments", token=self.code).json["comments"][0]["id"]
            self.site.call("DELETE", f"/api/comments/{cid}", token=self.code)
            clock[0] += 61
            r = self.post("d5")
        self.assertEqual((r.status, r.json["error"], r.json["limit"]), (429, "daily_limit", 5))
        self.assertEqual(app_module.WRITE_ERRORS["daily_limit"][0], 429)
        # The day ends at the next midnight in Thailand, and the reader may write again from then.
        self.assertEqual(r.json["retry_at"], db.next_midnight(db.now()))
        self.assertAlmostEqual(int(r.headers["retry-after"]), db.seconds_until(r.json["retry_at"]), delta=2)
        self.assertLessEqual(int(r.headers["retry-after"]), 24 * 3600 + 1)
        self.assertIn("today's limit of 5 new comments", r.json["message"])
        self.assertIn("midnight, Thailand time", r.json["message"])

    def test_after_midnight_in_thailand_the_reader_writes_again(self):
        con = sqlite3.connect(self.site.data / db.DB_NAME)
        rid = con.execute("SELECT id FROM reader").fetchone()[0]
        midnight = db.day_start(db.now())
        yesterday = db.stamp_of(db.parse_stamp(midnight) - timedelta(seconds=1))
        con.executemany("INSERT INTO comment_made (reader, at) VALUES (?, ?)",
                        [(rid, db.ago(3))] + [(rid, yesterday)] * 5 + [(rid, midnight)] * 4)
        con.commit()
        self.assertEqual(self.post("late").status, 201)
        self.assertEqual(self.post("later").json["error"], "daily_limit")
        # Rows older than two days are dropped as the reader writes.
        self.assertEqual(con.execute("SELECT COUNT(*) FROM comment_made WHERE at <= ?", (db.ago(2),)).fetchone()[0], 0)
        con.close()

    def test_the_day_runs_from_midnight_to_midnight_thailand_time(self):
        # Thailand is UTC+7 all year: its midnight is 17:00 UTC of the day before.
        self.assertEqual(db.day_start("2026-10-22T16:59:59Z"), "2026-10-21T17:00:00Z")
        self.assertEqual(db.day_start("2026-10-22T17:00:00Z"), "2026-10-22T17:00:00Z")
        self.assertEqual(db.next_midnight("2026-10-22T16:59:59Z"), "2026-10-22T17:00:00Z")
        self.assertEqual(db.next_midnight("2026-12-31T17:00:00Z"), "2027-01-01T17:00:00Z")
        self.assertEqual(db.thai_time("2026-10-22T17:00:00Z"), "2026-10-23 00:00")

    def test_me_carries_the_numbers(self):
        limits = self.site.call("GET", "/api/me", token=self.code).json["limits"]
        self.assertEqual(limits, {"quote": 4000, "text": 8000, "comments_per_minute": 3,
                                  "comments_per_day": 5, "writes_per_minute": 60, "devices_per_link": 2})


if __name__ == "__main__":
    unittest.main()
