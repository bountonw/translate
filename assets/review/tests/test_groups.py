"""Tests for groups, the access rule, many readers at once, and the reader list's filters."""
import sqlite3
import unittest

from helpers import Site, sample_chapter

from server import db


class Base(unittest.TestCase):
    def setUp(self):
        self.site = Site(writes_per_minute=10000)
        self.addCleanup(self.site.close)
        for n in (1, 2, 3, 4):
            self.site.publish(sample_chapter(n))
        self.site.publish(sample_chapter(1, book="GC"), book="GC")

    def admin(self, method, path, body=None, status=200):
        r = self.site.admin_call(method, path, body)
        self.assertEqual(r.status, status, r.body)
        return r.json

    def group(self, name, grants=(), english=False):
        return self.admin("POST", "/api/admin/groups", {"name": name, "grants": list(grants), "english": english},
                          201)

    def reader(self, name, grants=(), groups=(), english=False):
        r = self.site.admin_call("POST", "/api/admin/readers", {"name": name, "grants": list(grants),
                                                                 "groups": list(groups), "english": english})
        self.assertEqual(r.status, 201, r.body)
        return r.json

    def open_chapters(self, code):
        r = self.site.call("GET", "/api/me", token=code)
        self.assertEqual(r.status, 200, r.body)
        return [c["id"] for c in r.json["chapters"]]


