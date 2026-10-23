"""Development server: one threaded process on 127.0.0.1 serving web/ and the API, with two conveniences.

Standard library only (wsgiref). In production Apache serves web/ and
waitress runs the API (server/prod.py); this module is never used there, and
no production module imports it.

The conveniences, for the dev server alone (make(..., standins=True), which
review.py serve --dev uses):

- sign-in with LINE goes to StandInLine, a stand-in OpenID provider on another
  port of 127.0.0.1 that signs in one of a few test users, and email codes go
  to files in DATA/mail/ (server/mail.py, the file provider);
- GET /api/dev/readers and POST /api/dev/enter {reader} sign this browser in
  as any reader, for the page's "Enter as <reader>" button; GET
  /api/auth/state then says dev: true. The production API answers both paths
  404 not_found.

The tests use StandInLine too, with its knobs: tamper (claims to change in the
next ID tokens), alg (HS256, or ES256 to make the API ask the verify
endpoint), sign_secret (a wrong key to sign with), and token_status (an error
for /token to answer).
"""
import hashlib
import hmac
import html
import json
import secrets
import socketserver
import threading
import time
from collections import deque
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

from . import db
from .app import SECURITY_HEADERS
from .auth import b64url, b64url_decode
from .common import HTTPError, Request, dumps
from .mail import Mailer

TYPES = {
    ".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8", ".json": "application/json; charset=utf-8",
    ".txt": "text/plain; charset=utf-8", ".svg": "image/svg+xml", ".png": "image/png",
    ".ico": "image/x-icon", ".webmanifest": "application/manifest+json",
    ".ttf": "font/ttf", ".otf": "font/otf", ".woff": "font/woff", ".woff2": "font/woff2",
}


LOCAL_HOSTS = ("127.0.0.1", "localhost", "[::1]")


def local_host(host):
    """Whether a Host header names this machine (127.0.0.1, localhost or [::1], with any port). A request with
    no Host, as from a client of HTTP/1.0, is let through: a browser always sends one."""
    if not host:
        return True
    name = host.rsplit(":", 1)[0] if not host.endswith("]") else host
    return name.lower() in LOCAL_HOSTS


