"""Tests for review.py admin: the local admin server's key, host and origin checks, its page files, and its
routes, which run the same functions as review.py's commands against a dev server."""
import io
import json
import os
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
from wsgiref.util import setup_testing_defaults

from helpers import DEVICE, REPO, ROOT, sample_chapter
from test_cli import FRESH_LINK, Browser

import review
import review_admin
from server import db, dev
from server.app import App

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


class Console(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        cls.data = root / "data"
        db.setup(cls.data, "https://review.example.org")
        cls.token = cls.data / "admin-token"
        cls.app = App(cls.data, limits={"comments_per_minute": 1000})
        cls.httpd = dev.make(cls.app, root, 0, quiet=True)
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.httpd.server_address[1]}"
        cls.client = review.Client(cls.url, cls.token)
        cls.admin_dir = root / "admin"
        cls.admin_dir.mkdir()
        (cls.admin_dir / "index.html").write_text("<!doctype html><p>admin</p>")
        cls.console = review_admin.Console(cls.client, 8088, REPO, cls.admin_dir)
        cls.client.call("PUT", "/api/admin/chapters/SC/SC01", sample_chapter(1))

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.tmp.cleanup()

    def request(self, method, path, body=None, key=True, headers=None):
        environ = {}
        setup_testing_defaults(environ)
        path, _, query = path.partition("?")
        raw = b"" if body is None else json.dumps(body).encode()
        environ.update({"REQUEST_METHOD": method, "PATH_INFO": path, "QUERY_STRING": query,
                        "HTTP_HOST": "127.0.0.1:8088", "CONTENT_LENGTH": str(len(raw)), "wsgi.input": io.BytesIO(raw)})
        if key:
            environ["HTTP_X_ADMIN_KEY"] = self.console.key
        for k, v in (headers or {}).items():
            environ["HTTP_" + k.upper().replace("-", "_")] = v
        got = {}
        out = b"".join(self.console(environ, lambda s, h, e=None: got.update(status=int(s.split()[0]), headers=dict(h))))
        return got["status"], (json.loads(out) if got["headers"]["Content-Type"].startswith("application/json")
                               else out), got["headers"]

    def post(self, route, body):
        status, answer, _ = self.request("POST", f"/local/{route}", body)
        self.assertEqual(status, 200, answer)
        return answer

    # ---------- protection ----------

    def test_the_key_host_and_origin(self):
        status, answer, headers = self.request("GET", "/local/info", key=False)
        self.assertEqual((status, answer["error"]), (401, "bad_key"))
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        for wrong in ("another", self.console.key[:-1], self.console.key + "x"):
            status, answer, _ = self.request("GET", "/local/info", key=False, headers={"X-Admin-Key": wrong})
            self.assertEqual((status, answer["error"]), (401, "bad_key"))
        self.assertEqual(self.request("GET", "/local/info", headers={"Host": "evil.example:8088"})[1]["error"],
                         "bad_host")
        self.assertEqual(self.request("GET", "/", headers={"Host": "evil.example"})[0], 403)
        for origin in ("http://evil.example", "http://127.0.0.1:9999", "null"):
            status, answer, _ = self.request("POST", "/local/revoke", {"name": "x"}, headers={"Origin": origin})
            self.assertEqual((status, answer["error"]), (403, "bad_origin"), origin)
        status, answer, _ = self.request("GET", "/local/info", headers={"Sec-Fetch-Site": "cross-site"})
        self.assertEqual(status, 403)
        status, answer, _ = self.request("GET", "/local/info", headers={"Origin": "http://localhost:8088",
                                                                         "Host": "localhost:8088"})
        self.assertEqual(status, 200)

    def test_the_browser_gets_a_one_time_code_that_the_page_trades_for_the_key(self):
        """The browser's command line, which every account can read, holds only a code that works once."""
        url = self.console.once_url()
        self.assertTrue(url.startswith("http://127.0.0.1:8088/#once="))
        self.assertNotIn(self.console.key, url)
        code = url.rsplit("#once=", 1)[1]
        status, answer, _ = self.request("POST", "/local/trade", {"code": code}, key=False)
        self.assertEqual((status, answer["result"]["key"]), (200, self.console.key))
        status, answer, _ = self.request("POST", "/local/trade", {"code": code}, key=False)
        self.assertEqual((status, answer["error"]), (401, "bad_once"))
        for body in ({"code": "made-up"}, {}, {"code": 5}):
            self.assertEqual(self.request("POST", "/local/trade", body, key=False)[1]["error"], "bad_once")
        self.assertEqual(self.request("GET", "/local/trade", key=False)[0], 405)
        # The code too answers only the page itself, and only for a short while.
        late = self.console.once_url().rsplit("#once=", 1)[1]
        self.assertEqual(self.request("POST", "/local/trade", {"code": late}, key=False,
                                      headers={"Origin": "http://evil.example"})[1]["error"], "bad_origin")
        self.console.once[late] = 0
        self.assertEqual(self.request("POST", "/local/trade", {"code": late}, key=False)[1]["error"], "bad_once")

    def test_the_page_files_and_wrong_routes(self):
        status, body, headers = self.request("GET", "/", key=False)
        self.assertEqual((status, body), (200, b"<!doctype html><p>admin</p>"))
        self.assertEqual(headers["Content-Type"], "text/html; charset=utf-8")
        self.assertEqual(self.request("GET", "/local/nothing")[0], 404)
        self.assertEqual(self.request("GET", "/local/open")[0], 405)
        self.assertEqual(self.request("GET", "/local/grant")[0], 404)       # open replaced grant
        self.assertEqual(self.request("POST", "/local/chapters", {})[0], 405)
        for body in ({"spec": "SC01"}, {"names": ["--group"], "spec": "SC01"}, {"names": ["A"], "spec": ["-x"]},
                     {"names": [5], "spec": "SC01"}, {"names": "", "spec": "SC01"}, {"names": [" "], "spec": "SC01"},
                     {"name": "-x", "spec": "SC01"}):
            status, answer, _ = self.request("POST", "/local/open", body)
            self.assertEqual((status, answer["error"]), (400, "bad_field"), body)
        for route, body in (("device", {"action": "keep", "ids": [1]}), ("device", {"action": "approve"}),
                            ("round", {"book": "SC"}), ("delete-comments", {"name": "A", "from": "2026-10-01"}),
                            ("relink", {"group": "G", "names": ["A"]})):
            status, answer, _ = self.request("POST", f"/local/{route}", body)
            self.assertEqual((status, answer["error"]), (400, "bad_field"), route)
        self.assertTrue(self.console.url().startswith("http://127.0.0.1:8088/#key="))

    # ---------- reading ----------

    def test_info_and_lists(self):
        info = self.request("GET", "/local/info")[1]["result"]
        self.assertEqual((info["server"], info["ssh"], info["local"]), (self.url, False, True))
        self.assertEqual(info["dev_data"], str(self.data))
        self.assertIn("SC", info["books"])
        chapters = self.request("GET", "/local/chapters")[1]
        self.assertTrue(chapters["ok"])
        self.assertEqual(chapters["result"]["chapters"][0]["id"], "SC01")
        self.assertIn("english", [f["name"] for f in self.request("GET", "/local/features")[1]["result"]["features"]])
        self.assertIn("groups", self.request("GET", "/local/groups")[1]["result"])

    # ---------- commands ----------

    def test_readers_groups_and_grants(self):
        made = self.post("invite", {"name": "Admin Page Reader", "grant": ["SC01"], "english": True})
        self.assertTrue(made["ok"], made)
        self.assertTrue(made["result"]["link"].startswith("https://review.example.org/#k="))
        self.assertEqual(made["lines"][-2], made["result"]["link"])
        self.assertEqual(made["lines"][-1], f"Admin Page Reader is invited; {FRESH_LINK}.")
        again = self.post("invite", {"name": "Admin Page Reader", "grant": ["SC01"]})
        self.assertEqual(again["ok"], False)
        self.assertIn("already exists", again["error"])
        found = self.request("GET", "/local/readers?name=admin%20page")[1]
        self.assertEqual([r["name"] for r in found["result"]["readers"]], ["Admin Page Reader"])
        self.assertTrue(found["lines"][0].startswith("Admin Page Reader: active; own: SC01"))
        link = self.request("GET", "/local/readers?link=" + made["result"]["link"].replace("#", "%23"))[1]
        self.assertEqual(link["result"]["readers"][0]["name"], "Admin Page Reader")
        self.assertTrue(self.post("group", {"action": "create", "group": "AdminTest", "grant": ["SC01"]})["ok"])
        added = self.post("group", {"action": "add", "group": "AdminTest", "csv": "name\nAdmin Page Reader\n"})
        self.assertTrue(added["ok"], added)
        self.assertIn("1 reader added to AdminTest", added["lines"][0])
        self.assertTrue(self.post("open", {"names": ["Admin Page Reader"], "spec": "SC02"})["ok"])
        self.assertTrue(self.post("group", {"action": "close", "group": "AdminTest", "args": ["SC01"]})["ok"])
        self.assertTrue(self.post("english", {"names": ["Admin Page Reader"], "state": "off"})["ok"])
        self.assertTrue(self.post("feature", {"names": ["Admin Page Reader"], "feature": "english", "state": "on"})["ok"])
        self.assertTrue(self.post("revoke", {"names": ["Admin Page Reader"]})["ok"])
        self.assertTrue(self.post("restore", {"name": "Admin Page Reader"})["ok"])
        relinked = self.post("relink", {"names": ["Admin Page Reader"]})
        self.assertNotEqual(relinked["result"]["link"], made["result"]["link"])

    def test_one_request_acts_on_many_readers(self):
        made = self.post("invite", {"csv": "name,grants\nMany One,SC01\nMany Two,SC01\nMany Three,SC01\n"})
        self.assertTrue(made["ok"], made)
        names = ["Many One", "Many Two", "Many Three"]
        calls = []
        real = self.client.call

        def counting(method, path, *args, **kw):
            calls.append(path)
            return real(method, path, *args, **kw)

        with mock.patch.object(self.client, "call", counting):
            done = self.post("open", {"names": names, "spec": "SC02"})
        self.assertTrue(done["ok"], done)
        self.assertEqual(done["lines"][-1], "SC02 is now open to Many One, Many Three and Many Two.")
        self.assertLessEqual(len(calls), 3)
        relinked = self.post("relink", {"names": names[:2]})
        self.assertEqual([r["name"] for r in relinked["result"]["readers"]], names[:2])
        self.assertTrue(all(r["link"].startswith("https://review.example.org/#k=") for r in relinked["result"]["readers"]))
        self.assertTrue(self.post("close", {"names": names, "spec": "SC02"})["ok"])
        self.assertTrue(self.post("group", {"action": "create", "group": "Many"})["ok"])
        self.assertTrue(self.post("group", {"action": "add", "group": "Many", "args": names})["ok"])
        given = self.post("group", {"action": "give-each", "group": "Many", "args": ["SC02"]})
        self.assertEqual(given["lines"][-1], "SC02 is now among the own chapters of 3 members of Many; readers who "
                                             "join the group later do not get it.")

    def test_devices_rounds_and_deleting_a_readers_comments(self):
        reader = self.post("invite", {"name": "Device Reader", "grant": ["SC"]})["result"]
        code = reader["link"].split("#k=")[1]
        for k in range(1, 4):
            req = urllib.request.Request(f"{self.url}/api/me", headers={
                "Authorization": "Bearer " + code, "X-Review-Device": f"admin-device-000{k}"})
            try:
                OPENER.open(req, timeout=10).close()
            except urllib.error.HTTPError as e:
                self.assertEqual((k, e.code), (3, 403))
        waiting = self.request("GET", "/local/devices")[1]
        self.assertTrue(waiting["ok"], waiting)
        third = [d for d in waiting["result"]["devices"] if d["name"] == "Device Reader"]
        self.assertEqual([d["state"] for d in third], ["waiting"])
        listed = self.request("GET", "/local/devices?name=Device%20Reader")[1]
        self.assertEqual([d["state"] for d in listed["result"]["devices"]], ["ok", "ok", "waiting"])
        flagged = self.request("GET", "/local/readers?devices=1")[1]["result"]["readers"]
        self.assertIn("Device Reader", [r["name"] for r in flagged])
        done = self.post("device", {"action": "approve", "ids": [third[0]["id"]]})
        self.assertTrue(done["ok"], done)
        self.assertEqual(done["lines"][-1], f"Device {third[0]['id']} is approved: the link of Device Reader works on it.")
        done = self.post("device", {"action": "remove", "ids": str(third[0]["id"])})
        self.assertIn("is removed", done["lines"][-1])
        started = self.post("round", {"book": "SC", "name": "admin-round"})
        self.assertTrue(started["ok"], started)
        self.assertEqual(started["result"]["name"], "admin-round")
        rounds = self.request("GET", "/local/rounds?book=SC")[1]
        self.assertTrue(rounds["ok"], rounds)
        self.assertIn("admin-round", [r["name"] for r in rounds["result"]["rounds"]])
        counted = self.post("delete-comments", {"name": "Device Reader", "from": "2026-01-01", "to": "2099-12-31"})
        self.assertTrue(counted["ok"], counted)
        self.assertEqual((counted["result"]["comments"], counted["result"]["deleted"]), (0, 0))
        exported = self.post("export", {"all": True, "out": str(Path(self.tmp.name) / "all" / "review-all.json")})
        self.assertTrue(exported["ok"], exported)
        self.assertIsNone(exported["result"]["since"])
        by_round = self.post("export", {"round": "admin-round", "out": str(Path(self.tmp.name) / "r" / "r.json")})
        self.assertTrue(by_round["ok"], by_round)
        self.assertEqual(by_round["result"]["round"], "admin-round")

    def test_invite_from_an_uploaded_file_and_relink_a_group(self):
        self.post("group", {"action": "create", "group": "Upload"})
        csv = "name,groups,grants,english,email\nUp One,Upload,SC01,no,a@example.org\nUp Two,Upload,,yes,\n"
        done = self.post("invite", {"csv": csv, "filename": "readers.csv"})
        self.assertTrue(done["ok"], done)
        links = Path(done["result"]["links_file"])
        self.assertEqual(links.parent, self.data)
        self.assertEqual(oct(links.stat().st_mode & 0o777), "0o600")
        self.assertEqual(done["result"]["invited"], 2)
        bad = self.post("invite", {"csv": "name,grants\n=cmd,SC01\n", "filename": "../../x.csv"})
        self.assertFalse(bad["ok"])
        self.assertIn("formula", bad["error"])
        asked = self.post("relink", {"group": "Upload"})
        self.assertFalse(asked["ok"])
        self.assertIn("This gives 2 readers of Upload new links", asked["error"])
        self.assertEqual(asked["result"], {"confirm": 2})
        wrong = self.post("relink", {"group": "Upload", "confirm": 3})
        self.assertFalse(wrong["ok"])
        self.assertIn("Nothing was changed.", wrong["error"])
        done = self.post("relink", {"group": "Upload", "confirm": 2})
        self.assertTrue(done["ok"], done)
        self.assertEqual(done["result"]["relinked"], 2)

    def test_export_processed_replies_and_the_export_list(self):
        reader = self.post("invite", {"name": "Exported Reader", "grant": ["SC"]})["result"]
        code = reader["link"].split("#k=")[1]
        req = urllib.request.Request(f"{self.url}/api/comments", method="POST", data=json.dumps({
            "client_id": "admin-1", "book": "SC", "ch": "SC01", "a": "SC 101.1", "kind": "flag",
            "text": "A note"}).encode(), headers={"Authorization": "Bearer " + code, "X-Review-Device": DEVICE})
        with OPENER.open(req, timeout=10) as r:
            cid = json.loads(r.read())["id"]
        out = Path(self.tmp.name) / "export" / "review-20261022-101010.json"
        done = self.post("export", {"out": str(out), "reader": "Exported Reader"})
        self.assertTrue(done["ok"], done)
        self.assertEqual((done["result"]["comments"], done["result"]["json"]), (1, str(out)))
        replied = self.post("replies", {"replies": [{"id": cid, "reply": "Thank you."}]})
        self.assertTrue(replied["ok"], replied)
        self.assertEqual(replied["result"]["updated"], 1)
        marked = self.post("processed", {"ids": str(cid), "export": str(out)})
        self.assertTrue(marked["ok"], marked)
        self.assertEqual(marked["lines"], ["1 comment marked processed."])
        listed = self.request("GET", "/local/exports")[1]["result"]
        self.assertEqual(listed["folder"], str(review.DEV_DATA / "export"))

    @unittest.skipIf(REPO is None, "the translation repository is not found; set REVIEW_REPO")
    def test_publish_withdraw_and_triage_read_the_repository(self):
        done = self.post("publish", {"book": "SC", "chapters": "03"})
        self.assertTrue(done["ok"], done)
        self.assertRegex(done["lines"][0], r"^Reading main at ")
        self.assertEqual(done["result"]["chapters"][0]["id"], "SC03")
        refused = self.request("POST", "/local/publish", {"book": "SC"})
        self.assertEqual(refused[0], 400)
        self.assertTrue(self.post("withdraw", {"book": "SC", "chapters": "03"})["ok"])
        export = Path(self.tmp.name) / "triage" / "review-20261022-111111.json"
        self.post("export", {"out": str(export)})
        done = self.post("triage", {"export": str(export)})
        self.assertTrue(done["ok"], done)
        self.assertEqual(done["result"]["export"], str(export))

    def test_signing_in_through_the_local_routes(self):
        """The routes of 61-admin-contract.md: the sign-in settings, the switch Link signs in, browsers, LINE
        accounts and addresses, requests and general links, each running its review.py command."""
        auth = self.request("GET", "/local/auth")[1]
        self.assertTrue(auth["ok"], auth)
        self.assertEqual(auth["result"]["routes"], {"line": True, "email": True})
        self.assertTrue(auth["lines"][0].startswith("Sign-in with LINE: on, channel "))
        checked = self.post("signin", {"action": "check"})
        self.assertTrue(checked["ok"], checked)
        self.assertEqual(checked["lines"][-1], "Nothing changed: the check signs no one in and sends no mail.")
        sent = self.post("signin", {"action": "test-mail", "to": "admin-test@example.org"})
        self.assertEqual(sent["lines"], ["A test mail went to admin-test@example.org."])
        self.assertIn("a test mail by file: sent", " ".join(self.request("GET", "/local/auth")[1]["lines"]))
        for body in ({"action": "test-mail"}, {"action": "send"}, {}):
            self.assertEqual(self.request("POST", "/local/signin", body)[:2][0], 400, body)

        made = self.post("invite", {"name": "Switch Reader", "grant": ["SC01"], "link_signs_in": True})
        self.assertEqual(made["lines"][-1], "Switch Reader is invited; the link signs in by itself and works on the first "
                                            "devices that open it.")
        off = self.post("link-signs-in", {"names": ["Switch Reader"], "state": "off"})
        self.assertEqual(off["lines"][-1], "Link signs in is now off for Switch Reader: Switch Reader signs in with LINE "
                                           "or email.")
        self.assertEqual(self.request("POST", "/local/link-signs-in", {"names": ["Switch Reader"]})[0], 400)

        # A reader signs in with LINE through the stand-in; the page sees the identity and the browser.
        code = self.post("invite", {"name": "Line Reader", "grant": ["SC01"]})["result"]["link"].split("#k=")[1]
        standin = self.httpd.standin
        standin.users.append(("U" + "7" * 32, "Admin Tester"))
        browser = Browser(self.app)
        self.assertEqual(browser.line(standin, {"link": code}, len(standin.users) - 1), "signed_in")
        found = self.request("GET", "/local/readers?identity=line")[1]
        self.assertIn("Line Reader", [r["name"] for r in found["result"]["readers"]])
        self.assertTrue(any("signs in with LINE (Admin Tester); 1 browser signed in" in x for x in found["lines"]))
        sessions = self.request("GET", "/local/sessions?name=Line%20Reader")[1]
        self.assertTrue(sessions["ok"], sessions)
        (session,) = sessions["result"]["sessions"]
        self.assertEqual((session["name"], session["via"], session["active"]), ("Line Reader", "line", True))
        self.assertEqual(sessions["lines"][-1], "1 browser signed in. Sign one out with: review.py session end NUMBER")
        added = self.post("identity", {"action": "add", "name": "Line Reader", "address": "line-reader@example.org"})
        self.assertEqual(added["lines"][-1], "Line Reader can now sign in with a code sent to line-reader@example.org.")
        ids = self.request("GET", "/local/identities?name=Line%20Reader")[1]["result"]["identities"]
        self.assertEqual([i["provider"] for i in ids], ["line", "email"])
        ended = self.post("session", {"action": "end", "ids": [session["id"]]})
        self.assertEqual(ended["lines"][-1], f"Browser {session['id']} of Line Reader (iPhone, Safari) is signed out.")
        self.assertEqual(browser.call("GET", "/api/me")[1]["error"], "signed_out")
        everything = self.request("GET", "/local/sessions?name=Line%20Reader&all=1")[1]["result"]["sessions"]
        self.assertEqual([(s["id"], s["ended_by"]) for s in everything], [(session["id"], "translator")])
        out = self.post("signout", {"names": ["Line Reader"]})
        self.assertEqual(out["lines"][-1], "Nothing changed: Line Reader is signed in on no browser.")
        gone = self.post("unbind", {"ids": [ids[1]["id"]]})
        self.assertEqual(gone["lines"], ["line-reader@example.org no longer signs in to Line Reader, and no browser was "
                                         "signed in."])
        relinked = self.post("relink", {"names": ["Line Reader"], "unbind": True})
        self.assertEqual(relinked["lines"][-1], "Line Reader has a new link; the old link no longer works, LINE (Admin "
                                                "Tester) no longer signs in, and no browser was signed in.")
        self.assertEqual(self.request("GET", "/local/identities?name=Line%20Reader")[1]["result"]["identities"], [])
        for route, body in (("session", {"action": "end"}), ("session", {"action": "stop", "ids": [1]}),
                            ("identity", {"name": "Line Reader"}), ("unbind", {}), ("unbind", {"ids": ["-1"]})):
            self.assertEqual(self.request("POST", f"/local/{route}", body)[0], 400, (route, body))
        self.assertEqual(self.request("GET", "/local/sessions?name=-x")[0], 400)

        # A general link of a group takes requests, which the page approves, declines and forgets.
        self.post("group", {"action": "create", "group": "Askers", "grant": ["SC01"]})
        made = self.post("general-link", {"action": "new", "group": "Askers", "uses": 5, "days": "30"})
        self.assertTrue(made["ok"], made)
        self.assertIn("#join=", made["result"]["link"])
        self.assertIn(made["result"]["link"], made["lines"])
        self.assertRegex(made["lines"][-1], r"^Askers has a new general link, which takes up to 5 requests until ")
        join = made["result"]["link"].split("#join=")[1]
        links = self.request("GET", "/local/general-links?group=Askers")[1]
        self.assertEqual([x["state"] for x in links["result"]["links"]], ["open"])
        for address in ("asker-one@example.org", "asker-two@example.org"):
            self.assertEqual(Browser(self.app).email(self.data, self.app, address, {"join": join}), "request_sent")
        waiting = self.request("GET", "/local/requests")[1]
        self.assertEqual(waiting["result"]["open"], 2)
        self.assertEqual(waiting["lines"][-1], "2 requests waiting for you. Approve one with: review.py request approve "
                                               "NUMBER")
        number = {q["display"]: q["id"] for q in waiting["result"]["requests"]}
        approved = self.post("request", {"action": "approve", "id": number["asker-one@example.org"], "name": "Asker One",
                                         "grant": "SC01", "group": ["Askers"], "english": True})
        self.assertEqual(approved["lines"][-1], "asker-one@example.org is now the reader Asker One, who reads SC01 and "
                                                "is in the group Askers, and signs in with that address.")
        declined = self.post("request", {"action": "decline", "id": str(number["asker-two@example.org"])})
        self.assertTrue(declined["lines"][-1].startswith(f"Request {number['asker-two@example.org']} of "
                                                         "asker-two@example.org is declined;"))
        self.assertEqual(self.request("GET", "/local/requests?state=declined")[1]["result"]["requests"][0]["display"],
                         "asker-two@example.org")
        forgot = self.post("request", {"action": "forget", "id": number["asker-two@example.org"]})
        self.assertEqual(forgot["lines"], [f"Request {number['asker-two@example.org']} is forgotten; "
                                           "asker-two@example.org may ask again."])
        self.assertEqual(len(self.request("GET", "/local/requests?state=all")[1]["result"]["requests"]), 1)
        stopped = self.post("general-link", {"action": "off", "group": "Askers"})
        self.assertEqual(stopped["lines"][-1], "The general link of Askers no longer takes requests; a new one is made "
                                               "with: review.py general-link Askers --new")
        for route, body in (("request", {"action": "approve"}), ("request", {"action": "keep", "id": 1}),
                            ("request", {"action": "approve", "id": -1}), ("general-link", {"action": "on", "group": "Askers"}),
                            ("general-link", {"action": "new"}), ("general-link", {"action": "new", "group": "Askers",
                                                                                   "days": "x"})):
            self.assertEqual(self.request("POST", f"/local/{route}", body)[0], 400, (route, body))
        self.assertEqual(self.request("GET", "/local/requests?state=x")[0], 400)

    def test_backup_and_a_new_dev_token(self):
        done = self.post("backup", {"keep": 3})
        self.assertTrue(done["ok"], done)
        self.assertTrue(Path(done["result"]["backup"]).exists())
        before = self.token.read_text()
        done = self.post("new-token", {})
        self.assertTrue(done["ok"], done)
        self.assertNotEqual(self.token.read_text(), before)
        self.assertTrue(self.request("GET", "/local/chapters")[1]["ok"])     # the page goes on with the new token
        live = review_admin.Console(review.Client(self.url, Path(self.tmp.name) / "elsewhere" / "admin-token"), 8088)
        self.assertIsNone(live.dev_data())
        for route in ("backup", "new-token"):
            answer = getattr(live, route.replace("-", "_"))({})
            self.assertFalse(answer["ok"])
            self.assertIn("droplet", answer["error"])


