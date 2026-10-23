"""Tests for signing in (server/auth.py, server/accounts.py, server/mail.py): LINE Login through the stand-in
OpenID provider of server/dev.py, the six-digit email code through the file mailer, sessions in an HttpOnly
cookie, the spent invite link, "Link signs in" and auth.require_identity, general links and requests, the
notes to the translator, the admin routes of accounts, the settings checked at the start, the dev server's
"Enter as", and database version 8 on a version 7 database."""
import email
import email.policy
import io
import json
import re
import smtplib
import socketserver
import sqlite3
import ssl
import tempfile
import threading
import time
import unittest
from unittest import mock
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from wsgiref.util import setup_testing_defaults

from helpers import ROOT, Site, sample_chapter

from server import app as app_module
from server import auth, db, dev, mail
from server.app import App

IPHONE = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Version/17.0 Safari/604.1"
ANDROID_LINE = "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/126.0 Mobile Safari/537.36 Line/14.10.0"


def wsgi(app, method, path, body=None, headers=None, environ=None):
    """(status, [(header, value)], body) of one in-process request; headers None are left out."""
    env = {}
    setup_testing_defaults(env)
    path, _, query = path.partition("?")
    data = b"" if body is None else (body if isinstance(body, bytes) else json.dumps(body).encode())
    env.update({"REQUEST_METHOD": method, "PATH_INFO": path, "QUERY_STRING": query, "CONTENT_LENGTH": str(len(data)),
                "wsgi.input": io.BytesIO(data), "wsgi.errors": io.StringIO()})
    for k, v in (headers or {}).items():
        if v is not None:
            env["HTTP_" + k.upper().replace("-", "_")] = v
    env.update(environ or {})
    got = {}

    def start_response(status, hdrs, exc_info=None):
        got["status"], got["headers"] = int(status.split()[0]), hdrs

    out = b"".join(app(env, start_response))
    return got["status"], got["headers"], out


class Answer:
    def __init__(self, status, headers, body):
        self.status, self.raw, self.body = status, headers, body
        self.headers = {k.lower(): v for k, v in headers}

    @property
    def json(self):
        return json.loads(self.body) if self.body else None

    @property
    def cookies(self):
        """[(name, value, {attribute: value})] of every Set-Cookie."""
        out = []
        for k, v in self.raw:
            if k.lower() == "set-cookie":
                first, *attrs = [p.strip() for p in v.split(";")]
                name, _, value = first.partition("=")
                out.append((name, value, {a.partition("=")[0].lower(): a.partition("=")[2] for a in attrs}))
        return out


class Browser:
    """One browser: it keeps its cookies, and sends X-Review-Page: 1 as the page does."""

    def __init__(self, app, agent=IPHONE):
        self.app, self.agent, self.jar = app, agent, {}

    def call(self, method, path, body=None, page=True, headers=None, token=None, environ=None):
        h = {"User-Agent": self.agent}
        if page:
            h["X-Review-Page"] = "1"
        if self.jar:
            h["Cookie"] = "; ".join(f"{k}={v}" for k, v in self.jar.items())
        if token:
            h["Authorization"] = "Bearer " + token
            h["X-Review-Device"] = "browser-device-" + str(id(self))[-8:].rjust(8, "0")
        h.update(headers or {})
        r = Answer(*wsgi(self.app, method, path, body, h, environ))
        for name, value, attrs in r.cookies:
            if attrs.get("max-age") == "0":
                self.jar.pop(name, None)
            else:
                self.jar[name] = value
        return r

    def get(self, path, **kw):
        return self.call("GET", path, **kw)

    def post(self, path, body=None, **kw):
        return self.call("POST", path, body if body is not None else {}, **kw)


class AuthSite(Site):
    """helpers.Site with config.json's sign-in settings written before the App starts."""

    def __init__(self, config=None, **kw):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name) / "data"
        self.token_path, _ = db.setup(self.data, "https://review.example.org")
        self.admin = self.token_path.read_text().strip()
        path = self.data / db.CONFIG
        path.write_text(json.dumps(dict(json.loads(path.read_text()), **(config or {}))))
        self.app = App(self.data, **kw)

    def close(self):
        self.app.mail_idle()
        super().close()

    def mails(self):
        """The mails the file mailer wrote, oldest first: [(to, subject, text)]."""
        self.app.mail_idle()
        out = []
        for p in sorted((self.data / "mail").glob("*.eml"), key=lambda p: p.stat().st_mtime_ns):
            msg = email.message_from_bytes(p.read_bytes(), policy=email.policy.default)
            out.append((msg["To"], str(msg["Subject"]), msg.get_content()))
        return out

    def code_in(self, text):
        return next(w for w in text.replace(".", " ").split() if w.isdigit() and len(w) == 6)


def config_for(standin, **extra):
    cfg = {"auth": {"line": standin.settings(), "email": True},
           "mail": {"provider": "file", "from": "review@example.org"},
           "notify": {"email": "translator@example.org"}}
    for k, v in extra.items():
        if isinstance(v, dict) and isinstance(cfg.get(k), dict):
            cfg[k] = dict(cfg[k], **v)
        else:
            cfg[k] = v
    return cfg


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.line = dev.StandInLine().start()

    @classmethod
    def tearDownClass(cls):
        cls.line.close()

    def setUp(self):
        self.line.tamper, self.line.alg, self.line.token_status, self.line.sign_secret = {}, "HS256", None, None
        self.site = self.make()
        self.site.publish(sample_chapter(1))

    def make(self, **extra):
        site = AuthSite(config_for(self.line, **extra), writes_per_minute=10000)
        self.addCleanup(site.close)
        return site

    def invite(self, name="Anan", site=None, **fields):
        site = site or self.site
        r = site.admin_call("POST", "/api/admin/readers", dict({"name": name, "grants": ["SC"]}, **fields))
        self.assertEqual(r.status, 201, r.body)
        return r.json

    def line_signin(self, browser, body=None, user=0, cancel=False):
        """Start a LINE sign-in in the browser, sign in at the stand-in, and come back: the callback's answer."""
        r = browser.post("/api/auth/line/start", body or {})
        self.assertEqual(r.status, 200, r.body)
        q = {k: v[-1] for k, v in parse_qs(urlsplit(r.json["url"]).query).items()}
        back = urlsplit(self.line.cancel(q) if cancel else self.line.approve(q, user))
        return browser.get(back.path + "?" + back.query, page=False)

    def result(self, r):
        self.assertEqual(r.status, 302, r.body)
        return r.headers["location"].split("#auth=")[1]

    def email_signin(self, browser, address, body=None, site=None):
        """Ask for a code, read it from the mail file, and type it: the finish's answer."""
        site = site or self.site
        before = len(site.mails())
        r = browser.post("/api/auth/email/start", dict(body or {}, email=address))
        self.assertEqual(r.status, 200, r.body)
        mails = site.mails()
        self.assertEqual(len(mails), before + 1, "no code was sent")
        return browser.post("/api/auth/email/finish", {"code": site.code_in(mails[-1][2])})