class AccessRule(Base):
    def test_own_grants_and_group_grants_add_up(self):
        g = self.group("Pastors", ["SC03-04"])
        r = self.reader("Anan", ["SC01"], ["Pastors"])
        self.assertEqual(r["groups"], ["Pastors"])
        self.assertEqual(self.open_chapters(r["code"]), ["SC01", "SC03", "SC04"])
        self.assertEqual(self.site.call("GET", "/api/chapter/SC/SC03", token=r["code"]).status, 200)
        self.assertEqual(self.site.call("GET", "/api/chapter/SC/SC02", token=r["code"]).status, 404)
        # Switching the group off closes its chapters at once; the reader's own grant stays.
        self.admin("PATCH", f"/api/admin/groups/{g['id']}", {"active": False})
        self.assertEqual(self.open_chapters(r["code"]), ["SC01"])
        w = self.site.comment(r["code"], "SC 103.1", ch="SC03")
        self.assertEqual((w.status, w.json["error"]), (404, "no_chapter"))
        self.admin("PATCH", f"/api/admin/groups/{g['id']}", {"active": True})
        self.assertEqual(self.open_chapters(r["code"]), ["SC01", "SC03", "SC04"])

    def test_whole_book_group_grant_covers_later_chapters_of_that_book_only(self):
        self.group("All", ["SC"])
        r = self.reader("Boon", groups=["all"])
        self.assertEqual(self.open_chapters(r["code"]), ["SC01", "SC02", "SC03", "SC04"])
        self.site.publish(sample_chapter(9))
        self.assertIn("SC09", self.open_chapters(r["code"]))
        self.assertEqual(self.site.call("GET", "/api/chapter/GC/GC01", token=r["code"]).status, 404)

    def test_revoked_reader_opens_nothing_whatever_the_groups_say(self):
        self.group("All", ["SC", "GC"])
        r = self.reader("Chai", groups=["All"])
        self.admin("PATCH", f"/api/admin/readers/{r['id']}", {"active": False})
        for path in ("/api/me", "/api/chapter/SC/SC01", "/api/comments"):
            res = self.site.call("GET", path, token=r["code"])
            self.assertEqual((res.status, res.json["error"]), (401, "bad_code"), path)

    def test_two_groups_and_removing_one(self):
        a = self.group("A", ["SC01"])
        self.group("B", ["SC02"])
        r = self.reader("Dao", groups=["A", "B"])
        self.assertEqual(self.open_chapters(r["code"]), ["SC01", "SC02"])
        res = self.admin("DELETE", f"/api/admin/groups/{a['id']}")
        self.assertEqual((res["name"], res["members"]), ("A", 1))
        self.assertEqual(self.open_chapters(r["code"]), ["SC02"])
        self.assertEqual(self.admin("GET", f"/api/admin/readers?name=Dao")["readers"][0]["groups"], ["B"])
        self.admin("DELETE", f"/api/admin/groups/{a['id']}", status=404)

    def test_members_added_and_taken_out(self):
        g = self.group("Youth", ["SC02"])
        r1, r2 = self.reader("Ek", ["SC01"]), self.reader("Fon", ["SC01"])
        res = self.admin("POST", f"/api/admin/groups/{g['id']}/members", {"add": [r1["id"], r2["id"]]})
        self.assertEqual([m["name"] for m in res["members"]], ["Ek", "Fon"])
        self.assertEqual(self.open_chapters(r2["code"]), ["SC01", "SC02"])
        res = self.admin("POST", f"/api/admin/groups/{g['id']}/members", {"remove": [r2["id"]]})
        self.assertEqual([m["name"] for m in res["members"]], ["Ek"])
        self.assertEqual(self.open_chapters(r2["code"]), ["SC01"])
        self.admin("POST", f"/api/admin/groups/{g['id']}/members", {"add": [99999]}, status=404)
        self.admin("POST", f"/api/admin/groups/{g['id']}/members", {"add": ["x"]}, status=400)

    def test_group_names_and_grants_are_checked(self):
        for bad in ("", "has space", "-start", "x" * 41, "\u0e44\u0e17\u0e22"):
            r = self.site.admin_call("POST", "/api/admin/groups", {"name": bad})
            self.assertEqual((r.status, r.json["error"]), (400, "bad_group_name"), bad)
        self.group("Pastors")
        r = self.site.admin_call("POST", "/api/admin/groups", {"name": "pastors"})
        self.assertEqual((r.status, r.json["error"]), (409, "group_taken"))
        r = self.site.admin_call("POST", "/api/admin/groups", {"name": "X", "grants": ["SC3-1"]})
        self.assertEqual((r.status, r.json["error"]), (400, "bad_grants"))
        r = self.site.admin_call("POST", "/api/admin/readers", {"name": "Gun", "groups": ["Nobody"]})
        self.assertEqual((r.status, r.json["error"]), (400, "no_group"))

    def test_groups_listing(self):
        self.group("Pastors", ["SC01-02", "GC"], english=True)
        self.reader("Hong", groups=["Pastors"])
        (g,) = self.admin("GET", "/api/admin/groups")["groups"]
        self.assertEqual((g["name"], g["active"], g["english"], g["grants"]), ("Pastors", True, True,
                                                                              ["GC", "SC01", "SC02"]))
        self.assertEqual(g["settings"], {"english.on": True})
        self.assertEqual([m["name"] for m in g["members"]], ["Hong"])