class Site:
    """WSGI: /api/ goes to the API app; every other path is a file under web_dir. With dev true, /api/dev/
    answers the dev server's own routes. A request whose Host names another machine is refused (local_host)."""

    def __init__(self, app, web_dir, dev=False):
        self.app = app
        self.web = Path(web_dir).resolve()
        self.dev = dev

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "") or "/"
        if not local_host(environ.get("HTTP_HOST", "")):
            # DNS rebinding: a page of another site, opened while the dev server runs, can make the browser send
            # it requests under that site's own name, which then counts as the same origin. The dev server is
            # opened only at 127.0.0.1 or localhost, so any other name in Host is refused.
            body = dumps({"error": "bad_host", "message": "The dev server answers only at 127.0.0.1 or localhost."})
            start_response("403 Forbidden", SECURITY_HEADERS + [
                ("Cache-Control", "no-store"), ("Content-Type", "application/json; charset=utf-8"),
                ("Content-Length", str(len(body)))])
            return [body]
        if self.dev and path.startswith("/api/dev/"):
            return self.dev_route(environ, start_response, path)
        if path == "/api" or path.startswith("/api/"):
            return self.app(environ, start_response)
        return self.static(environ, start_response, path)

    def static(self, environ, start_response, path):
        method = environ.get("REQUEST_METHOD", "GET").upper()
        rel = path.lstrip("/")
        if not rel or rel.endswith("/"):
            rel += "index.html"
        target = None
        if "\0" not in rel and not any(part.startswith(".") for part in Path(rel).parts):
            try:
                target = (self.web / rel).resolve()
                if not target.is_relative_to(self.web) or not target.is_file():
                    target = None
            except (OSError, ValueError):
                target = None
        if method not in ("GET", "HEAD"):
            status, body, ctype = "405 Method Not Allowed", b"Method not allowed\n", TYPES[".txt"]
        elif target is None:
            status, body, ctype = "404 Not Found", b"Not found\n", TYPES[".txt"]
        else:
            status, body = "200 OK", target.read_bytes()
            ctype = TYPES.get(target.suffix.lower(), "application/octet-stream")
        headers = SECURITY_HEADERS + [("Content-Type", ctype), ("Content-Length", str(len(body))),
                                      ("Cache-Control", "no-cache")]
        start_response(status, headers)
        return [b""] if method == "HEAD" else [body]

    def dev_route(self, environ, start_response, path):
        """GET /api/dev/readers: every reader, {readers: [{id, name, active}]}. POST /api/dev/enter {reader}:
        this browser is signed in as that reader (a session of via "dev"), {id, name}. Both need X-Review-Page."""
        conn = db.connect(self.app.db_path)
        req = Request(environ, conn)
        extra = []
        try:
            self.app.page_guard(req)
            if path == "/api/dev/readers" and req.method == "GET":
                status, payload = 200, {"readers": [{"id": r[0], "name": r[1], "active": bool(r[2])} for r in
                                                    conn.execute("SELECT id, name, active FROM reader ORDER BY name")]}
            elif path == "/api/dev/enter" and req.method == "POST":
                rid = req.json().get("reader")
                reader = conn.execute("SELECT * FROM reader WHERE id = ?", (rid,)).fetchone() \
                    if type(rid) is int else None
                if reader is None:
                    raise HTTPError(404, "no_reader", "No such reader.")
                with db.tx(conn):
                    s = self.app.open_session(req, reader, "dev", None, db.now())
                extra = [self.app.set_cookie("session", s["token"], self.app.auth.session_days * 86400)]
                status, payload = 200, {"id": reader["id"], "name": reader["name"]}
            else:
                raise HTTPError(404, "not_found", "Not found.")
        except HTTPError as e:
            status, payload, extra = e.status, {"error": e.error, "message": e.message}, e.headers
        finally:
            conn.close()
        body = dumps(payload)
        start_response(f"{status} {HTTPStatus(status).phrase}", SECURITY_HEADERS + [
            ("Cache-Control", "no-store"), ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(body)))] + extra)
        return [body]


class ThreadingServer(socketserver.ThreadingMixIn, WSGIServer):
    daemon_threads = True
    allow_reuse_address = True
    standin = None

    def server_close(self):
        super().server_close()
        if self.standin is not None:
            self.standin.close()


class QuietHandler(WSGIRequestHandler):
    def log_message(self, *args):
        pass


def use_standins(app, standin):
    """The dev server's sign-in: LINE goes to the stand-in, and every mail to a file in DATA/mail/."""
    app.auth.line = standin.settings()
    app.auth.mail = {"provider": "file", "from": "review@dev.invalid", "from_name": "Proofreading site (dev)",
                     "dir": str(Path(app.data) / "mail")}
    app.auth.email = True
    app.mailer = Mailer(app.auth.mail)
    app.dev = True


def make(app, web_dir, port=8087, quiet=False, standins=True):
    """A threaded server on 127.0.0.1:port; call serve_forever() on it, and server_close() at the end. With
    standins, the dev server's sign-in conveniences are on (the module's docstring)."""
    standin = None
    if standins:
        standin = StandInLine().start()
        use_standins(app, standin)
    httpd = make_server("127.0.0.1", port, Site(app, web_dir, dev=standins), server_class=ThreadingServer,
                        handler_class=QuietHandler if quiet else WSGIRequestHandler)
    httpd.standin = standin
    if standin is not None and not quiet:
        print(f"Sign-in on this dev server: LINE goes to a stand-in at {standin.base}, and email codes are written "
              f"to {app.auth.mail['dir']}.", flush=True)
    return httpd


# ---------- the stand-in for LINE Login ----------

