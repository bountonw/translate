"""Signing in: accounts, identities, sessions, LINE Login and the email code, mixed into the App of server/app.py.

One person per account. Today every account is a reader: the account's number is the reader's number, and
the tables name it "account" (identity.account, session.account, auth_flow.account) so that an editor's or
the translator's account can join later without a change to them (EXTENDING.md, "Accounts and roles").

A reader signs in with LINE Login or with a six-digit code sent by email; config.json switches each route on
(auth.line, auth.email), and a route whose settings are absent is off. The invite link is used once: the first
sign-in through it ties the reader to a LINE account or an email address (an identity) and spends the link
(reader.link_used). Each browser then holds a session in an HttpOnly cookie, rv on the dev server and
__Host-rv over https, kept for auth.session_days (30) from the last visit; a new browser signs in again, with
nobody waiting. A reader with the switch "Link signs in" (reader.link_signs_in) keeps the personal link and
the two-device lock of server/app.py instead; so does every reader while no route is switched on, and a
reader with no identity yet while auth.require_identity is false.

A general link (general_link) belongs to a group and only asks for access: the person signs in, a row of
access_request is made, the translator is told (config.json "notify"), and nothing opens before he approves
it on the admin routes (server/accounts.py).

Cross-site requests: the session cookie is SameSite=Lax, and every request the page makes with it carries
X-Review-Page: 1, a header no other site can send without a preflight that the server never answers.
"""
import base64
import hashlib
import hmac
import ipaddress
import json
import re
import secrets
import shlex
import socket
import sqlite3
import sys
import threading
import time
import unicodedata
import urllib.error
import urllib.request
from collections import deque
from urllib.parse import quote, urlencode, urlsplit

from . import db
from .common import UNKNOWN_AGENT, HTTPError, device_agent
from .mail import Mailer, MailError, NoRedirect, address, both, is_local, subject
from .mail import load as load_mail
from .text import DIGITS, strip_invisible

LINE_DEFAULTS = {"authorize_url": "https://access.line.me/oauth2/v2.1/authorize",
                 "token_url": "https://api.line.me/oauth2/v2.1/token",
                 "verify_url": "https://api.line.me/oauth2/v2.1/verify",
                 "issuer": "https://access.line.me"}
LINE_SCOPE = "profile openid"
AUTH_DEFAULTS = {"session_days": 30, "require_identity": False}
NOTIFY_DEFAULTS = {"email": "", "requests": True, "first_signin": True}
INVITE_DEFAULTS = {"external_browser": False, "general_days": 90, "general_uses": 100}

CODE_MINUTES = 10           # an email code works for ten minutes (the translator's ruling)
CODE_TRIES = 3              # and takes three tries
FLOW_MINUTES = 10           # a LINE sign-in must come back within ten minutes
# Codes to one email address. A stranger's codes come from the stranger's own address on the internet, so the
# share per address on the internet keeps one stranger from using up a reader's codes; the cap per address
# alone bounds the guesses at one reader's code (12 codes of 3 tries a day: about 1 in 900 in 30 days) and the
# mail one address gets.
CODES_PER_CLIENT_DAY = 5    # codes to one address from one address on the internet in 24 hours
CODES_PER_DAY = 12          # codes to one address from anywhere in 24 hours
ADD_CODES_PER_HOUR = 5      # codes one signed-in reader asks for to add an address, in an hour
WRONG_CODES_PER_HOUR = 30   # wrong codes typed from one address on the internet in an hour
MAIL_WAIT = 6               # seconds the server waits for a code's mail before it answers mail_failed
STARTS_PER_MINUTE = 10      # sign-in starts (LINE or email) from one address on the internet in a minute
FINISHES_PER_MINUTE = 10    # codes typed from one address on the internet in a minute
LOOKUPS_PER_MINUTE = 30     # links and general links checked from one address on the internet in a minute
REQUESTS_PER_HOUR = 20      # new access requests through one general link in an hour
LINK_CODES_PER_HOUR = 10    # codes asked for through one personal link in an hour
JOIN_CODES_PER_HOUR = 60    # codes asked for through one general link in an hour, to any addresses
SEEN_EVERY = 10             # minutes between two records of a session's last visit
TIMEOUT = 10                # seconds LINE may take to answer
LEEWAY = 120                # seconds of clock difference allowed in an ID token's times
PAGE_HEADER = "X-Review-Page"
TOKEN_RE = re.compile(r"(?i:bearer) +([A-Za-z0-9_-]{16,128})")   # Authorization: Bearer <a link's code or the admin token>
COOKIE_RE = re.compile(r"[A-Za-z0-9_-]{20,100}")

# What each sign-in ends in: the page reads it from #auth=... after LINE, or from "result" after the email code.
RESULTS = {
    "signed_in": "the browser is signed in",
    "added": "the identity is now one more way to sign in to the account already signed in",
    "request_sent": "a request to read went to the translator; nothing opens before he approves it",
    "request_waiting": "this identity's request already waits for the translator",
    "request_declined": "the translator declined this identity's request",
    "no_account": "no reader uses this LINE account or address",
    "identity_taken": "this LINE account or address belongs to another reader",
    "link_used": "the link was used meanwhile to sign in",
    "link_signs_in": "the reader's link signs in by itself (\"Link signs in\"), so it ties no LINE account or address",
    "stopped": "the reader's access is stopped (revoke)",
    "join_closed": "the general link was switched off, expired or reached its limit",
    "join_busy": "too many requests came through the general link in the last hour",
    "cancelled": "the person cancelled at LINE",
    "expired": "the sign-in took longer than ten minutes, or was finished already",
    "other_browser": "the sign-in came back to another browser than the one that started it",
    "failed": "LINE's answer could not be used; the server's journal says why",
}


# What a mail of each kind is, for the line a failed send writes to the journal.
MAIL_KINDS = {"code": "a sign-in code", "notify": "a note to the translator",
              "approved": "the note of an approved request", "test": "a test mail"}


class SignInFailed(Exception):
    """LINE's answer could not be used: a plain sentence for the journal and the admin routes."""


# ---------- settings ----------

class Settings:
    """The sign-in settings of config.json: auth, mail, notify and invite, checked when the server starts."""

    def __init__(self):
        self.line = None                # LINE Login: channel_id, channel_secret and the endpoints; None when off
        self.email = False              # the email code
        self.mail = None                # the mailer's settings (server/mail.py)
        self.notify = dict(NOTIFY_DEFAULTS)
        self.invite = dict(INVITE_DEFAULTS)
        self.session_days = AUTH_DEFAULTS["session_days"]
        self.require_identity = AUTH_DEFAULTS["require_identity"]

    @property
    def routes(self):
        return {"line": self.line is not None, "email": bool(self.email and self.mail)}

    @property
    def any_route(self):
        return any(self.routes.values())


def _bool(where, block, key, value):
    if not isinstance(value, bool):
        raise ValueError(f'{where}: "{block}.{key}" must be true or false, not {value!r}.')
    return value


def _days(where, key, value, most):
    if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= most:
        raise ValueError(f'{where}: "{key}" must be a whole number from 1 to {most}, not {value!r}.')
    return value


