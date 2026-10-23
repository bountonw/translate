"""Pieces every route module of the API shares: the error type, the request, JSON and field checks.

server/app.py (the reader routes, chapters and export) and server/people.py
(readers and groups) both use them.
"""
import json
import re
import unicodedata
from urllib.parse import parse_qs

from . import db
from .text import DIGITS, strip_invisible

BODY_LIMIT = 64 * 1024          # every reader route; Apache refuses more before the API sees it
ADMIN_LIMIT = 4 * 1024 * 1024   # admin routes: a chapter upload, or hundreds of readers at once
NAME_LIMIT = 80
WAITING_MOST = 10               # devices that may wait for approval on one link; a further one is refused unrecorded
REPLY_LIMIT = 4000              # the translator's reply to a comment

# What a reader may write, as config.json's "limits" may set it. GET /api/me carries these numbers.
#   quote                the most characters in the quoted words of a comment
#   text                 the most characters in a comment
#   comments_per_minute  new comments in any 60 seconds
#   comments_per_day     new comments in one day, midnight to midnight Thailand time; deleting a comment does
#                        not give its place back
#   writes_per_minute    every other change in any 60 seconds: edits, deletions, places, finished marks
#   devices_per_link     the devices on which a link works without the translator's approval
# There is no limit on the comments a reader may keep: the daily limit replaced it.
LIMIT_DEFAULTS = {"quote": 4000, "text": 8000, "comments_per_minute": 10, "comments_per_day": 1000,
                  "writes_per_minute": 60, "devices_per_link": 2}
# Limits that no longer exist. A config.json that still names one starts as before; the number is not used.
RETIRED_LIMITS = {"comments"}
# A comment's quote and text must fit one request of BODY_LIMIT, which also bounds what a browser sends
# with keepalive: at most 4 bytes a character in UTF-8, and room for the other fields.
BYTES_PER_CHAR = 4
BODY_ROOM = 1024


def load_limits(data_dir, overrides=None):
    """The limits: LIMIT_DEFAULTS, then config.json's "limits", then overrides (a test's or a caller's).
    Raises ValueError, naming config.json, for an unknown name, a value that is not a whole number of at
    least 1, or a quote and text too long together for one request."""
    cfg = db.read_config(data_dir).get("limits") or {}
    where = f"{db.CONFIG} in {data_dir}"
    if not isinstance(cfg, dict):
        raise ValueError(f'{where}: "limits" must be an object such as {{"comments_per_day": 1000}}.')
    out = dict(LIMIT_DEFAULTS)
    for source in (cfg, {k: v for k, v in (overrides or {}).items() if v is not None}):
        for k, v in source.items():
            if k in RETIRED_LIMITS:
                continue
            if k not in LIMIT_DEFAULTS:
                raise ValueError(f"{where}: there is no limit named {k}. The limits are "
                                 f"{', '.join(LIMIT_DEFAULTS)}.")
            if not isinstance(v, int) or isinstance(v, bool) or v < 1:
                raise ValueError(f"{where}: the limit {k} must be a whole number of at least 1, not {v!r}.")
            out[k] = v
    most = (BODY_LIMIT - BODY_ROOM) // BYTES_PER_CHAR
    if out["quote"] + out["text"] > most:
        raise ValueError(f"{where}: quote ({out['quote']}) and text ({out['text']}) may come to at most {most} "
                         f"characters together, so that a comment fits one request of {BODY_LIMIT // 1024} KiB.")
    return out


class HTTPError(Exception):
    """An error answered as JSON {error, message} with its status code; details are added to the body."""

    def __init__(self, status, error, message, headers=None, details=None):
        super().__init__(message)
        self.status, self.error, self.message = status, error, message
        self.headers = headers or []
        self.details = details or {}


def dumps(payload):
    """A JSON answer, ending with a newline so that curl leaves the shell prompt on its own line."""
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode() + b"\n"


def clean(value, name, limit, required):
    """Reader text: newlines unified, invisible characters removed, NFC, Thai and Lao digits made Western."""
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise HTTPError(400, "bad_field", f"{name} must be text.")
    value = strip_invisible(value.replace("\r\n", "\n").replace("\r", "\n"))
    value = unicodedata.normalize("NFC", value).translate(DIGITS).strip()
    if required and not value:
        raise HTTPError(400, f"{name}_required", f"Write the {name}.")
    if len(value) > limit:
        raise HTTPError(400, f"{name}_too_long", f"The {name} is longer than {limit} characters.")
    return value


# A reader name that a spreadsheet would read as a formula (=, +, - or @ first), or that holds a line break
# or a tab, which would break the one-line lists of review.py and the links files.
FORMULA_START = ("=", "+", "-", "@")