class StandInLine:
    """A stand-in OpenID provider on 127.0.0.1 in the shape of LINE Login v2.1: /authorize shows "Sign in as"
    links for a few test users, /token trades a code for an HS256 ID token signed with the channel secret
    (checking the PKCE verifier), /verify checks a token as LINE's verify endpoint does, and
    /.well-known/openid-configuration describes it."""

    USERS = [("U0000000000000000000000000000dev1", "LINE tester 1"),
             ("U0000000000000000000000000000dev2", "LINE tester 2"),
             ("U0000000000000000000000000000dev3", "LINE tester 3")]

    def __init__(self, channel_id="1234567890", channel_secret=None, port=0):
        self.channel_id = channel_id
        self.channel_secret = channel_secret or secrets.token_hex(16)
        self.users = list(self.USERS)
        self.codes = {}
        self.issued = {}            # ID tokens given, for /verify
        self.tamper = {}            # claims to change in the ID tokens it gives
        self.alg = "HS256"
        self.token_status = None    # a status for /token to answer instead of a token
        self.sign_secret = None     # a key to sign ID tokens with instead of the channel secret
        self.requests = deque(maxlen=200)   # (path, form) of the requests it took, for the tests
        self.lock = threading.Lock()
        handler = type("Handler", (StandInHandler,), {"standin": self})
        self.httpd = ThreadingHTTPServer(("127.0.0.1", port), handler)
        self.httpd.daemon_threads = True
        self.thread = None

    @property
    def base(self):
        return f"http://127.0.0.1:{self.httpd.server_address[1]}"

    def settings(self):
        """auth.line for config.json, pointing at this stand-in."""
        return {"channel_id": self.channel_id, "channel_secret": self.channel_secret,
                "authorize_url": self.base + "/authorize", "token_url": self.base + "/token",
                "verify_url": self.base + "/verify", "issuer": self.base}

    def start(self):
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        return self

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()

    def check_authorize(self, q):
        """None when an authorize request is as LINE wants it; otherwise why not."""
        if q.get("response_type") != "code":
            return "response_type must be code"
        if q.get("client_id") != self.channel_id:
            return "unknown client_id"
        if not q.get("redirect_uri") or not q.get("state"):
            return "redirect_uri and state are required"
        if set(q.get("scope", "").split()) != {"profile", "openid"}:
            return "scope must be profile openid"
        if q.get("code_challenge_method") != "S256" or not q.get("code_challenge"):
            return "code_challenge with S256 is required"
        return None

    def approve(self, q, user=0):
        """Where the browser goes after a test user signs in: the redirect_uri with code and state."""
        code = secrets.token_urlsafe(16)
        with self.lock:
            self.codes[code] = {"q": dict(q), "user": user, "at": time.time()}
        return q["redirect_uri"] + "?" + urlencode({"code": code, "state": q["state"]})

    def cancel(self, q):
        return q["redirect_uri"] + "?" + urlencode({"error": "ACCESS_DENIED", "error_description":
                                                    "The user has denied the approval", "state": q["state"]})

    def id_token(self, q, user):
        sub, name = self.users[user]
        now = int(time.time())
        claims = {"iss": self.base, "sub": sub, "aud": self.channel_id, "exp": now + 3600, "iat": now,
                  "nonce": q.get("nonce"), "amr": ["linesso"], "name": name,
                  "picture": "https://profile.line-scdn.net/dev-picture"}
        claims.update(self.tamper)
        claims = {k: v for k, v in claims.items() if v is not None}
        head = b64url(json.dumps({"typ": "JWT", "alg": self.alg}).encode())
        body = b64url(json.dumps(claims).encode())
        if self.alg == "HS256":
            key = self.sign_secret or self.channel_secret
            sig = hmac.new(key.encode(), f"{head}.{body}".encode(), hashlib.sha256).digest()
        else:
            sig = secrets.token_bytes(64)       # a stand-in signature that only /verify knows
        token = f"{head}.{body}.{b64url(sig)}"
        with self.lock:
            self.issued[token] = claims
        return token

    def token(self, form):
        """(status, answer) of /token."""
        if self.token_status:
            return self.token_status, {"error": "invalid_request", "error_description": "a stand-in refusal"}
        with self.lock:
            entry = self.codes.pop(form.get("code", ""), None)
        if entry is None or time.time() - entry["at"] > 600:
            return 400, {"error": "invalid_grant", "error_description": "unknown or used code"}
        q = entry["q"]
        if form.get("grant_type") != "authorization_code" or form.get("client_id") != self.channel_id \
                or form.get("client_secret") != self.channel_secret or form.get("redirect_uri") != q["redirect_uri"]:
            return 400, {"error": "invalid_request", "error_description": "wrong client or redirect_uri"}
        verifier = form.get("code_verifier", "")
        if b64url(hashlib.sha256(verifier.encode()).digest()) != q["code_challenge"]:
            return 400, {"error": "invalid_grant", "error_description": "code_verifier does not match"}
        return 200, {"access_token": secrets.token_urlsafe(24), "expires_in": 2592000,
                     "id_token": self.id_token(q, entry["user"]), "refresh_token": secrets.token_urlsafe(24),
                     "scope": "profile openid", "token_type": "Bearer"}

    def verify(self, form):
        with self.lock:
            claims = self.issued.get(form.get("id_token", ""))
        if claims is None or form.get("client_id") != self.channel_id or (
                form.get("nonce") and form.get("nonce") != claims.get("nonce")):
            return 400, {"error": "invalid_request", "error_description": "Invalid IdToken."}
        return 200, claims