class Line(Base):
    def test_the_first_sign_in_through_the_link_ties_line_and_spends_the_link(self):
        anan = self.invite()
        b = Browser(self.site.app)
        claim = b.post("/api/auth/claim", {"link": anan["code"]}).json
        self.assertEqual((claim["state"], claim["skip"], claim["name"], claim["signed_in"]),
                         ("welcome", True, "Anan", None))
        self.assertEqual(claim["routes"], {"line": True, "email": True})
        start = b.post("/api/auth/line/start", {"link": anan["code"]})
        q = {k: v[-1] for k, v in parse_qs(urlsplit(start.json["url"]).query).items()}
        self.assertEqual((q["response_type"], q["scope"], q["code_challenge_method"], q["client_id"]),
                         ("code", "profile openid", "S256", self.line.channel_id))
        self.assertEqual(q["redirect_uri"], "https://review.example.org/api/auth/line/callback")
        self.assertTrue(q["state"] and q["nonce"] and len(q["code_challenge"]) == 43)
        self.assertNotIn(anan["code"], start.json["url"])
        (flow,) = [c for c in start.cookies if c[0] == "__Host-rvflow"]
        self.assertEqual(flow[2]["max-age"], "600")
        back = urlsplit(self.line.approve(q, 0))
        r = b.get(back.path + "?" + back.query, page=False)
        self.assertEqual(self.result(r), "signed_in")
        (session,) = [c for c in r.cookies if c[0] == "__Host-rv"]
        self.assertEqual(session[2], {"path": "/", "max-age": str(30 * 86400), "httponly": "", "samesite": "Lax",
                                      "secure": ""})
        self.assertNotIn("__Host-rvflow", b.jar)
        me = b.get("/api/me")
        self.assertEqual((me.status, me.json["id"], me.json["name"]), (200, anan["id"], "Anan"))
        state = b.get("/api/auth/state").json
        self.assertEqual((state["signed_in"], state["account"], state["via"]), (True, {"id": anan["id"],
                                                                                         "name": "Anan"}, "line"))
        self.assertEqual(state["identities"], [{"provider": "line", "display": "LINE tester 1"}])
        # The link is spent: alone it no longer signs in, and a claim says so.
        r = Browser(self.site.app).get("/api/me", token=anan["code"], page=False)
        self.assertEqual((r.status, r.json["error"]), (401, "link_used"))
        self.assertEqual(Browser(self.site.app).post("/api/auth/claim", {"link": anan["code"]}).json["state"], "used")
        r = Browser(self.site.app).post("/api/auth/line/start", {"link": anan["code"]})
        self.assertEqual((r.status, r.json["error"]), (409, "link_used"))
        row = self.site.admin_call("GET", f"/api/admin/readers?name=Anan").json["readers"][0]
        self.assertEqual([(i["provider"], i["display"]) for i in row["identities"]], [("line", "LINE tester 1")])
        self.assertEqual((row["sessions"], bool(row["link_used"]), bool(row["first_signin"])), (1, True, True))
        # The picture is never kept.
        con = sqlite3.connect(self.site.data / db.DB_NAME)
        self.addCleanup(con.close)
        self.assertNotIn("line-scdn", json.dumps(con.execute("SELECT * FROM identity").fetchall()))

    def test_a_new_browser_signs_in_with_line_with_nobody_waiting(self):
        anan = self.invite()
        self.assertEqual(self.result(self.line_signin(Browser(self.site.app), {"link": anan["code"]})), "signed_in")
        for n in range(4):      # far more than the two devices of a link
            b = Browser(self.site.app, agent=ANDROID_LINE)
            self.assertEqual(self.result(self.line_signin(b)), "signed_in")
            self.assertEqual(b.get("/api/me").status, 200)
        mine = b.get("/api/auth/sessions").json["sessions"]
        self.assertEqual(len(mine), 5)
        self.assertEqual([s["current"] for s in mine].count(True), 1)
        self.assertEqual([s["agent"] for s in mine if s["current"]], ["Android, LINE"])
        # A LINE account no reader uses opens nothing.
        self.assertEqual(self.result(self.line_signin(Browser(self.site.app), user=1)), "no_account")

    def test_refusals_of_the_callback(self):
        anan = self.invite()
        b = Browser(self.site.app)
        self.assertEqual(self.result(self.line_signin(b, {"link": anan["code"]}, cancel=True)), "cancelled")
        # Another browser comes back with this browser's state: refused.
        r = b.post("/api/auth/line/start", {"link": anan["code"]})
        q = {k: v[-1] for k, v in parse_qs(urlsplit(r.json["url"]).query).items()}
        back = urlsplit(self.line.approve(q))
        self.assertEqual(self.result(Browser(self.site.app).get(back.path + "?" + back.query, page=False)),
                         "other_browser")
        # The same answer twice: the second is refused.
        r = b.post("/api/auth/line/start", {"link": anan["code"]})
        q = {k: v[-1] for k, v in parse_qs(urlsplit(r.json["url"]).query).items()}
        back = urlsplit(self.line.approve(q))
        jar = dict(b.jar)
        self.assertEqual(self.result(b.get(back.path + "?" + back.query, page=False)), "signed_in")
        b.jar = jar
        self.assertEqual(self.result(b.get(back.path + "?" + back.query, page=False)), "expired")
        self.assertEqual(self.result(b.get("/api/auth/line/callback?state=nothing&code=x", page=False)), "expired")

    def test_a_token_that_fails_any_check_signs_nobody_in(self):
        for tamper, why in (({"nonce": "another"}, "nonce"), ({"aud": "999"}, "aud"), ({"iss": "https://x"}, "issuer"),
                            ({"exp": 1000}, "expired"), ({"iat": 9999999999}, "future"), ({"sub": None}, "sub")):
            with self.subTest(why):
                self.line.tamper = tamper
                anan = self.invite(f"Reader {why}")
                r = self.line_signin(Browser(self.site.app), {"link": anan["code"]})
                self.assertEqual(self.result(r), "failed")
                self.assertIn(why, self.site.app.last_line["detail"])
        self.line.tamper, self.line.sign_secret = {}, "0" * 32
        r = self.line_signin(Browser(self.site.app), {"link": self.invite("Wrong key")["code"]})
        self.line.sign_secret = None
        self.assertEqual(self.result(r), "failed")
        self.assertIn("signature", self.site.app.last_line["detail"])
        self.line.token_status = 400
        self.assertEqual(self.result(self.line_signin(Browser(self.site.app), {"link": self.invite("T")["code"]})),
                         "failed")
        self.assertIn("token endpoint answered 400", self.site.app.last_line["detail"])
        self.assertEqual(self.site.admin_call("GET", "/api/admin/readers?identity=any").json["readers"], [])

    def test_a_token_signed_with_es256_is_checked_by_the_verify_endpoint(self):
        self.line.alg = "ES256"
        anan = self.invite()
        self.assertEqual(self.result(self.line_signin(Browser(self.site.app), {"link": anan["code"]})), "signed_in")
        self.assertIn("/verify", [p for p, _ in self.line.requests])
        self.line.tamper = {"nonce": "wrong"}
        self.assertEqual(self.result(self.line_signin(Browser(self.site.app), {"link": self.invite("M")["code"]})),
                         "failed")

    def test_a_line_account_of_another_reader_is_refused(self):
        anan, mali = self.invite(), self.invite("Mali")
        self.assertEqual(self.result(self.line_signin(Browser(self.site.app), {"link": anan["code"]})), "signed_in")
        self.assertEqual(self.result(self.line_signin(Browser(self.site.app), {"link": mali["code"]})),
                         "identity_taken")
        # Mali's link is not spent by the refusal.
        self.assertEqual(Browser(self.site.app).post("/api/auth/claim", {"link": mali["code"]}).json["state"],
                         "welcome")

    def test_the_stand_in_shows_its_sign_in_page(self):
        import urllib.request
        anan = self.invite()
        url = Browser(self.site.app).post("/api/auth/line/start", {"link": anan["code"]}).json["url"]
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        page = opener.open(url, timeout=5).read().decode()
        self.assertIn("Sign in as LINE tester 1", page)
        status, _ = auth.http("GET", self.line.base + "/.well-known/openid-configuration")
        self.assertEqual(status, 200)


class Email(Base):
    def test_the_code_through_the_link(self):
        anan = self.invite()
        b = Browser(self.site.app)
        r = b.post("/api/auth/email/start", {"email": " Anan@Example.ORG ", "link": anan["code"]})
        self.assertEqual((r.status, r.json), (200, {"ok": True, "minutes": 10, "tries": 3}))
        to, title, text = self.site.mails()[-1]
        code = self.site.code_in(text)
        # The subject is in Thai, with the code first; the body gives the Thai, then the English (mail.both).
        words = mail.words()
        self.assertEqual((to, title), (" Anan@Example.ORG ".strip().lower(),
                                       words["code_subject"]["th"].format(code=code)))
        self.assertTrue(title.startswith(code + " "))
        th, en = (words["code_body"][lang].format(code=code, minutes=10) for lang in ("th", "en"))
        self.assertEqual(text.strip(), f"{th}\n\n{en}")
        self.assertIn("within 10 minutes", text)
        r = b.post("/api/auth/email/finish", {"code": code[:3] + " " + code[3:]})
        self.assertEqual((r.status, r.json), (200, {"result": "signed_in", "name": "Anan"}))
        self.assertEqual(b.get("/api/me").json["id"], anan["id"])
        # Later, a new browser signs in with the address alone.
        b2 = Browser(self.site.app)
        self.assertEqual(self.email_signin(b2, "anan@example.org").json["result"], "signed_in")
        self.assertEqual(b2.get("/api/auth/state").json["via"], "email")

    def test_three_tries_and_ten_minutes(self):
        anan = self.invite()
        b = Browser(self.site.app)
        b.post("/api/auth/email/start", {"email": "anan@example.org", "link": anan["code"]})
        code = self.site.code_in(self.site.mails()[-1][2])
        wrong = "000000" if code != "000000" else "111111"
        r = b.post("/api/auth/email/finish", {"code": wrong})
        self.assertEqual((r.status, r.json["error"], r.json["tries_left"]), (400, "wrong_code", 2))
        self.assertEqual(b.post("/api/auth/email/finish", {"code": wrong}).json["tries_left"], 1)
        self.assertEqual(b.post("/api/auth/email/finish", {"code": wrong}).json["error"], "code_used_up")
        self.assertEqual(b.post("/api/auth/email/finish", {"code": code}).json["error"], "code_expired")
        self.assertEqual(b.post("/api/auth/email/finish", {"code": "12345"}).json["error"], "bad_field")
        # A new code, then ten minutes pass.
        b.post("/api/auth/email/start", {"email": "anan@example.org", "link": anan["code"]})
        code = self.site.code_in(self.site.mails()[-1][2])
        con = db.connect(self.site.data / db.DB_NAME)
        self.addCleanup(con.close)
        con.execute("UPDATE auth_flow SET expires = ?", (db.ago(minutes=1),))
        self.assertEqual(b.post("/api/auth/email/finish", {"code": code}).json["error"], "code_expired")
        # A code typed in another browser does not work.
        b.post("/api/auth/email/start", {"email": "anan@example.org", "link": anan["code"]})
        code = self.site.code_in(self.site.mails()[-1][2])
        self.assertEqual(Browser(self.site.app).post("/api/auth/email/finish", {"code": code}).json["error"],
                         "code_expired")
        self.assertEqual(b.post("/api/auth/email/finish", {"code": code}).json["result"], "signed_in")

    def test_a_reader_signed_in_with_line_adds_an_address(self):
        anan = self.invite()
        b = Browser(self.site.app)
        self.line_signin(b, {"link": anan["code"]})
        r = Browser(self.site.app).post("/api/auth/email/start", {"email": "anan@example.org", "add": True})
        self.assertEqual((r.status, r.json["error"]), (401, "signed_out"))
        self.assertEqual(self.email_signin(b, "anan@example.org", {"add": True}).json,
                         {"result": "added", "name": None})
        self.assertEqual([i["provider"] for i in b.get("/api/auth/state").json["identities"]], ["line", "email"])
        # Now a computer without LINE signs in with the address; one LINE account cannot join a second reader.
        self.assertEqual(self.email_signin(Browser(self.site.app), "anan@example.org").json["result"], "signed_in")
        mali = self.invite("Mali")
        m = Browser(self.site.app)
        self.email_signin(m, "mali@example.org", {"link": mali["code"]})
        self.assertEqual(self.result(self.line_signin(m, {"add": True})), "identity_taken")
        self.assertEqual(self.result(self.line_signin(m, {"add": True}, user=1)), "added")

    def test_the_same_answer_whether_or_not_a_reader_uses_the_address(self):
        anan = self.invite()
        self.email_signin(Browser(self.site.app), "anan@example.org", {"link": anan["code"]})
        before = len(self.site.mails())
        known = Browser(self.site.app).post("/api/auth/email/start", {"email": "anan@example.org"})
        unknown = Browser(self.site.app).post("/api/auth/email/start", {"email": "nobody@example.org"})
        self.assertEqual((known.status, known.json), (unknown.status, unknown.json))
        self.assertEqual(len(self.site.mails()), before + 1)
        for bad in ("anan", "a@b", "a b@example.org", "x" * 300 + "@example.org"):
            self.assertEqual(Browser(self.site.app).post("/api/auth/email/start", {"email": bad}).json["error"],
                             "bad_email", bad)

    def test_codes_to_one_address_a_share_for_each_address_on_the_internet(self):
        # 65-security.md item 4 and 66-adversarial.md item 5: a stranger at one address on the internet uses up only
        # that address's share of a reader's codes, and the address alone gets at most CODES_PER_DAY in 24 hours.
        anan = self.invite()
        self.email_signin(Browser(self.site.app), "anan@example.org", {"link": anan["code"]})
        start = lambda ip: Browser(self.site.app).post("/api/auth/email/start", {"email": "anan@example.org"},
                                                       environ={"REMOTE_ADDR": ip})
        # The stranger asks five codes, and the sixth from the same address is refused for the day.
        self.assertEqual([start("198.51.100.7").status for _ in range(5)], [200] * 5)
        r = start("198.51.100.7")
        self.assertEqual((r.status, r.json["error"], r.json["limit"]), (429, "slow_down", "day"))
        self.assertGreater(int(r.headers["retry-after"]), 80000)
        # Anan, on her own network, still gets a code.
        before = len(self.site.mails())
        self.assertEqual(start("203.0.113.20").status, 200)
        self.assertEqual(len(self.site.mails()), before + 1)
        # One address gets at most CODES_PER_DAY codes in 24 hours from anywhere (1 sign-in + 5 + 1 so far).
        sent = [start(f"192.0.2.{n}").status for n in range(auth.CODES_PER_DAY - 7)]
        self.assertEqual(sent, [200] * (auth.CODES_PER_DAY - 7))
        r = start("192.0.2.99")
        self.assertEqual((r.status, r.json["limit"]), (429, "day"))
        self.assertIn(f"{auth.CODES_PER_DAY} codes went to this address in the last 24 hours", r.json["message"])
        # A refused start sends nothing and counts toward nothing: another address still gets its code.
        self.assertEqual(start("192.0.2.98").status, 429)
        self.assertEqual(Browser(self.site.app).post("/api/auth/email/start", {"email": "other@example.org"},
                                                     environ={"REMOTE_ADDR": "192.0.2.99"}).status, 200)

    def test_adding_addresses_is_capped_for_each_reader(self):
        # 66-adversarial.md item 6: a signed-in browser sends at most ADD_CODES_PER_HOUR add codes an hour, from
        # any address on the internet.
        anan = self.invite()
        b = Browser(self.site.app)
        self.line_signin(b, {"link": anan["code"]})
        got = [b.post("/api/auth/email/start", {"email": f"s{n}@example.org", "add": True},
                      environ={"REMOTE_ADDR": f"10.9.0.{n}"}).status for n in range(auth.ADD_CODES_PER_HOUR + 1)]
        self.assertEqual(got, [200] * auth.ADD_CODES_PER_HOUR + [429])
        r = b.post("/api/auth/email/start", {"email": "t@example.org", "add": True}, environ={"REMOTE_ADDR": "10.9.9.9"})
        self.assertEqual((r.status, r.json["limit"]), (429, "hour"))
        # Signing in is not an add: a code to sign in still goes.
        self.assertEqual(Browser(self.site.app).post("/api/auth/email/start", {"email": "t@example.org"},
                                                     environ={"REMOTE_ADDR": "10.9.9.9"}).status, 200)

    def test_codes_through_one_link_are_capped(self):
        anan = self.invite()
        for n in range(10):
            r = Browser(self.site.app).post("/api/auth/email/start", {"email": f"a{n}@example.org", "link": anan["code"]},
                                            environ={"REMOTE_ADDR": f"10.2.0.{n}"})
            self.assertEqual(r.status, 200)
        r = Browser(self.site.app).post("/api/auth/email/start", {"email": "z@example.org", "link": anan["code"]},
                                        environ={"REMOTE_ADDR": "10.2.1.1"})
        self.assertEqual((r.status, r.json["error"]), (429, "slow_down"))
        self.site.admin_call("POST", "/api/admin/groups", {"name": "Open", "grants": ["SC01"]})
        join = self.site.admin_call("POST", "/api/admin/general-links", {"group": "Open"}).json["code"]
        with mock.patch.object(auth, "JOIN_CODES_PER_HOUR", 2):
            codes = [Browser(self.site.app).post("/api/auth/email/start", {"email": f"j{n}@example.org", "join": join},
                                                 environ={"REMOTE_ADDR": f"10.3.0.{n}"}).status for n in range(3)]
        self.assertEqual(codes, [200, 200, 429])

    def test_ten_sign_in_starts_a_minute_from_one_address(self):
        b = Browser(self.site.app)
        for n in range(10):
            self.assertEqual(b.post("/api/auth/line/start", {}, environ={"REMOTE_ADDR": "2001:db8:1:2:3::4"}).status, 200)
        r = b.post("/api/auth/email/start", {"email": "x@example.org"}, environ={"REMOTE_ADDR": "2001:db8:1:2:9::9"})
        self.assertEqual((r.status, r.json["error"]), (429, "slow_down"))
        self.assertEqual(b.post("/api/auth/line/start", {}, environ={"REMOTE_ADDR": "10.1.1.1"}).status, 200)

    def test_a_failed_send_says_so_and_crashes_nothing(self):
        site = self.make(mail={"provider": "smtp", "host": "127.0.0.1", "port": closed_port(),
                               "from": "review@example.org"})
        site.publish(sample_chapter(1))
        anan = self.invite(site=site)
        r = Browser(site.app).post("/api/auth/email/start", {"email": "anan@example.org", "link": anan["code"]})
        self.assertEqual((r.status, r.json["error"]), (503, "mail_failed"))
        self.assertEqual(r.json["message"], "The code could not be sent. Try again later.")
        last = site.admin_call("GET", "/api/admin/auth").json["last_mail"]
        self.assertEqual((last["kind"], last["ok"], last["provider"]), ("code", False, "smtp"))
        self.assertIn("cannot be reached", last["detail"])
        # LINE still works.
        self.assertEqual(self.result(self.line_signin(Browser(site.app), {"link": anan["code"]})), "signed_in")