class English(Base):
    """English is on when the reader's own setting or any active group's setting turns it on."""

    def english(self, code):
        me = self.site.call("GET", "/api/me", token=code).json
        self.assertEqual(me["english"], me["features"]["english"]["on"])
        para = self.site.call("GET", "/api/chapter/SC/SC01", token=code).json["paragraphs"][0]
        self.assertEqual("en" in para, me["english"])
        return me["english"]

    def test_combination(self):
        g = self.group("Readers", ["SC"])
        r = self.reader("Ice", groups=["Readers"])
        self.assertFalse(self.english(r["code"]))
        self.admin("PATCH", f"/api/admin/groups/{g['id']}", {"english": True})
        self.assertTrue(self.english(r["code"]))
        # The reader's own "off" does not override a group that turns it on.
        self.admin("PATCH", f"/api/admin/readers/{r['id']}", {"english": False})
        self.assertTrue(self.english(r["code"]))
        listed = self.admin("GET", "/api/admin/readers?name=Ice")["readers"][0]
        self.assertEqual((listed["english"], listed["settings"], listed["effective"]["english.on"]),
                         (True, {"english.on": False}, True))
        # A group switched off gives nothing, settings included.
        self.admin("PATCH", f"/api/admin/groups/{g['id']}", {"active": False})
        self.assertEqual(self.site.call("GET", "/api/me", token=r["code"]).json["chapters"], [])
        self.admin("PATCH", f"/api/admin/groups/{g['id']}", {"active": True, "settings": {"english.on": False}})
        self.assertFalse(self.english(r["code"]))
        self.admin("PATCH", f"/api/admin/readers/{r['id']}", {"settings": {"english.on": True}})
        self.assertTrue(self.english(r["code"]))

    def test_etag_follows_the_setting(self):
        r = self.reader("Jan", ["SC"])
        first = self.site.call("GET", "/api/chapter/SC/SC01", token=r["code"]).headers["etag"]
        self.group("En", english=True)
        self.admin("PATCH", f"/api/admin/readers/{r['id']}", {"groups": ["En"]})
        again = self.site.call("GET", "/api/chapter/SC/SC01", token=r["code"], headers={"If-None-Match": first})
        self.assertEqual(again.status, 200)
        self.assertTrue(again.headers["etag"].endswith('.en"'))

    def test_unknown_setting_and_bad_value(self):
        r = self.reader("Kai", ["SC"])
        res = self.site.admin_call("PATCH", f"/api/admin/readers/{r['id']}", {"settings": {"bible.on": True}})
        self.assertEqual((res.status, res.json["error"]), (400, "unknown_setting"))
        res = self.site.admin_call("PATCH", f"/api/admin/readers/{r['id']}", {"settings": {"english.on": "yes"}})
        self.assertEqual((res.status, res.json["error"]), (400, "bad_setting"))
        res = self.site.admin_call("PATCH", f"/api/admin/readers/{r['id']}", {"settings": ["english.on"]})
        self.assertEqual((res.status, res.json["error"]), (400, "bad_setting"))