class Start(unittest.TestCase):
    def test_review_py_admin_prints_its_address_and_serves(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        data = Path(tmp.name) / "data"
        db.setup(data)
        app = App(data)
        httpd = dev.make(app, Path(tmp.name), 0, quiet=True)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        self.addCleanup(httpd.server_close)
        self.addCleanup(httpd.shutdown)
        with __import__("socket").socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        proc = subprocess.Popen([sys.executable, str(ROOT / "review.py"), "--server",
                                 f"http://127.0.0.1:{httpd.server_address[1]}", "--token-file", str(data / "admin-token"),
                                 "admin", "--port", str(port), "--no-open"], stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True)
        self.addCleanup(proc.wait)
        self.addCleanup(proc.terminate)
        self.addCleanup(proc.stdout.close)
        line = ""
        deadline = time.monotonic() + 20
        while "#key=" not in line and time.monotonic() < deadline:
            line = proc.stdout.readline()
        self.assertIn(f"http://127.0.0.1:{port}/#key=", line)
        key = line.strip().rsplit("#key=", 1)[1]
        req = urllib.request.Request(f"http://127.0.0.1:{port}/local/info", headers={"X-Admin-Key": key})
        with OPENER.open(req, timeout=10) as r:
            self.assertEqual(json.loads(r.read())["result"]["server"], f"http://127.0.0.1:{httpd.server_address[1]}")
        with self.assertRaises(urllib.error.HTTPError) as e:
            OPENER.open(f"http://127.0.0.1:{port}/local/info", timeout=10)
        e.exception.close()
        self.assertEqual(e.exception.code, 401)
        page = OPENER.open(f"http://127.0.0.1:{port}/", timeout=10)
        with page:
            self.assertEqual(page.status, 200)


if __name__ == "__main__":
    unittest.main()