class StandInHandler(BaseHTTPRequestHandler):
    standin = None

    def log_message(self, *args):
        pass

    def send(self, status, body, ctype="application/json", location=None):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(status)
        if location:
            self.send_header("Location", location)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        s = self.standin
        parts = urlsplit(self.path)
        q = {k: v[-1] for k, v in parse_qs(parts.query).items()}
        s.requests.append((parts.path, q))
        if parts.path == "/.well-known/openid-configuration":
            return self.send(200, {"issuer": s.base, "authorization_endpoint": s.base + "/authorize",
                                   "token_endpoint": s.base + "/token", "id_token_signing_alg_values_supported":
                                   ["HS256", "ES256"], "code_challenge_methods_supported": ["S256"]})
        if parts.path in ("/authorize", "/approve", "/cancel"):
            why = s.check_authorize(q)
            if why:
                return self.send(400, f"Stand-in LINE: {why}.\n".encode(), "text/plain; charset=utf-8")
            if parts.path == "/approve":
                return self.send(302, b"", "text/plain", location=s.approve(q, int(q.get("user", "0")) % len(s.users)))
            if parts.path == "/cancel":
                return self.send(302, b"", "text/plain", location=s.cancel(q))
            keep = urlencode({k: v for k, v in q.items() if k != "user"})
            links = "".join(f'<li><a href="/approve?{html.escape(keep)}&amp;user={i}">Sign in as {html.escape(name)}'
                            f"</a></li>" for i, (_, name) in enumerate(s.users))
            page = (f"<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width'>"
                    f"<title>Stand-in LINE Login</title><h1>Stand-in LINE Login</h1>"
                    f"<p>This dev server has no real LINE. Choose a test user.</p><ul>{links}</ul>"
                    f'<p><a href="/cancel?{html.escape(keep)}">Cancel</a></p>')
            return self.send(200, page.encode(), "text/html; charset=utf-8")
        if parts.path == "/token":
            return self.send(405, {"error": "invalid_request", "error_description": "POST only"})
        return self.send(404, {"error": "not_found"})

    def do_POST(self):
        s = self.standin
        length = int(self.headers.get("Content-Length") or 0)
        form = {k: v[-1] for k, v in parse_qs(self.rfile.read(length).decode()).items()}
        path = urlsplit(self.path).path
        s.requests.append((path, form))
        if path == "/token":
            return self.send(*s.token(form))
        if path == "/verify":
            return self.send(*s.verify(form))
        return self.send(404, {"error": "not_found"})


def decode_claims(token):
    """The claims of an ID token, unchecked: for the tests."""
    return json.loads(b64url_decode(token.split(".")[1]))