class Sessions(Base):
    def signed_in(self, name="Anan"):
        r = self.invite(name)
        b = Browser(self.site.app)
        self.assertEqual(self.result(self.line_signin(b, {"link": r["code"]})), "signed_in")
        return r, b

    def test_the_page_header_and_other_sites(self):
        anan, b = self.signed_in()
        self.assertEqual(b.get("/api/me", page=False).json["error"], "bad_page")
        for headers in ({"Origin": "https://evil.example"}, {"Sec-Fetch-Site": "cross-site"},
                        {"Sec-Fetch-Site": "same-site"}):
            r = b.call("PUT", "/api/place", {"book": "SC", "ch": "SC01", "a": "SC 101.1"}, headers=headers)
            self.assertEqual((r.status, r.json["error"]), (403, "bad_page"), headers)
        for headers in ({"Origin": "https://review.example.org"}, {"Origin": "null"}, {"Sec-Fetch-Site": "same-origin"}):
            r = b.call("PUT", "/api/place", {"book": "SC", "ch": "SC01", "a": "SC 101.1"}, headers=headers)
            self.assertEqual(r.status, 200, headers)
        # A preflight is never answered with leave to send.
        r = b.call("OPTIONS", "/api/me")
        self.assertEqual(r.status, 405)
        self.assertNotIn("access-control-allow-origin", r.headers)
        self.assertEqual(Browser(self.site.app).post("/api/auth/claim", {"link": anan["code"]}, page=False).status, 403)

    def test_thirty_days_from_the_last_visit(self):
        anan, b = self.signed_in()
        con = db.connect(self.site.data / db.DB_NAME)
        self.addCleanup(con.close)
        con.execute("UPDATE session SET last_seen = ?, expires = ?", (db.ago(29), db.later(db.now(), 1)))
        r = b.get("/api/me")
        self.assertEqual(r.status, 200)
        (cookie,) = [c for c in r.cookies if c[0] == "__Host-rv"]
        self.assertEqual(cookie[2]["max-age"], str(30 * 86400))
        expires = con.execute("SELECT expires FROM session").fetchone()[0]
        self.assertGreater(expires, db.later(db.now(), 29))
        # A visit a minute later writes nothing.
        self.assertEqual([c for c in b.get("/api/me").cookies], [])
        con.execute("UPDATE session SET expires = ?", (db.ago(minutes=1),))
        r = b.get("/api/me")
        self.assertEqual((r.status, r.json["error"]), (401, "signed_out"))
        self.assertNotIn("__Host-rv", b.jar)
        self.assertEqual(b.get("/api/me").json["error"], "no_code")

    def test_the_reader_and_the_translator_end_sessions(self):
        anan, b = self.signed_in()
        other = Browser(self.site.app)
        self.assertEqual(self.result(self.line_signin(other)), "signed_in")
        mine = b.get("/api/auth/sessions").json["sessions"]
        theirs = next(s for s in mine if not s["current"])
        self.assertEqual(b.call("DELETE", f"/api/auth/sessions/{theirs['id']}").json, {"ended": theirs["id"],
                                                                                        "current": False})
        self.assertEqual(other.get("/api/me").json["error"], "signed_out")
        self.assertEqual(b.call("DELETE", f"/api/auth/sessions/{theirs['id']}").json["error"], "no_session")
        # The translator signs out every browser of the reader.
        third = Browser(self.site.app)
        self.line_signin(third)
        r = self.site.admin_call("PATCH", "/api/admin/sessions", {"readers": [anan["id"]]})
        self.assertEqual((r.status, len(r.json["ended"]), r.json["missing"]), (200, 2, []))
        self.assertTrue(all(s["ended_by"] == "translator" for s in r.json["sessions"]))
        self.assertEqual(b.get("/api/me").json["error"], "signed_out")
        listed = self.site.admin_call("GET", f"/api/admin/sessions?reader={anan['id']}&all=1").json["sessions"]
        self.assertEqual(sorted(s["ended_by"] for s in listed), ["reader", "translator", "translator"])
        self.assertEqual(listed[0]["identity"]["provider"], "line")
        # Logout ends this browser's session.
        b4 = Browser(self.site.app)
        self.line_signin(b4)
        self.assertEqual(b4.post("/api/auth/logout").json, {"signed_out": True})
        self.assertEqual(b4.get("/api/me").json["error"], "no_code")
        self.assertEqual(b4.get("/api/auth/sessions").json["error"], "no_code")
        r = self.site.admin_call("PATCH", "/api/admin/sessions", {"ids": [listed[0]["id"], 999]})
        self.assertEqual((r.json["ended"], r.json["missing"], r.json["unchanged"]), ([], [999], [listed[0]["id"]]))

    def test_a_stopped_reader_is_refused_and_restored(self):
        anan, b = self.signed_in()
        self.site.admin_call("PATCH", f"/api/admin/readers/{anan['id']}", {"active": False})
        self.assertEqual(b.get("/api/me").json["error"], "stopped")
        self.assertEqual(self.result(self.line_signin(Browser(self.site.app))), "stopped")
        self.site.admin_call("PATCH", f"/api/admin/readers/{anan['id']}", {"active": True})
        self.assertEqual(b.get("/api/me").status, 200)

    def test_signing_in_as_another_reader_ends_the_old_session(self):
        anan, b = self.signed_in()
        mali = self.invite("Mali")
        self.assertEqual(self.result(self.line_signin(b, {"link": mali["code"]}, user=1)), "signed_in")
        self.assertEqual(b.get("/api/me").json["name"], "Mali")
        ended = self.site.admin_call("GET", f"/api/admin/sessions?reader={anan['id']}&all=1").json["sessions"]
        self.assertEqual([s["ended_by"] for s in ended], ["signin"])

    def test_comments_through_a_session(self):
        anan, b = self.signed_in()
        body = {"client_id": "s-1", "book": "SC", "ch": "SC01", "a": "SC 101.1", "kind": "flag", "text": "Hi"}
        r = b.post("/api/comments", body)
        self.assertEqual(r.status, 201, r.body)
        self.assertEqual(b.get("/api/comments?book=SC&ch=SC01").json["comments"][0]["client_id"], "s-1")
        # The same comment, sent again after a lost answer, is not made twice.
        self.assertEqual(b.post("/api/comments", body).status, 200)


