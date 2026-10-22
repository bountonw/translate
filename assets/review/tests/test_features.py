"""Tests for the feature registry (server/features/), its first user (english), and feature migrations."""
import re
import sqlite3
import tempfile
import types
import unittest

from helpers import Site, sample_chapter

from server import db, features


def fake_module(**kw):
    m = types.ModuleType("fake_feature")
    for k, v in kw.items():
        setattr(m, k, v)
    return m


def notes_route(app, req, book):
    """A feature route: the reader's own count of notes in a book, from the feature's own table."""
    n = req.conn.execute("SELECT COUNT(*) FROM notes_seen WHERE reader = ? AND book = ?",
                         (req.reader["id"], book)).fetchone()[0]
    return 200, {"book": book, "seen": n, "on": app.settings(req)["notes.on"]}


NOTES = fake_module(
    NAME="notes",
    SETTINGS={"on": {"type": "bool", "default": True, "help": "a test feature"}},
    ROUTES=[("GET", r"([A-Z]{1,10})", notes_route, "reader")],
    MIGRATIONS=[(1, ["CREATE TABLE notes_seen (reader INTEGER NOT NULL, book TEXT NOT NULL)"]),
                (2, ["ALTER TABLE notes_seen ADD COLUMN at TEXT NOT NULL DEFAULT ''"])],
    me=lambda ctx: {"on": ctx.settings["on"], "reader": ctx.reader["name"]},
)


class Registry(unittest.TestCase):
    def test_english_is_the_first_feature(self):
        found = {f.name: f for f in features.load()}
        self.assertIn("english", found)
        f = found["english"]
        self.assertEqual((f.routes, f.migrations, f.me_hook), ([], [], None))
        self.assertEqual(f.settings["on"].key, "english.on")
        self.assertFalse(f.settings["on"].default)

    def test_bad_declarations_are_refused(self):
        bad = [dict(NAME="Bad Name"), dict(NAME="x", SETTINGS={"on": {"type": "text"}}),
               dict(NAME="x", SETTINGS={"on": {"type": "bool", "default": "no"}}),
               dict(NAME="x", SETTINGS={"on": {"type": "bool", "combine": "all"}}),
               dict(NAME="x", ROUTES=[("GET", r"/api/other/1", notes_route, "reader")]),
               dict(NAME="x", ROUTES=[("GET", r"1", notes_route, "anyone")])]
        for kw in bad:
            with self.assertRaises(features.FeatureError, msg=kw):
                features.Feature(fake_module(**kw))
        f = features.Feature(fake_module(NAME="english"))
        with self.assertRaises(features.FeatureError):
            features.Registry([f, f])

    def test_routes_stay_under_their_prefix_and_admin_paths_take_the_token(self):
        """The registry builds each path, so no pattern leaves its prefix and every admin path needs the token."""
        for name in sorted(features.RESERVED):
            with self.assertRaises(features.FeatureError, msg=name):
                features.Feature(fake_module(NAME=name))
        for sub in ("/api/x/1", "x)|(/api/admin/export", "(?i)x|y)", "[unclosed"):
            with self.assertRaises(features.FeatureError, msg=sub):
                features.Feature(fake_module(NAME="gloss", ROUTES=[("GET", sub, notes_route, None)]))
        f = features.Feature(fake_module(NAME="gloss", ROUTES=[
            ("GET", r"x|/api/admin/export", notes_route, None), ("GET", r"stats", notes_route, "admin")]))
        self.assertEqual([p for _, p, _, _ in f.routes], [r"/api/gloss/(?:x|/api/admin/export)",
                                                          r"/api/admin/gloss/(?:stats)"])

    def test_every_core_path_name_is_reserved(self):
        site = Site()
        self.addCleanup(site.close)
        first = {re.match(r"/api/(?:admin/)?([a-z]+)", p.pattern).group(1)
                 for _, p, _, _, feature in site.app.routes if feature is None}
        self.assertLessEqual(first, features.RESERVED)

    def test_resolve(self):
        reg = features.Registry(features.load())
        self.assertFalse(reg.resolve({}, [])["english.on"])
        self.assertTrue(reg.resolve({"english.on": False}, [("english.on", True)])["english.on"])
        self.assertTrue(reg.resolve({"english.on": True}, [("english.on", False)])["english.on"])
        with self.assertRaises(KeyError):
            reg.check({"nothing.on": True})
        with self.assertRaises(ValueError):
            reg.check({"english.on": 1})


