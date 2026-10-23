"""WSGI application for the proofreading site: the JSON API under /api/.

server.app:application reads its data directory from REVIEW_DATA on the
first request. Tests and the dev server build their own with App(data_dir).
A reader signs in with LINE or an email code and then sends the session
cookie (server/auth.py); a reader whose link still signs in by itself sends
"Authorization: Bearer <code>"; the routes under /api/admin/ take the admin
token instead. Each reader sees and changes only their own
comments, and only in published chapters open to them: covered by their own
grants or by the grants of a group of theirs that is switched on.

This module holds the reader routes, the chapter, round, export and reply
admin routes and the routing. Readers, groups and devices are in
server/people.py, sign-in and sessions in server/auth.py, the admin routes of
accounts in server/accounts.py, the mailer in server/mail.py, shared helpers
in server/common.py, and each feature in server/features/.

Where a link signs in by itself (server/auth.py, link_alone), it works on the
first devices_per_link devices that open it (two unless config.json says
otherwise): the page sends a random key made on the device in
X-Review-Device, and a further device waits for the translator's approval
(403 device_waiting). A reader sees only the chapters open to them now, and
only their comments on those chapters in the book's current review round; a
closed chapter refuses adding, changing and deleting comments, and a comment
of an earlier round can be read but no longer changed.

Every published version of a chapter is kept (chapter_version). The page
learns from GET /api/me which paragraphs changed since the version the reader
last opened (PUT /api/opened records it), and GET /api/earlier gives a
paragraph's wording in an earlier version. The admin routes answer only
through the SSH tunnel that review.py opens: Apache refuses /api/admin/ from
the internet and marks every request it passes on with X-Review-Proxy, which
the admin routes refuse as well.
"""
import functools
import hmac
import json
import os
import re
import sqlite3
import sys
import threading
import time
import traceback
import unicodedata
from collections import deque
from http import HTTPStatus
from pathlib import Path

from . import db, features
from .accounts import Accounts
from .auth import TOKEN_RE, SignIn
from .common import (ADMIN_LIMIT, GROUP_NAME_RE, REPLY_LIMIT, WAITING_MOST, HTTPError, Request, bool_field, clean,
                     device_agent, dumps, id_list, load_limits, name_key)
from .content import align_text, plain, safe_html, words_html
from .languages import REGISTRY
from .people import People
from .text import forbidden_char

CSP = ("default-src 'self'; img-src 'self' data:; frame-ancestors 'none'; "
       "base-uri 'none'; form-action 'none'")
SECURITY_HEADERS = [
    ("Content-Security-Policy", CSP),
    ("X-Content-Type-Options", "nosniff"),
    ("Referrer-Policy", "no-referrer"),
    ("X-Robots-Tag", "noindex"),
]

CHAPTER_LIMIT = ADMIN_LIMIT
CACHE_MOST = 256                 # chapters kept parsed in memory, and as many earlier versions
CHANGES_MOST = 1024              # comparisons of two versions of a chapter kept in memory
PROCESSED_MOST = 10000           # comments marked processed in one request; review.py sends 5000 at a time
REPLIES_MOST = 10000             # replies set in one request; review.py sends 5000 at a time
PAIRS_MOST = 500                 # sentence pairs in one paragraph
PROXY_HEADER = "X-Review-Proxy"  # Apache sets it on every request it passes on (deploy/review-site.conf)
DEVICE_HEADER = "X-Review-Device"    # the random key the page makes once on each device
DEVICE_RE = re.compile(r"[A-Za-z0-9_-]{16,128}")
SEEN_EVERY = 10                  # minutes between two records of when a device was last seen
ROUND_NAME_RE = GROUP_NAME_RE    # a round name fits a command line: letters, digits, dots, hyphens, underscores
STAMP_RE = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ")

CLIENT_ID_RE = re.compile(r"[A-Za-z0-9_.:-]{1,64}")
ANCHOR_RE = re.compile(r"[A-Za-z]{1,10} \d{1,4}\.\d{1,4}")
COMMIT_RE = re.compile(r"[0-9a-f]{4,40}")
SEG = r"([A-Za-z0-9_.:-]{1,64})"
BOOK = r"([A-Z]{1,10})"
CHAP = r"([A-Z]{1,10}\d{1,3})"
BOOK_ID_RE = re.compile(BOOK)
CHAPTER_ID_RE = re.compile(CHAP)
SOURCE_RE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_./-]{0,199}")
NUM = r"(\d{1,12})"

# Why the server refuses a reader's write: code -> (status, meaning). The page explains each code in
# plain words; any other code is a fault in the site or the page, never in the reader's words.
WRITE_ERRORS = {
    "no_chapter": (404, "the chapter is closed: withdrawn, or no longer open to this reader"),
    "no_paragraph": (409, "the paragraph is no longer in the chapter"),
    "quote_required": (400, "a wording comment without the words to change"),
    "quote_too_long": (400, "the quoted words are longer than limits.quote characters"),
    "text_required": (400, "the comment is empty"),
    "text_too_long": (400, "the comment is longer than limits.text characters"),
    "too_large": (413, "the request is far over the size limit: for a comment, the comment is far too long"),
    "slow_down": (429, "more than limits.comments_per_minute new comments, or more than limits.writes_per_minute "
                       "other changes, in one minute; Retry-After says when to try again"),
    "daily_limit": (429, "the reader has written limits.comments_per_day new comments today, a day running from "
                         "midnight to midnight Thailand time; Retry-After gives the seconds until midnight, and the "
                         "answer adds limit and retry_at"),
    "no_comment": (404, "the comment no longer exists, as when it was deleted on another device"),
    "round_closed": (409, "the comment belongs to an earlier review round, which can be read but not changed"),
}

# Why the server refuses any request of a reader, before it looks at what the request asks.
ACCESS_ERRORS = {
    "no_code": (401, "the request carries neither a session cookie nor a link code: the browser is not signed in"),
    "signed_out": (401, "the browser's session ended: the reader or the translator ended it, or "
                        "auth.session_days passed without a visit; the answer clears the cookie"),
    "stopped": (401, "the reader signed in on this browser, but the reader's access is stopped (revoke)"),
    "bad_code": (401, "the code is wrong, or its link was stopped (revoke) or replaced by a new link (relink)"),
    "link_used": (401, "the link was used to sign in with LINE or email, so it no longer signs in by itself"),
    "sign_in_required": (401, "the link no longer signs in by itself (the reader has an identity, or "
                              "auth.require_identity is on); sign in with LINE or email"),
    "bad_page": (403, "a request with the session cookie that did not come from the site's own page: it lacks "
                      "X-Review-Page: 1, or names another site in Origin or Sec-Fetch-Site"),
    "no_device": (400, "the request carries no device key in X-Review-Device: a fault in the page"),
    "device_waiting": (403, "the link already works on limits.devices_per_link other devices; it works on this "
                            "device once the translator approves it"),
}

# Whether a chapter is open to reader :r: an own grant, or a grant of a group of theirs that is on.
GRANTED = """(
  EXISTS (SELECT 1 FROM "grant" g WHERE g.reader = :r AND g.book = c.book AND g.chapter IN (c.id, '*'))
  OR EXISTS (SELECT 1 FROM group_member m
             JOIN reader_group t ON t.id = m.grp AND t.active = 1
             JOIN group_grant gg ON gg.grp = m.grp AND gg.book = c.book AND gg.chapter IN (c.id, '*')
             WHERE m.reader = :r))"""
ACCESS_SQL = f"SELECT c.version FROM chapter c WHERE c.book = :book AND c.id = :ch AND c.published = 1 AND {GRANTED}"
OPEN_SQL = f"""SELECT c.book, c.id, c.n, c.title, c.title_en, c.version, c.count, c.updated FROM chapter c
WHERE c.published = 1 AND {GRANTED} ORDER BY c.book, c.n"""


def squash(text):
    return " ".join(unicodedata.normalize("NFC", text).split())


def etag_matches(header, etag):
    """True when If-None-Match names etag; tolerates W/ and a -gzip suffix added by Apache."""
    want = etag.strip('"')
    for tag in header.split(","):
        tag = tag.strip()
        if tag == "*":
            return True
        tag = tag.removeprefix("W/").strip('"')
        for suffix in ("-gzip", "-br", "-deflate"):
            tag = tag.removesuffix(suffix)
        if tag == want:
            return True
    return False


def comment_rev(kind, quote, text):
    """A short fingerprint of what a comment says; it changes whenever the reader changes the comment."""
    return db.sha256("\0".join((kind, quote, text)))[:12]


def comment_json(row, changed=(False, None), rounds=None):
    """A reader's comment as the reader routes give it. changed is (para_changed, para_changed_at): whether
    the paragraph's words changed after the version the comment was written on (None: not known), and when.
    rounds maps round ids to names (round_names()); round is null for a comment from before the first round."""
    return {"id": row["id"], "client_id": row["client_id"], "book": row["book"], "ch": row["ch"],
            "a": row["a"], "kind": row["kind"], "quote": row["quote"], "text": row["text"],
            "created": row["created"], "updated": row["updated"], "processed": bool(row["processed"]),
            "version": row["version"], "para_changed": changed[0], "para_changed_at": changed[1],
            "reply": row["reply"], "reply_at": row["reply_at"],
            "round": (rounds or {}).get(row["round"])}