class Links(Base):
    def test_link_signs_in_keeps_the_link_and_the_device_lock(self):
        chai = self.invite("Chai", link_signs_in=True)
        self.assertTrue(chai["link_signs_in"])
        self.assertEqual(Browser(self.site.app).post("/api/auth/claim", {"link": chai["code"]}).json["state"], "link")
        devices = [Browser(self.site.app) for _ in range(3)]
        self.assertEqual([d.get("/api/me", token=chai["code"], page=False).status for d in devices], [200, 200, 403])
        # 65-security.md item 1 and 66-adversarial.md item 3: while the switch is on, the link starts no sign-in
        # with LINE or email, so nobody holding it signs in past the two-device lock.
        third = devices[2]
        r = third.post("/api/auth/line/start", {"link": chai["code"]})
        self.assertEqual((r.status, r.json["error"]), (409, "link_signs_in"))
        r = third.post("/api/auth/email/start", {"email": "stranger@example.org", "link": chai["code"]})
        self.assertEqual((r.status, r.json["error"]), (409, "link_signs_in"))
        self.assertEqual(self.site.admin_call("GET", f"/api/admin/identities?reader={chai['id']}").json["identities"],
                         [])
        self.assertEqual(third.get("/api/me").json["error"], "no_code")
        self.assertEqual(devices[0].get("/api/me", token=chai["code"], page=False).status, 200)
        # A sign-in begun before the switch came on ties nothing when it comes back.
        r = self.site.admin_call("PATCH", f"/api/admin/readers/{chai['id']}", {"link_signs_in": False})
        self.assertFalse(r.json["link_signs_in"])
        b = Browser(self.site.app)
        start = b.post("/api/auth/line/start", {"link": chai["code"]})
        self.assertEqual(start.status, 200)
        self.site.admin_call("PATCH", f"/api/admin/readers/{chai['id']}", {"link_signs_in": True})
        q = {k: v[-1] for k, v in parse_qs(urlsplit(start.json["url"]).query).items()}
        back = urlsplit(self.line.approve(q, 2))
        self.assertEqual(self.result(b.get(back.path + "?" + back.query, page=False)), "link_signs_in")
        self.assertEqual(self.site.admin_call("GET", f"/api/admin/identities?reader={chai['id']}").json["identities"],
                         [])
        # Switched off, the link ties one identity once, as every reader's does.
        self.site.admin_call("PATCH", f"/api/admin/readers/{chai['id']}", {"link_signs_in": False})
        self.assertEqual(self.result(self.line_signin(Browser(self.site.app), {"link": chai["code"]})), "signed_in")
        self.assertEqual(devices[0].get("/api/me", token=chai["code"], page=False).json["error"], "link_used")
        r = Browser(self.site.app).post("/api/auth/line/start", {"link": chai["code"]})
        self.assertEqual((r.status, r.json["error"]), (409, "link_used"))

    def test_require_identity(self):
        site = self.make(auth={"require_identity": True})
        site.publish(sample_chapter(1))
        anan = self.invite(site=site)
        claim = Browser(site.app).post("/api/auth/claim", {"link": anan["code"]}).json
        self.assertEqual((claim["state"], claim["skip"]), ("welcome", False))
        r = Browser(site.app).get("/api/me", token=anan["code"], page=False)
        self.assertEqual((r.status, r.json["error"]), (401, "sign_in_required"))
        chai = self.invite("Chai", site=site, link_signs_in=True)
        self.assertEqual(Browser(site.app).get("/api/me", token=chai["code"], page=False).status, 200)

    def test_without_sign_in_routes_the_link_works_as_before(self):
        site = AuthSite({})
        self.addCleanup(site.close)
        site.publish(sample_chapter(1))
        anan = self.invite(site=site)
        b = Browser(site.app)
        self.assertEqual(b.post("/api/auth/claim", {"link": anan["code"]}).json["state"], "link")
        self.assertEqual(b.get("/api/auth/state").json["routes"], {"line": False, "email": False})
        self.assertEqual(b.post("/api/auth/line/start", {}).json["error"], "route_off")
        self.assertEqual(b.post("/api/auth/email/start", {"email": "a@example.org"}).json["error"], "route_off")
        self.assertEqual(b.get("/api/me", token=anan["code"], page=False).status, 200)

    def test_an_unbound_reader_keeps_the_link_until_signing_in(self):
        anan = self.invite()
        b = Browser(self.site.app)
        self.assertEqual(b.get("/api/me", token=anan["code"], page=False).status, 200)
        self.email_signin(b, "anan@example.org", {"link": anan["code"]})
        self.assertEqual(b.get("/api/me", token=anan["code"], page=False, headers={"Cookie": None}).json["error"],
                         "link_used")

    def test_a_new_link_keeps_the_identities_unless_asked(self):
        anan = self.invite()
        b = Browser(self.site.app)
        self.line_signin(b, {"link": anan["code"]})
        r = self.site.admin_call("POST", f"/api/admin/readers/{anan['id']}/code")
        self.assertEqual((r.status, r.json["unbound"], r.json["sessions_ended"]), (200, [], 0))
        self.assertIsNone(r.json["link_used"])
        self.assertEqual(len(r.json["identities"]), 1)
        claim = Browser(self.site.app).post("/api/auth/claim", {"link": r.json["code"]}).json
        self.assertEqual((claim["state"], claim["skip"]), ("welcome", False))
        r = Browser(self.site.app).get("/api/me", token=r.json["code"], page=False)
        self.assertEqual(r.json["error"], "sign_in_required")
        self.assertEqual(b.get("/api/me").status, 200)
        # A new link that also unbinds: the stranger's LINE is gone and its browsers are signed out.
        r = self.site.admin_call("POST", "/api/admin/readers/codes", {"ids": [anan["id"]], "unbind": True})
        (item,) = r.json["readers"]
        self.assertEqual((item["unbound"], item["sessions_ended"], item["identities"]),
                         ([{"provider": "line", "display": "LINE tester 1"}], 1, []))
        self.assertEqual(b.get("/api/me").json["error"], "signed_out")
        claim = Browser(self.site.app).post("/api/auth/claim", {"link": item["code"]}).json
        self.assertEqual((claim["state"], claim["skip"]), ("welcome", True))
        self.assertEqual(self.site.admin_call("POST", "/api/admin/readers/codes", {"ids": [anan["id"]],
                                                                                   "unbind": "yes"}).status, 400)

    def test_invite_links_for_the_phone_s_own_browser(self):
        site = self.make(invite={"external_browser": True})
        anan = self.invite(site=site)
        self.assertTrue(anan["link"].startswith("https://review.example.org/?openExternalBrowser=1#k="), anan["link"])
        self.assertEqual(anan["link"].split("#k=")[1], anan["code"])
        r = site.admin_call("POST", "/api/admin/readers/codes", {"ids": [anan["id"]]})
        self.assertIn("/?openExternalBrowser=1#k=", r.json["readers"][0]["link"])
        site.admin_call("POST", "/api/admin/groups", {"name": "Pastors", "grants": ["SC"]})
        r = site.admin_call("POST", "/api/admin/general-links", {"group": "Pastors"})
        self.assertIn("/?openExternalBrowser=1#join=", r.json["link"])
        self.assertIn("/#k=", self.invite("Mali")["link"])


