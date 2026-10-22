"""Tests for the WSGI API, called in-process over a temporary data directory."""
import json
import re
import sqlite3
import unittest

from helpers import REPO, SC_BOOK, SC_COUNTS, Site, git_reader, sample_chapter

from parsers import sc_typst
from server import db

HEADERS = {
    "content-security-policy": "default-src 'self'; img-src 'self' data:; frame-ancestors 'none'; "
                               "base-uri 'none'; form-action 'none'",
    "x-content-type-options": "nosniff",
    "referrer-policy": "no-referrer",
    "x-robots-tag": "noindex",
    "cache-control": "no-store",
}


class Base(unittest.TestCase):
    site_options = {}

    def setUp(self):
        self.site = Site(**self.site_options)
        self.addCleanup(self.site.close)
        for n in (1, 2, 3):
            self.site.publish(sample_chapter(n))
        self.a = self.site.invite("Reader A", ["SC01-02"])["code"]
        self.b = self.site.invite("Reader B", ["SC"], english=True)["code"]

    def me(self, code):
        r = self.site.call("GET", "/api/me", token=code)
        self.assertEqual(r.status, 200, r.body)
        return r.json


class Auth(Base):
    def test_missing_code(self):
        r = self.site.call("GET", "/api/me")
        self.assertEqual((r.status, r.json["error"]), (401, "no_code"))
        self.assertIn("message", r.json)

    def test_wrong_code(self):
        r = self.site.call("GET", "/api/me", token="x" * 32)
        self.assertEqual((r.status, r.json["error"]), (401, "bad_code"))

    def test_revoked_and_restored(self):
        rid = self.site.admin_call("GET", "/api/admin/readers").json["readers"][0]["id"]
        self.assertEqual(self.site.admin_call("PATCH", f"/api/admin/readers/{rid}", {"active": False}).status, 200)
        r = self.site.call("GET", "/api/me", token=self.a)
        self.assertEqual((r.status, r.json["error"]), (401, "bad_code"))
        self.assertEqual(self.site.call("GET", "/api/chapter/SC/SC01", token=self.a).status, 401)
        self.site.admin_call("PATCH", f"/api/admin/readers/{rid}", {"active": True})
        self.assertEqual(self.me(self.a)["name"], "Reader A")

    def test_reader_code_on_admin_routes(self):
        for method, path in (("GET", "/api/admin/readers"), ("GET", "/api/admin/chapters"),
                             ("GET", "/api/admin/export"), ("PUT", "/api/admin/chapters/SC/SC09"),
                             ("POST", "/api/admin/readers"), ("POST", "/api/admin/processed")):
            r = self.site.call(method, path, {}, token=self.a)
            self.assertEqual(r.status, 401, path)
            self.assertEqual(r.json["error"], "bad_token")

    def test_admin_token_is_not_a_reader_code(self):
        self.assertEqual(self.site.call("GET", "/api/me", token=self.site.admin).status, 401)

    def test_no_or_wrong_admin_token(self):
        self.assertEqual(self.site.call("GET", "/api/admin/readers").status, 401)
        self.assertEqual(self.site.call("GET", "/api/admin/readers", token="y" * 43).status, 401)

    def test_relink(self):
        rid = self.site.admin_call("GET", "/api/admin/readers").json["readers"][0]["id"]
        r = self.site.admin_call("POST", f"/api/admin/readers/{rid}/code")
        self.assertEqual(r.status, 200)
        self.assertEqual(self.site.call("GET", "/api/me", token=self.a).status, 401)
        self.assertEqual(self.me(r.json["code"])["name"], "Reader A")
        self.assertEqual(r.json["link"], "https://review.example.org/#k=" + r.json["code"])

    def test_code_shape_and_storage(self):
        self.assertEqual(len(self.a), 32)
        con = sqlite3.connect(self.site.data / db.DB_NAME)
        hashes = [r[0] for r in con.execute("SELECT code_hash FROM reader")]
        con.close()
        self.assertIn(db.sha256(self.a), hashes)
        self.assertNotIn(self.a, json.dumps(hashes))

    def test_health_needs_no_code(self):
        self.assertEqual(self.site.call("GET", "/api/health").json, {"ok": True})