def _block(where, cfg, name, keys):
    block = cfg.get(name)
    if block is None:
        return {}
    if not isinstance(block, dict):
        raise ValueError(f'{where}: "{name}" must be an object.')
    unknown = sorted(set(block) - set(keys))
    if unknown:
        raise ValueError(f'{where}: "{name}" has no setting named {unknown[0]}. Its settings are '
                         f"{', '.join(sorted(keys))}.")
    return block


def _url(where, key, value):
    if not isinstance(value, str) or not (value.startswith("https://") or is_local(value)) or len(value) > 300:
        raise ValueError(f'{where}: "{key}" must be an https address.')
    return value.rstrip("/") if key.endswith("issuer") else value


def load_settings(data_dir, public_url=None):
    """The sign-in settings from config.json in data_dir. Raises ValueError with a plain sentence that names
    config.json and the setting, so the server refuses to start rather than run with a wrong one."""
    cfg = db.read_config(data_dir)
    where = f"{db.CONFIG} in {data_dir}"
    out = Settings()
    auth = _block(where, cfg, "auth", ("line", "email", "require_identity", "session_days"))
    out.session_days = _days(where, "auth.session_days", auth.get("session_days", out.session_days), 400)
    out.require_identity = _bool(where, "auth", "require_identity", auth.get("require_identity", False))
    line = auth.get("line")
    if line is not None:
        if not isinstance(line, dict):
            raise ValueError(f'{where}: "auth.line" must be an object such as {{"channel_id": "1234567890", '
                             '"channel_secret": "..."}.')
        unknown = sorted(set(line) - {"channel_id", "channel_secret", *LINE_DEFAULTS})
        if unknown:
            raise ValueError(f'{where}: "auth.line" has no setting named {unknown[0]}. Its settings are '
                             f"channel_id, channel_secret, {', '.join(LINE_DEFAULTS)}.")
        cid = line.get("channel_id")
        cid = str(cid) if isinstance(cid, int) and not isinstance(cid, bool) else cid
        secret = line.get("channel_secret")
        if not isinstance(cid, str) or not re.fullmatch(r"\d{1,20}", cid):
            raise ValueError(f'{where}: "auth.line.channel_id" must be the Channel ID of the LINE Login channel, '
                             "a number from its Basic settings tab.")
        if not isinstance(secret, str) or not re.fullmatch(r"[A-Za-z0-9]{16,128}", secret):
            raise ValueError(f'{where}: "auth.line.channel_secret" must be the Channel secret of the LINE Login '
                             "channel, from its Basic settings tab.")
        out.line = {"channel_id": cid, "channel_secret": secret}
        for key, default in LINE_DEFAULTS.items():
            out.line[key] = _url(where, f"auth.line.{key}", line.get(key, default))
        base = public_url or cfg.get("public_url")
        if not base:
            raise ValueError(f'{where}: "auth.line" needs "public_url", since LINE sends readers back to '
                             "public_url/api/auth/line/callback.")
    email = auth.get("email", False)
    if not isinstance(email, bool):
        raise ValueError(f'{where}: "auth.email" must be true or false: true offers the six-digit code by email.')
    out.mail = load_mail(cfg.get("mail"), data_dir, where)
    if email and not out.mail:
        raise ValueError(f'{where}: "auth.email" is true, but there is no "mail" to send the codes with. Add '
                         '"mail", as {"provider": "smtp", "from": "review@forum.laoegw.com"} (README.md, '
                         '"Sign-in settings").')
    out.email = email
    if out.require_identity and not out.any_route:
        raise ValueError(f'{where}: "auth.require_identity" is true, but neither "auth.line" nor "auth.email" '
                         "is set, so no reader could sign in.")
    # The session cookie carries Secure only over https; an http address on another machine would send it
    # unencrypted, and an absent one would leave the cookie to the address of each request.
    base = public_url or cfg.get("public_url") or ""
    if out.any_route and not (isinstance(base, str) and (base.startswith("https://") or is_local(base))):
        raise ValueError(f'{where}: "public_url" must be the site\'s https address, as "https://review.laoegw.com", '
                         "while sign-in with LINE or email is on, so that the session cookie travels only "
                         f"encrypted; it is {base or 'missing'}.")
    notify = _block(where, cfg, "notify", NOTIFY_DEFAULTS)
    if notify.get("email"):
        if not address(notify["email"]):
            raise ValueError(f'{where}: "notify.email" must be the address that gets the notes, as '
                             '"translator@example.org".')
        out.notify["email"] = notify["email"].strip()
    for key in ("requests", "first_signin"):
        out.notify[key] = _bool(where, "notify", key, notify.get(key, True))
    invite = _block(where, cfg, "invite", INVITE_DEFAULTS)
    out.invite["external_browser"] = _bool(where, "invite", "external_browser", invite.get("external_browser",
                                                                                            False))
    out.invite["general_days"] = _days(where, "invite.general_days", invite.get("general_days", 90), 3650)
    out.invite["general_uses"] = _days(where, "invite.general_uses", invite.get("general_uses", 100), 100000)
    return out


# ---------- LINE Login ----------

def b64url(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def b64url_decode(text):
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def opener_for(url):
    """An opener that never follows a redirect; a stand-in on this machine is reached without any proxy."""
    handlers = [NoRedirect]
    if is_local(url):
        handlers.append(urllib.request.ProxyHandler({}))
    return urllib.request.build_opener(*handlers)


def http(method, url, form=None):
    """(status, body) of a request to LINE; SignInFailed when LINE cannot be reached."""
    data = urlencode(form).encode() if form is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={"User-Agent": "review-site/1"})
    if data is not None:
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with opener_for(url).open(req, timeout=TIMEOUT) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        with e:
            return e.code, e.read()
    except urllib.error.URLError as e:
        raise SignInFailed(f"{urlsplit(url).netloc} cannot be reached ({e.reason}).")
    except (socket.timeout, TimeoutError):
        raise SignInFailed(f"{urlsplit(url).netloc} did not answer within {TIMEOUT} seconds.")
    except OSError as e:
        raise SignInFailed(f"{urlsplit(url).netloc} cannot be reached ({e}).")


def pkce_pair():
    """(code_verifier, code_challenge): 64 characters, and their SHA-256 in base64url (S256)."""
    verifier = secrets.token_urlsafe(48)
    return verifier, b64url(hashlib.sha256(verifier.encode()).digest())


def authorize_url(line, redirect_uri, state, nonce, challenge):
    return line["authorize_url"] + "?" + urlencode({
        "response_type": "code", "client_id": line["channel_id"], "redirect_uri": redirect_uri, "state": state,
        "scope": LINE_SCOPE, "nonce": nonce, "code_challenge": challenge, "code_challenge_method": "S256"},
        quote_via=quote)