class Requests(Base):
    def setUp(self):
        super().setUp()
        r = self.site.admin_call("POST", "/api/admin/groups", {"name": "Pastors", "grants": ["SC01"]})
        self.assertEqual(r.status, 201)
        r = self.site.admin_call("POST", "/api/admin/general-links", {"group": "Pastors", "uses": 3})
        self.assertEqual(r.status, 201, r.body)
        self.link = r.json
        self.join = r.json["code"]

    def test_a_request_through_line_opens_nothing_before_approval(self):
        self.assertEqual((self.link["state"], self.link["uses_most"], self.link["link"].split("#join=")[1]),
                         ("open", 3, self.join))
        b = Browser(self.site.app)
        self.assertEqual(b.post("/api/auth/join", {"join": self.join}).json["state"], "open")
        self.assertEqual(b.post("/api/auth/join", {"join": "x" * 32}).json["state"], "closed")
        self.assertEqual(self.result(self.line_signin(b, {"join": self.join}, user=2)), "request_sent")
        self.assertEqual(b.get("/api/me").json["error"], "no_code")
        (note,) = [m for m in self.site.mails() if m[0] == "translator@example.org"]
        self.assertEqual(note[1], "A request to read: LINE tester 3")
        self.assertIn("general link of the group Pastors", note[2])
        self.assertEqual(self.result(self.line_signin(Browser(self.site.app), {"join": self.join}, user=2)),
                         "request_waiting")
        self.assertEqual(self.result(self.line_signin(Browser(self.site.app), user=2)), "request_waiting")
        reqs = self.site.admin_call("GET", "/api/admin/requests").json
        self.assertEqual((reqs["open"], reqs["requests"][0]["display"], reqs["requests"][0]["group"]),
                         (1, "LINE tester 3", "Pastors"))
        self.assertEqual(self.site.admin_call("GET", "/api/admin/auth").json["requests_open"], 1)
        r = self.site.admin_call("POST", f"/api/admin/requests/{reqs['requests'][0]['id']}/approve", {})
        self.assertEqual(r.status, 200, r.body)
        self.assertEqual((r.json["reader"]["name"], r.json["reader"]["groups"], r.json["request"]["decision"]),
                         ("LINE tester 3", ["Pastors"], "approved"))
        # Now the same LINE account signs in, and the group's chapters open.
        b2 = Browser(self.site.app)
        self.assertEqual(self.result(self.line_signin(b2, user=2)), "signed_in")
        self.assertEqual([c["id"] for c in b2.get("/api/me").json["chapters"]], ["SC01"])
        self.assertEqual(self.site.admin_call("POST", f"/api/admin/requests/{reqs['requests'][0]['id']}/approve",
                                              {}).json["error"], "request_decided")
        self.assertEqual(self.site.admin_call("GET", "/api/admin/general-links").json["links"][0]["uses"], 1)

    def test_decline_forget_and_approve_into_a_reader(self):
        b = Browser(self.site.app)
        self.assertEqual(self.email_signin(b, "new@example.org", {"join": self.join}).json["result"], "request_sent")
        qid = self.site.admin_call("GET", "/api/admin/requests").json["requests"][0]["id"]
        self.assertEqual(self.site.admin_call("POST", f"/api/admin/requests/{qid}/decline").json["request"]["decision"],
                         "declined")
        self.assertEqual(self.email_signin(Browser(self.site.app), "new@example.org", {"join": self.join})
                         .json["result"], "request_declined")
        self.assertEqual(self.site.admin_call("DELETE", f"/api/admin/requests/{qid}").json["deleted"], qid)
        self.assertEqual(self.email_signin(Browser(self.site.app), "new@example.org", {"join": self.join})
                         .json["result"], "request_sent")
        qid = self.site.admin_call("GET", "/api/admin/requests").json["requests"][0]["id"]
        anan = self.invite()
        r = self.site.admin_call("POST", f"/api/admin/requests/{qid}/approve", {"reader": anan["id"]})
        self.assertEqual((r.status, r.json["reader"]["id"], r.json["request"]["name"]), (200, anan["id"], "Anan"))
        approved = [m for m in self.site.mails() if m[0] == "new@example.org"][-1]
        self.assertEqual(approved[1], mail.words()["approved_subject"]["th"])
        self.assertIn("The translator approved your request. Open https://", approved[2])
        self.assertEqual(self.email_signin(Browser(self.site.app), "new@example.org").json,
                         {"result": "signed_in", "name": "Anan"})

    def test_a_name_taken_is_refused_and_another_name_given(self):
        self.invite("LINE tester 1")
        self.line_signin(Browser(self.site.app), {"join": self.join}, user=0)
        qid = self.site.admin_call("GET", "/api/admin/requests").json["requests"][0]["id"]
        r = self.site.admin_call("POST", f"/api/admin/requests/{qid}/approve", {})
        self.assertEqual((r.status, r.json["error"]), (409, "name_taken"))
        self.assertEqual(self.site.admin_call("GET", "/api/admin/requests").json["open"], 1)
        r = self.site.admin_call("POST", f"/api/admin/requests/{qid}/approve", {"name": "Somchai", "grants": ["SC"],
                                                                                "english": True})
        self.assertEqual((r.status, r.json["reader"]["grants"], r.json["reader"]["english"]), (200, ["SC"], True))
        self.assertEqual(r.json["reader"]["groups"], [])

    def test_the_link_closes(self):
        for user in range(3):
            self.assertEqual(self.result(self.line_signin(Browser(self.site.app), {"join": self.join}, user=user)),
                             "request_sent")
        links = self.site.admin_call("GET", "/api/admin/general-links?group=Pastors").json["links"]
        self.assertEqual((links[0]["state"], links[0]["uses"], links[0]["waiting"]), ("full", 3, 3))
        r = Browser(self.site.app).post("/api/auth/line/start", {"join": self.join})
        self.assertEqual((r.status, r.json["error"]), (410, "join_closed"))
        new = self.site.admin_call("POST", "/api/admin/general-links", {"group": "Pastors", "days": 5}).json
        self.assertEqual(new["replaced"], [self.link["id"]])
        old = self.site.admin_call("GET", "/api/admin/general-links").json["links"]
        self.assertEqual([x["state"] for x in old], ["open", "off"])
        self.assertEqual(Browser(self.site.app).post("/api/auth/join", {"join": self.join}).json["state"], "closed")
        r = self.site.admin_call("PATCH", f"/api/admin/general-links/{new['id']}", {"active": False})
        self.assertEqual((r.json["state"], r.json["changed"]), ("off", True))
        self.assertEqual(self.site.admin_call("PATCH", f"/api/admin/general-links/{new['id']}",
                                              {"active": True}).status, 400)
        self.assertEqual(Browser(self.site.app).post("/api/auth/join", {"join": new["code"]}).json["state"], "closed")
        con = db.connect(self.site.data / db.DB_NAME)
        self.addCleanup(con.close)
        last = self.site.admin_call("POST", "/api/admin/general-links", {"group": "Pastors"}).json
        con.execute("UPDATE general_link SET expires = ? WHERE id = ?", (db.ago(minutes=1), last["id"]))
        self.assertEqual(self.site.admin_call("GET", "/api/admin/general-links").json["links"][0]["state"], "expired")

    def test_a_reader_who_opens_the_general_link_is_signed_in(self):
        anan = self.invite()
        self.line_signin(Browser(self.site.app), {"link": anan["code"]})
        self.assertEqual(self.result(self.line_signin(Browser(self.site.app), {"join": self.join})), "signed_in")
        self.assertEqual(self.site.admin_call("GET", "/api/admin/requests").json["open"], 0)


class Notes(Base):
    def test_the_translator_is_told_of_a_first_sign_in_once(self):
        anan = self.invite()
        self.line_signin(Browser(self.site.app), {"link": anan["code"]})
        self.line_signin(Browser(self.site.app))
        notes = [m for m in self.site.mails() if m[0] == "translator@example.org"]
        self.assertEqual([n[1] for n in notes], ["Anan signed in for the first time"])
        self.assertIn("with LINE as LINE tester 1", notes[0][2])

    def test_the_switches_and_no_address(self):
        for extra in ({"notify": {"first_signin": False}}, {"notify": {"email": ""}}):
            site = self.make(**extra)
            anan = self.invite(site=site)
            r = self.line_signin(Browser(site.app), {"link": anan["code"]})
            self.assertEqual(self.result(r), "signed_in")
            self.assertEqual([m for m in site.mails() if m[0] == "translator@example.org"], [], extra)


class Admin(Base):
    def test_the_settings_without_any_secret(self):
        site = self.make(mail={"provider": "smtp", "host": "127.0.0.1", "port": 2525, "security": "none",
                               "user": "u", "password": "secret-password", "from": "review@example.org"})
        r = site.admin_call("GET", "/api/admin/auth")
        self.assertEqual(r.status, 200)
        text = r.body.decode()
        for secret in (self.line.channel_secret, "secret-password"):
            self.assertNotIn(secret, text)
        a = r.json
        self.assertEqual((a["routes"], a["session_days"], a["require_identity"]),
                         ({"line": True, "email": True}, 30, False))
        self.assertEqual((a["mail"]["provider"], a["mail"]["user"], a["notify"]["on"]), ("smtp", True, True))
        self.assertEqual(a["line"]["callback"], "https://review.example.org/api/auth/line/callback")
        self.assertEqual(a["invite"], {"external_browser": False, "general_days": 90, "general_uses": 100})
        self.assertIsNone(a["last_mail"])
        self.assertFalse(a["dev"])

    def test_check_and_test_mail(self):
        r = self.site.admin_call("POST", "/api/admin/auth/check")
        self.assertEqual((r.json["line"]["ok"], r.json["mail"]["ok"]), (True, True), r.body)
        r = self.site.admin_call("POST", "/api/admin/auth/test-mail", {"to": "Me@Example.org"})
        self.assertEqual(r.json, {"sent": True, "to": "me@example.org", "detail": ""})
        self.assertEqual(self.site.mails()[-1][1], "A test mail from the proofreading site")
        self.assertEqual(self.site.admin_call("GET", "/api/admin/auth").json["last_mail"]["kind"], "test")
        self.assertEqual(self.site.admin_call("POST", "/api/admin/auth/test-mail", {"to": "me"}).status, 400)
        bare = AuthSite({})
        self.addCleanup(bare.close)
        r = bare.admin_call("POST", "/api/admin/auth/check").json
        self.assertEqual((r["line"]["on"], r["mail"]["on"]), (False, False))
        self.assertEqual(bare.admin_call("POST", "/api/admin/auth/test-mail", {"to": "a@example.org"}).status, 409)

    def test_identities(self):
        anan, mali = self.invite(), self.invite("Mali")
        r = self.site.admin_call("POST", "/api/admin/identities", {"reader": anan["id"], "address": "Anan@Example.org"})
        self.assertEqual((r.status, r.json["display"], r.json["added"]), (201, "anan@example.org", True))
        self.assertEqual(self.site.admin_call("POST", "/api/admin/identities", {
            "reader": anan["id"], "address": "anan@example.org"}).status, 200)
        r = self.site.admin_call("POST", "/api/admin/identities", {"reader": mali["id"], "address": "anan@example.org"})
        self.assertEqual((r.status, r.json["error"], r.json["name"]), (409, "identity_taken", "Anan"))
        self.assertEqual(self.site.admin_call("POST", "/api/admin/identities", {
            "reader": anan["id"], "provider": "line", "address": "x"}).status, 400)
        # The reader signs in with the address without opening the link.
        b = Browser(self.site.app)
        self.assertEqual(self.email_signin(b, "anan@example.org").json["result"], "signed_in")
        ids = self.site.admin_call("GET", f"/api/admin/identities?reader={anan['id']}").json["identities"]
        self.assertEqual((len(ids), ids[0]["sessions"]), (1, 1))
        r = self.site.admin_call("DELETE", f"/api/admin/identities/{ids[0]['id']}")
        self.assertEqual((r.json["sessions_ended"], r.json["identities_left"], r.json["name"]), (1, 0, "Anan"))
        self.assertEqual(b.get("/api/me").json["error"], "signed_out")
        self.assertEqual(self.site.admin_call("DELETE", f"/api/admin/identities/{ids[0]['id']}").status, 404)

    def test_the_reader_list(self):
        anan = self.invite()
        self.invite("Mali")
        self.line_signin(Browser(self.site.app), {"link": anan["code"]})
        names = lambda q: [r["name"] for r in self.site.admin_call("GET", "/api/admin/readers" + q).json["readers"]]
        self.assertEqual(names("?identity=line"), ["Anan"])
        self.assertEqual(names("?identity=any"), ["Anan"])
        self.assertEqual(names("?identity=none"), ["Mali"])
        self.assertEqual(names("?identity=email"), [])
        self.assertEqual(self.site.admin_call("GET", "/api/admin/readers?identity=x").status, 400)
        r = self.site.admin_call("GET", "/api/admin/readers?name=Mali").json["readers"][0]
        self.assertEqual((r["identities"], r["sessions"], r["link_used"], r["first_signin"], r["link_signs_in"],
                          r["last_seen"]), ([], 0, None, None, False, None))
        r = self.site.admin_call("PATCH", "/api/admin/readers", {"changes": [{"id": anan["id"], "link_signs_in": True}]})
        self.assertTrue(r.json["readers"][0]["link_signs_in"])
        self.assertEqual(self.site.admin_call("PATCH", f"/api/admin/readers/{anan['id']}",
                                              {"link_signs_in": "on"}).status, 400)