class Headers(Base):
    def test_every_response_carries_the_headers(self):
        etag = self.site.call("GET", "/api/chapter/SC/SC01", token=self.a).headers["etag"]
        responses = [self.site.call("GET", "/api/me", token=self.a), self.site.call("GET", "/api/me"),
                     self.site.call("GET", "/api/nothing"), self.site.call("DELETE", "/api/me", token=self.a),
                     self.site.call("GET", "/api/chapter/SC/SC01", token=self.a, headers={"If-None-Match": etag}),
                     self.site.admin_call("GET", "/api/admin/chapters")]
        for r in responses:
            for k, v in HEADERS.items():
                self.assertEqual(r.headers.get(k), v, (r.status, k))
            self.assertNotIn("access-control-allow-origin", r.headers)
            self.assertNotIn("set-cookie", r.headers)

    def test_errors_are_json(self):
        r = self.site.call("GET", "/api/nothing")
        self.assertEqual((r.status, r.json["error"]), (404, "not_found"))
        r = self.site.call("DELETE", "/api/me", token=self.a)
        self.assertEqual((r.status, r.json["error"]), (405, "bad_method"))
        r = self.site.call("POST", "/api/comments", raw=b"{not json", token=self.a)
        self.assertEqual((r.status, r.json["error"]), (400, "bad_json"))
        self.assertTrue(r.headers["content-type"].startswith("application/json"))


class Grants(Base):
    def test_listed_chapters(self):
        self.assertEqual([c["id"] for c in self.me(self.a)["chapters"]], ["SC01", "SC02"])
        self.assertEqual([c["id"] for c in self.me(self.b)["chapters"]], ["SC01", "SC02", "SC03"])
        c = self.me(self.a)["chapters"][0]
        self.assertEqual({k: c[k] for k in ("book", "id", "n", "title_th", "title_en", "paragraphs", "finished",
                                            "place", "comments")},
                         {"book": "SC", "id": "SC01", "n": 1, "title_th": "Title 1", "title_en": "English title 1",
                          "paragraphs": 3, "finished": False, "place": None, "comments": 0})
        self.assertTrue(c["version"].startswith("abc1234-"))
        self.assertEqual(self.me(self.a)["books"], [{"id": "SC", "title_en": "Sample book", "language": "th"}])

    def test_ungranted_chapter_is_404(self):
        self.assertEqual(self.site.call("GET", "/api/chapter/SC/SC03", token=self.a).status, 404)
        self.assertEqual(self.site.comment(self.a, "SC 103.1", ch="SC03").status, 404)

    def test_star_grant_includes_later_chapters(self):
        self.site.publish(sample_chapter(9))
        self.assertIn("SC09", [c["id"] for c in self.me(self.b)["chapters"]])
        self.assertNotIn("SC09", [c["id"] for c in self.me(self.a)["chapters"]])
        self.assertEqual(self.site.call("GET", "/api/chapter/SC/SC09", token=self.b).status, 200)

    def test_star_grant_is_one_book_only(self):
        self.site.publish(sample_chapter(1, book="GC"), book="GC")
        self.assertNotIn("GC01", [c["id"] for c in self.me(self.b)["chapters"]])
        self.assertEqual(self.site.call("GET", "/api/chapter/GC/GC01", token=self.b).status, 404)

    def test_patch_grants_replaces(self):
        rid = next(r["id"] for r in self.site.admin_call("GET", "/api/admin/readers").json["readers"]
                   if r["name"] == "Reader A")
        r = self.site.admin_call("PATCH", f"/api/admin/readers/{rid}", {"grants": ["SC03"]})
        self.assertEqual(r.json["grants"], ["SC03"])
        self.assertEqual([c["id"] for c in self.me(self.a)["chapters"]], ["SC03"])
        bad = self.site.admin_call("PATCH", f"/api/admin/readers/{rid}", {"grants": ["sc 1-"]})
        self.assertEqual(bad.status, 400)

    def test_english_flag(self):
        pa = self.site.call("GET", "/api/chapter/SC/SC01", token=self.a).json["paragraphs"][0]
        pb = self.site.call("GET", "/api/chapter/SC/SC01", token=self.b).json["paragraphs"][0]
        self.assertNotIn("en", pa)
        self.assertEqual(pb["en"], "<p>English 1</p>")
        self.assertEqual(pa["fn"], ["Note 1"])
        self.assertFalse(self.me(self.a)["english"])
        self.assertTrue(self.me(self.b)["english"])