class ManyReaders(Base):
    def test_batch_creates_all_or_none(self):
        self.group("Pastors", ["SC01"])
        rows = [{"name": f"Reader {i:03d}", "groups": ["Pastors"] if i % 2 else [], "grants": ["SC02"],
                 "english": i % 3 == 0} for i in range(300)]
        res = self.admin("POST", "/api/admin/readers/batch", {"readers": rows}, 201)
        self.assertEqual(len(res["readers"]), 300)
        first = res["readers"][1]
        self.assertEqual(first["name"], "Reader 001")
        self.assertEqual(first["link"], "https://review.example.org/#k=" + first["code"])
        self.assertEqual(self.open_chapters(first["code"]), ["SC01", "SC02"])
        self.assertEqual(self.open_chapters(res["readers"][0]["code"]), ["SC02"])
        self.assertEqual(self.admin("GET", "/api/admin/readers")["total"], 300)
        # One bad row stops every row, and the answer names every problem.
        bad = [{"name": "New one", "grants": ["SC01"]}, {"name": "Reader 005"}, {"name": "x", "groups": ["Nope"]},
               {"name": "Twice"}, {"name": "twice"}, {"name": "", "grants": []}]
        r = self.site.admin_call("POST", "/api/admin/readers/batch", {"readers": bad})
        self.assertEqual((r.status, r.json["error"]), (400, "bad_readers"))
        self.assertEqual(len(r.json["problems"]), 4, r.json)
        self.assertIn("Row 2: A reader named Reader 005 already exists.", r.json["problems"])
        self.assertEqual(self.admin("GET", "/api/admin/readers")["total"], 300)
        self.assertEqual(self.admin("GET", "/api/admin/readers?name=New one")["readers"], [])
        r = self.site.admin_call("POST", "/api/admin/readers/batch", {"readers": [{"name": "Reader 007"}]})
        self.assertEqual((r.status, r.json["error"]), (409, "name_taken"))

    def test_bulk_change_and_new_codes(self):
        made = self.admin("POST", "/api/admin/readers/batch",
                          {"readers": [{"name": f"R{i}", "grants": ["SC01"]} for i in range(5)]}, 201)["readers"]
        ids = [r["id"] for r in made]
        res = self.admin("PATCH", "/api/admin/readers", {"changes": [{"id": i, "active": False} for i in ids[:3]]})
        self.assertEqual([r["active"] for r in res["readers"]], [False] * 3)
        self.assertEqual(self.site.call("GET", "/api/me", token=made[0]["code"]).status, 401)
        self.assertEqual(self.site.call("GET", "/api/me", token=made[4]["code"]).status, 200)
        # A change naming an unknown reader changes nobody.
        r = self.site.admin_call("PATCH", "/api/admin/readers", {"changes": [{"id": ids[4], "active": False},
                                                                             {"id": 99999, "active": False}]})
        self.assertEqual((r.status, r.json["error"]), (404, "no_reader"))
        self.assertEqual(self.site.call("GET", "/api/me", token=made[4]["code"]).status, 200)
        res = self.admin("POST", "/api/admin/readers/codes", {"ids": ids[3:]})
        self.assertEqual([r["name"] for r in res["readers"]], ["R3", "R4"])
        self.assertEqual(self.site.call("GET", "/api/me", token=made[4]["code"]).status, 401)
        self.assertEqual(self.site.call("GET", "/api/me", token=res["readers"][1]["code"]).status, 200)
        self.admin("POST", "/api/admin/readers/codes", {"ids": []}, status=400)

    def test_filters(self):
        self.group("Pastors", ["GC"])
        a = self.reader("Lek", ["SC01"])
        self.reader("Mai", groups=["Pastors"])
        c = self.reader("Nok", ["SC02"], ["Pastors"])
        self.site.comment(a["code"], "SC 101.1")
        self.admin("PATCH", f"/api/admin/readers/{c['id']}", {"active": False})
        names = lambda q: [r["name"] for r in self.admin("GET", "/api/admin/readers" + q)["readers"]]  # noqa: E731
        self.assertEqual(names(""), ["Lek", "Mai", "Nok"])
        self.assertEqual(names("?group=pastors"), ["Mai", "Nok"])
        self.assertEqual(names("?book=GC"), ["Mai"])        # Nok is revoked, so Nok reaches no book
        self.assertEqual(names("?book=sc"), ["Lek"])
        self.assertEqual(names("?idle=0"), ["Mai", "Nok"])
        self.assertEqual(names("?idle=30"), ["Mai", "Nok"])
        self.assertEqual(names("?revoked=1"), ["Nok"])
        self.assertEqual(names("?group=Pastors&revoked=1"), ["Nok"])
        self.assertEqual(self.admin("GET", "/api/admin/readers?group=Pastors")["total"], 3)
        self.admin("GET", "/api/admin/readers?group=Nobody", status=400)
        self.admin("GET", "/api/admin/readers?idle=x", status=400)
        # A switched-off group's book no longer counts for --book.
        g = self.admin("GET", "/api/admin/groups")["groups"][0]
        self.admin("PATCH", f"/api/admin/groups/{g['id']}", {"active": False})
        self.assertEqual(names("?book=GC"), [])
        # An old activity counts as quiet for idle=N.
        con = sqlite3.connect(self.site.data / db.DB_NAME)
        con.execute("UPDATE comment SET updated = '2020-01-01T00:00:00Z'")
        con.commit()
        con.close()
        self.assertEqual(names("?idle=30"), ["Lek", "Mai", "Nok"])
        self.assertEqual(names("?idle=0"), ["Mai", "Nok"])