class Settings(unittest.TestCase):
    def refused(self, config, words):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        data = Path(tmp.name)
        db.setup(data, "https://review.example.org")
        path = data / db.CONFIG
        path.write_text(json.dumps(dict(json.loads(path.read_text()), **config)))
        with self.assertRaises(ValueError) as e:
            App(data)
        self.assertIn("config.json", str(e.exception))
        self.assertIn(words, str(e.exception))

    def test_each_wrong_setting_is_named(self):
        line = {"channel_id": "1234567890", "channel_secret": "a" * 32}
        cases = [
            ({"auth": {"line": {"channel_id": "1234567890"}}}, '"auth.line.channel_secret"'),
            ({"auth": {"line": {"channel_id": "abc", "channel_secret": "a" * 32}}}, '"auth.line.channel_id"'),
            ({"auth": {"line": dict(line, token_url="http://api.line.me/x")}}, '"auth.line.token_url"'),
            ({"auth": {"line": dict(line, scope="x")}}, "no setting named scope"),
            ({"auth": {"email": True}}, 'there is no "mail"'),
            ({"auth": {"email": "yes"}}, '"auth.email" must be true or false'),
            ({"auth": {"require_identity": True}}, "no reader could sign in"),
            ({"auth": {"session_days": 0}}, '"auth.session_days"'),
            ({"auth": {"sessions": 3}}, '"auth" has no setting named sessions'),
            ({"mail": {"provider": "sendmail"}}, '"mail.provider"'),
            ({"mail": {"provider": "smtp"}}, '"mail.from"'),
            ({"mail": {"provider": "smtp", "from": "a@example.org", "user": "u"}}, "go together"),
            ({"mail": {"provider": "smtp", "from": "a@example.org", "host": "mail.example.org", "user": "u",
                       "password": "p"}}, "starttls or ssl"),
            ({"mail": {"provider": "smtp", "from": "a@example.org", "security": "tls"}}, '"mail.security"'),
            ({"mail": {"provider": "resend", "from": "a@example.org"}}, '"mail.api_key"'),
            ({"mail": {"provider": "file", "from": "a@example.org", "api_key": "x"}}, "no setting named api_key"),
            ({"notify": {"email": "translator"}}, '"notify.email"'),
            ({"notify": {"requests": "on"}}, '"notify.requests"'),
            ({"invite": {"external_browser": 1}}, '"invite.external_browser"'),
            ({"invite": {"general_days": 0}}, '"invite.general_days"'),
        ]
        for config, words in cases:
            with self.subTest(words):
                self.refused(config, words)

    def test_line_needs_the_public_url(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        data = Path(tmp.name)
        data.joinpath(db.CONFIG).write_text(json.dumps({"auth": {"line": {"channel_id": "1",
                                                                           "channel_secret": "a" * 32}}}))
        with self.assertRaises(ValueError) as e:
            auth.load_settings(data)
        self.assertIn("public_url", str(e.exception))

    def test_defaults(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        s = auth.load_settings(Path(tmp.name))
        self.assertEqual((s.routes, s.session_days, s.require_identity, s.mail), ({"line": False, "email": False}, 30,
                                                                                 False, None))
        self.assertEqual(s.notify, {"email": "", "requests": True, "first_signin": True})
        self.assertEqual(auth.LINE_DEFAULTS, {"authorize_url": "https://access.line.me/oauth2/v2.1/authorize",
                                              "token_url": "https://api.line.me/oauth2/v2.1/token",
                                              "verify_url": "https://api.line.me/oauth2/v2.1/verify",
                                              "issuer": "https://access.line.me"})
        m = mail.load({"provider": "smtp", "from": "review@laoegw.com"}, tmp.name, "x")
        self.assertEqual((m["host"], m["port"], m["security"], m["user"]), ("127.0.0.1", 25, "none", ""))
        self.assertEqual(mail.load({"provider": "smtp", "from": "a@b.org", "security": "starttls"}, tmp.name,
                                   "x")["port"], 587)

    def test_the_api_names_a_wrong_setting_and_does_not_start(self):
        text = (ROOT / "server" / "prod.py").read_text()
        self.assertIn("except ValueError as e:", text)
        self.assertIn("The API did not start.", text)


class Mailers(unittest.TestCase):
    def test_smtp(self):
        server = SMTPStandIn()
        self.addCleanup(server.server_close)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.shutdown)
        m = mail.Mailer(mail.load({"provider": "smtp", "from": "review@laoegw.com", "port": server.server_address[1],
                                   "from_name": "Proofreading"}, "/tmp", "x"))
        m.send("reader@example.org", "123456 is your sign-in code", "123456 is your code. ภาษาไทย")
        (got,) = server.messages
        self.assertEqual([r.upper() for r in got["rcpt"]], ["RCPT TO:<READER@EXAMPLE.ORG>"])
        msg = email.message_from_bytes(got["data"], policy=email.policy.default)
        self.assertEqual((msg["From"], msg["Subject"]), ("Proofreading <review@laoegw.com>",
                                                         "123456 is your sign-in code"))
        self.assertIn("ภาษาไทย", msg.get_content())
        # The code mail as the site sends it: the Thai subject travels encoded and arrives whole (70-verify.md item 3).
        title = mail.subject("code_subject", code="654321")
        m.send("reader@example.org", title, mail.both("code_body", code="654321", minutes=10))
        self.assertEqual(len(server.messages), 2)
        msg = email.message_from_bytes(server.messages[1]["data"], policy=email.policy.default)
        self.assertEqual(msg["Subject"], title)
        self.assertTrue(server.messages[1]["data"].isascii())
        self.assertTrue(msg.get_content().startswith("654321 "))
        self.assertEqual(m.check()[0], True)

    def test_smtp_that_cannot_be_reached(self):
        m = mail.Mailer(mail.load({"provider": "smtp", "from": "a@example.org", "port": closed_port()}, "/tmp", "x"))
        with self.assertRaises(mail.MailError) as e:
            m.send("b@example.org", "s", "t")
        self.assertIn(f"The mail server at 127.0.0.1:", str(e.exception))
        self.assertFalse(m.check()[0])

    def test_resend(self):
        got = []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                got.append((self.headers["Authorization"], body))
                status = 200 if body["to"] == ["ok@example.org"] else 422
                data = json.dumps({"id": "1"} if status == 200 else {"message": "The to field is invalid."}).encode()
                self.send_response(status)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.addCleanup(server.server_close)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.shutdown)
        m = mail.Mailer(mail.load({"provider": "resend", "from": "review@laoegw.com", "api_key": "re_testkey123",
                                   "url": f"http://127.0.0.1:{server.server_address[1]}/emails"}, "/tmp", "x"))
        m.send("ok@example.org", "Subject", "Text")
        self.assertEqual(got[0][0], "Bearer re_testkey123")
        self.assertEqual(got[0][1], {"from": "Proofreading site <review@laoegw.com>", "to": ["ok@example.org"],
                                     "subject": "Subject", "text": "Text"})
        with self.assertRaises(mail.MailError) as e:
            m.send("bad@example.org", "Subject", "Text")
        self.assertEqual(str(e.exception), "Resend answered 422: The to field is invalid.")

    def test_the_words_have_english_and_thai(self):
        words = mail.words()
        self.assertEqual(set(words), {"code_subject", "code_body", "approved_subject", "approved_body"})
        for key, w in words.items():
            self.assertEqual(set(w), {"en", "th"}, key)
            self.assertTrue(w["en"], key)
            # The Thai of 69b-thai-strings-9.md item 6 is written (70-verify.md item 3): the same values to fill in,
            # the same paragraphs, no Thai or Lao digit, no invisible character and no full stop at the end.
            self.assertTrue(w["th"], key)
            self.assertEqual(sorted(re.findall(r"\{(\w+)\}", w["th"])), sorted(re.findall(r"\{(\w+)\}", w["en"])), key)
            self.assertEqual(w["th"].count("\n\n"), w["en"].count("\n\n"), key)
            self.assertIsNone(re.search("[\u0e50-\u0e59\u0ed0-\u0ed9\u200b-\u200d\u2060\ufeff]", w["th"]), key)
            self.assertFalse(w["th"].endswith("."), key)
            self.assertEqual(w["th"], w["th"].strip(), key)
        values = {"code": "123456", "minutes": 10, "url": "https://review.example.org/"}
        self.assertEqual(mail.subject("code_subject", **values), words["code_subject"]["th"].format(**values))
        self.assertTrue(mail.subject("code_subject", **values).startswith("123456 "))
        th, en = (words["approved_body"][lang].format(**values) for lang in ("th", "en"))
        self.assertEqual(mail.both("approved_body", **values), f"{th}\n\n{en}")
        self.assertIn(" https://review.example.org/ ", th)


class Dev(unittest.TestCase):
    def test_enter_as_a_reader_on_the_dev_server_alone(self):
        site = Site()
        self.addCleanup(site.close)
        anan = site.invite("Anan", ["SC"])
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        # The production API knows no dev route and says dev false.
        self.assertEqual(wsgi(site.app, "POST", "/api/dev/enter", {"reader": anan["id"]}, {"X-Review-Page": "1"})[0],
                         404)
        self.assertFalse(json.loads(wsgi(site.app, "GET", "/api/auth/state", None, {"X-Review-Page": "1"})[2])["dev"])
        httpd = dev.make(site.app, Path(tmp.name), 0, quiet=True)
        self.addCleanup(httpd.server_close)
        dev_site = httpd.get_app()
        b = Browser(dev_site)
        self.assertTrue(b.get("/api/auth/state").json["dev"])
        self.assertEqual(b.get("/api/auth/state").json["routes"], {"line": True, "email": True})
        self.assertEqual(b.get("/api/dev/readers").json["readers"], [{"id": anan["id"], "name": "Anan", "active": True}])
        self.assertEqual(b.post("/api/dev/enter", {"reader": anan["id"]}, page=False).status, 403)
        r = b.post("/api/dev/enter", {"reader": anan["id"]})
        self.assertEqual(r.json, {"id": anan["id"], "name": "Anan"})
        self.assertEqual(b.get("/api/me").json["name"], "Anan")
        self.assertEqual(b.get("/api/auth/state").json["via"], "dev")
        self.assertEqual(b.post("/api/dev/enter", {"reader": 999}).status, 404)
        # Email codes go to files in the data directory.
        b2 = Browser(dev_site)
        b2.post("/api/auth/email/start", {"email": "x@example.org", "link": anan["code"]})
        site.app.mail_idle()
        self.assertEqual(len(list((site.data / "mail").glob("*.eml"))), 1)

    def test_no_production_module_imports_the_dev_server(self):
        for name in ("app.py", "auth.py", "accounts.py", "people.py", "prod.py", "mail.py", "common.py", "db.py"):
            text = (ROOT / "server" / name).read_text()
            self.assertNotIn("import dev", text, name)
            self.assertNotIn("from .dev", text, name)
            self.assertNotIn("StandIn", text, name)