def round_names(conn):
    """{round id: name} of every review round."""
    return {r[0]: r[1] for r in conn.execute("SELECT id, name FROM review_round")}


def current_rounds(conn):
    """{book: the id of its current review round}: the newest round of each book that has one. A book without
    a round is missing, and its comments of round NULL are the current ones."""
    return {r[0]: r[1] for r in conn.execute("SELECT book, MAX(id) FROM review_round GROUP BY book")}


def para_words(p):
    """What the reader reads of a paragraph: its text and footnotes without span tags."""
    return words_html(p["text"]), tuple(words_html(f) for f in p["fn"])


def check_pairs(pairs, a, text, en):
    """A paragraph's sentence pairs as publish sends them: [{"text": [start, end], "en": [[start, end], ...]}],
    each range within the alignment text of the paragraph's text or of its English (server/content.py,
    align_text)."""
    if not isinstance(pairs, list) or len(pairs) > PAIRS_MOST:
        raise HTTPError(400, "bad_pairs", f"{a}: al must be a list of at most {PAIRS_MOST} sentence pairs.")
    n_text, n_en = len(align_text(text)), len(align_text(en))

    def span(x, most):
        return (isinstance(x, list) and len(x) == 2 and all(type(v) is int for v in x)
                and 0 <= x[0] < x[1] <= most)

    for pair in pairs:
        if not isinstance(pair, dict) or set(pair) != {"text", "en"} or not span(pair["text"], n_text) \
                or not isinstance(pair["en"], list) or not pair["en"] or not all(span(r, n_en) for r in pair["en"]):
            raise HTTPError(400, "bad_pairs", f"{a}: each sentence pair is {{\"text\": [start, end], \"en\": "
                            "[[start, end], ...]}, within the paragraph's text.")
    return pairs


def forget(conn, rows):
    """Delete comments (rows with id, client_id, reader, book and ch), inside the caller's transaction, and record
    each in comment_gone, so the next export of what changed names it, and a device that sends the comment again
    with its client_id learns that it was deleted (add_comment)."""
    stamp = db.now()
    conn.executemany("INSERT OR REPLACE INTO comment_gone (id, reader, book, ch, at, client_id)"
                     " VALUES (?, ?, ?, ?, ?, ?)",
                     [(r["id"], r["reader"], r["book"], r["ch"], stamp, r["client_id"]) for r in rows])
    conn.executemany("DELETE FROM comment WHERE id = ?", [(r["id"],) for r in rows])


def anchor_order(a):
    """A paragraph's tag as numbers for sorting, "SC 24.2" as (24, 2), so the comments on paragraphs no longer in
    a chapter stand in the order of their paragraphs."""
    return tuple(int(x) for x in re.findall(r"\d+", a or ""))


