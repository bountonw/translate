"""WSGI application for the proofreading site: the JSON API under /api/.

server.app:application reads its data directory from REVIEW_DATA on the
first request. Tests and the dev server build their own with App(data_dir).
Readers send "Authorization: Bearer <code>"; the routes under /api/admin/
take the admin token instead. Each reader sees and changes only their own
comments, and only in published chapters open to them: covered by their own
grants or by the grants of a group of theirs that is switched on.

This module holds the reader routes, the chapter and export admin routes and
the routing. Readers and groups are in server/people.py, shared helpers in
server/common.py, and each feature in server/features/.
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
from .common import (ADMIN_LIMIT, QUOTE_LIMIT, TEXT_LIMIT, HTTPError, Request, bool_field, clean, dumps,
                     id_list)
from .content import plain, safe_html
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
CACHE_MOST = 256                 # chapters kept parsed in memory
PROCESSED_MOST = 10000           # comments marked processed in one request; review.py sends 5000 at a time

TOKEN_RE = re.compile(r"(?i:bearer) +([A-Za-z0-9_-]{16,128})")
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
    "comment_limit": (403, "the reader already has limits.comments comments"),
    "slow_down": (429, "more than limits.writes_per_minute changes in one minute; Retry-After says when to try"),
    "no_comment": (404, "the comment no longer exists, as when it was deleted on another device"),
}

# Whether a chapter is open to reader :r: an own grant, or a grant of a group of theirs that is on.
GRANTED = """(
  EXISTS (SELECT 1 FROM "grant" g WHERE g.reader = :r AND g.book = c.book AND g.chapter IN (c.id, '*'))
  OR EXISTS (SELECT 1 FROM group_member m
             JOIN reader_group t ON t.id = m.grp AND t.active = 1
             JOIN group_grant gg ON gg.grp = m.grp AND gg.book = c.book AND gg.chapter IN (c.id, '*')
             WHERE m.reader = :r))"""
ACCESS_SQL = f"SELECT c.version FROM chapter c WHERE c.book = :book AND c.id = :ch AND c.published = 1 AND {GRANTED}"
OPEN_SQL = f"""SELECT c.book, c.id, c.n, c.title_th, c.title_en, c.version, c.count FROM chapter c
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


def comment_json(row):
    return {"id": row["id"], "client_id": row["client_id"], "book": row["book"], "ch": row["ch"],
            "a": row["a"], "kind": row["kind"], "quote": row["quote"], "text": row["text"],
            "created": row["created"], "updated": row["updated"], "processed": bool(row["processed"])}