class FakeFeature(unittest.TestCase):
    """A second feature plugged in as a module: its route, settings, /api/me part and migrations work."""

    def setUp(self):
        self.site = Site(feature_list=features.load() + [features.Feature(NOTES)])
        self.addCleanup(self.site.close)
        self.site.publish(sample_chapter(1))
        self.reader = self.site.invite("Reader", ["SC"])

    def test_route_settings_and_me(self):
        code = self.reader["code"]
        r = self.site.call("GET", "/api/notes/SC", token=code)
        self.assertEqual((r.status, r.json), (200, {"book": "SC", "seen": 0, "on": True}))
        self.assertEqual(self.site.call("GET", "/api/notes/SC").status, 401)
        me = self.site.call("GET", "/api/me", token=code).json
        self.assertEqual(me["features"]["notes"], {"on": True, "reader": "Reader"})
        self.assertEqual(me["features"]["english"], {"on": False})
        self.site.admin_call("PATCH", f"/api/admin/readers/{self.reader['id']}", {"settings": {"notes.on": False}})
        self.assertFalse(self.site.call("GET", "/api/me", token=code).json["features"]["notes"]["on"])
        listed = {f["name"]: f for f in self.site.admin_call("GET", "/api/admin/features").json["features"]}
        self.assertIn("english", listed)
        self.assertEqual(listed["notes"]["routes"], ["GET /api/notes/(?:([A-Z]{1,10})) (reader)"])

    def test_reader_routes_answer_only_readers_with_the_feature_on(self):
        def ok(app, req):
            return 200, {"ok": True}

        site = Site(feature_list=features.load() + [features.Feature(fake_module(
            NAME="gloss", SETTINGS={"on": {"type": "bool", "default": False}},
            ROUTES=[("GET", r"terms", ok, "reader"), ("GET", r"about", ok, "any_reader"),
                    ("GET", r"x|/api/admin/export", ok, None), ("GET", r"stats", ok, "admin")])),
            features.Feature(fake_module(NAME="bible", SETTINGS={"on": {"type": "bool", "default": True}},
                                         enabled=lambda s: False, ROUTES=[("GET", r"v", ok, "reader")]))])
        self.addCleanup(site.close)
        site.publish(sample_chapter(1))
        r = site.invite("Reader", ["SC"])
        code = r["code"]
        self.assertEqual(site.call("GET", "/api/gloss/terms", token=code).status, 404)   # off by default
        self.assertEqual(site.call("GET", "/api/gloss/about", token=code).status, 200)   # declared for any reader
        self.assertEqual(site.call("GET", "/api/gloss/about").status, 401)
        self.assertEqual(site.call("GET", "/api/bible/v", token=code).status, 404)       # enabled() says no
        site.admin_call("PATCH", f"/api/admin/readers/{r['id']}", {"settings": {"gloss.on": True}})
        self.assertEqual(site.call("GET", "/api/gloss/terms", token=code).status, 200)
        # A pattern with | stays inside its own prefix, and an admin route takes the token.
        self.assertEqual(site.call("DELETE", "/api/admin/export").status, 405)
        self.assertEqual(site.call("GET", "/api/admin/export").status, 401)
        self.assertEqual(site.call("GET", "/api/admin/gloss/stats").status, 401)
        self.assertEqual(site.call("GET", "/api/admin/gloss/stats", token=code).status, 401)
        self.assertEqual(site.admin_call("GET", "/api/admin/gloss/stats").status, 200)

    def test_migrations_run_once_and_are_recorded(self):
        con = sqlite3.connect(self.site.data / db.DB_NAME)
        self.assertEqual(con.execute("SELECT version FROM feature_schema WHERE feature = 'notes'").fetchone(), (2,))
        self.assertIsNone(con.execute("SELECT version FROM feature_schema WHERE feature = 'english'").fetchone())
        self.assertIn("at", [r[1] for r in con.execute("PRAGMA table_info(notes_seen)")])
        con.close()
        db.init_db(self.site.data / db.DB_NAME, [("notes", NOTES.MIGRATIONS)])   # a second start changes nothing

    def test_a_new_migration_of_one_feature_runs_alone(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = f"{tmp}/review.sqlite3"
            db.init_db(path, [("notes", NOTES.MIGRATIONS[:1])])
            db.init_db(path, [("notes", NOTES.MIGRATIONS)])
            con = sqlite3.connect(path)
            self.assertEqual(con.execute("SELECT feature, version FROM feature_schema").fetchall(), [("notes", 2)])
            con.close()


if __name__ == "__main__":
    unittest.main()
