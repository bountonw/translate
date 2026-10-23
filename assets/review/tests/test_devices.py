"""Tests for one person per link: the page sends a random device key, a link works on the first two devices that
open it, a further device waits for the translator's approval, and the admin routes list, approve and remove
devices and flag a link on more than two devices. The reader number in /api/me lets the page send the waiting
comments of an old link under a new one."""
import unittest

from helpers import Site, sample_chapter

from server import app as app_module
from server import db


def device(n):
    return {"X-Review-Device": f"phone-or-laptop-{n:04d}"}


class Devices(unittest.TestCase):
    def setUp(self):
        self.site = Site(writes_per_minute=10000)
        self.addCleanup(self.site.close)
        self.site.publish(sample_chapter(1))
        r = self.site.invite("Anan", ["SC"])
        self.code, self.rid = r["code"], r["id"]

    def me(self, n, code=None):
        return self.site.call("GET", "/api/me", token=code or self.code,
                              headers=dict(device(n), **{"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 12_5 like "
                                                                       "Mac OS X) AppleWebKit Version/12.1 Safari/605.1"}))

    def devices(self, **query):
        q = "&".join(f"{k}={v}" for k, v in query.items())
        return self.site.admin_call("GET", "/api/admin/devices" + (f"?{q}" if q else "")).json["devices"]

    def test_the_first_two_devices_work_and_a_third_waits(self):
        self.assertEqual([self.me(n).status for n in (1, 2, 1, 2)], [200, 200, 200, 200])
        r = self.me(3)
        self.assertEqual((r.status, r.json["error"]), (403, "device_waiting"))
        self.assertEqual(app_module.ACCESS_ERRORS["device_waiting"][0], 403)
        # Every route refuses the waiting device, writes too; the first two go on.
        body = {"client_id": "c1", "book": "SC", "ch": "SC01", "a": "SC 101.1", "kind": "flag", "text": "x"}
        self.assertEqual(self.site.call("POST", "/api/comments", body, token=self.code, headers=device(3)).status, 403)
        self.assertEqual(self.site.call("GET", "/api/chapter/SC/SC01", token=self.code, headers=device(3)).status, 403)
        self.assertEqual(self.site.call("POST", "/api/comments", body, token=self.code, headers=device(1)).status, 201)
        listed = self.devices(reader=self.rid)
        self.assertEqual([d["state"] for d in listed], ["ok", "ok", "waiting"])
        self.assertEqual(listed[0]["agent"], "iPhone, Safari")
        self.assertEqual({d["name"] for d in listed}, {"Anan"})
        self.assertTrue(all(d["current"] for d in listed))
        self.assertEqual([d["id"] for d in self.devices(state="waiting")], [listed[2]["id"]])

    def test_the_admin_list_flags_a_link_on_more_than_two_devices(self):
        other = self.site.invite("Mali", ["SC"])["code"]
        for n in (1, 2, 3):
            self.me(n)
        self.me(1, other)
        readers = {r["name"]: r for r in self.site.admin_call("GET", "/api/admin/readers").json["readers"]}
        self.assertEqual(readers["Anan"]["devices"], {"total": 3, "ok": 2, "waiting": 1, "removed": 0, "full": False})
        self.assertEqual(readers["Mali"]["devices"], {"total": 1, "ok": 1, "waiting": 0, "removed": 0, "full": False})
        flagged = self.site.admin_call("GET", "/api/admin/readers?devices=1").json["readers"]
        self.assertEqual([r["name"] for r in flagged], ["Anan"])

    def test_approve_and_remove(self):
        for n in (1, 2, 3):
            self.me(n)
        third = self.devices(state="waiting")[0]["id"]
        r = self.site.admin_call("PATCH", "/api/admin/devices", {"ids": [third, 999], "state": "ok"})
        self.assertEqual((r.status, r.json["missing"], r.json["devices"][0]["state"]), (200, [999], "ok"))
        self.assertIsNotNone(r.json["devices"][0]["changed"])
        self.assertEqual(self.me(3).status, 200)
        first = self.devices(reader=self.rid)[0]["id"]
        self.site.admin_call("PATCH", "/api/admin/devices", {"ids": [first], "state": "removed"})
        r = self.me(1)
        self.assertEqual((r.status, r.json["error"]), (403, "device_waiting"))
        # A removed device frees no place: a new device still waits, since the link has met two already.
        self.assertEqual(self.me(4).json["error"], "device_waiting")
        for bad in ({"ids": [first], "state": "waiting"}, {"ids": [], "state": "ok"}, {"ids": "1", "state": "ok"}):
            self.assertEqual(self.site.admin_call("PATCH", "/api/admin/devices", bad).status, 400, bad)

    def test_a_removed_device_that_comes_back_waits_and_is_listed_as_waiting(self):
        for n in (1, 2):
            self.me(n)
        second = self.devices(reader=self.rid)[1]["id"]
        r = self.site.admin_call("PATCH", "/api/admin/devices", {"ids": [second], "state": "removed"})
        self.assertEqual(r.json["unchanged"], [])
        self.assertEqual(self.devices(state="waiting"), [])
        r = self.me(2)
        self.assertEqual((r.status, r.json["error"], r.json["device"]), (403, "device_waiting", second))
        waiting = self.devices(state="waiting")
        self.assertEqual([d["id"] for d in waiting], [second])
        self.assertIsNotNone(waiting[0]["changed"])
        flagged = self.site.admin_call("GET", "/api/admin/readers?devices=1").json["readers"]
        self.assertEqual([(r["name"], r["devices"]["waiting"]) for r in flagged], [("Anan", 1)])
        # Approved again, it works; removed again, it waits again.
        self.site.admin_call("PATCH", "/api/admin/devices", {"ids": [second], "state": "ok"})
        self.assertEqual(self.me(2).status, 200)

    def test_a_waiting_device_is_told_its_number(self):
        for n in (1, 2):
            self.assertNotIn("device", self.me(n).json)
        r = self.me(3)
        self.assertEqual(r.json["device"], self.devices(state="waiting")[0]["id"])

    def test_a_link_keeps_at_most_ten_devices_waiting(self):
        for n in range(1, 3 + app_module.WAITING_MOST):
            self.me(n)
        self.assertEqual(len(self.devices(state="waiting")), app_module.WAITING_MOST)
        rows = len(self.devices(reader=self.rid))
        # Further new devices wait too, but none is recorded, so no link can fill the disk with devices.
        for n in range(100, 140):
            r = self.me(n)
            self.assertEqual((r.status, r.json["error"], r.json["device"]), (403, "device_waiting", None))
        self.assertEqual(len(self.devices(reader=self.rid, all=1)), rows)
        # The reader's devices that work go on working, and the reader's row says the link needs replacing.
        self.assertEqual(self.me(1).status, 200)
        anan = self.site.admin_call("GET", "/api/admin/readers?devices=1").json["readers"][0]
        self.assertTrue(anan["devices"]["full"])
        # Removing a waiting device makes room for one more; a new link starts a new count.
        first_waiting = self.devices(state="waiting")[0]["id"]
        self.site.admin_call("PATCH", "/api/admin/devices", {"ids": [first_waiting], "state": "removed"})
        self.assertIsNotNone(self.me(200).json["device"])
        self.assertIsNone(self.me(201).json["device"])
        new = self.site.admin_call("POST", f"/api/admin/readers/{self.rid}/code").json["code"]
        self.assertEqual([self.me(n, new).status for n in (300, 301, 302)], [200, 200, 403])
        anan = self.site.admin_call("GET", "/api/admin/readers").json["readers"][0]
        self.assertFalse(anan["devices"]["full"])

    def test_approving_an_approved_device_changes_nothing(self):
        for n in (1, 2, 3):
            self.me(n)
        ids = [d["id"] for d in self.devices(reader=self.rid)]
        r = self.site.admin_call("PATCH", "/api/admin/devices", {"ids": ids, "state": "ok"})
        self.assertEqual(r.json["unchanged"], ids[:2])
        r = self.site.admin_call("PATCH", "/api/admin/devices", {"ids": [ids[2]], "state": "ok"})
        self.assertEqual(r.json["unchanged"], [ids[2]])

    def test_the_reader_list_names_the_number_of_devices_a_link_works_on(self):
        self.assertEqual(self.site.admin_call("GET", "/api/admin/readers").json["devices_per_link"], 2)

    def test_a_new_link_starts_a_new_count_and_keeps_the_reader_number(self):
        for n in (1, 2, 3):
            self.me(n)
        before = self.me(1).json["id"]
        self.assertEqual(before, self.rid)
        new = self.site.admin_call("POST", f"/api/admin/readers/{self.rid}/code").json["code"]
        self.assertEqual(self.me(1).status, 401)
        # The old link's devices stay in the record, and the new link works on the first two that open it.
        self.assertEqual([self.me(n, new).status for n in (3, 4, 5)], [200, 200, 403])
        self.assertEqual(self.me(3, new).json["id"], before)
        self.assertEqual(len(self.devices(reader=self.rid)), 3)
        self.assertEqual(len(self.devices(reader=self.rid, all=1)), 6)
        readers = self.site.admin_call("GET", "/api/admin/readers").json["readers"]
        self.assertEqual(readers[0]["devices"]["total"], 3)

    def test_the_number_of_devices_is_a_setting(self):
        site = Site(limits={"devices_per_link": 3})
        self.addCleanup(site.close)
        site.publish(sample_chapter(1))
        code = site.invite("R", ["SC"])["code"]
        statuses = [site.call("GET", "/api/me", token=code, headers=device(n)).status for n in range(1, 5)]
        self.assertEqual(statuses, [200, 200, 200, 403])

    def test_when_a_device_was_last_seen_is_written_at_most_every_few_minutes(self):
        self.me(1)
        con = db.connect(self.site.data / db.DB_NAME)
        self.addCleanup(con.close)
        con.execute("UPDATE reader_device SET last_seen = '2026-01-01T00:00:00Z'")
        self.me(1)
        seen = con.execute("SELECT last_seen FROM reader_device").fetchone()[0]
        self.assertGreater(seen, "2026-01-01T00:00:00Z")
        con.execute("UPDATE reader_device SET last_seen = ?", (db.ago(minutes=1),))
        kept = con.execute("SELECT last_seen FROM reader_device").fetchone()[0]
        self.me(1)
        self.assertEqual(con.execute("SELECT last_seen FROM reader_device").fetchone()[0], kept)

    def test_the_agent_is_a_short_description(self):
        for ua, want in (("Mozilla/5.0 (Linux; Android 13) AppleWebKit Chrome/120 Mobile Safari/537 Line/13.1.0",
                          "Android, LINE"),
                         ("Mozilla/5.0 (Windows NT 10.0; Win64) AppleWebKit Chrome/120 Safari/537 Edg/120", "Windows, Edge"),
                         ("Mozilla/5.0 (X11; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0", "Linux, Firefox"),
                         ("", "an unknown browser")):
            self.assertEqual(app_module.device_agent(ua), want)


if __name__ == "__main__":
    unittest.main()