class App(People):
    """The API as a WSGI callable over one data directory."""

    def __init__(self, data_dir, writes_per_minute=60, max_comments=5000, public_url=None, feature_list=None):
        self.data = Path(data_dir)
        self.db_path = self.data / db.DB_NAME
        self.registry = features.Registry(features.load() if feature_list is None else feature_list)
        db.init_db(self.db_path, [(f.name, f.migrations) for f in self.registry.features.values()])
        self.writes_per_minute = writes_per_minute
        self.max_comments = max_comments
        self.public_url = public_url
        self.lock = threading.Lock()
        self.writes = {}
        self.swept = time.monotonic()
        self.cache = {}
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
            ("GET", r"/api/admin/groups", self.admin_groups, "admin"),
            ("POST", r"/api/admin/groups", self.admin_new_group, "admin"),
            ("PATCH", rf"/api/admin/groups/{NUM}", self.admin_edit_group, "admin"),
            ("DELETE", rf"/api/admin/groups/{NUM}", self.admin_remove_group, "admin"),
            ("POST", rf"/api/admin/groups/{NUM}/members", self.admin_group_members, "admin"),
            ("GET", r"/api/admin/features", self.admin_features, "admin"),
            ("GET", r"/api/admin/export", self.admin_export, "admin"),
            ("POST", r"/api/admin/processed", self.admin_processed, "admin"),
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
                self.admin_auth(req)
                req.limit = ADMIN_LIMIT
            result = handler(req, *m.groups())
            status, payload = result[0], result[1]
            extra = result[2] if len(result) > 2 else []
            if payload is None or isinstance(payload, bytes):
                return status, payload, extra
            return status, dumps(payload), extra
        if allowed:
            raise HTTPError(405, "bad_method", "This method is not allowed here.")
        raise HTTPError(404, "not_found", "Not found.")

    # ---------- auth and limits ----------

    def reader_auth(self, req):
        m = TOKEN_RE.fullmatch(req.header("Authorization").strip())
        if not m:
            raise HTTPError(401, "no_code", "This link has no code. Ask the translator for a new link.")
        row = req.conn.execute("SELECT * FROM reader WHERE code_hash = ?", (db.sha256(m.group(1)),)).fetchone()
        if row is None or not row["active"]:
            raise HTTPError(401, "bad_code", "This link does not work. Ask the translator for a new link.")
        req.reader = row

    def admin_auth(self, req):
        m = TOKEN_RE.fullmatch(req.header("Authorization").strip())
        expected = db.admin_hash(self.data)
        if not m or not expected or not hmac.compare_digest(db.sha256(m.group(1)), expected):
            raise HTTPError(401, "bad_token", "The admin token is missing or wrong.")

    def rate(self, req):
        """Allow writes_per_minute writes per reader in any 60 seconds. Only readers who wrote in the
        last minute or two are remembered, so the table stays small however many readers there are."""
        now = time.monotonic()
        with self.lock:
            if now - self.swept >= 60:
                self.writes = {k: q for k, q in self.writes.items() if q and now - q[-1] < 60}
                self.swept = now
            q = self.writes.setdefault(req.reader["id"], deque())
            while q and now - q[0] >= 60:
                q.popleft()
            if len(q) >= self.writes_per_minute:
                wait = int(60 - (now - q[0])) + 1
                raise HTTPError(429, "slow_down", "Too many changes in one minute. Wait and try again.",
                                [("Retry-After", str(wait))])
            q.append(now)

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
        row = conn.execute("SELECT * FROM chapter WHERE book = ? AND id = ?", (book, ch)).fetchone()
        paras = json.loads(row["paragraphs"])
        meta = {"book": book, "id": ch, "n": row["n"], "title_th": row["title_th"],
                "title_en": row["title_en"], "version": row["version"]}
        short = [{k: v for k, v in p.items() if k != "en"} for p in paras]
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
        rid = req.reader["id"]
        q = req.conn.execute
        chapters = q(OPEN_SQL, {"r": rid}).fetchall()
        counts = {(r[0], r[1]): r[2] for r in q(
            "SELECT book, ch, COUNT(*) FROM comment WHERE reader = ? GROUP BY book, ch", (rid,))}
        places = {(r[0], r[1]): r[2] for r in q("SELECT book, ch, a FROM place WHERE reader = ?", (rid,))}
        done = {(r[0], r[1]): (bool(r[2]), r[3]) for r in q(
            "SELECT book, ch, finished, at FROM finished WHERE reader = ?", (rid,))}
        books = {r[0]: (r[1], r[2], r[3]) for r in q("SELECT id, title_en, language, title_th FROM book")}
        out = []
        for c in chapters:
            k = (c["book"], c["id"])
            fin, at = done.get(k, (False, None))
            place = places.get(k)
            if place is not None and place not in self.parsed(req.conn, *k)["order"]:
                place = None        # the paragraph is not in the chapter's current version
            out.append({"book": c["book"], "id": c["id"], "n": c["n"], "title_th": c["title_th"],
                        "title_en": c["title_en"], "version": c["version"], "paragraphs": c["count"],
                        "finished": fin, "finished_at": at if fin else None,
                        "place": place, "comments": counts.get(k, 0)})
        used = sorted({c["book"] for c in chapters})
        settings = self.settings(req)
        return 200, {"name": req.reader["name"],
                     # The same value as features.english.on, kept for a page saved on the device before
                     # the features field existed; the service worker can serve such a page for one visit.
                     "english": bool(settings.get("english.on")),
                     "features": self.registry.me(req.conn, req.reader, settings),
                     "limits": {"quote": QUOTE_LIMIT, "text": TEXT_LIMIT, "comments": self.max_comments,
                                "writes_per_minute": self.writes_per_minute},
                     "comments_total": sum(counts.values()),
                     "books": [{"id": b, "title_en": books[b][0], "title_th": books[b][2], "language": books[b][1]}
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
        sql, args = "SELECT * FROM comment WHERE reader = ?", [req.reader["id"]]
        for name in ("book", "ch"):
            if req.query.get(name):
                sql += f" AND {name} = ?"
                args.append(req.query[name])
        rows = req.conn.execute(sql + " ORDER BY id", args).fetchall()
        return 200, {"comments": [comment_json(r) for r in rows]}

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
        quote = clean(quote, "quote", QUOTE_LIMIT, kind == "wording")
        text = clean(text, "text", TEXT_LIMIT, True)
        return kind, quote, text

    def add_comment(self, req):
        data = req.json()
        self.rate(req)
        rid = req.reader["id"]
        client_id = data.get("client_id")
        if not isinstance(client_id, str) or not CLIENT_ID_RE.fullmatch(client_id):
            raise HTTPError(400, "bad_client_id", "client_id is missing or malformed.")
        get = "SELECT * FROM comment WHERE reader = ? AND client_id = ?"
        row = req.conn.execute(get, (rid, client_id)).fetchone()
        if row is not None:
            return 200, comment_json(row)
        entry = self.access(req, data.get("book"), data.get("ch"))
        a = self.anchor(entry, data.get("a"))
        kind, quote, text = self.comment_fields(data.get("kind"), data.get("quote"), data.get("text"))
        stamp = db.now()
        try:
            with db.tx(req.conn):
                n = req.conn.execute("SELECT COUNT(*) FROM comment WHERE reader = ?", (rid,)).fetchone()[0]
                if n >= self.max_comments:
                    raise HTTPError(403, "comment_limit", f"You have {self.max_comments} comments, the most allowed.")
                cur = req.conn.execute(
                    "INSERT INTO comment (client_id, reader, book, ch, a, kind, quote, text, version, created, updated)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (client_id, rid, data["book"], data["ch"], a, kind, quote, text, entry["version"], stamp, stamp))
        except sqlite3.IntegrityError:
            row = req.conn.execute(get, (rid, client_id)).fetchone()
            if row is None:
                raise
            return 200, comment_json(row)
        row = req.conn.execute("SELECT * FROM comment WHERE id = ?", (cur.lastrowid,)).fetchone()
        return 201, comment_json(row)

    def edit_comment(self, req, ref):
        data = req.json()
        self.rate(req)
        row = self.own(req, ref)
        self.access(req, row["book"], row["ch"])
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
        return 200, comment_json(row)

    def delete_comment(self, req, ref):
        self.rate(req)
        row = self.own(req, ref)
        self.access(req, row["book"], row["ch"])
        with db.tx(req.conn):
            req.conn.execute("DELETE FROM comment WHERE id = ?", (row["id"],))
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

    # ---------- admin: chapters ----------

    def admin_chapters(self, req):
        rows = req.conn.execute("""
            SELECT c.book, c.id, c.n, c.title_th, c.title_en, c.version, c.published, c.count, c.updated,
              (SELECT COUNT(*) FROM comment m WHERE m.book = c.book AND m.ch = c.id) AS comments,
              (SELECT COUNT(*) FROM comment m WHERE m.book = c.book AND m.ch = c.id AND m.processed = 0) AS open
            FROM chapter c ORDER BY c.book, c.n""").fetchall()
        return 200, {"chapters": [{
            "book": r["book"], "id": r["id"], "n": r["n"], "title_th": r["title_th"], "title_en": r["title_en"],
            "version": r["version"], "published": bool(r["published"]), "paragraphs": r["count"],
            "comments": r["comments"], "open": r["open"], "updated": r["updated"]} for r in rows]}

    def check_paragraphs(self, paras, language):
        if not isinstance(paras, list) or not 1 <= len(paras) <= 5000:
            raise HTTPError(400, "bad_paragraphs", "paragraphs must be a list of 1 to 5000 items.")
        out, seen = [], set()
        for p in paras:
            if not isinstance(p, dict):
                raise HTTPError(400, "bad_paragraphs", "Each paragraph must be an object.")
            a, th, fn, en = p.get("a"), p.get("th"), p.get("fn", []), p.get("en", "")
            if not isinstance(a, str) or not ANCHOR_RE.fullmatch(a) or a in seen:
                raise HTTPError(400, "bad_anchor", f"Bad or repeated anchor: {a!r}.")
            seen.add(a)
            if not isinstance(th, str) or not th.strip() or not isinstance(en, str) \
                    or not isinstance(fn, list) or not all(isinstance(x, str) for x in fn):
                raise HTTPError(400, "bad_paragraphs", f"{a}: th, fn and en must be text.")
            for part in [th, en, *fn]:
                if not safe_html(part):
                    raise HTTPError(400, "unsafe_html", f"{a}: only the tags of the content model are allowed.")
            # The English is checked by the rules for every book: no invisible character, no Thai or Lao digit.
            bad = forbidden_char(th + "".join(fn), language) or forbidden_char(en)
            if bad:
                raise HTTPError(400, "forbidden_character", f"{a}: holds the character U+{ord(bad):04X}.")
            out.append({"a": a, "th": th, "fn": fn, "en": en})
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
        title_th, title_en = data.get("title_th"), data.get("title_en", "")
        if not isinstance(title_th, str) or not title_th.strip() or not isinstance(title_en, str) \
                or len(title_th) > 300 or len(title_en) > 300:
            raise HTTPError(400, "bad_field", "title_th and title_en must be short text.")
        if forbidden_char(title_th, language) or forbidden_char(title_en) or "<" in title_th + title_en:
            raise HTTPError(400, "bad_field", "The title holds a forbidden character.")
        paras = self.check_paragraphs(data.get("paragraphs"), language)
        commit = data.get("commit") or ""
        if not isinstance(commit, str) or (commit and not COMMIT_RE.fullmatch(commit)):
            raise HTTPError(400, "bad_field", "commit must be a git commit id.")
        book_title = data.get("book_title_en") or ""
        if not isinstance(book_title, str) or len(book_title) > 300:
            raise HTTPError(400, "bad_field", "book_title_en must be short text.")
        # The book's title in its own language (the field is named th whatever the language is).
        book_title_th = data.get("book_title_th") or ""
        if not isinstance(book_title_th, str) or len(book_title_th) > 300 or "<" in book_title_th \
                or forbidden_char(book_title_th, language):
            raise HTTPError(400, "bad_field", "book_title_th must be short text without a forbidden character.")
        sources = data.get("sources") or []
        if not isinstance(sources, list) or len(sources) > 2 \
                or not all(isinstance(x, str) and SOURCE_RE.fullmatch(x) and ".." not in x for x in sources):
            raise HTTPError(400, "bad_field", "sources must be the Thai and English file paths.")
        source_th, source_en = (sources + ["", ""])[:2]
        content = json.dumps([title_th, title_en, paras], ensure_ascii=False, sort_keys=True)
        digest = db.sha256(content)[:12]
        version = f"{commit[:12]}-{digest}" if commit else digest
        stamp = db.now()
        with db.tx(req.conn):
            req.conn.execute(
                "INSERT INTO book (id, title_en, title_th, language) VALUES (?, ?, ?, ?) ON CONFLICT (id) DO UPDATE SET"
                " title_en = CASE WHEN excluded.title_en != '' THEN excluded.title_en ELSE book.title_en END,"
                " title_th = CASE WHEN excluded.title_th != '' THEN excluded.title_th ELSE book.title_th END,"
                " language = excluded.language", (book, book_title, book_title_th, language))
            old = req.conn.execute("SELECT version, content_hash, published FROM chapter WHERE book = ? AND id = ?",
                                   (book, ch)).fetchone()
            changed = old is None or old["content_hash"] != digest
            if changed:
                req.conn.execute(
                    "INSERT INTO chapter (book, id, n, title_th, title_en, version, content_hash, published, count,"
                    " paragraphs, updated) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?) ON CONFLICT (book, id) DO UPDATE SET"
                    " n = excluded.n, title_th = excluded.title_th, title_en = excluded.title_en,"
                    " version = excluded.version, content_hash = excluded.content_hash, published = 1,"
                    " count = excluded.count, paragraphs = excluded.paragraphs, updated = excluded.updated",
                    (book, ch, n, title_th, title_en, version, digest, len(paras),
                     json.dumps(paras, ensure_ascii=False), stamp))
            else:
                version = old["version"]
                req.conn.execute("UPDATE chapter SET published = 1, n = ? WHERE book = ? AND id = ?", (n, book, ch))
            # The files and their revision move together, so the pair can always be read back with git show.
            req.conn.execute("UPDATE chapter SET source_th = ?, source_en = ?, source_commit = ? WHERE book = ? AND id = ?",
                             (source_th, source_en, commit, book, ch))
        anchors = {p["a"] for p in paras}
        orphans = sum(1 for r in req.conn.execute("SELECT a FROM comment WHERE book = ? AND ch = ?", (book, ch))
                      if r[0] not in anchors)
        return 200, {"book": book, "id": ch, "version": version, "changed": changed, "paragraphs": len(paras),
                     "was_published": bool(old and old["published"]), "orphans": orphans}

    def admin_withdraw(self, req, book, ch):
        with db.tx(req.conn):
            cur = req.conn.execute("UPDATE chapter SET published = 0 WHERE book = ? AND id = ?", (book, ch))
        if cur.rowcount == 0:
            raise HTTPError(404, "no_chapter", "No such chapter.")
        return 200, {"book": book, "id": ch, "published": False}

    # ---------- admin: export ----------

    def admin_export(self, req):
        sql = "SELECT m.*, r.name AS reader_name FROM comment m JOIN reader r ON r.id = m.reader WHERE 1 = 1"
        args = []
        for name, col in (("book", "m.book"), ("ch", "m.ch"), ("reader", "r.name")):
            if req.query.get(name):
                sql += f" AND {col} = ?"
                args.append(req.query[name])
        if req.query.get("unprocessed") in ("1", "true", "yes"):
            sql += " AND m.processed = 0"
        rows = req.conn.execute(sql, args).fetchall()
        chapters, out = {}, []
        for r in rows:
            key = (r["book"], r["ch"])
            if key not in chapters:
                chapters[key] = self.parsed(req.conn, *key)
            entry = chapters[key]
            i = entry["order"].get(r["a"])
            para = entry["paras"][i] if i is not None else None
            th = plain(para["th"]) if para else ""
            notes = [plain(f) for f in para["fn"]] if para else []
            found = None
            if r["quote"]:
                q = squash(r["quote"])
                found = any(q in squash(t) for t in [th, *notes])
            out.append(({"n": entry["meta"]["n"], "i": i if i is not None else 10 ** 6}, {
                "id": r["id"], "rev": comment_rev(r["kind"], r["quote"], r["text"]), "reader": r["reader_name"],
                "book": r["book"], "ch": r["ch"], "anchor": r["a"],
                "kind": r["kind"], "quote": r["quote"], "text": r["text"], "created": r["created"],
                "updated": r["updated"], "processed": bool(r["processed"]), "version_seen": r["version"],
                "version_now": entry["version"], "anchor_missing": para is None, "quote_found": found,
                "th": th, "footnotes": notes}))
        out.sort(key=lambda x: (x[1]["book"], x[0]["n"], x[0]["i"], x[1]["created"], x[1]["id"]))
        rows = {(r["book"], r["id"]): r for r in req.conn.execute(
            "SELECT book, id, published, source_th, source_en, source_commit FROM chapter")}
        info = {f"{b}/{c}": dict(e["meta"], published=bool(rows[(b, c)]["published"]),
                                 source_th=rows[(b, c)]["source_th"], source_en=rows[(b, c)]["source_en"],
                                 commit=rows[(b, c)]["source_commit"]) for (b, c), e in chapters.items()}
        return 200, {"exported": db.now(), "chapters": info, "comments": [c for _, c in out]}

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