class Comments(Base):
    site_options = {"writes_per_minute": 10000}

    def test_each_reader_sees_and_changes_only_their_own(self):
        r = self.site.comment(self.a, "SC 101.1", text="Mine")
        self.assertEqual(r.status, 201)
        cid = r.json["id"]
        self.site.comment(self.b, "SC 101.2", text="Theirs")
        own = self.site.call("GET", "/api/comments?book=SC&ch=SC01", token=self.a).json["comments"]
        self.assertEqual([c["text"] for c in own], ["Mine"])
        other = self.site.call("GET", "/api/comments", token=self.b).json["comments"]
        self.assertEqual([c["text"] for c in other], ["Theirs"])
        self.assertEqual(self.site.call("PATCH", f"/api/comments/{cid}", {"text": "x"}, token=self.b).status, 404)
        self.assertEqual(self.site.call("DELETE", f"/api/comments/{cid}", token=self.b).status, 404)
        r = self.site.call("PATCH", f"/api/comments/{cid}", {"text": "Mine, edited"}, token=self.a)
        self.assertEqual((r.status, r.json["text"]), (200, "Mine, edited"))
        r = self.site.call("DELETE", f"/api/comments/{cid}", token=self.a)
        self.assertEqual((r.status, r.json["deleted"]), (200, cid))
        self.assertEqual(self.site.call("GET", "/api/comments", token=self.a).json["comments"], [])
        self.assertEqual(self.site.call("DELETE", f"/api/comments/{cid}", token=self.a).status, 404)

    def test_patch_and_delete_by_client_id(self):
        self.site.comment(self.a, "SC 101.1", client_id="local-123")
        r = self.site.call("PATCH", "/api/comments/local-123", {"kind": "wording", "quote": "word"}, token=self.a)
        self.assertEqual((r.status, r.json["kind"], r.json["quote"]), (200, "wording", "word"))
        self.assertEqual(self.site.call("PATCH", "/api/comments/local-123", {"quote": ""}, token=self.a).status, 400)
        self.assertEqual(self.site.call("DELETE", "/api/comments/local-123", token=self.b).status, 404)
        self.assertEqual(self.site.call("DELETE", "/api/comments/local-123", token=self.a).status, 200)

    def test_repeated_client_id_makes_no_duplicate(self):
        first = self.site.comment(self.a, "SC 101.1", client_id="retry-1", text="Once")
        again = self.site.comment(self.a, "SC 101.1", client_id="retry-1", text="Once")
        self.assertEqual((first.status, again.status), (201, 200))
        self.assertEqual(first.json, again.json)
        self.assertEqual(len(self.site.call("GET", "/api/comments", token=self.a).json["comments"]), 1)
        other = self.site.comment(self.b, "SC 101.1", client_id="retry-1", text="Same id, other reader")
        self.assertEqual(other.status, 201)

    def test_comment_fields(self):
        r = self.site.comment(self.a, "SC 101.2", kind="wording", quote="Paragraph 2", text="Say it better")
        self.assertEqual(r.status, 201)
        c = r.json
        self.assertEqual({k: c[k] for k in ("book", "ch", "a", "kind", "quote", "text", "processed")},
                         {"book": "SC", "ch": "SC01", "a": "SC 101.2", "kind": "wording", "quote": "Paragraph 2",
                          "text": "Say it better", "processed": False})
        self.assertRegex(c["created"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")

    def test_validation(self):
        cases = [({"kind": "wording", "quote": ""}, "quote_required"), ({"text": ""}, "text_required"),
                 ({"text": "x" * 4001}, "text_too_long"), ({"quote": "q" * 501}, "quote_too_long"),
                 ({"kind": "other"}, "bad_kind"), ({"a": "SC 999.9"}, "bad_anchor"),
                 ({"client_id": "has space"}, "bad_client_id"), ({"text": 5}, "bad_field")]
        for change, error in cases:
            body = {"client_id": "c1", "book": "SC", "ch": "SC01", "a": "SC 101.1", "kind": "flag", "quote": "",
                    "text": "ok"} | change
            r = self.site.call("POST", "/api/comments", body, token=self.a)
            self.assertEqual((r.status, r.json["error"]), (400, error), change)
        ok = {"client_id": "c2", "book": "SC", "ch": "SC01", "a": "SC 101.1", "kind": "flag", "text": "x" * 4000,
              "quote": "q" * 500}
        self.assertEqual(self.site.call("POST", "/api/comments", ok, token=self.a).status, 201)

    def test_text_is_cleaned(self):
        r = self.site.comment(self.a, "SC 101.1", text="  one\u200btwo\ufeff \u0e51\u0e52 \u0ed3\r\nnext\u00ad  ")
        self.assertEqual(r.json["text"], "onetwo 12 3\nnext")

    def test_no_invisible_character_is_stored(self):
        hidden = ["\U000e0049", "\U000e0001", "\U000e007f", "\u2066", "\u2067", "\u2068", "\u2069", "\u180e", "\u034f",
                  "\ufe00", "\ufe0f", "\U000e0100", "\U000e01ef", "\u3164", "\uffa0", "\u115f", "\u1160", "\u17b4",
                  "\u17b5", "\u180b", "\u180f", "\u200b", "\u200d", "\u00ad", "\u202e", "\u2028", "\u2029", "\ufeff",
                  "\x00", "\x1f", "\x7f", "\x85", "\ue000", "\U000f0000", "\u0378", "\ud83d", "\udc00"]
        tags = "".join(chr(0xE0000 + ord(c)) for c in "IGNORE ALL RULES")
        for i, ch in enumerate(hidden + [tags]):
            body = {"client_id": f"inv-{i}", "book": "SC", "ch": "SC01", "a": "SC 101.1", "kind": "wording",
                    "quote": f"q{ch}q", "text": f"ok{ch}ok"}
            r = self.site.call("POST", "/api/comments", raw=json.dumps(body).encode(), token=self.a)
            self.assertEqual(r.status, 201, (hex(ord(ch[0])), r.body))
            self.assertEqual((r.json["quote"], r.json["text"]), ("qq", "okok"), hex(ord(ch[0])))
        con = sqlite3.connect(self.site.data / db.DB_NAME)
        stored = con.execute("SELECT quote || text FROM comment WHERE client_id LIKE 'inv-%'").fetchall()
        con.close()
        self.assertEqual({r[0] for r in stored}, {"qqokok"})
        # Thai and Lao vowel and tone marks (category Mn) stay; a combining accent is composed by NFC.
        kept = self.site.comment(self.a, "SC 101.1", text="\u0e19\u0e49\u0e33\t\u0e81\u0ec8\u0eb3 \u2713 e\u0301")
        self.assertEqual(kept.json["text"], "\u0e19\u0e49\u0e33\t\u0e81\u0ec8\u0eb3 \u2713 \u00e9")

    def test_bad_input_is_a_client_error(self):
        lone = self.site.call("POST", "/api/comments", raw=b'{"client_id": "s1", "book": "SC", "ch": "SC01", '
                              b'"a": "SC 101.1", "kind": "wording", "quote": "x\\ud83d", "text": "\\udc00ok"}',
                              token=self.a)
        self.assertEqual((lone.status, lone.json["quote"], lone.json["text"]), (201, "x", "ok"))
        huge = "9" * 30
        for method in ("PATCH", "DELETE"):
            r = self.site.call(method, f"/api/comments/{huge}", {"text": "x"}, token=self.a)
            self.assertEqual((r.status, r.json["error"]), (404, "no_comment"), method)
        r = self.site.call("POST", "/api/comments", raw=b"[" * 60000, token=self.a)
        self.assertEqual((r.status, r.json["error"]), (400, "bad_json"))
        for ids in ([2 ** 63], [0], [-1]):
            r = self.site.admin_call("POST", "/api/admin/processed", {"ids": ids})
            self.assertEqual((r.status, r.json["error"]), (400, "bad_ids"), ids)
        for i, (book, ch) in enumerate((("SC", "SC01\x00"), ("sc", "sc01"), ("SC", "SC" + "1" * 40))):
            body = {"client_id": f"b{i}", "book": book, "ch": ch, "a": "SC 101.1", "kind": "flag", "text": "x"}
            r = self.site.call("POST", "/api/comments", raw=json.dumps(body).encode(), token=self.a)
            self.assertEqual((r.status, r.json["error"]), (404, "no_chapter"), (book, ch))

    def test_closed_chapter_comments_cannot_change(self):
        cid = self.site.comment(self.b, "SC 103.1", ch="SC03", text="Before").json["id"]
        self.site.admin_call("POST", "/api/admin/processed", {"ids": [cid]})
        self.site.admin_call("DELETE", "/api/admin/chapters/SC/SC03")
        for method, body in (("PATCH", {"text": "edited after withdraw"}), ("DELETE", None)):
            r = self.site.call(method, f"/api/comments/{cid}", body, token=self.b)
            self.assertEqual((r.status, r.json["error"]), (404, "no_chapter"), method)
        self.site.publish(sample_chapter(3))
        rid = next(r["id"] for r in self.site.admin_call("GET", "/api/admin/readers").json["readers"]
                   if r["name"] == "Reader B")
        self.site.admin_call("PATCH", f"/api/admin/readers/{rid}", {"grants": ["SC01"]})
        self.assertEqual(self.site.call("PATCH", f"/api/comments/{cid}", {"text": "x"}, token=self.b).status, 404)
        self.assertEqual(self.site.call("DELETE", f"/api/comments/{cid}", token=self.b).status, 404)
        row = self.site.admin_call("GET", "/api/admin/export").json["comments"][0]
        self.assertEqual((row["text"], row["processed"]), ("Before", True))

    def test_deleted_ids_are_never_used_again(self):
        first = self.site.comment(self.a, "SC 101.1").json["id"]
        last = self.site.comment(self.a, "SC 101.2").json["id"]
        self.assertEqual(self.site.call("DELETE", f"/api/comments/{last}", token=self.a).status, 200)
        new = self.site.comment(self.b, "SC 101.1").json["id"]
        self.assertGreater(new, last)
        self.assertGreater(last, first)

    def test_edit_clears_processed(self):
        cid = self.site.comment(self.a, "SC 101.1").json["id"]
        self.site.admin_call("POST", "/api/admin/processed", {"ids": [cid]})
        self.assertTrue(self.site.call("GET", "/api/comments", token=self.a).json["comments"][0]["processed"])
        same = self.site.call("PATCH", f"/api/comments/{cid}", {"text": "A note"}, token=self.a).json
        self.assertTrue(same["processed"])
        changed = self.site.call("PATCH", f"/api/comments/{cid}", {"text": "Changed"}, token=self.a).json
        self.assertFalse(changed["processed"])

    def test_counts_place_and_finished(self):
        self.site.comment(self.a, "SC 101.1")
        self.site.comment(self.a, "SC 101.2")
        r = self.site.call("PUT", "/api/place", {"book": "SC", "ch": "SC01", "a": "SC 101.2"}, token=self.a)
        self.assertEqual(r.status, 200)
        r = self.site.call("PUT", "/api/finished", {"book": "SC", "ch": "SC01", "finished": True}, token=self.a)
        self.assertEqual((r.status, r.json["finished"]), (200, True))
        c = self.me(self.a)["chapters"][0]
        self.assertEqual((c["comments"], c["place"], c["finished"]), (2, "SC 101.2", True))
        self.site.call("PUT", "/api/finished", {"book": "SC", "ch": "SC01", "finished": False}, token=self.a)
        self.assertFalse(self.me(self.a)["chapters"][0]["finished"])
        self.assertEqual(self.me(self.b)["chapters"][0]["comments"], 0)
        bad = self.site.call("PUT", "/api/place", {"book": "SC", "ch": "SC01", "a": "SC 1.1"}, token=self.a)
        self.assertEqual(bad.status, 400)
        self.assertEqual(self.site.call("PUT", "/api/place", {"book": "SC", "ch": "SC03", "a": "SC 103.1"},
                                        token=self.a).status, 404)
        self.assertEqual(self.site.call("PUT", "/api/finished", {"book": "SC", "ch": "SC01", "finished": "yes"},
                                        token=self.a).status, 400)


class WithdrawAndRepublish(Base):
    def test_withdraw_keeps_comments_and_republish_restores(self):
        cid = self.site.comment(self.a, "SC 101.3", text="Keep me").json["id"]
        r = self.site.admin_call("DELETE", "/api/admin/chapters/SC/SC01")
        self.assertEqual((r.status, r.json["published"]), (200, False))
        self.assertNotIn("SC01", [c["id"] for c in self.me(self.a)["chapters"]])
        self.assertEqual(self.site.call("GET", "/api/chapter/SC/SC01", token=self.a).status, 404)
        self.assertEqual(self.site.comment(self.a, "SC 101.1").status, 404)
        listed = {c["id"]: c for c in self.site.admin_call("GET", "/api/admin/chapters").json["chapters"]}
        self.assertEqual((listed["SC01"]["published"], listed["SC01"]["comments"]), (False, 1))
        again = self.site.publish(sample_chapter(1))
        self.assertEqual((again["changed"], again["was_published"]), (False, False))
        self.assertEqual([c["id"] for c in self.site.call("GET", "/api/comments", token=self.a).json["comments"]],
                         [cid])

    def test_changed_chapter_keeps_comments_and_counts_orphans(self):
        old = self.site.call("GET", "/api/chapter/SC/SC01", token=self.a)
        self.site.comment(self.a, "SC 101.3", text="On the last paragraph")
        res = self.site.publish(sample_chapter(1, count=2, tag="v2"))
        self.assertEqual((res["changed"], res["orphans"]), (True, 1))
        self.assertNotEqual(res["version"], old.json["version"])
        new = self.site.call("GET", "/api/chapter/SC/SC01", token=self.a,
                             headers={"If-None-Match": old.headers["etag"]})
        self.assertEqual(new.status, 200)
        self.assertIn("(v2)", new.json["paragraphs"][0]["th"])
        self.assertEqual(len(self.site.call("GET", "/api/comments", token=self.a).json["comments"]), 1)
        export = self.site.admin_call("GET", "/api/admin/export").json["comments"]
        self.assertTrue(export[0]["anchor_missing"])

    def test_unknown_chapter_withdraw(self):
        self.assertEqual(self.site.admin_call("DELETE", "/api/admin/chapters/SC/SC77").status, 404)


class Limits(Base):
    def test_body_limit(self):
        big = {"client_id": "big", "book": "SC", "ch": "SC01", "a": "SC 101.1", "kind": "flag",
               "text": "x" * (65 * 1024)}
        r = self.site.call("POST", "/api/comments", big, token=self.a)
        self.assertEqual((r.status, r.json["error"]), (413, "too_large"))

    def test_chapter_upload_limit(self):
        ch = sample_chapter(5, count=40)
        for p in ch["paragraphs"]:
            p["en"] = "<p>" + "e" * 3000 + "</p>"
        self.assertGreater(len(json.dumps(ch)), 64 * 1024)
        self.assertEqual(self.site.admin_call("PUT", "/api/admin/chapters/SC/SC05", ch).status, 200)
        for p in ch["paragraphs"]:
            p["en"] = "<p>" + "e" * 110000 + "</p>"
        self.assertEqual(self.site.admin_call("PUT", "/api/admin/chapters/SC/SC05", ch).status, 413)

    def test_writes_per_minute(self):
        codes = []
        for i in range(61):
            r = self.site.call("PUT", "/api/place", {"book": "SC", "ch": "SC01", "a": "SC 101.1"}, token=self.a)
            codes.append(r.status)
        self.assertEqual(codes[:60], [200] * 60)
        self.assertEqual(codes[60], 429)
        self.assertGreater(int(r.headers["retry-after"]), 0)
        self.assertEqual(self.site.call("PUT", "/api/place", {"book": "SC", "ch": "SC01", "a": "SC 101.1"},
                                        token=self.b).status, 200)
        self.assertEqual(self.site.call("GET", "/api/me", token=self.a).status, 200)

    def test_comment_cap(self):
        rid = next(r["id"] for r in self.site.admin_call("GET", "/api/admin/readers").json["readers"]
                   if r["name"] == "Reader A")
        con = sqlite3.connect(self.site.data / db.DB_NAME)
        con.executemany("INSERT INTO comment (client_id, reader, book, ch, a, kind, text, created, updated)"
                        " VALUES (?, ?, 'SC', 'SC01', 'SC 101.1', 'flag', 'x', 'now', 'now')",
                        [(f"bulk-{i}", rid) for i in range(4999)])
        con.commit()
        con.close()
        self.assertEqual(self.site.comment(self.a, "SC 101.1").status, 201)
        r = self.site.comment(self.a, "SC 101.1")
        self.assertEqual((r.status, r.json["error"]), (403, "comment_limit"))
        self.assertEqual(self.site.comment(self.b, "SC 101.1").status, 201)


class ETags(Base):
    def test_not_modified(self):
        r = self.site.call("GET", "/api/chapter/SC/SC01", token=self.a)
        etag = r.headers["etag"]
        self.assertEqual(etag, '"' + r.json["version"] + '"')
        for sent in (etag, "W/" + etag, etag[:-1] + '-gzip"', '"other", ' + etag, "*"):
            again = self.site.call("GET", "/api/chapter/SC/SC01", token=self.a, headers={"If-None-Match": sent})
            self.assertEqual((again.status, again.body), (304, b""), sent)
            self.assertEqual(again.headers["etag"], etag)
        self.assertEqual(self.site.call("GET", "/api/chapter/SC/SC01", token=self.a,
                                        headers={"If-None-Match": '"stale"'}).status, 200)

    def test_english_readers_get_their_own_etag(self):
        a = self.site.call("GET", "/api/chapter/SC/SC01", token=self.a).headers["etag"]
        b = self.site.call("GET", "/api/chapter/SC/SC01", token=self.b).headers["etag"]
        self.assertEqual(b, a[:-1] + '.en"')
        self.assertEqual(self.site.call("GET", "/api/chapter/SC/SC01", token=self.b,
                                        headers={"If-None-Match": a}).status, 200)


class Export(Base):
    site_options = {"writes_per_minute": 10000}

    def test_export_content_and_processed(self):
        c1 = self.site.comment(self.a, "SC 101.2", kind="wording", quote="Paragraph 2 of", text="Better words").json
        c2 = self.site.comment(self.b, "SC 101.1", quote="not in the text", text="Odd").json
        c3 = self.site.comment(self.b, "SC 103.1", ch="SC03", text="Chapter three").json
        res = self.site.admin_call("GET", "/api/admin/export").json
        self.assertEqual([c["id"] for c in res["comments"]], [c2["id"], c1["id"], c3["id"]])
        first = res["comments"][1]
        for key, value in {"reader": "Reader A", "book": "SC", "ch": "SC01", "anchor": "SC 101.2", "kind": "wording",
                           "quote": "Paragraph 2 of", "text": "Better words", "processed": False,
                           "anchor_missing": False, "quote_found": True,
                           "th": "Paragraph 2 of chapter 1 (v1) word"}.items():
            self.assertEqual(first[key], value, key)
        self.assertEqual(first["version_seen"], first["version_now"])
        self.assertFalse(res["comments"][0]["quote_found"])
        self.assertEqual(res["comments"][0]["th"], "Paragraph 1 of chapter 1 (v1) word")
        self.assertEqual(res["comments"][0]["footnotes"], ["Note 1"])
        self.assertEqual(res["chapters"]["SC/SC01"]["title_th"], "Title 1")
        self.assertTrue(res["chapters"]["SC/SC01"]["published"])
        self.site.admin_call("DELETE", "/api/admin/chapters/SC/SC01")
        self.assertFalse(self.site.admin_call("GET", "/api/admin/export").json["chapters"]["SC/SC01"]["published"])
        self.site.publish(sample_chapter(1))
        only = self.site.admin_call("GET", "/api/admin/export?ch=SC03").json["comments"]
        self.assertEqual([c["id"] for c in only], [c3["id"]])
        r = self.site.admin_call("POST", "/api/admin/processed", {"ids": [c1["id"], 9999]})
        self.assertEqual(r.json, {"updated": 1, "missing": [9999], "changed": []})
        rest = self.site.admin_call("GET", "/api/admin/export?unprocessed=1").json["comments"]
        self.assertEqual(sorted(c["id"] for c in rest), sorted([c2["id"], c3["id"]]))
        mine = self.site.admin_call("GET", "/api/admin/export?reader=Reader%20A").json["comments"]
        self.assertEqual([c["id"] for c in mine], [c1["id"]])
        self.assertEqual(self.site.admin_call("POST", "/api/admin/processed", {"ids": "1"}).status, 400)

    def test_processed_only_as_exported(self):
        c = self.site.comment(self.a, "SC 101.1", text="sent as text/plain").json
        other = self.site.comment(self.b, "SC 101.2", text="unchanged").json
        exported = {x["id"]: x["rev"] for x in self.site.admin_call("GET", "/api/admin/export").json["comments"]}
        self.assertRegex(exported[c["id"]], r"^[0-9a-f]{12}$")
        self.site.call("PATCH", f"/api/comments/{c['id']}", {"text": "changed my mind"}, token=self.a)
        r = self.site.admin_call("POST", "/api/admin/processed", {
            "ids": [c["id"], other["id"]], "revs": {str(k): v for k, v in exported.items()}})
        self.assertEqual(r.json, {"updated": 1, "missing": [], "changed": [c["id"]]})
        now = {x["id"]: x for x in self.site.admin_call("GET", "/api/admin/export").json["comments"]}
        self.assertEqual((now[c["id"]]["processed"], now[other["id"]]["processed"]), (False, True))
        self.assertNotEqual(now[c["id"]]["rev"], exported[c["id"]])
        # A reused id would carry another rev, so this guard also covers it.
        r = self.site.admin_call("POST", "/api/admin/processed", {"ids": [c["id"]], "revs": {str(c["id"]): "0" * 12}})
        self.assertEqual(r.json["changed"], [c["id"]])

    def test_export_names_the_source_files(self):
        ch = sample_chapter(1)
        ch["sources"] = ["th/SC/03_public/SC01_th.typ", "th/SC/00_source/SC01_en.md"]
        self.site.publish(ch)
        self.site.comment(self.a, "SC 101.1")
        info = self.site.admin_call("GET", "/api/admin/export").json["chapters"]["SC/SC01"]
        self.assertEqual((info["source_th"], info["source_en"], info["commit"]),
                         ("th/SC/03_public/SC01_th.typ", "th/SC/00_source/SC01_en.md", "abc1234"))
        for bad in (["../etc/passwd"], ["/abs"], ["a b"], "x", ["a", "b", "c"]):
            ch["sources"] = bad
            r = self.site.admin_call("PUT", "/api/admin/chapters/SC/SC01", ch)
            self.assertEqual((r.status, r.json["error"]), (400, "bad_field"), bad)


class Migrations(unittest.TestCase):
    def setUp(self):
        import tempfile
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = f"{tmp.name}/review.sqlite3"

    def version_1(self):
        """A database as the first build made it, holding one comment."""
        con = sqlite3.connect(self.path)
        con.executescript(db.SCHEMA.read_text())
        con.executescript("""
            INSERT INTO book (id) VALUES ('SC');
            INSERT INTO chapter (book, id, n, title_th, title_en, version, content_hash, count, paragraphs, updated)
              VALUES ('SC', 'SC01', 1, 't', 'e', 'v', 'h', 1, '[]', 'now');
            INSERT INTO reader (name, code_hash, created) VALUES ('R', 'x', 'now');
            INSERT INTO comment (id, client_id, reader, book, ch, a, kind, text, created, updated)
              VALUES (7, 'c7', 1, 'SC', 'SC01', 'SC 1.1', 'flag', 'kept', 'now', 'now');""")
        con.close()

    def test_old_database_is_brought_up_to_date(self):
        self.version_1()
        db.init_db(self.path)
        con = sqlite3.connect(self.path)
        self.assertEqual(con.execute("PRAGMA user_version").fetchone()[0], db.MIGRATIONS[-1][0])
        self.assertEqual(con.execute("SELECT id, text FROM comment").fetchall(), [(7, "kept")])
        self.assertIn("AUTOINCREMENT", con.execute("SELECT sql FROM sqlite_master WHERE name = 'comment'").fetchone()[0])
        self.assertEqual(con.execute("SELECT source_th, source_commit FROM chapter").fetchone(), ("", ""))
        con.execute("DELETE FROM comment")
        con.execute("INSERT INTO comment (client_id, reader, book, ch, a, kind, text, created, updated)"
                    " VALUES ('c8', 1, 'SC', 'SC01', 'SC 1.1', 'flag', 'new', 'now', 'now')")
        self.assertEqual(con.execute("SELECT id FROM comment").fetchone()[0], 8)
        con.close()
        db.init_db(self.path)   # a second start changes nothing

    def test_a_failing_migration_changes_nothing(self):
        from unittest import mock
        self.version_1()
        broken = db.MIGRATIONS + [(99, ["ALTER TABLE reader ADD COLUMN note TEXT", "SELECT * FROM no_such_table"])]
        with mock.patch.object(db, "MIGRATIONS", broken), self.assertRaises(sqlite3.OperationalError):
            db.init_db(self.path)
        con = sqlite3.connect(self.path)
        self.assertEqual(con.execute("PRAGMA user_version").fetchone()[0], 1)
        self.assertNotIn("AUTOINCREMENT", con.execute("SELECT sql FROM sqlite_master WHERE name = 'comment'").fetchone()[0])
        self.assertNotIn("note", [r[1] for r in con.execute("PRAGMA table_info(reader)")])
        con.close()


class AdminChapters(Base):
    def test_refuses_bad_uploads(self):
        def put(change, cid="SC04"):
            ch = sample_chapter(4)
            change(ch)
            return self.site.admin_call("PUT", f"/api/admin/chapters/SC/{cid}", ch)

        def para(key, value):
            return lambda ch: ch["paragraphs"][0].__setitem__(key, value)

        cases = [(para("th", "<script>x</script>"), "unsafe_html"),
                 (para("en", '<p onclick="x">a</p>'), "unsafe_html"),
                 (para("th", "Thai digit \u0e51"), "forbidden_character"),
                 (para("fn", ["zero\u200bwidth"]), "forbidden_character"),
                 (para("a", "not an anchor"), "bad_anchor"),
                 (lambda ch: ch["paragraphs"].append(dict(ch["paragraphs"][0])), "bad_anchor"),
                 (lambda ch: ch.update(paragraphs=[]), "bad_paragraphs"),
                 (lambda ch: ch.update(commit="not hex!"), "bad_field"),
                 (lambda ch: ch.update(title_th=""), "bad_field")]
        for change, error in cases:
            r = put(change)
            self.assertEqual((r.status, r.json["error"]), (400, error), error)
        self.assertEqual(put(lambda ch: None, cid="GC04").json["error"], "bad_chapter")

    def test_republish_same_content_keeps_version(self):
        v1 = self.site.publish(sample_chapter(2))
        self.assertEqual((v1["changed"], v1["was_published"]), (False, True))
        ch = sample_chapter(2)
        ch["commit"] = "def5678"
        self.assertFalse(self.site.publish(ch)["changed"])

    def test_readers_listing(self):
        r = self.site.admin_call("GET", "/api/admin/readers").json["readers"]
        self.assertEqual([x["name"] for x in r], ["Reader A", "Reader B"])
        self.assertEqual(r[0]["grants"], ["SC01", "SC02"])
        self.assertEqual(r[1]["grants"], ["SC"])
        self.assertNotIn("code", r[0])
        self.assertNotIn("code_hash", r[0])
        dup = self.site.admin_call("POST", "/api/admin/readers", {"name": "reader a", "grants": ["SC"]})
        self.assertEqual((dup.status, dup.json["error"]), (409, "name_taken"))
        invite = self.site.invite("Reader C", ["SC01"])
        self.assertEqual(invite["link"], "https://review.example.org/#k=" + invite["code"])


@unittest.skipIf(REPO is None, "the translation repository is not found; set REVIEW_REPO")
class RealChapters(unittest.TestCase):
    def test_publish_sc01_to_sc08(self):
        site = Site()
        self.addCleanup(site.close)
        read = git_reader(REPO)
        for n in SC_COUNTS:
            ch = sc_typst.load_chapter(SC_BOOK, n, read)
            site.publish({k: ch[k] for k in ("n", "title_th", "title_en", "paragraphs")})
        code = site.invite("Translator", ["SC"], english=True)["code"]
        me = site.call("GET", "/api/me", token=code).json
        self.assertEqual(sum(c["paragraphs"] for c in me["chapters"]), 149)
        body = site.call("GET", "/api/chapter/SC/SC03", token=code).json
        self.assertEqual(len(body["paragraphs"]), 37)
        a = body["paragraphs"][0]["a"]
        words = re.sub(r"<[^>]+>", "", body["paragraphs"][0]["th"]).split()[0]
        r = site.comment(code, a, ch="SC03", kind="wording", quote=words, text="Try other words")
        self.assertEqual(r.status, 201)
        export = site.admin_call("GET", "/api/admin/export").json["comments"][0]
        self.assertTrue(export["quote_found"])
        self.assertNotIn("<", export["th"])


if __name__ == "__main__":
    unittest.main()