class App(People, SignIn, Accounts):
    """The API as a WSGI callable over one data directory."""

    def __init__(self, data_dir, writes_per_minute=None, public_url=None, feature_list=None, limits=None):
        """limits overrides config.json's "limits" (server/common.py, LIMIT_DEFAULTS); writes_per_minute is
        short for its writes_per_minute. A wrong limit stops the start before the database is touched."""
        self.data = Path(data_dir)
        self.db_path = self.data / db.DB_NAME
        overrides = dict(limits or {})
        if writes_per_minute is not None:
            overrides["writes_per_minute"] = writes_per_minute
        self.limits = load_limits(self.data, overrides)
        self.public_url = public_url
        self.setup_auth()               # the sign-in settings: a wrong one stops the start, naming config.json
        self.registry = features.Registry(features.load() if feature_list is None else feature_list)
        db.init_db(self.db_path, [(f.name, f.migrations) for f in self.registry.features.values()])
        self.writes_per_minute = self.limits["writes_per_minute"]
        self.lock = threading.Lock()
        self.writes = {}                # reader id -> times of their other writes in the last minute
        self.made = {}                  # reader id -> times of their new comments in the last minute
        self.swept = time.monotonic()
        self.cache = {}
        self.kept = {}                  # (book, ch, version) -> an earlier version, parsed
        self.compared = {}              # (book, ch, since, to) -> changes()
        r = [
            ("GET", r"/api/health", self.health, None),
            ("GET", r"/api/me", self.me, "reader"),
            ("GET", rf"/api/chapter/{BOOK}/{CHAP}", self.chapter, "reader"),
            ("GET", r"/api/comments", self.list_comments, "reader"),
            ("POST", r"/api/comments", self.add_comment, "reader"),
            ("PATCH", rf"/api/comments/{SEG}", self.edit_comment, "reader"),
            ("DELETE", rf"/api/comments/{SEG}", self.delete_comment, "reader"),
            ("PUT", r"/api/place", self.put_place, "reader"),
            ("PUT", r"/api/finished", self.put_finished, "reader"),
            ("PUT", r"/api/opened", self.put_opened, "reader"),
            ("GET", rf"/api/earlier/{BOOK}/{CHAP}", self.earlier, "reader"),
            # Signing in (server/auth.py). "page": only the site's own page may call it (X-Review-Page: 1);
            # "account": a reader signed in with LINE or email, never a link's code.
            ("GET", r"/api/auth/state", self.auth_state, "page"),
            ("POST", r"/api/auth/claim", self.auth_claim, "page"),
            ("POST", r"/api/auth/join", self.auth_join, "page"),
            ("POST", r"/api/auth/line/start", self.line_start, "page"),
            ("GET", r"/api/auth/line/callback", self.line_callback, None),
            ("POST", r"/api/auth/email/start", self.email_start, "page"),
            ("POST", r"/api/auth/email/finish", self.email_finish, "page"),
            ("POST", r"/api/auth/logout", self.logout, "page"),
            ("GET", r"/api/auth/sessions", self.my_sessions, "account"),
            ("DELETE", rf"/api/auth/sessions/{NUM}", self.end_my_session, "account"),
            ("GET", r"/api/admin/chapters", self.admin_chapters, "admin"),
            ("PUT", rf"/api/admin/chapters/{BOOK}/{CHAP}", self.admin_publish, "admin"),
            ("DELETE", rf"/api/admin/chapters/{BOOK}/{CHAP}", self.admin_withdraw, "admin"),
            ("GET", r"/api/admin/readers", self.admin_readers, "admin"),
            ("POST", r"/api/admin/readers", self.admin_invite, "admin"),
            ("PATCH", r"/api/admin/readers", self.admin_edit_readers, "admin"),
            ("POST", r"/api/admin/readers/batch", self.admin_invite_batch, "admin"),
            ("POST", r"/api/admin/readers/codes", self.admin_new_codes, "admin"),
            ("PATCH", rf"/api/admin/readers/{NUM}", self.admin_edit_reader, "admin"),
            ("POST", rf"/api/admin/readers/{NUM}/code", self.admin_new_code, "admin"),
            ("POST", rf"/api/admin/readers/{NUM}/delete-comments", self.admin_delete_comments, "admin"),
            ("GET", r"/api/admin/devices", self.admin_devices, "admin"),
            ("PATCH", r"/api/admin/devices", self.admin_set_devices, "admin"),
            ("GET", r"/api/admin/rounds", self.admin_rounds, "admin"),
            ("POST", r"/api/admin/rounds", self.admin_new_round, "admin"),
            ("GET", r"/api/admin/groups", self.admin_groups, "admin"),
            ("POST", r"/api/admin/groups", self.admin_new_group, "admin"),
            ("PATCH", rf"/api/admin/groups/{NUM}", self.admin_edit_group, "admin"),
            ("DELETE", rf"/api/admin/groups/{NUM}", self.admin_remove_group, "admin"),
            ("POST", rf"/api/admin/groups/{NUM}/members", self.admin_group_members, "admin"),
            ("GET", r"/api/admin/features", self.admin_features, "admin"),
            ("GET", r"/api/admin/export", self.admin_export, "admin"),
            ("POST", r"/api/admin/processed", self.admin_processed, "admin"),
            ("POST", r"/api/admin/replies", self.admin_replies, "admin"),
            # Accounts (server/accounts.py): sign-in settings, sessions, identities, requests, general links.
            ("GET", r"/api/admin/auth", self.admin_auth_status, "admin"),
            ("POST", r"/api/admin/auth/check", self.admin_auth_check, "admin"),
            ("POST", r"/api/admin/auth/test-mail", self.admin_test_mail, "admin"),
            ("GET", r"/api/admin/sessions", self.admin_sessions, "admin"),
            ("PATCH", r"/api/admin/sessions", self.admin_end_sessions, "admin"),
            ("GET", r"/api/admin/identities", self.admin_identities, "admin"),
            ("POST", r"/api/admin/identities", self.admin_add_identity, "admin"),
            ("DELETE", rf"/api/admin/identities/{NUM}", self.admin_remove_identity, "admin"),
            ("GET", r"/api/admin/requests", self.admin_requests, "admin"),
            ("POST", rf"/api/admin/requests/{NUM}/approve", self.admin_approve_request, "admin"),
            ("POST", rf"/api/admin/requests/{NUM}/decline", self.admin_decline_request, "admin"),
            ("DELETE", rf"/api/admin/requests/{NUM}", self.admin_forget_request, "admin"),
            ("GET", r"/api/admin/general-links", self.admin_general_links, "admin"),
            ("POST", r"/api/admin/general-links", self.admin_new_general_link, "admin"),
            ("PATCH", rf"/api/admin/general-links/{NUM}", self.admin_edit_general_link, "admin"),
        ]
        # (method, pattern, handler, auth, feature): feature is None for a core route.
        r = [route + (None,) for route in r]
        for f in self.registry.features.values():
            r += [(m, p, functools.partial(h, self), auth, f.name) for m, p, h, auth in f.routes]
        self.routes = [(m, re.compile(p), h, auth, name) for m, p, h, auth, name in r]

    # ---------- WSGI ----------

    def __call__(self, environ, start_response):
        headers = []
        try:
            conn = db.connect(self.db_path)
            try:
                status, body, headers = self.dispatch(Request(environ, conn))
            finally:
                conn.close()
        except HTTPError as e:
            status, headers = e.status, e.headers
            body = dumps({"error": e.error, "message": e.message, **e.details})
        except Exception:
            traceback.print_exc(file=environ.get("wsgi.errors") or sys.stderr)
            status, headers = 500, []
            body = dumps({"error": "server_error", "message": "Something went wrong. Try again."})
        out = SECURITY_HEADERS + [("Cache-Control", "no-store")] + headers
        if body is not None:
            out += [("Content-Type", "application/json; charset=utf-8"), ("Content-Length", str(len(body)))]
        start_response(f"{status} {HTTPStatus(status).phrase}", out)
        return [body] if body is not None else []

    def dispatch(self, req):
        allowed = False
        for method, pattern, handler, auth, feature in self.routes:
            m = pattern.fullmatch(req.path)
            if not m:
                continue
            allowed = True
            if method != req.method:
                continue
            if auth in ("reader", "any_reader"):
                self.reader_auth(req)
                # A feature's reader route answers only readers who have the feature on.
                if feature and auth == "reader" and not self.registry.is_on(feature, self.settings(req)):
                    raise HTTPError(404, "not_found", "Not found.")
            elif auth == "admin":
                # Apache marks what it passes on from the internet; the admin routes answer only the SSH tunnel.
                if req.header(PROXY_HEADER):
                    raise HTTPError(403, "admin_local_only", "The admin routes answer only through the SSH "
                                    "tunnel that review.py opens.")
                self.admin_auth(req)
                req.limit = ADMIN_LIMIT
            elif auth == "account":
                self.reader_auth(req, session_only=True)
            elif auth == "page":
                self.page_guard(req)
            result = handler(req, *m.groups())
            status, payload = result[0], result[1]
            extra = list(result[2] if len(result) > 2 else []) + req.headers_out
            if payload is None or isinstance(payload, bytes):
                return status, payload, extra
            return status, dumps(payload), extra
        if allowed:
            raise HTTPError(405, "bad_method", "This method is not allowed here.")
        raise HTTPError(404, "not_found", "Not found.")

    # ---------- auth and limits ----------

    def device_check(self, req, reader):
        """The device check of a link that signs in by itself (server/auth.py, reader_auth): the page's device key,
        and the device's state for the reader's current link; otherwise no_device or device_waiting."""
        key = req.header(DEVICE_HEADER).strip()
        if not DEVICE_RE.fullmatch(key):
            raise HTTPError(400, "no_device", "The page sent no device key. Reload the page.")
        state, number = self.device_state(req, reader, key)
        if state != "ok":
            # The device's number, which the waiting page shows, so the reader can tell the translator which
            # device to approve; none for a device refused unrecorded (WAITING_MOST).
            raise HTTPError(403, "device_waiting", "This link already works on other devices. It works on this "
                            "device once the translator approves it.", details={"device": number})

    def device_state(self, req, reader, key):
        """(state, number) of this device for the reader's current link: state is ok or waiting, and number is
        the device's number in reader_device, or None. A device the link has not met is recorded: ok while the
        link has met fewer than limits.devices_per_link devices, so the first devices that open a link work at
        once; waiting after that, until the translator approves it. A link keeps at most WAITING_MOST devices
        waiting: a further new device waits too, but is not recorded, so no link can fill the disk with devices.
        A device the translator removed that opens the link again waits for approval again, and the lists of
        waiting devices show it. When a device was last seen is recorded at most every SEEN_EVERY minutes, so
        reading writes little."""
        device, link, stamp = db.sha256(key), reader["code_hash"], db.now()
        find = "SELECT id, state, last_seen FROM reader_device WHERE reader = ? AND link = ? AND device = ?"
        row = req.conn.execute(find, (reader["id"], link, device)).fetchone()
        if row is None:
            with db.tx(req.conn):
                row = req.conn.execute(find, (reader["id"], link, device)).fetchone()
                if row is None:
                    met = {r[0]: r[1] for r in req.conn.execute(
                        "SELECT state, COUNT(*) FROM reader_device WHERE reader = ? AND link = ? GROUP BY state",
                        (reader["id"], link))}
                    state = "ok" if sum(met.values()) < self.limits["devices_per_link"] else "waiting"
                    if state == "waiting" and met.get("waiting", 0) >= WAITING_MOST:
                        return "waiting", None
                    cur = req.conn.execute(
                        "INSERT INTO reader_device (reader, link, device, state, agent, first_seen, last_seen)"
                        " VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (reader["id"], link, device, state, device_agent(req.header("User-Agent"))[:120], stamp,
                         stamp))
                    return state, cur.lastrowid
        if row["state"] == "removed":
            with db.tx(req.conn):
                req.conn.execute("UPDATE reader_device SET state = 'waiting', changed = ?, last_seen = ? WHERE id = ?"
                                 " AND state = 'removed'", (stamp, stamp, row["id"]))
            return "waiting", row["id"]
        if row["last_seen"] < db.ago(minutes=SEEN_EVERY):
            with db.tx(req.conn):
                req.conn.execute("UPDATE reader_device SET last_seen = ? WHERE id = ?", (stamp, row["id"]))
        return row["state"], row["id"]

    def admin_auth(self, req):
        m = TOKEN_RE.fullmatch(req.header("Authorization").strip())
        expected = db.admin_hash(self.data)
        if not m or not expected or not hmac.compare_digest(db.sha256(m.group(1)), expected):
            raise HTTPError(401, "bad_token", "The admin token is missing or wrong.")

    def window(self, name, req, most, message):
        """Count one write of this reader in the table self.<name> (writes or made), allowing most in any
        60 seconds; returns its time, which unreserve() takes back. Only readers who wrote in the last
        minute or two are remembered, so the tables stay small however many readers there are."""
        now = time.monotonic()
        with self.lock:
            if now - self.swept >= 60:
                self.writes = {k: q for k, q in self.writes.items() if q and now - q[-1] < 60}
                self.made = {k: q for k, q in self.made.items() if q and now - q[-1] < 60}
                self.swept = now
            q = getattr(self, name).setdefault(req.reader["id"], deque())
            while q and now - q[0] >= 60:
                q.popleft()
            if len(q) >= most:
                wait = int(60 - (now - q[0])) + 1
                raise HTTPError(429, "slow_down", message, [("Retry-After", str(wait))])
            q.append(now)
        return now

    def rate(self, req):
        """Every write but a new comment: edits, deletions, places, finished marks, opened versions."""
        self.window("writes", req, self.writes_per_minute, "Too many changes in one minute. Wait and try again.")

    def unreserve(self, req, stamp):
        """Take back a new comment's place in the minute's count when the comment was not made."""
        with self.lock:
            q = self.made.get(req.reader["id"])
            if q and stamp in q:
                q.remove(stamp)

    def settings(self, req):
        """The reader's feature settings, as the reader's own and active groups' values combine."""
        if getattr(req, "_settings", None) is None:
            req._settings = self.registry.effective(req.conn, req.reader["id"])
        return req._settings

    # ---------- chapters ----------

    def parsed(self, conn, book, ch):
        """The stored chapter with its anchors and both response bodies, cached by version."""
        row = conn.execute("SELECT version FROM chapter WHERE book = ? AND id = ?", (book, ch)).fetchone()
        if row is None:
            return None
        key = (book, ch, row["version"])
        with self.lock:
            hit = self.cache.pop(key, None)
            if hit:
                self.cache[key] = hit       # the newest use goes last; the oldest is dropped first
                return hit
        row = conn.execute("SELECT c.*, b.language FROM chapter c LEFT JOIN book b ON b.id = c.book"
                           " WHERE c.book = ? AND c.id = ?", (book, ch)).fetchone()
        paras = json.loads(row["paragraphs"])
        # title and each paragraph's text are in the book's language, which the answer names beside them.
        meta = {"book": book, "id": ch, "n": row["n"], "language": row["language"] or "", "title": row["title"],
                "title_en": row["title_en"], "version": row["version"], "at": row["updated"]}
        # Without English the paragraphs carry neither the English nor the sentence pairs, which only
        # link the Thai to the English.
        short = [{k: v for k, v in p.items() if k not in ("en", "al")} for p in paras]
        entry = {"version": row["version"], "meta": meta,
                 "paras": paras, "order": {p["a"]: i for i, p in enumerate(paras)},
                 "body": {True: dumps(dict(meta, paragraphs=paras)), False: dumps(dict(meta, paragraphs=short))}}
        with self.lock:
            for k in [k for k in self.cache if k[:2] == (book, ch)]:
                del self.cache[k]
            self.cache[(book, ch, row["version"])] = entry
            while len(self.cache) > CACHE_MOST:
                del self.cache[next(iter(self.cache))]
        return entry

    # ---------- versions ----------

    def kept_version(self, conn, book, ch, version):
        """A kept version of a chapter: {version, paras, order}, or None when the site does not keep that
        version (one published before the site kept versions). When it was published is read from
        chapter_version where needed, since publishing it again moves it to the end of the history."""
        key = (book, ch, version)
        with self.lock:
            hit = self.kept.pop(key, None)
            if hit:
                self.kept[key] = hit
                return hit
        row = conn.execute("SELECT paragraphs FROM chapter_version WHERE book = ? AND ch = ? AND version = ?",
                           key).fetchone()
        if row is None:
            return None
        paras = json.loads(row["paragraphs"])
        entry = {"version": version, "paras": paras, "order": {p["a"]: i for i, p in enumerate(paras)}}
        with self.lock:
            self.kept[key] = entry
            while len(self.kept) > CACHE_MOST:
                del self.kept[next(iter(self.kept))]
        return entry

    def changes(self, conn, book, ch, since, to):
        """What changed for a reader between two kept versions of a chapter, or None when either is not
        kept. {since, since_at, at, paragraphs: [{a, at, new}], removed: [{a, at}]}: the paragraphs of `to`
        whose words differ from `since`, or that `since` lacks (new), each with the time of the last version
        that changed it; the paragraphs of `since` that `to` lacks; and at, the latest of those times. A
        paragraph changed and changed back is not listed. Results are kept in memory by the two versions."""
        key = (book, ch, since, to)
        with self.lock:
            if key in self.compared:
                return self.compared[key]
        hist = conn.execute("SELECT version, published FROM chapter_version WHERE book = ? AND ch = ? ORDER BY seq",
                            (book, ch)).fetchall()
        where = {r["version"]: i for i, r in enumerate(hist)}
        if since not in where or to not in where:
            return None
        i, j = where[since], where[to]
        first, last = self.kept_version(conn, book, ch, since), self.kept_version(conn, book, ch, to)
        changed_at, removed_at = {}, {}
        for k in range(i, j):
            a, b = self.kept_version(conn, book, ch, hist[k]["version"]), \
                self.kept_version(conn, book, ch, hist[k + 1]["version"])
            at = hist[k + 1]["published"]
            for p in b["paras"]:
                old = a["order"].get(p["a"])
                if old is None or para_words(a["paras"][old]) != para_words(p):
                    changed_at[p["a"]] = at
            for p in a["paras"]:
                if p["a"] not in b["order"]:
                    removed_at[p["a"]] = at
        paragraphs, removed = [], []
        if i < j:
            for p in last["paras"]:
                old = first["order"].get(p["a"])
                if old is None or para_words(first["paras"][old]) != para_words(p):
                    paragraphs.append({"a": p["a"], "at": changed_at.get(p["a"], hist[j]["published"]),
                                       "new": old is None})
            removed = [{"a": p["a"], "at": removed_at.get(p["a"], hist[j]["published"])}
                       for p in first["paras"] if p["a"] not in last["order"]]
        times = [x["at"] for x in paragraphs + removed]
        out = {"since": since, "since_at": hist[i]["published"], "at": max(times) if times else None,
               "paragraphs": paragraphs, "removed": removed}
        with self.lock:
            self.compared[key] = out
            while len(self.compared) > CHANGES_MOST:
                del self.compared[next(iter(self.compared))]
        return out

    def para_changed(self, conn, book, ch, a, seen, now):
        """(changed, at) for the paragraph a of a comment written on version seen, now that the chapter is at
        version now: whether its words changed or it left the chapter since, and when; (None, None) when the
        site does not keep version seen."""
        if seen == now:
            return False, None
        diff = self.changes(conn, book, ch, seen, now)
        if diff is None:
            return None, None
        for x in diff["paragraphs"] + diff["removed"]:
            if x["a"] == a:
                return True, x["at"]
        return False, None

    def access(self, req, book, ch):
        """The chapter if it is published and open to this reader; otherwise 404 no_chapter."""
        if not isinstance(book, str) or not isinstance(ch, str):
            raise HTTPError(400, "bad_field", "book and ch are required.")
        row = None
        if BOOK_ID_RE.fullmatch(book) and CHAPTER_ID_RE.fullmatch(ch):
            row = req.conn.execute(ACCESS_SQL, {"book": book, "ch": ch, "r": req.reader["id"]}).fetchone()
        if row is None:
            raise HTTPError(404, "no_chapter", "This chapter is not open to you.")
        return self.parsed(req.conn, book, ch)

    def anchor(self, entry, a):
        if not isinstance(a, str) or a not in entry["order"]:
            raise HTTPError(409, "no_paragraph", "This paragraph is no longer in the chapter.")
        return a

    # ---------- reader routes ----------

    def health(self, req):
        req.conn.execute("SELECT 1").fetchone()
        return 200, {"ok": True}

    def me(self, req):
        """The reader, their open chapters and their books. Comment counts hold only the reader's comments of
        the book's current review round on chapters open to them now; earlier counts their comments of earlier
        rounds on those chapters, which GET /api/comments?earlier=1 gives."""
        rid = req.reader["id"]
        q = req.conn.execute
        chapters = q(OPEN_SQL, {"r": rid}).fetchall()
        open_now = {(c["book"], c["id"]) for c in chapters}
        current = current_rounds(req.conn)
        counts, earlier = {}, {}
        for book, ch, rnd, n in q("SELECT book, ch, round, COUNT(*) FROM comment WHERE reader = ?"
                                  " GROUP BY book, ch, round", (rid,)):
            if (book, ch) not in open_now:
                continue
            if rnd == current.get(book):
                counts[(book, ch)] = counts.get((book, ch), 0) + n
            else:
                earlier[book] = earlier.get(book, 0) + n
        places = {(r[0], r[1]): r[2] for r in q("SELECT book, ch, a FROM place WHERE reader = ?", (rid,))}
        rounds = {r["id"]: r for r in q("SELECT id, book, name, started FROM review_round")}
        done = {}
        for book, ch, fin, at in q("SELECT book, ch, finished, at FROM finished WHERE reader = ?", (rid,)):
            # A chapter finished before the book's current round started is to be read again in this round.
            started = rounds[current[book]]["started"] if book in current else ""
            done[(book, ch)] = (bool(fin) and at >= started, at)
        books = {r[0]: (r[1], r[2], r[3]) for r in q("SELECT id, title_en, language, title FROM book")}
        opened = {(r[0], r[1]): r[2] for r in q("SELECT book, ch, version FROM reader_opened WHERE reader = ?", (rid,))}
        out = []
        for c in chapters:
            k = (c["book"], c["id"])
            fin, at = done.get(k, (False, None))
            place = places.get(k)
            if place is not None and place not in self.parsed(req.conn, *k)["order"]:
                place = None        # the paragraph is not in the chapter's current version
            seen = opened.get(k)
            changed = None
            if seen and seen != c["version"]:
                diff = self.changes(req.conn, *k, seen, c["version"])
                changed = diff if diff and (diff["paragraphs"] or diff["removed"]) else None
            out.append({"book": c["book"], "id": c["id"], "n": c["n"], "title": c["title"],
                        "title_en": c["title_en"], "version": c["version"], "at": c["updated"],
                        "paragraphs": c["count"], "finished": fin, "finished_at": at if fin else None,
                        "place": place, "comments": counts.get(k, 0), "opened": seen, "changed": changed})
        used = sorted({c["book"] for c in chapters})
        settings = self.settings(req)

        def round_of(book):
            r = rounds.get(current.get(book))
            return {"name": r["name"], "started": r["started"]} if r else None

        return 200, {"id": rid, "name": req.reader["name"],
                     # The same value as features.english.on, kept for a page saved on the device before
                     # the features field existed; the service worker can serve such a page for one visit.
                     "english": bool(settings.get("english.on")),
                     "features": self.registry.me(req.conn, req.reader, settings),
                     "limits": dict(self.limits),
                     "comments_total": sum(counts.values()),
                     "books": [{"id": b, "title": books[b][2], "title_en": books[b][0], "language": books[b][1],
                                "round": round_of(b), "earlier": earlier.get(b, 0)}
                               for b in used],
                     "chapters": out}

    def chapter(self, req, book, ch):
        entry = self.access(req, book, ch)
        english = bool(self.settings(req).get("english.on"))
        etag = '"' + entry["version"] + (".en" if english else "") + '"'
        if etag_matches(req.header("If-None-Match"), etag):
            return 304, None, [("ETag", etag)]
        return 200, entry["body"][english], [("ETag", etag)]

    def list_comments(self, req):
        """GET /api/comments?book=&ch=: the reader's own comments of the book's current review round, on
        chapters open to the reader now. ?earlier=1 gives instead their comments of earlier rounds on those
        chapters, which can be read but not changed, with the rounds of those books in "rounds"."""
        sql, args = "SELECT * FROM comment WHERE reader = ?", [req.reader["id"]]
        for name in ("book", "ch"):
            if req.query.get(name):
                sql += f" AND {name} = ?"
                args.append(req.query[name])
        earlier = req.query.get("earlier") in ("1", "true", "yes")
        open_now = {(r[0], r[1]) for r in req.conn.execute(OPEN_SQL, {"r": req.reader["id"]})}
        current = current_rounds(req.conn)
        rows = [r for r in req.conn.execute(sql + " ORDER BY id", args)
                if (r["book"], r["ch"]) in open_now and (r["round"] != current.get(r["book"])) == earlier]
        now = {(r[0], r[1]): r[2] for r in req.conn.execute("SELECT book, id, version FROM chapter")}
        names = round_names(req.conn)
        out = {"comments": [comment_json(r, self.para_changed(
            req.conn, r["book"], r["ch"], r["a"], r["version"], now.get((r["book"], r["ch"]))), names) for r in rows]}
        if earlier:
            books = sorted({r["book"] for r in rows})
            out["rounds"] = [{"book": r["book"], "name": r["name"], "started": r["started"],
                              "current": r["id"] == current.get(r["book"])}
                             for r in req.conn.execute("SELECT id, book, name, started FROM review_round ORDER BY id")
                             if r["book"] in books]
        return 200, out

    def own(self, req, ref):
        """The reader's own comment by server id or client_id; anyone else's is 404."""
        row = None
        if ref.isdigit() and len(ref) <= 18:
            row = req.conn.execute("SELECT * FROM comment WHERE reader = ? AND id = ?",
                                   (req.reader["id"], int(ref))).fetchone()
        if row is None:
            row = req.conn.execute("SELECT * FROM comment WHERE reader = ? AND client_id = ?",
                                   (req.reader["id"], ref)).fetchone()
        if row is None:
            raise HTTPError(404, "no_comment", "No such comment.")
        return row

    def comment_fields(self, kind, quote, text):
        if kind not in ("flag", "wording"):
            raise HTTPError(400, "bad_kind", "kind must be flag or wording.")
        quote = clean(quote, "quote", self.limits["quote"], kind == "wording")
        text = clean(text, "text", self.limits["text"], True)
        return kind, quote, text

    def add_comment(self, req):
        """A new comment, in the book's current review round. A client_id sent before answers the comment it
        made and counts toward no limit; one whose comment was deleted since answers 404 no_comment, so a device
        that sends it again after a lost answer does not bring the comment back. A new comment counts toward
        comments_per_minute and comments_per_day, never writes_per_minute. There is no limit on the comments a
        reader keeps. The comment's time is taken once the write lock is held, so no export of what changed that
        ran meanwhile has a later time than the comment and yet missed it."""
        data = req.json()
        rid = req.reader["id"]
        client_id = data.get("client_id")
        if not isinstance(client_id, str) or not CLIENT_ID_RE.fullmatch(client_id):
            raise HTTPError(400, "bad_client_id", "client_id is missing or malformed.")
        get = "SELECT * FROM comment WHERE reader = ? AND client_id = ?"
        row = req.conn.execute(get, (rid, client_id)).fetchone()
        if row is not None:
            return 200, comment_json(row, rounds=round_names(req.conn))
        self.not_deleted(req.conn, rid, client_id)
        entry = self.access(req, data.get("book"), data.get("ch"))
        a = self.anchor(entry, data.get("a"))
        kind, quote, text = self.comment_fields(data.get("kind"), data.get("quote"), data.get("text"))
        reserved = self.window("made", req, self.limits["comments_per_minute"],
                               "Too many new comments in one minute. Wait and try again.")
        try:
            with db.tx(req.conn):
                stamp = db.now()
                self.not_deleted(req.conn, rid, client_id)
                self.check_day(req.conn, rid, stamp)
                cur = req.conn.execute(
                    "INSERT INTO comment (client_id, reader, book, ch, a, kind, quote, text, version, created, updated,"
                    " round) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (client_id, rid, data["book"], data["ch"], a, kind, quote, text, entry["version"], stamp, stamp,
                     current_rounds(req.conn).get(data["book"])))
                req.conn.execute("INSERT INTO comment_made (reader, at) VALUES (?, ?)", (rid, stamp))
                req.conn.execute("DELETE FROM comment_made WHERE reader = ? AND at <= ?", (rid, db.ago(2)))
        except sqlite3.IntegrityError:
            self.unreserve(req, reserved)
            row = req.conn.execute(get, (rid, client_id)).fetchone()
            if row is None:
                raise
            return 200, comment_json(row, rounds=round_names(req.conn))
        except HTTPError:
            self.unreserve(req, reserved)
            raise
        row = req.conn.execute("SELECT * FROM comment WHERE id = ?", (cur.lastrowid,)).fetchone()
        return 201, comment_json(row, rounds=round_names(req.conn))

    @staticmethod
    def not_deleted(conn, rid, client_id):
        """404 no_comment when the reader's comment of this client_id was deleted."""
        if conn.execute("SELECT 1 FROM comment_gone WHERE reader = ? AND client_id = ?", (rid, client_id)).fetchone():
            raise HTTPError(404, "no_comment", "This comment was deleted, on this device or another.")

    def check_day(self, conn, rid, stamp):
        """Refuse a new comment when the reader made comments_per_day of them today, a day that runs from
        midnight to midnight Thailand time: 429 daily_limit, with Retry-After and retry_at set to the next
        Thailand midnight, when the count starts again."""
        most = self.limits["comments_per_day"]
        n = conn.execute("SELECT COUNT(*) FROM comment_made WHERE reader = ? AND at >= ?",
                         (rid, db.day_start(stamp))).fetchone()[0]
        if n >= most:
            free = db.next_midnight(stamp)
            raise HTTPError(429, "daily_limit", f"You have reached today's limit of {most} new comments. You can "
                            f"write more from midnight, Thailand time ({db.thai_time(free)}).",
                            [("Retry-After", str(db.seconds_until(free)))], details={"limit": most, "retry_at": free})

    def changeable(self, req, ref):
        """The reader's own comment, when it may still be changed or deleted: its chapter is open to the reader
        (else 404 no_chapter) and it belongs to the book's current round (else 409 round_closed)."""
        row = self.own(req, ref)
        self.access(req, row["book"], row["ch"])
        if row["round"] != current_rounds(req.conn).get(row["book"]):
            raise HTTPError(409, "round_closed", "This comment belongs to an earlier review round. It can be read "
                            "but no longer changed.")
        return row

    def edit_comment(self, req, ref):
        data = req.json()
        self.rate(req)
        row = self.changeable(req, ref)
        if not any(k in data for k in ("kind", "quote", "text")):
            raise HTTPError(400, "bad_field", "Send kind, quote or text.")
        kind, quote, text = self.comment_fields(data.get("kind", row["kind"]), data.get("quote", row["quote"]),
                                                data.get("text", row["text"]))
        if (kind, quote, text) != (row["kind"], row["quote"], row["text"]):
            v = req.conn.execute("SELECT version FROM chapter WHERE book = ? AND id = ?",
                                 (row["book"], row["ch"])).fetchone()
            with db.tx(req.conn):
                cur = req.conn.execute(
                    "UPDATE comment SET kind = ?, quote = ?, text = ?, version = ?, updated = ?, processed = 0"
                    " WHERE id = ?", (kind, quote, text, v["version"] if v else row["version"], db.now(), row["id"]))
            # A delete of the same comment from another tab or device may land between the read and the change.
            row = req.conn.execute("SELECT * FROM comment WHERE id = ?", (row["id"],)).fetchone() \
                if cur.rowcount else None
            if row is None:
                raise HTTPError(404, "no_comment", "No such comment.")
        return 200, comment_json(row, rounds=round_names(req.conn))

    def delete_comment(self, req, ref):
        self.rate(req)
        row = self.changeable(req, ref)
        with db.tx(req.conn):
            forget(req.conn, [row])
        return 200, {"deleted": row["id"], "client_id": row["client_id"]}

    def put_place(self, req):
        data = req.json()
        self.rate(req)
        entry = self.access(req, data.get("book"), data.get("ch"))
        a = self.anchor(entry, data.get("a"))
        stamp = db.now()
        with db.tx(req.conn):
            req.conn.execute(
                "INSERT INTO place (reader, book, ch, a, updated) VALUES (?, ?, ?, ?, ?)"
                " ON CONFLICT (reader, book, ch) DO UPDATE SET a = excluded.a, updated = excluded.updated",
                (req.reader["id"], data["book"], data["ch"], a, stamp))
        return 200, {"book": data["book"], "ch": data["ch"], "a": a, "updated": stamp}

    def put_finished(self, req):
        data = req.json()
        self.rate(req)
        self.access(req, data.get("book"), data.get("ch"))
        finished = bool_field(data, "finished")
        stamp = db.now()
        with db.tx(req.conn):
            req.conn.execute(
                "INSERT INTO finished (reader, book, ch, finished, at) VALUES (?, ?, ?, ?, ?)"
                " ON CONFLICT (reader, book, ch) DO UPDATE SET finished = excluded.finished, at = excluded.at",
                (req.reader["id"], data["book"], data["ch"], int(finished), stamp))
        return 200, {"book": data["book"], "ch": data["ch"], "finished": finished, "at": stamp}

    def put_opened(self, req):
        """Record the version of a chapter the reader opened: {book, ch, version}. The record only moves
        forward, to the recorded version or one published after it in the chapter's history, so a change sent
        late from another device never brings back marks the reader has cleared. A version the site does not
        keep, or an older one, changes nothing: the answer is 200 with recorded false."""
        data = req.json()
        self.rate(req)
        self.access(req, data.get("book"), data.get("ch"))
        book, ch, version = data["book"], data["ch"], data.get("version")
        if not isinstance(version, str) or not 1 <= len(version) <= 80:
            raise HTTPError(400, "bad_field", "version must be the version of the chapter the reader opened.")
        recorded = False
        stamp = db.now()
        with db.tx(req.conn):
            new = req.conn.execute("SELECT seq FROM chapter_version WHERE book = ? AND ch = ? AND version = ?",
                                   (book, ch, version)).fetchone()
            old = req.conn.execute(
                "SELECT o.version, v.seq FROM reader_opened o LEFT JOIN chapter_version v"
                " ON v.book = o.book AND v.ch = o.ch AND v.version = o.version"
                " WHERE o.reader = ? AND o.book = ? AND o.ch = ?", (req.reader["id"], book, ch)).fetchone()
            if new is not None and (old is None or (old["seq"] or 0) <= new["seq"]):
                req.conn.execute(
                    "INSERT INTO reader_opened (reader, book, ch, version, at) VALUES (?, ?, ?, ?, ?)"
                    " ON CONFLICT (reader, book, ch) DO UPDATE SET version = excluded.version, at = excluded.at",
                    (req.reader["id"], book, ch, version, stamp))
                recorded = True
        now = version if recorded else (old["version"] if old else None)
        return 200, {"book": book, "ch": ch, "version": version, "recorded": recorded, "opened": now}

    def earlier(self, req, book, ch):
        """GET /api/earlier/<book>/<ch>?a=SC%209.1[&version=V]: the paragraph's wording in an earlier kept
        version, by default the version the reader last opened. 404 no_earlier when there is none to show:
        the reader has opened no other version, the site does not keep it, or the paragraph is not in it."""
        entry = self.access(req, book, ch)
        a = req.query.get("a")
        if not isinstance(a, str) or not ANCHOR_RE.fullmatch(a):
            raise HTTPError(400, "bad_field", "a must name a paragraph, as SC 9.1.")
        version = req.query.get("version")
        if not version:
            row = req.conn.execute("SELECT version FROM reader_opened WHERE reader = ? AND book = ? AND ch = ?",
                                   (req.reader["id"], book, ch)).fetchone()
            version = row["version"] if row else None
        old = self.kept_version(req.conn, book, ch, version) if version and version != entry["version"] else None
        i = old["order"].get(a) if old else None
        if i is None:
            raise HTTPError(404, "no_earlier", "There is no earlier wording of this paragraph to show.")
        p = old["paras"][i]
        now = entry["order"].get(a)
        same = now is not None and para_words(entry["paras"][now]) == para_words(p)
        at = req.conn.execute("SELECT published FROM chapter_version WHERE book = ? AND ch = ? AND version = ?",
                              (book, ch, version)).fetchone()["published"]
        return 200, {"book": book, "ch": ch, "a": a, "version": version, "at": at,
                     "language": entry["meta"]["language"], "text": p["text"], "fn": p["fn"], "same": same}

    # ---------- admin: chapters ----------

    def admin_chapters(self, req):
        rows = req.conn.execute("""
            SELECT c.book, c.id, c.n, c.title, c.title_en, c.version, c.published, c.count, c.updated,
              c.source_commit,
              (SELECT COUNT(*) FROM comment m WHERE m.book = c.book AND m.ch = c.id) AS comments,
              (SELECT COUNT(*) FROM comment m WHERE m.book = c.book AND m.ch = c.id AND m.processed = 0) AS open,
              (SELECT COUNT(*) FROM chapter_version v WHERE v.book = c.book AND v.ch = c.id) AS versions
            FROM chapter c ORDER BY c.book, c.n""").fetchall()
        return 200, {"chapters": [{
            "book": r["book"], "id": r["id"], "n": r["n"], "title": r["title"], "title_en": r["title_en"],
            "version": r["version"], "published": bool(r["published"]), "paragraphs": r["count"],
            "comments": r["comments"], "open": r["open"], "updated": r["updated"], "versions": r["versions"],
            "commit": r["source_commit"]}
            for r in rows]}

    def check_paragraphs(self, paras, language):
        if not isinstance(paras, list) or not 1 <= len(paras) <= 5000:
            raise HTTPError(400, "bad_paragraphs", "paragraphs must be a list of 1 to 5000 items.")
        out, seen = [], set()
        for p in paras:
            if not isinstance(p, dict):
                raise HTTPError(400, "bad_paragraphs", "Each paragraph must be an object.")
            a, text, fn, en = p.get("a"), p.get("text"), p.get("fn", []), p.get("en", "")
            if not isinstance(a, str) or not ANCHOR_RE.fullmatch(a) or a in seen:
                raise HTTPError(400, "bad_anchor", f"Bad or repeated anchor: {a!r}.")
            seen.add(a)
            if not isinstance(text, str) or not text.strip() or not isinstance(en, str) \
                    or not isinstance(fn, list) or not all(isinstance(x, str) for x in fn):
                raise HTTPError(400, "bad_paragraphs", f"{a}: text, fn and en must be text.")
            for part in [text, en, *fn]:
                if not safe_html(part):
                    raise HTTPError(400, "unsafe_html", f"{a}: only the tags of the content model are allowed.")
            # The English is checked by the rules for every book: no invisible character, no Thai or Lao digit.
            bad = forbidden_char(text + "".join(fn), language) or forbidden_char(en)
            if bad:
                raise HTTPError(400, "forbidden_character", f"{a}: holds the character U+{ord(bad):04X}.")
            item = {"a": a, "text": text, "fn": fn, "en": en}
            if p.get("al"):
                item["al"] = check_pairs(p["al"], a, text, en)
            out.append(item)
        return out

    def book_language(self, req, book, data):
        """The language of the book being published: as sent, or as stored for a book already known."""
        language = data.get("language") or ""
        if not isinstance(language, str) or (language and language not in REGISTRY.refuse):
            raise HTTPError(400, "unknown_language", f"language must be one of {', '.join(REGISTRY.codes)} "
                            "(web/languages.json).")
        if not language:
            row = req.conn.execute("SELECT language FROM book WHERE id = ?", (book,)).fetchone()
            if row is None:
                raise HTTPError(400, "unknown_language", "Name the language of a new book.")
            language = row["language"]
        return language

    def admin_publish(self, req, book, ch):
        data = req.json(CHAPTER_LIMIT)
        if not ch.startswith(book) or not ch[len(book):].isdigit():
            raise HTTPError(400, "bad_chapter", "The chapter id must be the book id and a number.")
        n = data.get("n", int(ch[len(book):]))
        if not isinstance(n, int) or isinstance(n, bool) or not 0 <= n <= 999:
            raise HTTPError(400, "bad_field", "n must be a chapter number.")
        language = self.book_language(req, book, data)
        title, title_en = data.get("title"), data.get("title_en", "")
        if not isinstance(title, str) or not title.strip() or not isinstance(title_en, str) \
                or len(title) > 300 or len(title_en) > 300:
            raise HTTPError(400, "bad_field", "title and title_en must be short text.")
        if forbidden_char(title, language) or forbidden_char(title_en) or "<" in title + title_en:
            raise HTTPError(400, "bad_field", "The title holds a forbidden character.")
        paras = self.check_paragraphs(data.get("paragraphs"), language)
        commit = data.get("commit") or ""
        if not isinstance(commit, str) or (commit and not COMMIT_RE.fullmatch(commit)):
            raise HTTPError(400, "bad_field", "commit must be a git commit id.")
        book_title_en = data.get("book_title_en") or ""
        if not isinstance(book_title_en, str) or len(book_title_en) > 300:
            raise HTTPError(400, "bad_field", "book_title_en must be short text.")
        # The book's title in its own language.
        book_title = data.get("book_title") or ""
        if not isinstance(book_title, str) or len(book_title) > 300 or "<" in book_title \
                or forbidden_char(book_title, language):
            raise HTTPError(400, "bad_field", "book_title must be short text without a forbidden character.")
        sources = data.get("sources") or []
        if not isinstance(sources, list) or len(sources) > 2 \
                or not all(isinstance(x, str) and SOURCE_RE.fullmatch(x) and ".." not in x for x in sources):
            raise HTTPError(400, "bad_field", "sources must be the paths of the chapter's file and its English.")
        source, source_en = (sources + ["", ""])[:2]
        digest = db.content_hash(title, title_en, paras)
        version = f"{commit[:12]}-{digest}" if commit else digest
        stamp = db.now()
        with db.tx(req.conn):
            req.conn.execute(
                "INSERT INTO book (id, title_en, title, language) VALUES (?, ?, ?, ?) ON CONFLICT (id) DO UPDATE SET"
                " title_en = CASE WHEN excluded.title_en != '' THEN excluded.title_en ELSE book.title_en END,"
                " title = CASE WHEN excluded.title != '' THEN excluded.title ELSE book.title END,"
                " language = excluded.language", (book, book_title_en, book_title, language))
            old = req.conn.execute("SELECT version, content_hash, published, paragraphs, updated FROM chapter"
                                   " WHERE book = ? AND id = ?", (book, ch)).fetchone()
            changed = old is None or old["content_hash"] != digest
            if changed:
                req.conn.execute(
                    "INSERT INTO chapter (book, id, n, title, title_en, version, content_hash, published, count,"
                    " paragraphs, updated) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?) ON CONFLICT (book, id) DO UPDATE SET"
                    " n = excluded.n, title = excluded.title, title_en = excluded.title_en,"
                    " version = excluded.version, content_hash = excluded.content_hash, published = 1,"
                    " count = excluded.count, paragraphs = excluded.paragraphs, updated = excluded.updated",
                    (book, ch, n, title, title_en, version, digest, len(paras),
                     json.dumps(paras, ensure_ascii=False), stamp))
            else:
                version = old["version"]
                req.conn.execute("UPDATE chapter SET published = 1, n = ? WHERE book = ? AND id = ?", (n, book, ch))
            # The files and their revision move together, so the pair can always be read back with git show.
            req.conn.execute("UPDATE chapter SET source = ?, source_en = ?, source_commit = ? WHERE book = ? AND id = ?",
                             (source, source_en, commit, book, ch))
            # Every version is kept. A version published again after another goes to the end of the history.
            req.conn.execute(
                "INSERT INTO chapter_version (book, ch, version, title, title_en, paragraphs, source_commit,"
                " published, seq) VALUES (?, ?, ?, ?, ?, ?, ?, ?, (SELECT COALESCE(MAX(seq), 0) + 1"
                " FROM chapter_version WHERE book = ? AND ch = ?)) ON CONFLICT (book, ch, version)"
                " DO UPDATE SET published = excluded.published, seq = excluded.seq WHERE ?",
                (book, ch, version, title, title_en, json.dumps(paras, ensure_ascii=False), commit,
                 stamp if changed else old["updated"], book, ch, int(changed)))
        # What was worked out from this chapter's history before is worked out again.
        with self.lock:
            self.compared = {k: v for k, v in self.compared.items() if k[:2] != (book, ch)}
        anchors = {p["a"] for p in paras}
        orphans = sum(1 for r in req.conn.execute("SELECT a FROM comment WHERE book = ? AND ch = ?", (book, ch))
                      if r[0] not in anchors)
        # How many paragraphs a reader of the version before sees changed, new or gone.
        before = {p["a"]: para_words(p) for p in json.loads(old["paragraphs"])} if old and changed else None
        differ = None if before is None else sum(1 for p in paras if before.get(p["a"]) != para_words(p))
        gone = None if before is None else len(set(before) - anchors)
        return 200, {"book": book, "id": ch, "version": version, "changed": changed, "paragraphs": len(paras),
                     "was_published": bool(old and old["published"]), "orphans": orphans,
                     "previous": old["version"] if old and changed else None, "paragraphs_changed": differ,
                     "paragraphs_removed": gone, "pairs": sum(1 for p in paras if p.get("al"))}

    def admin_withdraw(self, req, book, ch):
        with db.tx(req.conn):
            cur = req.conn.execute("UPDATE chapter SET published = 0 WHERE book = ? AND id = ?", (book, ch))
        if cur.rowcount == 0:
            raise HTTPError(404, "no_chapter", "No such chapter.")
        return 200, {"book": book, "id": ch, "published": False}

    # ---------- admin: export ----------

    def admin_export(self, req):
        """GET /api/admin/export?book=&ch=&reader=&unprocessed=1&since=&round=&before_first=1: the comments, with
        the paragraph each is on, now and as its reader saw it. since (a UTC time) limits them to those written
        or changed since, and adds "deleted", the comments deleted since; round (a round's name) limits them to
        one review round, and before_first=1 to the comments written before the book's first round. reader is a
        reader's name, whatever its case and spaces. "exported" is taken before the comments are read, so a
        comment written meanwhile is in the next export of what changed too."""
        stamp = db.now()
        since = req.query.get("since") or None
        if since is not None and not STAMP_RE.fullmatch(since):
            raise HTTPError(400, "bad_field", "since must be a UTC time such as 2026-10-22T08:30:00Z.")
        before_first = req.query.get("before_first") in ("1", "true", "yes")
        round_name = req.query.get("round") or None
        if before_first and round_name:
            raise HTTPError(400, "bad_field", "Give round or before_first, not both.")
        sql = "SELECT m.*, r.name AS reader_name FROM comment m JOIN reader r ON r.id = m.reader WHERE 1 = 1"
        args = []
        for name, col in (("book", "m.book"), ("ch", "m.ch")):
            if req.query.get(name):
                sql += f" AND {col} = ?"
                args.append(req.query[name])
        who = None
        if req.query.get("reader"):
            who = [r[0] for r in req.conn.execute("SELECT id, name FROM reader")
                   if name_key(r[1]) == name_key(req.query["reader"])]
            sql += f" AND m.reader IN ({', '.join('?' * len(who)) or 'NULL'})"
            args += who
        if req.query.get("unprocessed") in ("1", "true", "yes"):
            sql += " AND m.processed = 0"
        if since:
            sql += " AND m.updated >= ?"
            args.append(since)
        if before_first:
            sql += " AND m.round IS NULL"
        if round_name:
            ids = [r[0] for r in req.conn.execute(
                "SELECT id FROM review_round WHERE name = ? COLLATE NOCASE" + (" AND book = ?" if req.query.get("book")
                                                                             else ""),
                [round_name] + ([req.query["book"]] if req.query.get("book") else []))]
            if not ids:
                raise HTTPError(404, "no_round", f"There is no review round named {round_name}. "
                                "Run: review.py rounds")
            sql += f" AND m.round IN ({', '.join('?' * len(ids))})"
            args += ids
        rows = req.conn.execute(sql, args).fetchall()
        names = round_names(req.conn)
        chapters, out = {}, []
        for r in rows:
            key = (r["book"], r["ch"])
            if key not in chapters:
                chapters[key] = self.parsed(req.conn, *key)
            entry = chapters[key]
            i = entry["order"].get(r["a"])
            para = entry["paras"][i] if i is not None else None
            text = plain(para["text"]) if para else ""
            notes = [plain(f) for f in para["fn"]] if para else []
            found = None
            if r["quote"]:
                q = squash(r["quote"])
                found = any(q in squash(t) for t in [text, *notes])
            # The paragraph as the reader saw it, from the version the comment was written on, when kept.
            seen = self.kept_version(req.conn, *key, r["version"]) if r["version"] != entry["version"] else None
            j = seen["order"].get(r["a"]) if seen else None
            if r["version"] == entry["version"]:
                text_seen, notes_seen = text, notes
            elif j is not None:
                text_seen, notes_seen = plain(seen["paras"][j]["text"]), [plain(f) for f in seen["paras"][j]["fn"]]
            else:
                text_seen, notes_seen = None, None
            changed, changed_at = self.para_changed(req.conn, *key, r["a"], r["version"], entry["version"])
            # A paragraph no longer in the chapter goes after those in it, in the order of its tag, so each
            # paragraph's comments stand together.
            at = (0, i, ()) if i is not None else (1, 0, anchor_order(r["a"]))
            out.append(({"n": entry["meta"]["n"], "at": at}, {
                "id": r["id"], "rev": comment_rev(r["kind"], r["quote"], r["text"]), "reader": r["reader_name"],
                "book": r["book"], "ch": r["ch"], "anchor": r["a"], "round": names.get(r["round"]),
                "kind": r["kind"], "quote": r["quote"], "text": r["text"], "created": r["created"],
                "updated": r["updated"], "processed": bool(r["processed"]), "version_seen": r["version"],
                "version_now": entry["version"], "anchor_missing": para is None, "quote_found": found,
                "paragraph": text, "footnotes": notes, "en": plain(para.get("en", "")) if para else "",
                "paragraph_seen": text_seen, "footnotes_seen": notes_seen, "changed": changed,
                "changed_at": changed_at, "reply": r["reply"], "reply_at": r["reply_at"]}))
        out.sort(key=lambda x: (x[1]["book"], x[0]["n"], x[0]["at"], x[1]["anchor"], x[1]["created"], x[1]["id"]))
        rows = {(r["book"], r["id"]): r for r in req.conn.execute(
            "SELECT book, id, published, source, source_en, source_commit FROM chapter")}
        info = {f"{b}/{c}": dict(e["meta"], published=bool(rows[(b, c)]["published"]),
                                 source=rows[(b, c)]["source"], source_en=rows[(b, c)]["source_en"],
                                 commit=rows[(b, c)]["source_commit"]) for (b, c), e in chapters.items()}
        deleted = []
        if since and not round_name and not before_first:
            dsql = ("SELECT g.id, g.book, g.ch, g.at, r.name FROM comment_gone g LEFT JOIN reader r ON r.id = g.reader"
                    " WHERE g.at >= ?")
            dargs = [since]
            for name, col in (("book", "g.book"), ("ch", "g.ch")):
                if req.query.get(name):
                    dsql += f" AND {col} = ?"
                    dargs.append(req.query[name])
            if who is not None:
                dsql += f" AND g.reader IN ({', '.join('?' * len(who)) or 'NULL'})"
                dargs += who
            deleted = [{"id": r[0], "book": r[1], "ch": r[2], "at": r[3], "reader": r[4]}
                       for r in req.conn.execute(dsql + " ORDER BY g.id", dargs)]
        return 200, {"exported": stamp, "since": since, "round": round_name, "before_first_round": before_first,
                     "chapters": info, "comments": [c for _, c in out], "deleted": deleted}

    def admin_processed(self, req):
        """Mark comments processed. With revs ({id: rev} from an export), a comment changed since then is left alone."""
        data = req.json()
        ids = data.get("ids")
        if not isinstance(ids, list) or not ids:
            raise HTTPError(400, "bad_ids", f"ids must be a list of 1 to {PROCESSED_MOST} comment numbers.")
        try:
            ids = id_list(ids, "ids", PROCESSED_MOST)
        except HTTPError:
            raise HTTPError(400, "bad_ids", f"ids must be a list of 1 to {PROCESSED_MOST} comment numbers; "
                            f"send at most {PROCESSED_MOST} at once.")
        flag = data.get("processed", True)
        if not isinstance(flag, bool):
            raise HTTPError(400, "bad_field", "processed must be true or false.")
        revs = data.get("revs") or {}
        if not isinstance(revs, dict) or not all(isinstance(v, str) for v in revs.values()):
            raise HTTPError(400, "bad_field", "revs must map comment numbers to the rev in the export.")
        found, changed = set(), set()
        with db.tx(req.conn):
            for i in ids:
                row = req.conn.execute("SELECT kind, quote, text FROM comment WHERE id = ?", (i,)).fetchone()
                if row is None:
                    continue
                found.add(i)
                rev = revs.get(str(i))
                if rev is not None and rev != comment_rev(row["kind"], row["quote"], row["text"]):
                    changed.add(i)
                    continue
                req.conn.execute("UPDATE comment SET processed = ? WHERE id = ?", (int(flag), i))
        return 200, {"updated": len(found - changed), "missing": sorted(set(ids) - found), "changed": sorted(changed)}

    def admin_replies(self, req):
        """Set or clear the translator's replies: {"replies": [{"id": 12, "reply": "...", "rev": "..."}]}, at most
        REPLIES_MOST. An empty reply clears one. With rev (from the export or the triage packet), a comment its
        reader changed since is left alone and listed in changed. All are applied in one transaction.
        Answers {updated, cleared, missing, changed}."""
        items = req.json().get("replies")
        if not isinstance(items, list) or not 1 <= len(items) <= REPLIES_MOST:
            raise HTTPError(400, "bad_field", f"replies must be a list of 1 to {REPLIES_MOST} replies.")
        wanted, problems = [], []
        for k, item in enumerate(items, 1):
            cid = item.get("id") if isinstance(item, dict) else None
            if type(cid) is not int or not 1 <= cid <= 2 ** 63 - 1:
                problems.append(f"Reply {k}: id must be a comment number.")
                continue
            rev = item.get("rev")
            if rev is not None and not isinstance(rev, str):
                problems.append(f"Reply {k} (comment {cid}): rev must be text, as in the export.")
                continue
            try:
                text = clean(item.get("reply"), "reply", REPLY_LIMIT, False)
            except HTTPError as e:
                problems.append(f"Reply {k} (comment {cid}): {e.message}")
                continue
            wanted.append((cid, text, rev))
        if problems:
            raise HTTPError(400, "bad_replies", " ".join(problems[:20]), details={"problems": problems})
        updated, cleared, missing, changed = 0, 0, [], []
        stamp = db.now()
        with db.tx(req.conn):
            for cid, text, rev in wanted:
                row = req.conn.execute("SELECT kind, quote, text FROM comment WHERE id = ?", (cid,)).fetchone()
                if row is None:
                    missing.append(cid)
                elif rev is not None and rev != comment_rev(row["kind"], row["quote"], row["text"]):
                    changed.append(cid)
                else:
                    req.conn.execute("UPDATE comment SET reply = ?, reply_at = ? WHERE id = ?",
                                     (text, stamp if text else None, cid))
                    if text:
                        updated += 1
                    else:
                        cleared += 1
        return 200, {"updated": updated, "cleared": cleared, "missing": sorted(set(missing)),
                     "changed": sorted(set(changed))}

    # ---------- admin: review rounds ----------

    def rounds_json(self, conn, only=None):
        current = set(current_rounds(conn).values())
        counts = {r[0]: r[1] for r in conn.execute("SELECT round, COUNT(*) FROM comment WHERE round IS NOT NULL"
                                                   " GROUP BY round")}
        return [{"id": r["id"], "book": r["book"], "name": r["name"], "started": r["started"],
                 "current": r["id"] in current, "comments": counts.get(r["id"], 0)}
                for r in conn.execute("SELECT id, book, name, started FROM review_round ORDER BY book, id")
                if only is None or r["id"] == only]

    def admin_rounds(self, req):
        """Every review round, oldest first in each book, with its comment count. before counts each book's
        comments written before its first round."""
        before = {r[0]: r[1] for r in req.conn.execute(
            "SELECT book, COUNT(*) FROM comment WHERE round IS NULL GROUP BY book")}
        return 200, {"rounds": self.rounds_json(req.conn), "before": before}

    def admin_new_round(self, req):
        """{book, name}: a new review round of the book starts now and becomes its current round. Readers then
        see only the comments they write from now on; earlier comments stay on the site."""
        data = req.json()
        book, name = data.get("book"), data.get("name")
        if not isinstance(book, str) or not BOOK_ID_RE.fullmatch(book):
            raise HTTPError(400, "bad_field", "book must be a book id, as SC.")
        if not isinstance(name, str) or not ROUND_NAME_RE.fullmatch(name):
            raise HTTPError(400, "bad_round_name", "A round name is 1 to 40 letters, digits, dots, hyphens or "
                            "underscores, starting with a letter or digit, as 2026-11 or second-reading.")
        try:
            with db.tx(req.conn):
                cur = req.conn.execute("INSERT INTO review_round (book, name, started) VALUES (?, ?, ?)",
                                       (book, name, db.now()))
        except sqlite3.IntegrityError:
            raise HTTPError(409, "round_taken", f"{book} already has a round named {name}.")
        return 201, self.rounds_json(req.conn, cur.lastrowid)[0]

    # ---------- admin: one reader's comments between two times ----------

    def admin_delete_comments(self, req, rid):
        """{from, to, delete, upto}: the comments reader rid wrote from the UTC time from up to, but not including,
        the UTC time to, in every chapter and round. Without delete true it only counts them. upto, the last
        comment number a count gave, keeps out the comments written after that count, so a delete removes only
        the comments counted. The answer is {reader, name, from, to, comments, deleted, chapters, last}: comments
        counts those found, chapters counts them by chapter, deleted those deleted, and last is the highest
        comment number found, or null. A deleted comment is recorded for the next export of what changed."""
        reader = self.reader_json(req.conn, int(rid))
        data = req.json()
        start, end = data.get("from"), data.get("to")
        if not all(isinstance(x, str) and STAMP_RE.fullmatch(x) for x in (start, end)) or start >= end:
            raise HTTPError(400, "bad_field", "from and to must be UTC times such as 2026-10-22T08:30:00Z, from "
                            "before to.")
        delete = data.get("delete", False)
        if not isinstance(delete, bool):
            raise HTTPError(400, "bad_field", "delete must be true or false.")
        upto = data.get("upto")
        if upto is not None and (type(upto) is not int or not 1 <= upto <= 2 ** 63 - 1):
            raise HTTPError(400, "bad_field", "upto must be a comment number, the last that the count gave.")
        sql = "SELECT id, client_id, reader, book, ch FROM comment WHERE reader = ? AND created >= ? AND created < ?"
        args = [reader["id"], start, end]
        if upto is not None:
            sql += " AND id <= ?"
            args.append(upto)
        with db.tx(req.conn):
            rows = req.conn.execute(sql + " ORDER BY id", args).fetchall()
            if delete:
                forget(req.conn, rows)
        chapters = {}
        for r in rows:
            chapters[r["ch"]] = chapters.get(r["ch"], 0) + 1
        return 200, {"reader": reader["id"], "name": reader["name"], "from": start, "to": end,
                     "comments": len(rows), "deleted": len(rows) if delete else 0, "chapters": chapters,
                     "last": rows[-1]["id"] if rows else None}


class _FromEnvironment:
    """The production application: an App on the data directory named by REVIEW_DATA."""

    def __init__(self):
        self.app = None
        self.lock = threading.Lock()

    def __call__(self, environ, start_response):
        if self.app is None:
            with self.lock:
                if self.app is None:
                    data = os.environ.get("REVIEW_DATA")
                    if not data:
                        raise RuntimeError("REVIEW_DATA is not set")
                    self.app = App(data)
        return self.app(environ, start_response)


application = _FromEnvironment()