class Helpers(unittest.TestCase):
    def test_client_key_and_six_digits(self):
        class R:
            def __init__(self, addr):
                self.environ = {"REMOTE_ADDR": addr}
        # 65-security.md item 11: every written form of an IPv6 address counts as its /64 network.
        self.assertEqual(auth.client_key(R("2001:db8:1:2:3:4:5:6")), "2001:db8:1:2::/64")
        self.assertEqual(auth.client_key(R("2001:db8::1")), auth.client_key(R("2001:db8:0:0:ffff::9")))
        self.assertEqual(auth.client_key(R("2001:DB8::1")), "2001:db8::/64")
        self.assertNotEqual(auth.client_key(R("2001:db8::1")), auth.client_key(R("2001:db8:0:1::1")))
        self.assertEqual(auth.client_key(R("::ffff:203.0.113.7")), "203.0.113.7")
        self.assertEqual(auth.client_key(R("203.0.113.7")), "203.0.113.7")
        self.assertEqual(auth.client_key(R("")), "")
        self.assertEqual(auth.six_digits(" 12 34 56 "), "123456")
        self.assertEqual(auth.six_digits("\u0e51\u0e52\u0e53\u0e54\u0e55\u0e56"), "123456")
        self.assertIsNone(auth.six_digits("12345a"))

    def test_access_errors_have_their_status(self):
        for code, status in (("signed_out", 401), ("stopped", 401), ("link_used", 401), ("sign_in_required", 401),
                             ("bad_page", 403)):
            self.assertEqual(app_module.ACCESS_ERRORS[code][0], status)
        self.assertEqual(set(auth.RESULTS), {"signed_in", "added", "request_sent", "request_waiting",
                                             "request_declined", "no_account", "identity_taken", "link_used",
                                             "link_signs_in", "stopped",
                                             "join_closed", "join_busy", "cancelled", "expired", "other_browser",
                                             "failed"})


class Migration8(unittest.TestCase):
    def test_a_version_7_database_keeps_every_row(self):
        from test_versions import database_at
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / db.DB_NAME
        con = database_at(path, 7)
        con.execute("INSERT INTO reader (name, code_hash, created) VALUES ('R', 'x', 'now')")
        con.execute("INSERT INTO reader_device (reader, link, device, state, first_seen, last_seen)"
                    " VALUES (1, 'x', 'd', 'ok', 'now', 'now')")
        con.execute("INSERT INTO comment_gone (id, reader, book, ch, at, client_id) VALUES (4, 1, 'SC', 'SC01', 'now', 'c')")
        con.commit()
        counts = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in
                  ("reader", "reader_device", "comment_gone")}
        con.close()
        db.init_db(path)
        con = sqlite3.connect(path)
        self.addCleanup(con.close)
        self.assertEqual(con.execute("PRAGMA user_version").fetchone()[0], 8)
        for t, n in counts.items():
            self.assertEqual(con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0], n, t)
        self.assertEqual(con.execute("SELECT link_used, first_signin, link_signs_in FROM reader").fetchall(),
                         [(None, None, 0)])
        for t in ("identity", "session", "auth_flow", "general_link", "access_request", "mail_log"):
            self.assertEqual(con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0], 0, t)
        self.assertEqual(con.execute("PRAGMA integrity_check").fetchone()[0], "ok")
        self.assertEqual(con.execute("PRAGMA foreign_key_check").fetchall(), [])
        con.close()
        db.init_db(path)        # a second start changes nothing