class ReaderNames(Base):
    def test_a_name_that_a_spreadsheet_would_run_or_that_breaks_a_line_is_refused(self):
        for bad in ("=HYPERLINK(\"x\")", "+1", "-x", "@SUM(1)", "Eve\n**999. Wording**", "Eve\tx"):
            r = self.site.admin_call("POST", "/api/admin/readers", {"name": bad, "grants": ["SC01"]})
            self.assertEqual((r.status, r.json["error"]), (400, "bad_name"), bad)
        r = self.site.admin_call("POST", "/api/admin/readers/batch", {"readers": [
            {"name": "Good One", "grants": ["SC01"]}, {"name": "=1+1", "grants": ["SC01"]}]})
        self.assertEqual(r.status, 400)
        self.assertIn("Row 2: A reader name may not hold a line break or a tab", r.json["problems"][0])
        ok = self.reader("Somchai-Jaidee", ["SC01"])
        res = self.site.admin_call("PATCH", f"/api/admin/readers/{ok['id']}", {"name": "@Somchai"})
        self.assertEqual((res.status, res.json["error"]), (400, "bad_name"))


class FindingReaders(Base):
    def test_part_of_a_name_and_a_link(self):
        a = self.reader("Somchai Jaidee", ["SC01"])
        self.reader("Somsak", ["SC01"])
        names = lambda q: [r["name"] for r in self.admin("GET", "/api/admin/readers" + q)["readers"]]  # noqa: E731
        self.assertEqual(names("?contains=somchai"), ["Somchai Jaidee"])
        self.assertEqual(names("?contains=som"), ["Somchai Jaidee", "Somsak"])
        self.assertEqual(names("?code_hash=" + db.sha256(a["code"])), ["Somchai Jaidee"])
        self.assertEqual(names("?code_hash=" + db.sha256("not-a-code-of-anyone")), [])


class Books(Base):
    def test_books_name_what_an_active_reader_can_open_now(self):
        g = self.group("Pastors", ["GC"])
        a = self.reader("Lek", ["SC02"], ["Pastors"])
        listed = lambda: self.admin("GET", "/api/admin/readers?name=Lek")["readers"][0]["books"]  # noqa: E731
        self.assertEqual(listed(), ["GC", "SC"])
        self.admin("DELETE", "/api/admin/chapters/SC/SC02")          # Lek's only SC chapter is withdrawn
        self.assertEqual(listed(), ["GC"])
        self.admin("PATCH", f"/api/admin/groups/{g['id']}", {"active": False})
        self.assertEqual(listed(), [])
        self.site.publish(sample_chapter(2))
        self.assertEqual(listed(), ["SC"])
        self.admin("PATCH", f"/api/admin/readers/{a['id']}", {"active": False})
        self.assertEqual(listed(), [])                                 # a revoked reader opens nothing
        self.assertEqual(self.admin("GET", "/api/admin/readers?book=SC")["readers"], [])


class Members(Base):
    def test_the_answer_says_what_changed(self):
        g = self.group("Youth", ["SC01"])
        a, b, c = self.reader("Ann", ["SC02"]), self.reader("Ben", ["SC02"]), self.reader("Cat", ["SC02"])
        res = self.admin("POST", f"/api/admin/groups/{g['id']}/members", {"add": [a["id"], b["id"]]})
        self.assertEqual((res["added"], res["already"]), ([a["id"], b["id"]], []))
        res = self.admin("POST", f"/api/admin/groups/{g['id']}/members", {"add": [a["id"], c["id"]]})
        self.assertEqual((res["added"], res["already"]), ([c["id"]], [a["id"]]))
        res = self.admin("POST", f"/api/admin/groups/{g['id']}/members", {"remove": [b["id"], b["id"] + 0]})
        self.assertEqual((res["removed"], res["not_members"]), ([b["id"]], []))
        res = self.admin("POST", f"/api/admin/groups/{g['id']}/members", {"remove": [b["id"]]})
        self.assertEqual((res["removed"], res["not_members"]), ([], [b["id"]]))
        self.assertEqual([m["name"] for m in res["members"]], ["Ann", "Cat"])


if __name__ == "__main__":
    unittest.main()
