"""Pieces every route module of the API shares: the error type, the request, JSON and field checks.

server/app.py (the reader routes, chapters and export) and server/people.py
(readers and groups) both use them.
"""
import json
import re
import unicodedata
from urllib.parse import parse_qs

from .text import DIGITS, strip_invisible

BODY_LIMIT = 64 * 1024          # every reader route; Apache refuses more before the API sees it
ADMIN_LIMIT = 4 * 1024 * 1024   # admin routes: a chapter upload, or hundreds of readers at once
QUOTE_LIMIT = 500
TEXT_LIMIT = 4000
NAME_LIMIT = 80


class HTTPError(Exception):
    """An error answered as JSON {error, message} with its status code; details are added to the body."""

    def __init__(self, status, error, message, headers=None, details=None):
        super().__init__(message)
        self.status, self.error, self.message = status, error, message
        self.headers = headers or []
        self.details = details or {}


def dumps(payload):
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()


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
    """A cleaned reader name, refused when it starts like a formula or holds a line break or a tab."""
    if "\n" in name or "\t" in name or name.startswith(FORMULA_START):
        raise HTTPError(400, "bad_name", "A reader name may not hold a line break or a tab, or start with "
                        "=, +, - or @.")
    return name


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
        self.limit = BODY_LIMIT

    def header(self, name):
        return self.environ.get("HTTP_" + name.upper().replace("-", "_"), "")

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