class Round4aFixes(Base):
    """The fixes of 69-fixes.md: each test names the finding it covers."""

    def test_an_add_finishes_only_while_its_browser_is_signed_in(self):
        # 65-security.md item 2: the translator's sign-out also ends an add the browser began.
        anan = self.invite()
        b = Browser(self.site.app)
        self.email_signin(b, "anan@example.org", {"link": anan["code"]})
        r = b.post("/api/auth/email/start", {"email": "keeper@example.org", "add": True})
        self.assertEqual(r.status, 200)
        code = self.site.code_in(self.site.mails()[-1][2])
        self.site.admin_call("PATCH", "/api/admin/sessions", {"readers": [anan["id"]]})
        self.assertEqual(b.post("/api/auth/email/finish", {"code": code}).json["result"], "expired")
        # LINE: the add began, then every browser of the reader was signed out.
        b2 = Browser(self.site.app)
        self.email_signin(b2, "anan@example.org")
        start = b2.post("/api/auth/line/start", {"add": True})
        self.site.admin_call("PATCH", "/api/admin/sessions", {"readers": [anan["id"]]})
        q = {k: v[-1] for k, v in parse_qs(urlsplit(start.json["url"]).query).items()}
        back = urlsplit(self.line.approve(q, 1))
        self.assertEqual(self.result(b2.get(back.path + "?" + back.query, page=False)), "expired")
        ids = self.site.admin_call("GET", f"/api/admin/identities?reader={anan['id']}").json["identities"]
        self.assertEqual([i["display"] for i in ids], ["anan@example.org"])
        # A browser still signed in adds as before.
        self.assertEqual(self.email_signin(b2, "anan@example.org").json["result"], "signed_in")
        self.assertEqual(self.email_signin(b2, "second@example.org", {"add": True}).json["result"], "added")

    def test_codes_typed_at_the_same_moment_get_three_tries_between_them(self):
        # 65-security.md item 3 and 66-adversarial.md item 4.
        anan = self.invite()
        for run in range(3):
            b = Browser(self.site.app)
            b.post("/api/auth/email/start", {"email": f"anan{run}@example.org", "link": anan["code"]},
                   environ={"REMOTE_ADDR": f"10.40.{run}.1"})
            code = self.site.code_in(self.site.mails()[-1][2])
            wrong = [f"{(int(code) + n) % 10 ** 6:06d}" for n in range(1, 9)]
            gate = threading.Barrier(len(wrong))
            answers = []

            def guess(digits, n):
                gate.wait()
                answers.append(b.post("/api/auth/email/finish", {"code": digits},
                                      environ={"REMOTE_ADDR": f"10.41.{run}.{n}"}).json)

            threads = [threading.Thread(target=guess, args=(d, n)) for n, d in enumerate(wrong)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            con = db.connect(self.site.data / db.DB_NAME)
            tries = con.execute("SELECT MAX(tries) FROM auth_flow WHERE email = ?", (f"anan{run}@example.org",)).fetchone()[0]
            con.close()
            self.assertEqual(tries, 3, answers)
            self.assertEqual(sum(1 for a in answers if a.get("error") == "wrong_code"), 2, answers)

    def test_thirty_wrong_codes_an_hour_from_one_address(self):
        # 65-security.md item 4.
        anan = self.invite()
        refused = None
        for n in range(auth.WRONG_CODES_PER_HOUR // 2 + 2):
            b = Browser(self.site.app)
            ip = {"REMOTE_ADDR": "198.51.100.30"}
            with mock.patch.object(auth, "FINISHES_PER_MINUTE", 1000), mock.patch.object(auth, "LINK_CODES_PER_HOUR", 1000):
                b.post("/api/auth/email/start", {"email": f"w{n}@example.org", "link": anan["code"]},
                       environ={"REMOTE_ADDR": f"10.42.0.{n}"})
                code = self.site.code_in(self.site.mails()[-1][2])
                wrong = f"{(int(code) + 1) % 10 ** 6:06d}"
                for _ in range(2):
                    r = b.post("/api/auth/email/finish", {"code": wrong}, environ=ip)
                    if r.status == 429:
                        refused = refused or (n, r)
        self.assertIsNotNone(refused)
        n, r = refused
        self.assertEqual((n, r.json["limit"]), (auth.WRONG_CODES_PER_HOUR // 2, "wrong"))
        self.assertGreater(int(r.headers["retry-after"]), 3000)

    def test_the_first_sign_in_note_names_the_step_that_removes_a_stranger(self):
        # 65-security.md item 6.
        mali = self.invite("Mali Boon")
        self.line_signin(Browser(self.site.app), {"link": mali["code"]})
        (note,) = [m for m in self.site.mails() if m[0] == "translator@example.org"]
        self.assertIn("review.py relink 'Mali Boon' --unbind", note[2])
        self.assertIn('New links with "and remove their LINE accounts and addresses" ticked', note[2])
        self.assertNotIn("sign that browser out", note[2])

    def test_an_unknown_browser_is_sent_to_the_page_without_a_name(self):
        # 68-reader.md item 8.
        anan = self.invite()
        b = Browser(self.site.app, agent="Mozilla/5.0 (Mobile; rv:48.0) Gecko/48.0")
        self.line_signin(b, {"link": anan["code"]})
        (mine,) = b.get("/api/auth/sessions").json["sessions"]
        self.assertEqual(mine["agent"], "")
        (theirs,) = self.site.admin_call("GET", f"/api/admin/sessions?reader={anan['id']}").json["sessions"]
        self.assertEqual(theirs["agent"], "an unknown browser")

    def test_a_person_who_asked_by_email_sees_the_request_from_the_sign_in_screen(self):
        # 66-adversarial.md item 2: a closed general link shows the sign-in screen, where a person who asked by
        # email gets a code and sees whether the request waits or was declined.
        self.site.admin_call("POST", "/api/admin/groups", {"name": "Youth", "grants": ["SC01"]})
        join = self.site.admin_call("POST", "/api/admin/general-links", {"group": "Youth"}).json["code"]
        self.assertEqual(self.email_signin(Browser(self.site.app), "ploy@example.org", {"join": join}).json["result"],
                         "request_sent")
        self.site.admin_call("POST", "/api/admin/general-links", {"group": "Youth"})
        r = Browser(self.site.app).post("/api/auth/email/start", {"email": "ploy@example.org", "join": join})
        self.assertEqual((r.status, r.json["error"]), (410, "join_closed"))
        self.assertEqual(self.email_signin(Browser(self.site.app), "ploy@example.org").json["result"],
                         "request_waiting")
        qid = self.site.admin_call("GET", "/api/admin/requests").json["requests"][0]["id"]
        self.site.admin_call("POST", f"/api/admin/requests/{qid}/decline")
        self.assertEqual(self.email_signin(Browser(self.site.app), "ploy@example.org").json["result"],
                         "request_declined")
        # An address that never asked still gets no code, with the same answer.
        before = len(self.site.mails())
        r = Browser(self.site.app).post("/api/auth/email/start", {"email": "nobody@example.org"})
        self.assertEqual((r.status, len(self.site.mails())), (200, before))

    def test_removing_a_group_counts_its_general_link_and_waiting_requests(self):
        # 66-adversarial.md item 9.
        self.site.admin_call("POST", "/api/admin/groups", {"name": "Youth", "grants": ["SC01"]})
        join = self.site.admin_call("POST", "/api/admin/general-links", {"group": "Youth"}).json["code"]
        self.assertEqual(self.result(self.line_signin(Browser(self.site.app), {"join": join}, user=2)), "request_sent")
        gid = next(g["id"] for g in self.site.admin_call("GET", "/api/admin/groups").json["groups"]
                   if g["name"] == "Youth")
        r = self.site.admin_call("DELETE", f"/api/admin/groups/{gid}")
        self.assertEqual((r.json["general_links"], r.json["requests_waiting"]), (1, 1))
        (q,) = self.site.admin_call("GET", "/api/admin/requests").json["requests"]
        r = self.site.admin_call("POST", f"/api/admin/requests/{q['id']}/approve", {})
        self.assertEqual((r.status, r.json["error"]), (400, "no_group"))
        self.assertIn(f"review.py request approve {q['id']} --grant SC01, or --group GROUP", r.json["message"])
        r = self.site.admin_call("POST", f"/api/admin/requests/{q['id']}/approve", {"grants": ["SC01"]})
        self.assertEqual(r.status, 200, r.body)


class Round4aServer(unittest.TestCase):
    """The fixes of 69-fixes.md that need no stand-in for LINE."""

    def data_with(self, text):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        data = Path(tmp.name)
        db.setup(data, "https://review.example.org")
        (data / db.CONFIG).write_text(text)
        return data

    def test_a_config_json_that_is_not_valid_json_stops_the_start(self):
        # 67-operations.md item 1: a stray comma no longer starts the site without its settings.
        data = self.data_with('{"public_url": "https://review.example.org", "auth": {"email": true,}}')
        with self.assertRaises(ValueError) as e:
            App(data)
        self.assertIn("config.json in", str(e.exception))
        self.assertIn("is not valid JSON (line 1, column", str(e.exception))
        self.assertIn("python3 -m json.tool", str(e.exception))
        for text, words in (('{"public_url": "https://review.example.org", "notfy": {}}', 'no entry named "notfy"'),
                            ("[1, 2]", "must hold one JSON object"),
                            ('{"public_url": \u201chttps://x\u201d}', "is not valid JSON")):
            with self.subTest(words), self.assertRaises(ValueError) as e:
                App(self.data_with(text))
            self.assertIn(words, str(e.exception))
        # setup never writes over a config.json it cannot read.
        data = self.data_with('{"public_url": "https://review.example.org",}')
        with self.assertRaises(ValueError):
            db.setup(data, "https://other.example.org")
        self.assertEqual((data / db.CONFIG).read_text(), '{"public_url": "https://review.example.org",}')
        # A missing config.json is still an empty one.
        (data / db.CONFIG).unlink()
        self.assertEqual(db.read_config(data), {})

    def test_an_http_public_url_with_signing_in_on_stops_the_start(self):
        # 65-security.md item 12.
        mail_cfg = {"provider": "file", "from": "review@example.org"}
        for url, ok in (("http://review.example.org", False), ("", False), ("https://review.example.org", True),
                        ("http://127.0.0.1:8087", True), ("http://localhost:8090", True)):
            cfg = {"auth": {"email": True}, "mail": mail_cfg}
            if url:
                cfg["public_url"] = url
            data = self.data_with(json.dumps(cfg))
            with self.subTest(url):
                if ok:
                    self.assertEqual(auth.load_settings(data).routes["email"], True)
                else:
                    with self.assertRaises(ValueError) as e:
                        auth.load_settings(data)
                    self.assertIn('"public_url" must be the site\'s https address', str(e.exception))
        # Without a sign-in route, an http address still starts, as before accounts.
        self.assertFalse(auth.load_settings(self.data_with('{"public_url": "http://review.example.org"}')).any_route)

    def test_an_address_holds_only_plain_characters_before_the_at(self):
        # 65-security.md item 10.
        for good in ("a.b-c_d+e%f@example.org", "Somchai.W@Gmail.com"):
            self.assertEqual(mail.address(good), good.lower(), good)
        for bad in ("x\x1b@evil.example", "x\x00@evil.example", "group:x@evil.example", "a(b)c@evil.example",
                    "\u202ex@evil.example", "x\u200b@evil.example", "\uff58@evil.example", "\"a b\"@evil.example",
                    "a,b@evil.example", "a@b@evil.example"):
            self.assertIsNone(mail.address(bad), repr(bad))

    def test_the_dev_server_refuses_another_host(self):
        # 65-security.md item 8: a page on a rebound address cannot reach the dev server.
        site = Site()
        self.addCleanup(site.close)
        anan = site.invite("Anan", ["SC"])
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        httpd = dev.make(site.app, Path(tmp.name), 0, quiet=True)
        self.addCleanup(httpd.server_close)
        dev_site = httpd.get_app()
        headers = {"X-Review-Page": "1", "Origin": "null", "Sec-Fetch-Site": "same-origin"}
        for host in ("rebind.example:8087", "evil.example", "127.0.0.1.evil.example:8087"):
            for method, path, body in (("GET", "/api/dev/readers", None), ("POST", "/api/dev/enter",
                                                                            {"reader": anan["id"]}),
                                       ("GET", "/api/me", None), ("GET", "/", None)):
                status, _, out = wsgi(dev_site, method, path, body, dict(headers, Host=host))
                self.assertEqual(status, 403, (host, path))
                if path.startswith("/api"):
                    self.assertEqual(json.loads(out)["error"], "bad_host")
        for host in ("127.0.0.1:8087", "localhost:8087", "[::1]:8087", "LOCALHOST"):
            self.assertEqual(wsgi(dev_site, "GET", "/api/dev/readers", None, dict(headers, Host=host))[0], 200, host)

    def test_mail_failures_quote_the_server_and_the_check_asks_it_to_take_a_mail(self):
        # 67-operations.md item 4.
        relay = smtp_standin(self, refuse_rcpt="554 5.7.1 <x@example.org>: Relay access denied")
        m = mail.Mailer(mail.load({"provider": "smtp", "from": "review@forum.laoegw.com",
                                   "port": relay.server_address[1]}, "/tmp", "x"))
        with self.assertRaises(mail.MailError) as e:
            m.send("reader@example.org", "s", "t")
        text = str(e.exception)
        self.assertIn(f"The mail server at 127.0.0.1:{relay.server_address[1]} refused to take the mail for that "
                      "address: 554 5.7.1 <x@example.org>: Relay access denied.", text)
        self.assertIn("may pass mail on to other domains only after a login", text)
        ok, detail = m.check("translator@example.org")
        self.assertFalse(ok)
        self.assertIn("Relay access denied", detail)
        self.assertEqual(relay.messages, [])
        good = smtp_standin(self)
        m = mail.Mailer(mail.load({"provider": "smtp", "from": "review@forum.laoegw.com",
                                   "port": good.server_address[1]}, "/tmp", "x"))
        ok, detail = m.check("translator@example.org")
        self.assertTrue(ok, detail)
        self.assertEqual(detail, f"The mail server at 127.0.0.1:{good.server_address[1]} accepted the connection and a "
                                 "mail from review@forum.laoegw.com to translator@example.org; no mail was sent.")
        self.assertEqual(good.messages, [])
        self.assertEqual(m.where(False), f"the mail server at 127.0.0.1:{good.server_address[1]}")
        # A certificate for another name: the reason stays, with the step to take.
        err = ssl.SSLCertVerificationError(1, "certificate verify failed")
        err.verify_message = "IP address mismatch, certificate is not valid for '127.0.0.1'."
        text = m.explain(err)
        self.assertTrue(text.startswith("The secure connection to the mail server at 127.0.0.1:"), text)
        self.assertIn("IP address mismatch", text)
        self.assertIn("Set mail.host to the name on the server's certificate", text)
        text = m.explain(smtplib.SMTPServerDisconnected("Connection unexpectedly closed: timed out"))
        self.assertTrue(text.endswith("did not answer within 10 seconds."), text)

    def test_a_stalled_mail_server_answers_mail_failed_in_seconds(self):
        # 67-operations.md item 5 and item 10: the API waits at most MAIL_WAIT seconds, and the journal says so.
        stalled = smtp_standin(self, stall=True)
        site = AuthSite({"auth": {"email": True}, "mail": {"provider": "smtp", "from": "review@example.org",
                                                           "port": stalled.server_address[1]}})
        self.addCleanup(site.close)
        site.publish(sample_chapter(1))
        anan = site.invite("Anan", ["SC"])
        journal = io.StringIO()
        began = time.monotonic()
        with mock.patch.object(auth, "MAIL_WAIT", 1), mock.patch("sys.stderr", journal):
            r = Browser(site.app).post("/api/auth/email/start", {"email": "anan@example.org", "link": anan["code"]})
        self.assertLess(time.monotonic() - began, 5)
        self.assertEqual((r.status, r.json["error"]), (503, "mail_failed"))
        self.assertIn("review: a sign-in code could not be sent: The mail server at 127.0.0.1:", journal.getvalue())
        self.assertIn("did not answer within 1 second.", journal.getvalue())
        last = site.admin_call("GET", "/api/admin/auth").json["last_mail"]
        self.assertEqual((last["kind"], last["ok"]), ("code", False))
        self.assertIn("did not answer within 1 second.", last["detail"])
        con = db.connect(site.data / db.DB_NAME)
        self.addCleanup(con.close)
        self.assertEqual(con.execute("SELECT COUNT(*) FROM auth_flow").fetchone()[0], 0)


# ---------- stand-ins ----------

def closed_port():
    import socket
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class SMTPHandler(socketserver.StreamRequestHandler):
    def handle(self):
        def say(text):
            self.wfile.write((text + "\r\n").encode())
        if getattr(self.server, "stall", False):
            # A mail server that takes the connection and never answers.
            self.server.stalled.wait(30)
            return
        say("220 stand-in ESMTP")
        rcpt = []
        while True:
            line = self.rfile.readline()
            if not line:
                return
            cmd = line.decode().strip()
            up = cmd.upper()
            if up.startswith("EHLO"):
                say("250-stand-in")
                say("250 8BITMIME")
            elif up.startswith(("HELO", "MAIL FROM", "NOOP", "RSET")):
                say("250 OK")
            elif up.startswith("RCPT TO") and getattr(self.server, "refuse_rcpt", ""):
                say(self.server.refuse_rcpt)
            elif up.startswith("RCPT TO"):
                rcpt.append(cmd)
                say("250 OK")
            elif up == "DATA":
                say("354 go on")
                data = b""
                while True:
                    part = self.rfile.readline()
                    if part in (b".\r\n", b""):
                        break
                    data += part[1:] if part.startswith(b"..") else part
                self.server.messages.append({"rcpt": rcpt, "data": data})
                say("250 OK")
            elif up == "QUIT":
                say("221 bye")
                return
            else:
                say("502 not here")


class SMTPStandIn(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, refuse_rcpt="", stall=False):
        super().__init__(("127.0.0.1", 0), SMTPHandler)
        self.messages = []
        self.refuse_rcpt, self.stall, self.stalled = refuse_rcpt, stall, threading.Event()


def smtp_standin(test, **kw):
    """An SMTP stand-in running until the test ends; its port is server_address[1]."""
    server = SMTPStandIn(**kw)
    test.addCleanup(server.server_close)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    test.addCleanup(server.shutdown)
    test.addCleanup(server.stalled.set)
    return server


if __name__ == "__main__":
    unittest.main()