def check_claims(line, claims, nonce, now=None):
    """The claims of an ID token, checked as LINE's "Verify ID token" and OpenID Connect Core ask: iss is the
    issuer, aud the channel id, exp in the future, iat not in the future, nonce the one this sign-in sent, and
    sub a user id. Returns the claims; SignInFailed names the claim that failed."""
    now = time.time() if now is None else now
    if not isinstance(claims, dict):
        raise SignInFailed("The ID token holds no claims.")
    if claims.get("iss") != line["issuer"]:
        raise SignInFailed(f"The ID token's issuer is {claims.get('iss')!r}, not {line['issuer']}.")
    aud = claims.get("aud")
    if aud != line["channel_id"] and not (isinstance(aud, list) and line["channel_id"] in aud):
        raise SignInFailed("The ID token was made for another channel (aud).")
    exp, iat = claims.get("exp"), claims.get("iat")
    if not isinstance(exp, (int, float)) or exp < now - LEEWAY:
        raise SignInFailed("The ID token has expired (exp).")
    if not isinstance(iat, (int, float)) or iat > now + LEEWAY:
        raise SignInFailed("The ID token was made in the future (iat); check the server's clock.")
    if not isinstance(nonce, str) or not hmac.compare_digest(str(claims.get("nonce", "")), nonce):
        raise SignInFailed("The ID token's nonce is not the one this sign-in sent.")
    sub = claims.get("sub")
    if not isinstance(sub, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", sub):
        raise SignInFailed("The ID token names no user (sub).")
    return claims


def verify_id_token(line, token, nonce):
    """The claims of an ID token that LINE's token endpoint gave. A token of web login is HS256, signed with the
    channel secret, and checked here; a token signed otherwise (ES256) is sent to LINE's verify endpoint, which
    checks its signature, and its claims are then checked here as well."""
    parts = token.split(".") if isinstance(token, str) else []
    if len(parts) != 3:
        raise SignInFailed("LINE's answer holds no ID token.")
    try:
        header = json.loads(b64url_decode(parts[0]))
        claims = json.loads(b64url_decode(parts[1]))
        signature = b64url_decode(parts[2])
    except (ValueError, TypeError):
        raise SignInFailed("The ID token cannot be read.")
    alg = header.get("alg") if isinstance(header, dict) else None
    if alg == "HS256":
        want = hmac.new(line["channel_secret"].encode(), f"{parts[0]}.{parts[1]}".encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(want, signature):
            raise SignInFailed("The ID token's signature does not match the channel secret.")
    elif alg == "ES256":
        status, body = http("POST", line["verify_url"], {"id_token": token, "client_id": line["channel_id"],
                                                         "nonce": nonce})
        if status != 200:
            raise SignInFailed(f"LINE's verify endpoint refused the ID token ({status}).")
        try:
            claims = json.loads(body)
        except ValueError:
            raise SignInFailed("LINE's verify endpoint did not answer with JSON.")
    else:
        raise SignInFailed(f"The ID token is signed with {alg!r}; only HS256 and ES256 are accepted.")
    return check_claims(line, claims, nonce)


def exchange(line, redirect_uri, code, verifier, nonce):
    """The checked claims for the authorization code that LINE sent back to the callback."""
    status, body = http("POST", line["token_url"], {
        "grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri,
        "client_id": line["channel_id"], "client_secret": line["channel_secret"], "code_verifier": verifier})
    try:
        data = json.loads(body)
    except ValueError:
        data = None
    if status != 200 or not isinstance(data, dict):
        why = data.get("error_description") or data.get("error") if isinstance(data, dict) else ""
        raise SignInFailed(f"LINE's token endpoint answered {status}" + (f": {why}" if why else "."))
    return verify_id_token(line, data.get("id_token"), nonce)


def display_name(text):
    """A LINE display name as the site keeps it: one line, no invisible character, at most 80 characters."""
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize("NFC", strip_invisible(text)).translate(DIGITS)
    return " ".join(text.split())[:80]


# ---------- helpers ----------

def cookies(req):
    """The request's cookies as {name: value}; the first of two cookies of one name wins."""
    out = {}
    for part in req.header("Cookie").split(";"):
        name, sep, value = part.strip().partition("=")
        if sep and name and name not in out:
            out[name] = value.strip()
    return out


def client_key(req):
    """Who a limit counts: the address on the internet the request came from (waitress takes it from Apache's
    X-Forwarded-For, server/prod.py). An IPv6 address counts as its /64 network, whatever way it is written
    ("::" included), and an IPv4 address written inside IPv6 (::ffff:203.0.113.7) as that IPv4 address."""
    addr = (req.environ.get("REMOTE_ADDR") or "").strip()
    try:
        ip = ipaddress.ip_address(addr.split("%", 1)[0])
    except ValueError:
        return addr
    if ip.version == 6 and ip.ipv4_mapped is not None:
        return str(ip.ipv4_mapped)
    if ip.version == 6:
        return str(ipaddress.ip_network(f"{ip}/64", strict=False))
    return str(ip)


def six_digits(value):
    """The code typed on the page as six Western digits, or None."""
    if not isinstance(value, str):
        return None
    value = "".join(value.split()).translate(DIGITS)
    return value if re.fullmatch(r"\d{6}", value) else None


def provider_label(provider, display):
    return f"LINE as {display}" if provider == "line" else f"the email address {display}"


def stranger_step(name):
    """The one step that removes everything a stranger holds who signed in as the reader: a new link that
    unties every LINE account and address and signs out every browser."""
    return ("If this is not the reader you invited, give the reader a new link that removes every LINE account and "
            f"address and signs out every browser: review.py relink {shlex.quote(name)} --unbind (on the admin "
            "page, New links with \"and remove their LINE accounts and addresses\" ticked).")


class SignIn:
    """The sign-in routes and the session check. Needs self.data, self.db_path, self.lock and self.public_url."""

    def setup_auth(self):
        """Read the sign-in settings; a wrong one stops the start with ValueError, naming config.json."""
        self.auth = load_settings(self.data, self.public_url)
        self.mailer = Mailer(self.auth.mail) if self.auth.mail else None
        self.dev = False                # True on the dev server alone (server/dev.py)
        self.throttles = {}             # (limit, who) -> times in the window
        self.throttle_swept = time.monotonic()
        self.last_line = None           # the last LINE sign-in that came back: {at, ok, detail}
        self.mail_threads = []
        # The site's address as the server starts, for the cookies and the Origin check of every request. It is
        # read once: config.json is checked when the server starts, and a later edit takes effect at a restart.
        self.config_url = db.read_config(self.data).get("public_url")
        self.site_url = (self.public_url or self.config_url or "").rstrip("/")

    # ---------- addresses and cookies ----------

    def base_url(self, req=None):
        """The site's address: public_url, or the address of the request when none is set."""
        base = self.public_url or self.config_url
        if not base and req is not None:
            scheme = req.header("X-Forwarded-Proto") or req.environ.get("wsgi.url_scheme", "http")
            base = f"{scheme}://{req.header('Host') or 'localhost'}"
        return (base or "").rstrip("/")

    def origin(self, req):
        parts = urlsplit(self.site_url or self.base_url(req))
        return f"{parts.scheme}://{parts.netloc}"

    def callback_url(self, req):
        return self.base_url(req) + "/api/auth/line/callback"

    def secure(self):
        return self.site_url.startswith("https://")

    def cookie_name(self, kind):
        """The session cookie and the cookie of a sign-in under way: __Host-rv and __Host-rvflow over https,
        rv and rvflow on the dev server over http, where a browser refuses the __Host- prefix."""
        name = "rv" if kind == "session" else "rvflow"
        return "__Host-" + name if self.secure() else name

    def set_cookie(self, kind, value, max_age):
        parts = [f"{self.cookie_name(kind)}={value}", "Path=/", f"Max-Age={int(max_age)}", "HttpOnly",
                 "SameSite=Lax"]
        if self.secure():
            parts.append("Secure")
        return ("Set-Cookie", "; ".join(parts))

    def clear_cookie(self, kind):
        return self.set_cookie(kind, "", 0)

    # ---------- limits ----------

    def throttle(self, name, who, most, seconds, message, limit=None):
        """Count one event of this kind from who, allowing most in any window of seconds; 429 slow_down with
        Retry-After past that. Only the recent events are remembered."""
        self.throttle_all([(name, who, most, seconds, message, limit)])

    def throttle_wait(self, name, who, most, seconds, now):
        """Seconds until one more event of this kind from who is allowed; 0 when it is allowed now. Call with
        self.lock held."""
        if now - self.throttle_swept >= 3600:
            # A queue whose newest event is older than the longest window (a day) is forgotten.
            self.throttles = {k: q for k, q in self.throttles.items() if q and now - q[-1] < 86400}
            self.throttle_swept = now
        q = self.throttles.setdefault((name, who), deque())
        while q and now - q[0] >= seconds:
            q.popleft()
        return int(seconds - (now - q[0])) + 1 if len(q) >= most else 0

    def throttle_all(self, checks):
        """Several limits at once, [(name, who, most, seconds, message, limit)]: when one is full, 429 slow_down
        with its message, its Retry-After and, when given, {"limit": limit}, and none of them counts the event;
        otherwise each counts it."""
        now = time.monotonic()
        with self.lock:
            for name, who, most, seconds, message, limit in checks:
                wait = self.throttle_wait(name, who, most, seconds, now)
                if wait:
                    raise HTTPError(429, "slow_down", message, [("Retry-After", str(wait))],
                                    details={"limit": limit} if limit else None)
            for name, who, most, seconds, message, limit in checks:
                self.throttles[(name, who)].append(now)

    def throttle_note(self, name, who):
        """Count one event of this kind from who, without a check (as a wrong code, counted after it is typed)."""
        with self.lock:
            self.throttles.setdefault((name, who), deque()).append(time.monotonic())

    # ---------- the session check ----------

    def page_guard(self, req):
        """Refuse a request that did not come from the site's own page: 403 bad_page. The page sends
        X-Review-Page: 1 with every request; another site cannot send that header without a preflight, which
        the server never answers, and a browser that names another site in Origin or Sec-Fetch-Site is
        refused too."""
        site = req.header("Sec-Fetch-Site")
        origin = req.header("Origin")
        if req.header(PAGE_HEADER) != "1" or site not in ("", "same-origin", "none") \
                or (origin and origin != "null" and origin != self.origin(req)):
            raise HTTPError(403, "bad_page", "This request did not come from the site's own page. Reload the page.")

    def session_of(self, req):
        """The session of the request's cookie, with its reader's active flag, or None. A cookie of a session that
        ended or expired sets req.dead_session, so the answer can clear it."""
        token = cookies(req).get(self.cookie_name("session"))
        if not token:
            return None
        row = None
        if COOKIE_RE.fullmatch(token):
            row = req.conn.execute("SELECT s.*, r.active, r.name FROM session s JOIN reader r ON r.id = s.account"
                                   " WHERE s.token_hash = ?", (db.sha256(token),)).fetchone()
        if row is None or row["ended"] or row["expires"] <= db.now():
            req.dead_session = True
            return None
        req.session_token = token
        return row

    def touch(self, req, s):
        """Record the visit at most every SEEN_EVERY minutes; each record starts the session's days again and
        sends the cookie again with its full age, so a reader who visits stays signed in."""
        if s["last_seen"] >= db.ago(minutes=SEEN_EVERY):
            return
        stamp = db.now()
        with db.tx(req.conn):
            req.conn.execute("UPDATE session SET last_seen = ?, expires = ? WHERE id = ? AND ended IS NULL",
                             (stamp, db.later(stamp, self.auth.session_days), s["id"]))
        req.headers_out.append(self.set_cookie("session", req.session_token, self.auth.session_days * 86400))

    def reader_auth(self, req, session_only=False):
        """The reader of the request: by the session cookie, or by the link's code on a device where the link
        works; otherwise one of ACCESS_ERRORS (server/app.py). session_only refuses the link's code."""
        s = self.session_of(req)
        if s is not None:
            self.page_guard(req)
            if not s["active"]:
                raise HTTPError(401, "stopped", "Your access to the site is stopped. Ask the translator.")
            self.touch(req, s)
            req.reader = req.conn.execute("SELECT * FROM reader WHERE id = ?", (s["account"],)).fetchone()
            req.session = s
            return
        dead = [self.clear_cookie("session")] if getattr(req, "dead_session", False) else []
        m = None if session_only else TOKEN_RE.fullmatch(req.header("Authorization").strip())
        if not m:
            if dead:
                raise HTTPError(401, "signed_out", "This browser is no longer signed in. Sign in again.", dead)
            raise HTTPError(401, "no_code", "Sign in, or open your personal link.")
        req.headers_out += dead
        row = req.conn.execute("SELECT * FROM reader WHERE code_hash = ?", (db.sha256(m.group(1)),)).fetchone()
        if row is None or not row["active"]:
            raise HTTPError(401, "bad_code", "This link does not work. Ask the translator for a new link.")
        if not self.link_alone(req.conn, row):
            if row["link_used"]:
                raise HTTPError(401, "link_used", "This link was used to sign in. Sign in with LINE or your email "
                                "to continue.")
            raise HTTPError(401, "sign_in_required", "Sign in with LINE or your email to continue.")
        self.device_check(req, row)
        req.reader = row

    def link_alone(self, conn, reader):
        """Whether the reader's link signs a browser in by itself, with the two-device lock: always for a reader
        with "Link signs in" on and while no sign-in route is switched on; otherwise only while the link is
        unused, the reader has no identity, and auth.require_identity is false."""
        if reader["link_signs_in"] or not self.auth.any_route:
            return True
        if reader["link_used"] or self.auth.require_identity:
            return False
        return conn.execute("SELECT 1 FROM identity WHERE account = ? LIMIT 1", (reader["id"],)).fetchone() is None

    # ---------- what the page asks before it signs in ----------

    def account_json(self, conn, session):
        if session is None:
            return None
        return {"id": session["account"], "name": session["name"]}

    def auth_state(self, req):
        """GET /api/auth/state: whether this browser is signed in, as whom and how, and which routes are on."""
        s = self.session_of(req)
        headers = [self.clear_cookie("session")] if getattr(req, "dead_session", False) else []
        if s is not None and not s["active"]:
            s = None
        identities = []
        if s is not None:
            identities = [{"provider": r[0], "display": r[1]} for r in req.conn.execute(
                "SELECT provider, display FROM identity WHERE account = ? ORDER BY id", (s["account"],))]
        return 200, {"signed_in": s is not None, "account": self.account_json(req.conn, s),
                     "via": s["via"] if s else None, "identities": identities, "routes": self.auth.routes,
                     "require_identity": self.auth.require_identity, "session_days": self.auth.session_days,
                     "dev": self.dev}, headers

    def link_reader(self, req, code):
        """The reader of a personal link's code; 401 bad_code for an unknown code or a stopped reader."""
        if not isinstance(code, str) or not re.fullmatch(r"[A-Za-z0-9_-]{16,128}", code):
            raise HTTPError(400, "bad_field", "link must be the code after #k= in the link.")
        row = req.conn.execute("SELECT * FROM reader WHERE code_hash = ?", (db.sha256(code),)).fetchone()
        if row is None or not row["active"]:
            raise HTTPError(401, "bad_code", "This link does not work. Ask the translator for a new link.")
        return row

    def auth_claim(self, req):
        """POST /api/auth/claim {link}: what the page shows for a personal link. state is "link" (the link signs
        in by itself, as before accounts), "welcome" (sign in with LINE or email to tie the link to you; skip
        is true when the link alone also works for now) or "used" (the link was used; sign in instead)."""
        self.throttle("lookup", client_key(req), LOOKUPS_PER_MINUTE, 60, "Too many tries in one minute. Wait "
                      "and try again.")
        reader = self.link_reader(req, req.json().get("link"))
        s = self.session_of(req)
        if reader["link_signs_in"] or not self.auth.any_route:
            state = "link"
        elif reader["link_used"]:
            state = "used"
        else:
            state = "welcome"
        return 200, {"id": reader["id"], "name": reader["name"], "state": state,
                     "skip": state == "welcome" and self.link_alone(req.conn, reader),
                     "routes": self.auth.routes,
                     "signed_in": self.account_json(req.conn, s) if s is not None and s["active"] else None}

    def general_link(self, conn, code):
        """The general link of a code, and its state: open, off, expired or full; (None, "closed") when unknown."""
        if not isinstance(code, str) or not re.fullmatch(r"[A-Za-z0-9_-]{16,128}", code):
            return None, "closed"
        row = conn.execute("SELECT * FROM general_link WHERE code_hash = ?", (db.sha256(code),)).fetchone()
        return (row, general_state(row)) if row else (None, "closed")

    def auth_join(self, req):
        """POST /api/auth/join {join}: whether a general link still takes requests: state open or closed."""
        self.throttle("lookup", client_key(req), LOOKUPS_PER_MINUTE, 60, "Too many tries in one minute. Wait "
                      "and try again.")
        _, state = self.general_link(req.conn, req.json().get("join"))
        s = self.session_of(req)
        return 200, {"state": "open" if state == "open" else "closed", "routes": self.auth.routes,
                     "signed_in": self.account_json(req.conn, s) if s is not None and s["active"] else None}

    # ---------- starting a sign-in ----------

    def flow_purpose(self, req, data):
        """(purpose, account, link hash, general link) of a sign-in about to start: claim through a personal
        link, join through a general link, add an identity to the account signed in now, or sign in."""
        given = [k for k in ("link", "join", "add") if data.get(k)]
        if len(given) > 1:
            raise HTTPError(400, "bad_field", "Give link, join or add, not more than one.")
        if data.get("link"):
            reader = self.link_reader(req, data["link"])
            # "Link signs in" keeps the personal link and the two-device lock for this reader alone: the link
            # ties no LINE account or address, which would sign in past the lock. The page never offers it.
            if reader["link_signs_in"]:
                raise HTTPError(409, "link_signs_in", "This link signs in by itself. Open it without signing in.")
            if reader["link_used"]:
                raise HTTPError(409, "link_used", "This link was used to sign in. Sign in with LINE or your email "
                                "to continue.")
            return "claim", reader["id"], reader["code_hash"], None
        if data.get("join"):
            row, state = self.general_link(req.conn, data["join"])
            if state != "open":
                raise HTTPError(410, "join_closed", "This link no longer takes requests. Ask the translator.")
            return "join", None, None, row["id"]
        if data.get("add"):
            if data["add"] is not True:
                raise HTTPError(400, "bad_field", "add must be true.")
            s = self.session_of(req)
            if s is None or not s["active"]:
                raise HTTPError(401, "signed_out", "Sign in first, then add another way to sign in.")
            return "add", s["account"], None, None
        return "signin", None, None, None

    def new_flow(self, req, kind, purpose, account, link, general, **fields):
        """A sign-in under way, kept for ten minutes and tied to this browser by the cookie rvflow, whose value
        the database keeps only as its SHA-256. Returns (flow id, the cookie's value, the Set-Cookie header)."""
        token = secrets.token_urlsafe(32)
        stamp = db.now()
        with db.tx(req.conn):
            req.conn.execute("DELETE FROM auth_flow WHERE created < ?", (db.ago(minutes=120),))
            cur = req.conn.execute(
                "INSERT INTO auth_flow (token_hash, kind, purpose, account, link, general_link, state, nonce,"
                " verifier, email, code_hash, sent, created, expires) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (db.sha256(token), kind, purpose, account, link, general, fields.get("state"), fields.get("nonce"),
                 fields.get("verifier"), fields.get("email"), None, 0, stamp,
                 db.later(stamp, minutes=FLOW_MINUTES)))
        return cur.lastrowid, token, self.set_cookie("flow", token, FLOW_MINUTES * 60)

    def flow_of(self, req, kind):
        """The sign-in under way in this browser, by its cookie; None when there is none."""
        token = cookies(req).get(self.cookie_name("flow"))
        if not token or not COOKIE_RE.fullmatch(token):
            return None
        return req.conn.execute("SELECT * FROM auth_flow WHERE token_hash = ? AND kind = ?",
                                (db.sha256(token), kind)).fetchone()

    def route_on(self, name):
        if not self.auth.routes[name]:
            raise HTTPError(404, "route_off", f"Sign-in with {'LINE' if name == 'line' else 'email'} is not "
                            "switched on.")

    def line_start(self, req):
        """POST /api/auth/line/start {link?, join?, add?}: the address of LINE's sign-in page for this browser,
        {url}, which the page opens. The link's code goes in the body, never in an address."""
        self.route_on("line")
        data = req.json()
        self.throttle("start", client_key(req), STARTS_PER_MINUTE, 60, "Too many sign-ins started in one minute. "
                      "Wait and try again.")
        purpose, account, link, general = self.flow_purpose(req, data)
        verifier, challenge = pkce_pair()
        state, nonce = secrets.token_urlsafe(24), secrets.token_urlsafe(24)
        _, _, cookie = self.new_flow(req, "line", purpose, account, link, general, state=state, nonce=nonce,
                                     verifier=verifier)
        return 200, {"url": authorize_url(self.auth.line, self.callback_url(req), state, nonce, challenge)}, [cookie]

    def line_callback(self, req):
        """GET /api/auth/line/callback: LINE sends the browser back here. The server checks the state against
        this browser's sign-in, trades the code for an ID token at LINE's token endpoint, checks the token, and
        sends the browser to /#auth=RESULT (RESULTS)."""
        out = [self.clear_cookie("flow")]

        def go(result):
            return 302, None, out + [("Location", "/#auth=" + result)]

        state = req.query.get("state") or ""
        flow = req.conn.execute("SELECT * FROM auth_flow WHERE state = ? AND kind = 'line'",
                                (state,)).fetchone() if state else None
        if flow is None or flow["used"] or flow["expires"] <= db.now() or not self.auth.line:
            return go("expired")
        token = cookies(req).get(self.cookie_name("flow")) or ""
        if not hmac.compare_digest(db.sha256(token), flow["token_hash"]):
            return go("other_browser")
        with db.tx(req.conn):
            taken = req.conn.execute("UPDATE auth_flow SET used = ? WHERE id = ? AND used IS NULL",
                                     (db.now(), flow["id"])).rowcount
        if not taken:
            return go("expired")
        if req.query.get("error"):
            return go("cancelled" if req.query["error"].lower() == "access_denied" else "failed")
        try:
            claims = exchange(self.auth.line, self.callback_url(req), req.query.get("code") or "", flow["verifier"],
                              flow["nonce"])
        except SignInFailed as e:
            self.last_line = {"at": db.now(), "ok": False, "detail": str(e)}
            print(f"review: a LINE sign-in failed: {e}", file=req.environ.get("wsgi.errors"))
            return go("failed")
        self.last_line = {"at": db.now(), "ok": True, "detail": ""}
        result, headers = self.complete(req, flow, "line", claims["sub"], display_name(claims.get("name")))
        out += headers
        return go(result)

    def email_start(self, req):
        """POST /api/auth/email/start {email, link?, join?, add?}: send a six-digit code to the address. The
        answer is the same whether or not a reader uses the address; to sign in, a code goes only to an
        address a reader uses, while through a link, a general link or to add an address it goes to any."""
        self.route_on("email")
        data = req.json()
        email = address(data.get("email"))
        if not email:
            raise HTTPError(400, "bad_email", "Write the whole email address, as name@example.com.")
        self.throttle("start", client_key(req), STARTS_PER_MINUTE, 60, "Too many sign-ins started in one minute. "
                      "Wait and try again.")
        purpose, account, link, general = self.flow_purpose(req, data)
        # The codes to one address: a share for each address on the internet, and a cap for the address alone
        # (CODES_PER_CLIENT_DAY, CODES_PER_DAY). Adding an address sends mail to any address, so a signed-in
        # reader asks for few such codes (ADD_CODES_PER_HOUR).
        checks = [("code_client", (email, client_key(req)), CODES_PER_CLIENT_DAY, 86400,
                   f"{CODES_PER_CLIENT_DAY} codes were asked for this address from here in the last 24 hours. Try "
                   "again tomorrow.", "day"),
                  ("code_address", email, CODES_PER_DAY, 86400, f"{CODES_PER_DAY} codes went to this address in the "
                   "last 24 hours. Try again tomorrow.", "day")]
        if purpose == "add":
            checks.insert(0, ("code_add", account, ADD_CODES_PER_HOUR, 3600, "Too many codes were asked for in the "
                              "last hour to add an address. Wait an hour and try again.", "hour"))
        # A link, personal or general, sends codes to any address; these caps keep a leaked link from sending mail
        # to many addresses.
        for column, value, most in (("link", link, LINK_CODES_PER_HOUR), ("general_link", general,
                                                                         JOIN_CODES_PER_HOUR)):
            if value is not None and req.conn.execute(
                    f"SELECT COUNT(*) FROM auth_flow WHERE kind = 'email' AND {column} = ? AND created >= ?",
                    (value, db.ago(minutes=60))).fetchone()[0] >= most:
                raise HTTPError(429, "slow_down", "Too many codes were asked for through this link in the last hour. "
                                "Wait and try again.", [("Retry-After", "3600")])
        self.throttle_all(checks)
        # To sign in, a code goes to an address a reader uses, or that asked to read through a general link and
        # waits or was declined, so that such a person sees the request's state from the sign-in screen.
        send = purpose != "signin" or req.conn.execute(
            "SELECT 1 FROM identity i JOIN reader r ON r.id = i.account WHERE i.provider = 'email' AND i.subject = ?"
            " AND r.active = 1 UNION ALL SELECT 1 FROM access_request WHERE provider = 'email' AND subject = ? AND"
            " (decided IS NULL OR decision = 'declined')", (email, email)).fetchone() is not None
        flow_id, token, cookie = self.new_flow(req, "email", purpose, account, link, general, email=email)
        if send:
            code = f"{secrets.randbelow(10 ** 6):06d}"
            ok, detail = self.send_mail_waiting("code", email, subject("code_subject", code=code),
                                                both("code_body", code=code, minutes=CODE_MINUTES), MAIL_WAIT)
            if not ok:
                with db.tx(req.conn):
                    req.conn.execute("DELETE FROM auth_flow WHERE id = ?", (flow_id,))
                raise HTTPError(503, "mail_failed", "The code could not be sent. Try again later.",
                                [("Retry-After", "60"), self.clear_cookie("flow")])
            with db.tx(req.conn):
                req.conn.execute("UPDATE auth_flow SET code_hash = ?, sent = 1 WHERE id = ?",
                                 (db.sha256(f"{token}:{code}"), flow_id))
        return 200, {"ok": True, "minutes": CODE_MINUTES, "tries": CODE_TRIES}, [cookie]

    def email_finish(self, req):
        """POST /api/auth/email/finish {code}: the six digits typed on the page, for the code this browser asked
        for. Three tries; then, or after ten minutes, a new code is needed. The answer is {result, name}
        (RESULTS), with the session cookie when the browser is signed in."""
        self.route_on("email")
        data = req.json()
        digits = six_digits(data.get("code"))
        if digits is None:
            raise HTTPError(400, "bad_field", "code must be the six digits of the email.")
        who = client_key(req)
        self.throttle("finish", who, FINISHES_PER_MINUTE, 60, "Too many codes typed in one minute. Wait and try "
                      "again.")
        with self.lock:
            wait = self.throttle_wait("wrong", who, WRONG_CODES_PER_HOUR, 3600, time.monotonic())
        if wait:
            raise HTTPError(429, "slow_down", "Too many wrong codes were typed from here in the last hour. Wait and "
                            "try again.", [("Retry-After", str(wait))], details={"limit": "wrong"})
        flow = self.flow_of(req, "email")
        if flow is None or flow["used"] or flow["expires"] <= db.now():
            raise HTTPError(400, "code_expired", "This code no longer works. Ask for a new code.",
                            [self.clear_cookie("flow")])
        token = cookies(req).get(self.cookie_name("flow"))
        right = flow["code_hash"] is not None and hmac.compare_digest(db.sha256(f"{token}:{digits}"),
                                                                      flow["code_hash"])
        # The try is counted in the same write that checks the three tries, so codes sent at the same moment
        # take turns and never get more than three tries between them.
        with db.tx(req.conn):
            counted = req.conn.execute("UPDATE auth_flow SET tries = tries + 1 WHERE id = ? AND tries < ? AND used"
                                       " IS NULL", (flow["id"], CODE_TRIES)).rowcount
            tries = req.conn.execute("SELECT tries, used FROM auth_flow WHERE id = ?", (flow["id"],)).fetchone()
            taken = counted and right and req.conn.execute(
                "UPDATE auth_flow SET used = ? WHERE id = ? AND used IS NULL", (db.now(), flow["id"])).rowcount
        if not counted:
            if tries is not None and tries["used"] is None and tries["tries"] >= CODE_TRIES:
                raise HTTPError(400, "code_used_up", "The code was typed wrong three times. Ask for a new code.",
                                [self.clear_cookie("flow")])
            raise HTTPError(400, "code_expired", "This code no longer works. Ask for a new code.",
                            [self.clear_cookie("flow")])
        if not right:
            self.throttle_note("wrong", who)
            left = CODE_TRIES - tries["tries"]
            if left <= 0:
                raise HTTPError(400, "code_used_up", "The code was typed wrong three times. Ask for a new code.",
                                [self.clear_cookie("flow")])
            raise HTTPError(400, "wrong_code", f"This is not the code. {left} {'try' if left == 1 else 'tries'} left.",
                            details={"tries_left": left})
        if not taken:
            raise HTTPError(400, "code_expired", "This code no longer works. Ask for a new code.",
                            [self.clear_cookie("flow")])
        result, headers = self.complete(req, flow, "email", flow["email"], flow["email"])
        s = getattr(req, "new_session", None)
        return 200, {"result": result, "name": s["name"] if s else None}, [self.clear_cookie("flow")] + headers

    # ---------- finishing a sign-in ----------

    def complete(self, req, flow, provider, subject_id, display):
        """What a sign-in through LINE or the email code ends in, for the identity (provider, subject_id):
        (result, headers). It binds the identity, opens a session, or makes an access request, as the flow's
        purpose says; the translator is told of a first sign-in and of a new request."""
        stamp = db.now()
        conn = req.conn
        first, request, result, session = None, None, None, None
        # An add finishes only while the browser that began it is still signed in to the same account, so that
        # every way of ending its session (the reader's or the translator's) also ends the add it began.
        adder = self.session_of(req) if flow["purpose"] == "add" else None
        with db.tx(conn):
            ident = conn.execute("SELECT * FROM identity WHERE provider = ? AND subject = ?",
                                 (provider, subject_id)).fetchone()
            purpose = flow["purpose"]
            if purpose == "add" and (adder is None or adder["account"] != flow["account"]):
                result = "expired"
            elif purpose in ("claim", "add"):
                reader = conn.execute("SELECT * FROM reader WHERE id = ?", (flow["account"],)).fetchone()
                if reader is None or not reader["active"]:
                    result = "stopped"
                elif purpose == "claim" and reader["code_hash"] == flow["link"] and reader["link_signs_in"]:
                    # The switch "Link signs in" came on during the sign-in: the link ties no identity.
                    result = "link_signs_in"
                elif purpose == "claim" and (reader["code_hash"] != flow["link"] or (
                        reader["link_used"] and not (ident and ident["account"] == reader["id"]))):
                    result = "link_used"
                elif ident is not None and ident["account"] != reader["id"]:
                    result = "identity_taken"
                else:
                    iid = bind(conn, reader["id"], provider, subject_id, display, stamp)
                    if purpose == "claim":
                        conn.execute("UPDATE reader SET link_used = ? WHERE id = ? AND link_used IS NULL",
                                     (stamp, reader["id"]))
                        first = self.first_signin(conn, reader, stamp)
                        session = self.open_session(req, reader, provider, iid, stamp)
                        result = "signed_in"
                    else:
                        result = "added"
            else:
                if ident is not None:
                    reader = conn.execute("SELECT * FROM reader WHERE id = ?", (ident["account"],)).fetchone()
                    if not reader["active"]:
                        result = "stopped"
                    else:
                        bind(conn, reader["id"], provider, subject_id, display, stamp)
                        first = self.first_signin(conn, reader, stamp)
                        session = self.open_session(req, reader, provider, ident["id"], stamp)
                        result = "signed_in"
                else:
                    last = conn.execute("SELECT decided, decision FROM access_request WHERE provider = ? AND subject = ?"
                                        " ORDER BY id DESC LIMIT 1", (provider, subject_id)).fetchone()
                    if last is not None and last["decided"] is None:
                        result = "request_waiting"
                    elif last is not None and last["decision"] == "declined":
                        result = "request_declined"
                    elif purpose == "signin":
                        result = "no_account"
                    else:
                        result, request = self.new_request(conn, flow, provider, subject_id, display, stamp)
        headers = []
        if session is not None:
            headers.append(self.set_cookie("session", session["token"], self.auth.session_days * 86400))
            req.new_session = session
        if first:
            self.notify("first_signin", f"{first} signed in for the first time",
                        f"{first} signed in to the proofreading site for the first time, with "
                        f"{provider_label(provider, display)}.\n\n" + stranger_step(first))
        if request:
            self.notify("requests", f"A request to read: {display}", request)
        return result, headers

    def first_signin(self, conn, reader, stamp):
        """The reader's name when this is the reader's first sign-in with LINE or email; None otherwise."""
        done = conn.execute("UPDATE reader SET first_signin = ? WHERE id = ? AND first_signin IS NULL",
                            (stamp, reader["id"])).rowcount
        return reader["name"] if done else None

    def new_request(self, conn, flow, provider, subject_id, display, stamp):
        """A request to read through a general link: (result, the note for the translator or None)."""
        link = conn.execute("SELECT g.*, t.name AS group_name FROM general_link g JOIN reader_group t"
                            " ON t.id = g.grp WHERE g.id = ?", (flow["general_link"],)).fetchone()
        if link is None or general_state(link) != "open":
            return "join_closed", None
        recent = conn.execute("SELECT COUNT(*) FROM access_request WHERE general_link = ? AND created >= ?",
                              (link["id"], db.ago(minutes=60))).fetchone()[0]
        if recent >= REQUESTS_PER_HOUR:
            return "join_busy", None
        cur = conn.execute("INSERT INTO access_request (general_link, grp, provider, subject, display, created)"
                           " VALUES (?, ?, ?, ?, ?, ?)", (link["id"], link["grp"], provider, subject_id, display, stamp))
        conn.execute("UPDATE general_link SET uses = uses + 1 WHERE id = ?", (link["id"],))
        note = (f"{display} asked to read on the proofreading site, signed in with "
                f"{provider_label(provider, display)}, through the general link of the group {link['group_name']} "
                f"(request {cur.lastrowid}).\n\nNothing opens before you approve it. Approve or decline it on the "
                "admin page, or list the requests with: review.py requests")
        return "request_sent", note

    def open_session(self, req, reader, via, identity, stamp):
        """A new session for the reader in this browser, inside the caller's transaction. A session of another
        account that this browser held ends, since its cookie is written over."""
        old = self.session_of(req)
        if old is not None:
            req.conn.execute("UPDATE session SET ended = ?, ended_by = 'signin' WHERE id = ? AND ended IS NULL",
                             (stamp, old["id"]))
        req.conn.execute("DELETE FROM session WHERE expires < ? OR ended < ?", (db.ago(90), db.ago(90)))
        token = secrets.token_urlsafe(32)
        agent = device_agent(req.header("User-Agent"))[:120]
        cur = req.conn.execute(
            "INSERT INTO session (account, token_hash, identity, via, agent, created, last_seen, expires)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (reader["id"], db.sha256(token), identity, via, agent, stamp, stamp,
                                                 db.later(stamp, self.auth.session_days)))
        return {"id": cur.lastrowid, "token": token, "name": reader["name"], "account": reader["id"]}

    # ---------- the reader's own sessions ----------

    def logout(self, req):
        """POST /api/auth/logout: this browser signs out; its session ends."""
        s = self.session_of(req)
        if s is not None:
            with db.tx(req.conn):
                req.conn.execute("UPDATE session SET ended = ?, ended_by = 'reader' WHERE id = ? AND ended IS NULL",
                                 (db.now(), s["id"]))
        return 200, {"signed_out": s is not None}, [self.clear_cookie("session")]

    def my_sessions(self, req):
        """GET /api/auth/sessions: the browsers where the reader is signed in now, this one marked current."""
        rows = req.conn.execute("SELECT * FROM session WHERE account = ? AND ended IS NULL AND expires > ?"
                                " ORDER BY last_seen DESC, id DESC", (req.reader["id"], db.now())).fetchall()
        # A browser the server cannot name goes as "", so that the page shows its own word in the reader's
        # language; the translator's lists keep UNKNOWN_AGENT.
        return 200, {"sessions": [{"id": r["id"], "agent": "" if r["agent"] == UNKNOWN_AGENT else r["agent"],
                                   "via": r["via"], "created": r["created"], "last_seen": r["last_seen"],
                                   "expires": r["expires"], "current": r["id"] == req.session["id"]} for r in rows]}

    def end_my_session(self, req, sid):
        """DELETE /api/auth/sessions/<id>: the reader signs out one of their browsers, this one too."""
        with db.tx(req.conn):
            n = req.conn.execute("UPDATE session SET ended = ?, ended_by = 'reader' WHERE id = ? AND account = ?"
                                 " AND ended IS NULL", (db.now(), int(sid), req.reader["id"])).rowcount
        if not n:
            raise HTTPError(404, "no_session", "That browser is not signed in.")
        current = int(sid) == req.session["id"]
        return 200, {"ended": int(sid), "current": current}, [self.clear_cookie("session")] if current else []

    # ---------- mail ----------

    def send_mail(self, kind, to, title, text):
        """Send one mail now: (ok, detail). Every send is recorded in mail_log, which the admin routes show, and
        a failed one also in the journal."""
        if self.mailer is None:
            return False, "No mailer is set in config.json (\"mail\")."
        try:
            self.mailer.send(to, title, text)
            ok, detail = True, ""
        except MailError as e:
            ok, detail = False, str(e)
        self.log_mail(kind, ok, detail)
        return ok, detail

    def log_mail(self, kind, ok, detail):
        """Record one send in mail_log; a failed send also writes one line to the journal."""
        if not ok:
            print(f"review: {MAIL_KINDS.get(kind, 'a mail')} could not be sent: {detail}", file=sys.stderr, flush=True)
        try:
            conn = db.connect(self.db_path)
            try:
                with db.tx(conn):
                    conn.execute("INSERT INTO mail_log (at, kind, provider, ok, detail) VALUES (?, ?, ?, ?, ?)",
                                 (db.now(), kind, self.mailer.provider, int(ok), detail[:500]))
                    conn.execute("DELETE FROM mail_log WHERE id <= (SELECT MAX(id) FROM mail_log) - 200")
            finally:
                conn.close()
        except sqlite3.Error as e:
            print(f"review: the mail log could not be written ({e}).", file=sys.stderr)

    def send_mail_waiting(self, kind, to, title, text, wait):
        """Send one mail, waiting at most `wait` seconds: (ok, detail). A mail server that takes longer leaves the
        send to its own thread, whose end is not recorded, and the answer is a failure; so a stalled mail
        server never holds a thread of the API longer than that, and the page, which gives up at eight
        seconds, says that the code could not be sent."""
        if self.mailer is None:
            return False, "No mailer is set in config.json (\"mail\")."
        got = {}

        def run():
            try:
                self.mailer.send(to, title, text)
                got["out"] = (True, "")
            except MailError as e:
                got["out"] = (False, str(e))
            except Exception as e:      # a fault of the mailer itself; the API goes on
                got["out"] = (False, f"The mailer failed ({e}).")

        t = threading.Thread(target=run, daemon=True)
        t.start()
        t.join(wait)
        if "out" in got:
            ok, detail = got["out"]
        else:
            ok, detail = False, f"{self.mailer.where()} did not answer within {wait} second{'' if wait == 1 else 's'}."
        self.log_mail(kind, ok, detail)
        return ok, detail

    def send_later(self, kind, to, title, text):
        """Send one mail in the background, so a slow mail server never holds up a reader's answer."""
        t = threading.Thread(target=self.send_mail, args=(kind, to, title, text), daemon=True)
        with self.lock:
            self.mail_threads = [x for x in self.mail_threads if x.is_alive()] + [t]
        t.start()

    def mail_idle(self, timeout=10):
        """Wait for the mails sent in the background; the tests use it."""
        with self.lock:
            threads = list(self.mail_threads)
        for t in threads:
            t.join(timeout)

    def notify(self, switch, title, text):
        """A note to the translator (config.json "notify"): sent when an address is set, the switch of this kind
        is on and a mailer is set; otherwise the admin page and the commands alone show the news."""
        n = self.auth.notify
        if n["email"] and n[switch] and self.mailer is not None:
            self.send_later("notify", n["email"], title, text)


def bind(conn, account, provider, subject_id, display, stamp, used=True):
    """Tie an identity to an account, or record its use when it is tied already; returns its id. used is false
    when the translator ties it (approving a request), before the person signs in with it."""
    row = conn.execute("SELECT id FROM identity WHERE provider = ? AND subject = ?", (provider, subject_id)).fetchone()
    if row is not None:
        if used:
            conn.execute("UPDATE identity SET display = ?, last_used = ? WHERE id = ?",
                         (display or "", stamp, row["id"]))
        return row["id"]
    return conn.execute("INSERT INTO identity (account, provider, subject, display, created, last_used)"
                        " VALUES (?, ?, ?, ?, ?, ?)", (account, provider, subject_id, display or "", stamp,
                                                       stamp if used else None)).lastrowid


def general_state(row, now=None):
    """open, off (switched off, or replaced by a newer link of the group), expired, or full."""
    now = now or db.now()
    if not row["active"]:
        return "off"
    if row["expires"] <= now:
        return "expired"
    if row["uses"] >= row["uses_most"]:
        return "full"
    return "open"