def reader_name(name):
    """A cleaned reader name, refused when it starts like a formula or holds a line break or a tab. Every run of
    spaces, a no-break space or an ideographic space among them, becomes one plain space, so two names that
    differ only in their spaces are one name (name_key)."""
    if "\n" in name or "\t" in name or name.startswith(FORMULA_START):
        raise HTTPError(400, "bad_name", "A reader name may not hold a line break or a tab, or start with "
                        "=, +, - or @.")
    return " ".join(name.split())


def name_key(name):
    """What makes two reader names the same name: their spaces squeezed and their case folded. Names are unique
    by this key, and review.py finds a reader by it."""
    return " ".join(name.split()).casefold()


def text_field(data, name):
    value = data.get(name)
    if not isinstance(value, str) or not value:
        raise HTTPError(400, "bad_field", f"{name} is missing.")
    return value


def bool_field(data, name):
    value = data.get(name)
    if not isinstance(value, bool):
        raise HTTPError(400, "bad_field", f"{name} must be true or false.")
    return value


def id_list(value, name, most=10000):
    """A list of database ids, each a positive whole number."""
    if not isinstance(value, list) or len(value) > most \
            or not all(isinstance(i, int) and not isinstance(i, bool) and 1 <= i <= 2 ** 63 - 1 for i in value):
        raise HTTPError(400, "bad_field", f"{name} must be a list of numbers.")
    return list(dict.fromkeys(value))


def without_surrogates(value):
    """A parsed JSON body with every lone surrogate taken out of its strings."""
    if isinstance(value, str):
        return "".join(c for c in value if not 0xD800 <= ord(c) <= 0xDFFF)
    if isinstance(value, list):
        return [without_surrogates(v) for v in value]
    if isinstance(value, dict):
        return {without_surrogates(k): without_surrogates(v) for k, v in value.items()}
    return value


# The name of a browser whose User-Agent names no known system or browser, in the translator's lists; the
# reader's page gets "" in its place and shows its own word (server/auth.py, my_sessions).
UNKNOWN_AGENT = "an unknown browser"


def device_agent(ua):
    """A short description of a device from its User-Agent, so the translator can tell a reader's phone from
    their computer: "iPhone, Safari", "Android, LINE", "Windows, Chrome"."""
    ua = ua or ""
    system = next((name for key, name in (("iPhone", "iPhone"), ("iPad", "iPad"), ("Android", "Android"),
                                          ("Windows", "Windows"), ("Macintosh", "Mac"), ("CrOS", "ChromeOS"),
                                          ("Linux", "Linux")) if key in ua), "")
    browser = next((name for key, name in (("Line/", "LINE"), ("FBAN", "Facebook"), ("FBAV", "Facebook"),
                                           ("Edg/", "Edge"), ("SamsungBrowser", "Samsung Internet"),
                                           ("Firefox/", "Firefox"), ("FxiOS", "Firefox"), ("CriOS", "Chrome"),
                                           ("Chrome/", "Chrome"), ("Safari/", "Safari")) if key in ua), "")
    return ", ".join(x for x in (system, browser) if x) or UNKNOWN_AGENT


# A group name: letters, digits, dot, hyphen and underscore, so it fits a command line and a CSV cell.
GROUP_NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,39}")


class Request:
    def __init__(self, environ, conn):
        self.environ = environ
        self.conn = conn
        self.method = environ.get("REQUEST_METHOD", "GET").upper()
        self.path = environ.get("PATH_INFO", "") or "/"
        self.query = {k: v[-1] for k, v in parse_qs(environ.get("QUERY_STRING", "")).items()}
        self.reader = None
        self.session = None             # the session of a reader signed in with LINE or email (server/auth.py)
        self.limit = BODY_LIMIT
        self.headers_out = []           # headers every answer adds, such as a session cookie sent again

    def header(self, name):
        return self.environ.get("HTTP_" + name.upper().replace("-", "_"), "")

    def json_or_empty(self, limit=None):
        """The JSON body, or {} when the request has no body."""
        try:
            length = int(self.environ.get("CONTENT_LENGTH") or 0)
        except ValueError:
            length = 1
        return self.json(limit) if length else {}

    def json(self, limit=None):
        limit = limit or self.limit
        try:
            length = int(self.environ.get("CONTENT_LENGTH") or 0)
        except ValueError:
            raise HTTPError(400, "bad_request", "Bad Content-Length.")
        if length > limit:
            raise HTTPError(413, "too_large", "The request is too large.")
        raw = self.environ["wsgi.input"].read(length) if length > 0 else b""
        if len(raw) > limit:
            raise HTTPError(413, "too_large", "The request is too large.")
        try:
            data = without_surrogates(json.loads(raw.decode("utf-8")))
        except (UnicodeDecodeError, ValueError, RecursionError):
            raise HTTPError(400, "bad_json", "The request body is not JSON.")
        if not isinstance(data, dict):
            raise HTTPError(400, "bad_json", "The request body must be a JSON object.")
        return data
