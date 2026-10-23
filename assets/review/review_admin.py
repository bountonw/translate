"""review.py admin: the translator's admin page, served on this computer only.

`python3 review.py admin` starts a small web server on 127.0.0.1 (port 8088 by
default). It serves the page in admin/ and local JSON routes under /local/
that run the same functions as review.py's commands, against the server named
for the admin token: the dev server, or the live site through the SSH tunnel
that review.py opens at the start and keeps open while the page runs.

The page never holds the admin token: this server adds it to each request it
sends on. Every local route needs the key made at the start, which the page
reads from the address review.py prints (http://127.0.0.1:8088/#key=...) and
sends back in the header X-Admin-Key. The browser is opened at an address with
a one-time code instead (#once=...), which the page trades for the key at its
first load, so the browser's command line never holds the key. A request whose
Host is not this server's own, or whose Origin is another site's, is refused.

Every command route answers {"ok", "lines", "error", "result"}: lines are what
the command prints, error its message when it stops, and result the data the
admin page needs, such as a new reader's link or the path of a links file.
"""
import contextlib
import hashlib
import hmac
import io
import json
import re
import secrets
import shutil
import sys
import tempfile
import threading
import time
import traceback
import urllib.parse
import webbrowser
from datetime import datetime, timezone
from http import HTTPStatus
from pathlib import Path
from wsgiref.simple_server import make_server

import parsers
import review
from server import db, dev, specs
from server.app import SECURITY_HEADERS

ADMIN_DIR = review.HERE / "admin"
KEY_HEADER = "X-Admin-Key"
BODY_MOST = 32 * 1024 * 1024        # an uploaded CSV or replies file
UPLOAD_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,80}")


class Refused(Exception):
    """A local request refused before any command runs: (status, error code, message)."""

    def __init__(self, status, error, message):
        super().__init__(message)
        self.status, self.error, self.message = status, error, message


# ---------- the fields of a request ----------

def text(body, key, required=False):
    value = body.get(key)
    if value is None or value == "":
        if required:
            raise Refused(400, "bad_field", f"{key} is required.")
        return None
    if not isinstance(value, str) or "\0" in value:
        raise Refused(400, "bad_field", f"{key} must be text.")
    if value.startswith("-"):
        raise Refused(400, "bad_field", f"{key} may not start with -, which the command line reads as an option.")
    return value


def texts(body, key):
    """A list of strings, or one string split at spaces and commas."""
    value = body.get(key)
    if value is None or value == "":
        return []
    if isinstance(value, str):
        value = [x for x in re.split(r"[\s,]+", value) if x]
    if not isinstance(value, list) or not all(isinstance(x, str) and x and "\0" not in x for x in value):
        raise Refused(400, "bad_field", f"{key} must be a list of text.")
    if any(x.startswith("-") for x in value):
        raise Refused(400, "bad_field", f"{key} may not hold an item that starts with -, which the command line "
                      "reads as an option.")
    return value


def flag(body, key):
    value = body.get(key, False)
    if not isinstance(value, bool):
        raise Refused(400, "bad_field", f"{key} must be true or false.")
    return value


def names_of(body):
    """The readers a command acts on: names, a list of whole names (one request for many readers), or name,
    one name. Reader names hold spaces, so a string in names is one name, never split."""
    value = body.get("names")
    if isinstance(value, str):
        value = [value]
    if value is None or value == []:
        one = text(body, "name")
        value = [one] if one else []
    if not isinstance(value, list) or not value or not all(isinstance(x, str) and x.strip() and "\0" not in x
                                                            for x in value):
        raise Refused(400, "bad_field", "Give names, a list of the readers' whole names.")
    if any(x.startswith("-") for x in value):
        raise Refused(400, "bad_field", "A name may not start with -, which the command line reads as an option.")
    return value


def state(body):
    value = text(body, "state", True)
    if value not in ("on", "off"):
        raise Refused(400, "bad_field", "state must be on or off.")
    return value


# ---------- the commands, as argument lists ----------
# Each takes the request body and returns (argv, upload): upload is (field, file suffix) when the body
# carries a file's text, which is written to a private temporary file and named with --from or as the file.

def a_publish(b):
    chapters = texts(b, "chapters")
    if not chapters:
        raise Refused(400, "bad_field", "chapters is required, as \"01-08\": only the chapters named reach readers.")
    argv = ["publish", text(b, "book", True), *chapters]
    return argv + (["--ref", text(b, "ref")] if text(b, "ref") else []), None


def a_withdraw(b):
    return ["withdraw", text(b, "book", True), *texts(b, "chapters")], None


def a_invite(b):
    if b.get("csv") is not None:
        return ["invite", "--from"], ("csv", ".csv")
    argv = ["invite", text(b, "name", True)]
    for g in texts(b, "grant"):
        argv += ["--grant", g]
    for g in texts(b, "group"):
        argv += ["--group", g]
    return argv + (["--english"] if flag(b, "english") else []) + \
        (["--link-signs-in"] if flag(b, "link_signs_in") else []), None


def a_spec(cmd):
    return lambda b: ([cmd, *names_of(b), text(b, "spec", True)], None)


def a_plain(cmd):
    return lambda b: ([cmd, *names_of(b)], None)


def a_relink(b):
    """relink NAME [NAME ...], or relink --group G (which asks for the count first: see Console.local)."""
    group = text(b, "group")
    if group and (b.get("names") or b.get("name")):
        raise Refused(400, "bad_field", "Give names, or group, not both.")
    unbind = ["--unbind"] if flag(b, "unbind") else []
    return (["relink", "--group", group, *unbind] if group else ["relink", *names_of(b), *unbind]), None


def a_english(b):
    return ["english", *names_of(b), state(b)], None


def a_feature(b):
    return ["feature", *names_of(b), text(b, "feature", True), state(b)], None


def a_round(b):
    action = text(b, "action") or "start"
    if action != "start":
        raise Refused(400, "bad_field", "action must be start.")
    return ["round", "start", text(b, "book", True), text(b, "name", True)], None


def numbers(b, what):
    """ids: a list of numbers, or text such as "12 13 20-25"."""
    ids = b.get("ids")
    ids = [str(i) for i in ids] if isinstance(ids, list) and ids and all(type(i) is int for i in ids) \
        else texts(b, "ids")
    if not ids:
        raise Refused(400, "bad_field", f"ids is required: the numbers of the {what}.")
    return ids


def a_device(b):
    action = text(b, "action", True)
    if action not in ("approve", "remove"):
        raise Refused(400, "bad_field", "action must be approve or remove.")
    return ["device", action, *numbers(b, "devices")], None


# ---------- signing in ----------

def a_signin(b):
    """signin check, or signin test-mail ADDRESS; the settings themselves are the GET route auth."""
    action = text(b, "action", True)
    if action not in ("check", "test-mail"):
        raise Refused(400, "bad_field", "action must be check or test-mail.")
    return ["signin", action, *([text(b, "to", True)] if action == "test-mail" else [])], None


def a_link_signs_in(b):
    return ["link-signs-in", *names_of(b), state(b)], None


def a_session(b):
    action = text(b, "action") or "end"
    if action != "end":
        raise Refused(400, "bad_field", "action must be end.")
    return ["session", "end", *numbers(b, "browsers")], None


def a_identity(b):
    action = text(b, "action") or "add"
    if action != "add":
        raise Refused(400, "bad_field", "action must be add.")
    return ["identity", "add", text(b, "name", True), text(b, "address", True)], None


def a_unbind(b):
    return ["unbind", *numbers(b, "LINE accounts and addresses")], None


def whole(b, key, required=False):
    """A whole number of the body, as text for the command line, or None."""
    value = b.get(key)
    if value is None or value == "":
        if required:
            raise Refused(400, "bad_field", f"{key} is required.")
        return None
    if isinstance(value, str) and value.strip().isdigit():
        value = int(value.strip())
    if type(value) is not int or value < 0:
        raise Refused(400, "bad_field", f"{key} must be a whole number.")
    return str(value)


def a_request(b):
    """request approve|decline|forget NUMBER, and for approve --name, --grant, --group, --english or --reader."""
    action = text(b, "action", True)
    if action not in ("approve", "decline", "forget"):
        raise Refused(400, "bad_field", "action must be approve, decline or forget.")
    argv = ["request", action, whole(b, "id", True)]
    for key in ("name", "reader"):
        if text(b, key):
            argv += [f"--{key}", text(b, key)]
    for g in texts(b, "grant"):
        argv += ["--grant", g]
    for g in texts(b, "group"):
        argv += ["--group", g]
    return argv + (["--english"] if flag(b, "english") else []), None


def a_general_link(b):
    """general-link G --new [--days N] [--uses N], or general-link G --off; the list is the GET route general-links."""
    action = text(b, "action", True)
    if action not in ("new", "off"):
        raise Refused(400, "bad_field", "action must be new or off.")
    argv = ["general-link", text(b, "group", True), f"--{action}"]
    for key in ("days", "uses"):
        if whole(b, key) is not None:
            argv += [f"--{key}", whole(b, key)]
    return argv, None


def a_delete_comments(b):
    argv = ["delete-comments", text(b, "name", True), "--from", text(b, "from", True), "--to", text(b, "to", True)]
    upto = b.get("upto")
    if upto is not None:
        if type(upto) is not int or upto < 1:
            raise Refused(400, "bad_field", "upto must be a comment number, the last that the count gave.")
        argv += ["--upto", str(upto)]
    return argv + (["--yes"] if flag(b, "yes") else []), None


def a_group(b):
    action = text(b, "action", True)
    if action not in review.GROUP_ACTIONS:
        raise Refused(400, "bad_field", f"action must be one of {', '.join(review.GROUP_ACTIONS)}.")
    argv = ["group", action, text(b, "group", True), *texts(b, "args")]
    for g in texts(b, "grant"):
        argv += ["--grant", g]
    if flag(b, "english"):
        argv.append("--english")
    if b.get("csv") is not None:
        return argv + ["--from"], ("csv", ".csv")
    return argv, None


def a_export(b):
    argv = ["export"]
    for key in ("book", "ch", "reader", "out", "round"):
        if text(b, key):
            argv += [f"--{key}", text(b, key)]
    return argv + (["--unprocessed"] if flag(b, "unprocessed") else []) + (["--all"] if flag(b, "all") else []) + \
        (["--before-first-round"] if flag(b, "before_first_round") else []), None


def a_processed(b):
    argv = ["processed", *texts(b, "ids")]
    if len(argv) == 1:
        raise Refused(400, "bad_field", "ids is required, as \"12 13 20-25\".")
    if text(b, "export"):
        argv += ["--export", text(b, "export")]
    return argv + (["--undo"] if flag(b, "undo") else []), None


def a_triage(b):
    argv = ["triage"]
    for key in ("export", "ref"):
        if text(b, key):
            argv += [f"--{key}", text(b, key)]
    return argv, None


def a_replies(b):
    if b.get("replies") is not None:
        if not isinstance(b["replies"], list):
            raise Refused(400, "bad_field", "replies must be a list of {id, reply, rev}.")
        return ["replies"], ("replies", ".json")
    if b.get("csv") is not None:
        return ["replies"], ("csv", ".csv")
    if b.get("json") is not None:
        return ["replies"], ("json", ".json")
    raise Refused(400, "bad_field", "Send replies (a list), or the text of a file as csv or json.")


def a_align_packet(b):
    argv = ["align-packet", text(b, "book", True), text(b, "chapter", True)]
    for key in ("ref", "out"):
        if text(b, key):
            argv += [f"--{key}", text(b, key)]
    return argv, None


COMMANDS = {
    "publish": a_publish, "withdraw": a_withdraw, "invite": a_invite,
    "open": a_spec("open"), "close": a_spec("close"), "revoke": a_plain("revoke"),
    "restore": a_plain("restore"), "relink": a_relink, "english": a_english, "feature": a_feature,
    "group": a_group, "round": a_round, "device": a_device, "delete-comments": a_delete_comments,
    "export": a_export, "processed": a_processed, "triage": a_triage, "replies": a_replies,
    "align-packet": a_align_packet, "signin": a_signin, "link-signs-in": a_link_signs_in, "session": a_session,
    "signout": a_plain("signout"), "identity": a_identity, "unbind": a_unbind, "request": a_request,
    "general-link": a_general_link,
}
# GET, each a method of Console (general-links is general_links)
READS = ("info", "chapters", "readers", "groups", "features", "exports", "source", "rounds", "devices", "auth",
         "sessions", "identities", "requests", "general-links")
DEV_ONLY = ("backup", "new-token")      # POST, on the dev server's own data
TRADE = "trade"                         # POST without the key: a one-time code of the browser's address for the key
ONCE_SECONDS = 120                      # how long a one-time code waits for the page to trade it
CHAPTERS_MOST = 200                     # chapter numbers 0 to 199 are looked for in the repository


def routes():
    """Every local route and its method. tests/test_admin_page.py checks that the admin page reaches each."""
    return {**{r: "GET" for r in READS}, **{r: "POST" for r in (*COMMANDS, *DEV_ONLY, TRADE)}}


class Console:
    """The local admin server as a WSGI application."""

    def __init__(self, client, port, repo=None, admin_dir=ADMIN_DIR):
        self.client, self.port, self.repo = client, port, repo
        self.key = secrets.token_urlsafe(32)
        self.hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
        self.origins = {f"http://{h}" for h in self.hosts}
        self.static = dev.Site(None, admin_dir)
        self.run_lock = threading.Lock()
        self.once = {}                  # one-time code -> when it stops working (time.monotonic())
        self.once_lock = threading.Lock()

    def url(self):
        """The address with the key, which review.py admin prints."""
        return f"http://127.0.0.1:{self.port}/#key={self.key}"

    def once_url(self):
        """The address the browser is opened at: a one-time code, which the page trades for the key at its first
        load (route trade). The browser's command line, which every account of the computer can read, then holds
        only a code that no longer works."""
        code = secrets.token_urlsafe(24)
        with self.once_lock:
            self.once[code] = time.monotonic() + ONCE_SECONDS
        return f"http://127.0.0.1:{self.port}/#once={code}"

    def trade(self, environ):
        """POST /local/trade {code}: the key, once, for a one-time code of once_url()."""
        if environ.get("REQUEST_METHOD", "GET").upper() != "POST":
            raise Refused(405, "bad_method", "/local/trade takes POST with a JSON body.")
        code = self.body(environ).get("code")
        with self.once_lock:
            until = self.once.pop(code, None) if isinstance(code, str) else None
        if until is None or until < time.monotonic():
            raise Refused(401, "bad_once", "This address worked once and is used up. Open the address that "
                          "review.py admin printed.")
        return 200, {"ok": True, "lines": [], "error": "", "result": {"key": self.key}}

    def dev_data(self):
        """The dev server's data directory when the token in use is that directory's own admin-token;
        otherwise None, and the commands that change the data directory itself are refused."""
        folder = self.client.token_file.parent
        if self.client.local and self.client.token_file.name == db.TOKEN_FILE and (folder / db.DB_NAME).exists():
            return folder
        return None

    # ---------- WSGI ----------

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "") or "/"
        try:
            if environ.get("HTTP_HOST", "") not in self.hosts:
                raise Refused(403, "bad_host", "This page answers only at its own address, 127.0.0.1.")
            if path.startswith("/local/"):
                status, payload = self.local(environ, path[len("/local/"):])
            else:
                return self.static.static(environ, start_response, path)
        except Refused as e:
            status, payload = e.status, {"error": e.error, "message": e.message}
        body = json.dumps(payload, ensure_ascii=False).encode()
        start_response(f"{status} {HTTPStatus(status).phrase}", SECURITY_HEADERS + [
            ("Cache-Control", "no-store"), ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(body)))])
        return [body]

    def local(self, environ, route):
        origin = environ.get("HTTP_ORIGIN")
        if origin is not None and origin not in self.origins:
            raise Refused(403, "bad_origin", "Requests come only from the admin page itself.")
        if environ.get("HTTP_SEC_FETCH_SITE", "same-origin") not in ("same-origin", "none"):
            raise Refused(403, "bad_origin", "Requests come only from the admin page itself.")
        if route == TRADE:
            return self.trade(environ)
        sent = environ.get("HTTP_" + KEY_HEADER.upper().replace("-", "_"), "")
        if not hmac.compare_digest(sent.encode(), self.key.encode()):
            raise Refused(401, "bad_key", "The page's key is missing or wrong. Open the address that "
                          "review.py admin printed.")
        method = environ.get("REQUEST_METHOD", "GET").upper()
        query = {k: v[-1] for k, v in urllib.parse.parse_qs(environ.get("QUERY_STRING", "")).items()}
        reads = {r: getattr(self, r.replace("-", "_")) for r in READS}
        writes = dict({c: None for c in COMMANDS}, **{r: getattr(self, r.replace("-", "_")) for r in DEV_ONLY})
        if route in reads:
            if method != "GET":
                raise Refused(405, "bad_method", f"/local/{route} takes GET.")
            return 200, reads[route](query)
        if route in writes:
            if method != "POST":
                raise Refused(405, "bad_method", f"/local/{route} takes POST with a JSON body.")
            body = self.body(environ)
            if writes[route]:
                return 200, writes[route](body)
            argv, upload = COMMANDS[route](body)
            if route == "relink" and text(body, "group") and body.get("confirm") is None:
                asked = self.confirm_needed(text(body, "group"))
                if asked:
                    return 200, asked
            return 200, self.run(argv, body, upload)
        raise Refused(404, "not_found", f"There is no route /local/{route}.")

    @staticmethod
    def body(environ):
        try:
            length = int(environ.get("CONTENT_LENGTH") or 0)
        except ValueError:
            raise Refused(400, "bad_json", "Bad Content-Length.")
        if length > BODY_MOST:
            raise Refused(413, "too_large", f"The request is over {BODY_MOST // (1024 * 1024)} MiB.")
        raw = environ["wsgi.input"].read(length) if length > 0 else b"{}"
        try:
            data = json.loads(raw.decode("utf-8") or "{}")
        except (UnicodeDecodeError, ValueError):
            raise Refused(400, "bad_json", "The request body is not JSON.")
        if not isinstance(data, dict):
            raise Refused(400, "bad_json", "The request body must be a JSON object.")
        return data

    # ---------- running a command ----------

    def run(self, argv, body=None, upload=None, stdin=""):
        """Run one review.py command in this process, as the command line would, with its printed lines
        captured. One command runs at a time."""
        body = body or {}
        folder = None
        if upload:
            field, suffix = upload
            content = body.get(field)
            if field == "replies":
                content = json.dumps(content, ensure_ascii=False)
            if not isinstance(content, str):
                raise Refused(400, "bad_field", f"{field} must be the text of the file.")
            name = Path(text(body, "filename") or "").name
            name = name if UPLOAD_NAME.fullmatch(name) and name.lower().endswith(suffix) else f"upload{suffix}"
            folder = Path(tempfile.mkdtemp(prefix="review-admin-"))
            path = folder / name
            path.write_text(content, encoding="utf-8")
            path.chmod(0o600)
            argv = argv + [str(path)]
        if argv[0] == "relink" and isinstance(body.get("confirm"), int):
            stdin = f"{body['confirm']}\n"
        out, err = io.StringIO(), io.StringIO()
        ok, error, result = False, "", None
        try:
            with self.run_lock, contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                old_stdin, sys.stdin = sys.stdin, io.StringIO(stdin)
                a = None
                try:
                    a = review.build_parser().parse_args(argv)
                    a.result = None
                    if self.repo and not getattr(a, "repo", None):
                        a.repo = self.repo
                    if a.cmd in review.LOCAL:
                        a.server, a.token_file = self.client.server, str(self.client.token_file)
                        a.func(a)
                    else:
                        a.func(a, self.client)
                    ok = True
                except (review.CLIError, specs.SpecError) as e:
                    error = str(e)
                except SystemExit:
                    error = "\n".join(line.split("error: ", 1)[-1] for line in err.getvalue().splitlines()
                                      if "error: " in line) or "The command could not be read."
                except Exception as e:      # a fault, not a refusal: the page gets one line, the terminal the trace
                    traceback.print_exc(file=sys.__stderr__)
                    error = (f"The command stopped on a fault: {e.__class__.__name__}: {e}. The terminal that runs "
                             "review.py admin shows where.")
                finally:
                    sys.stdin = old_stdin
                    result = getattr(a, "result", None) if a is not None else None
        finally:
            if folder:
                shutil.rmtree(folder, ignore_errors=True)
        question = [line for line in err.getvalue().splitlines() if line.startswith("This gives ")]
        if question and not ok:
            error = "\n".join([question[0].split(" Type ")[0]] + [error])
        return {"ok": ok, "lines": out.getvalue().splitlines(), "error": error, "result": result}

    def confirm_needed(self, group):
        """relink --group asks for the number of readers on the command line; the page sends it as confirm.
        Without it, the answer names the number to send, and nothing changes."""
        try:
            n = len(self.client.call("GET", "/api/admin/readers", query={"group": group})["readers"])
        except review.CLIError as e:
            return {"ok": False, "lines": [], "error": str(e), "result": None}
        if n <= 1:
            return None
        return {"ok": False, "lines": [], "result": {"confirm": n},
                "error": f"This gives {n} readers of {group} new links, and their old links stop working. Nothing "
                         f"was changed. To go on, send confirm: {n}."}

    def call(self, method, path, query=None):
        """A server call whose answer is the result; a refusal is ok false with the message."""
        try:
            return {"ok": True, "lines": [], "error": "", "result": self.client.call(method, path, query=query)}
        except review.CLIError as e:
            return {"ok": False, "lines": [], "error": str(e), "result": None}

    # ---------- reading ----------

    def info(self, query):
        books = {k: {"title_en": v.get("title_en", ""), "title": v.get("title", ""),
                     "language": v.get("language")} for k, v in review.load_books().items()}
        return {"ok": True, "lines": [], "error": "", "result": {
            "server": self.client.server, "ssh": self.client.tunnel is not None, "local": self.client.local,
            "token_file": str(self.client.token_file), "repo": str(self.repo) if self.repo else None,
            "export_dir": str(self.client.export_dir()), "dev_data": str(self.dev_data() or "") or None,
            "books": books, "group_actions": list(review.GROUP_ACTIONS)}}

    def chapters(self, query):
        return self.call("GET", "/api/admin/chapters")

    def groups(self, query):
        return self.call("GET", "/api/admin/groups")

    def features(self, query):
        return self.call("GET", "/api/admin/features")

    def readers(self, query):
        """The readers, filtered as readers --name, --link, --group, --book, --inactive and --revoked filter
        them. A link is hashed here, so its code never travels."""
        try:
            q = {"group": query.get("group", ""), "book": query.get("book", "").upper(),
                 "revoked": "1" if query.get("revoked") in ("1", "true", "yes") else "",
                 "idle": query.get("inactive", ""), "contains": query.get("name", ""),
                 "devices": "1" if query.get("devices") in ("1", "true", "yes") else "",
                 "identity": query.get("identity", ""),
                 "code_hash": hashlib.sha256(review.code_of(query["link"]).encode()).hexdigest()
                 if query.get("link") else ""}
            res = self.client.call("GET", "/api/admin/readers", query=q)
            lines = review.describe_all(self.client, res["readers"])
        except review.CLIError as e:
            return {"ok": False, "lines": [], "error": str(e), "result": None}
        return {"ok": True, "lines": lines, "error": "", "result": res}

    def rounds(self, query):
        """The review rounds, as review.py rounds [BOOK] lists them."""
        book = query.get("book", "").strip()
        if book.startswith("-"):
            raise Refused(400, "bad_field", "book may not start with -.")
        return self.run(["rounds", *([book] if book else [])])

    def devices(self, query):
        """The devices waiting for approval, or with ?name= every device of that reader (all=1: of earlier links
        too), as review.py devices lists them."""
        name = query.get("name", "").strip()
        if name.startswith("-"):
            raise Refused(400, "bad_field", "name may not start with -.")
        return self.run(["devices", *([name] if name else []),
                         *(["--all"] if query.get("all") in ("1", "true", "yes") else [])])

    # ---------- signing in ----------

    @staticmethod
    def word(query, key):
        value = query.get(key, "").strip()
        if value.startswith("-"):
            raise Refused(400, "bad_field", f"{key} may not start with -.")
        return value

    def auth(self, query):
        """The sign-in settings, the mailer, the last mails and the counts, as review.py signin shows them; the
        result is GET /api/admin/auth."""
        return self.run(["signin"])

    def sessions(self, query):
        """The browsers signed in, of every reader or with ?name= of one (all=1: those ended too), as review.py
        sessions lists them."""
        name = self.word(query, "name")
        return self.run(["sessions", *([name] if name else []),
                         *(["--all"] if query.get("all") in ("1", "true", "yes") else [])])

    def identities(self, query):
        """The LINE accounts and addresses readers sign in with, or with ?name= one reader's."""
        name = self.word(query, "name")
        return self.run(["identities", *([name] if name else [])])

    def requests(self, query):
        """The requests to read: ?state=open (the default), approved, declined or all, as review.py requests."""
        state = query.get("state") or "open"
        if state not in ("open", "approved", "declined", "all"):
            raise Refused(400, "bad_field", "state must be open, approved, declined or all.")
        return self.run(["requests", *([] if state == "open" else [f"--{state}"])])

    def general_links(self, query):
        """The general links, of every group or with ?group= of one, as review.py general-link [G] lists them."""
        group = self.word(query, "group")
        return self.run(["general-link", *([group] if group else [])])

    def exports(self, query):
        """The exports in this server's export folder, newest first, with their triage folders."""
        folder = self.client.export_dir()
        files = sorted(folder.glob("review-*.json"), reverse=True) if folder.is_dir() else []
        out = []
        for f in files:
            st = f.stat()
            triage = f.with_name(f.stem + "-triage")
            out.append({"name": f.name, "path": str(f), "size": st.st_size,
                        "modified": datetime.fromtimestamp(st.st_mtime, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "markdown": str(f.with_suffix(".md")) if f.with_suffix(".md").exists() else None,
                        "triage": sorted(str(p) for p in triage.glob("*.md")) if triage.is_dir() else []})
        return {"ok": True, "lines": [], "error": "", "result": {"folder": str(folder), "exports": out}}

    def source(self, query):
        """What publish would read, before it runs: for each book of books.json (or ?book=), the newest commit of
        its ref (or ?ref=), and the chapters whose file in the book's language (source) is there, each with the
        newest commit that changed it or its English, which is the commit publish would record for it."""
        ref = query.get("ref", "").strip()
        if ref.startswith("-") or "\0" in ref:
            raise Refused(400, "bad_field", "ref may not start with -, which git reads as an option.")
        try:
            if self.repo is None:
                raise review.CLIError("review.py admin found no translation repository. Stop it and start it "
                                      "again with --repo PATH.")
            books = review.load_books()
            if query.get("book"):
                books = {query["book"].upper(): review.book_entry(books, query["book"])}
            out = [self.book_source(b, ref or b.get("ref", "main")) for b in books.values()]
        except review.CLIError as e:
            return {"ok": False, "lines": [], "error": str(e), "result": None}
        return {"ok": True, "lines": [b["line"] for b in out], "error": "",
                "result": {"repo": str(self.repo), "books": out}}

    def book_source(self, book, ref):
        short, line = review.tip_line(self.repo, ref)
        tip = review.git(self.repo, "log", "-1", "--format=%ad%x00%s", "--date=short", ref, "--").stdout
        date, _, subject = tip.strip().partition("\0")
        files = set(review.git(self.repo, "ls-tree", "-r", "--name-only", ref).stdout.splitlines())
        try:
            paths = getattr(parsers.module("parser", book.get("parser")), "chapter_paths", None)
        except parsers.ParseError as e:
            raise review.CLIError(str(e))
        chapters = []
        for n in range(CHAPTERS_MOST if paths else 0):
            for stage in book.get("stages") or [None]:
                try:
                    th, en = paths(book, n, stage)
                except (KeyError, IndexError, ValueError):
                    break
                if th in files:
                    chapters.append({"n": n, "id": specs.chapter_id(book["id"], n), "source": th, "english": en,
                                     "english_found": en in files, "commit": None})
                    break
        if chapters:
            log = review.git(self.repo, "log", "--format=%x01%h", "--name-only", ref, "--",
                             *[p for c in chapters for p in (c["source"], c["english"])]).stdout
            first, commit = {}, None
            for i, row in enumerate(log.splitlines()):
                if row.startswith("\x01"):
                    commit = row[1:]
                elif row and row not in first:
                    first[row] = (i, commit)
            for c in chapters:
                seen = [first[p] for p in (c["source"], c["english"]) if p in first]
                c["commit"] = min(seen)[1] if seen else None
        return {"book": book["id"], "ref": ref, "commit": short, "date": date, "subject": subject, "line": line,
                "chapters": chapters}

    # ---------- the dev server's own data ----------

    def backup(self, body):
        data = self.dev_data()
        if data is None:
            return {"ok": False, "lines": [], "result": None, "error": (
                "Backups of the live site are made on the droplet each day by review-backup.timer; deploy/DEPLOY.md, "
                "\"Daily backup\", gives the command that copies the newest one home.")}
        keep = body.get("keep", 14)
        if type(keep) is not int or keep < 0:
            raise Refused(400, "bad_field", "keep must be a number of days.")
        return self.run(["backup", "--data", str(data), "--keep", str(keep)])

    def new_token(self, body):
        data = self.dev_data()
        if data is None:
            return {"ok": False, "lines": [], "result": None, "error": (
                "A new admin token for the live site is made on the droplet, as deploy/DEPLOY.md, \"What is "
                "secret\", says: sudo -u review python3 /srv/review/app/review.py setup --data /var/lib/review "
                "--new-token, then save it in ~/.config/review/admin-token as in step 5.")}
        with self.run_lock:
            path, _ = db.setup(data, new_token=True)
        return {"ok": True, "result": {"token_file": str(path)}, "error": "",
                "lines": [f"New admin token written to {path}. The old token stops working now; this page goes on "
                          "with the new one."]}


def serve(a, client):
    """review.py admin: open the tunnel when the server is the live site, check the token, then serve the
    page until Ctrl-C."""
    if client.tunnel is not None:
        print(f"Opening the SSH tunnel to {client.tunnel.dest} ...", flush=True)
        client.tunnel.open()
    client.call("GET", "/api/admin/features")
    repo = None
    try:
        repo = review.find_repo(a.repo)
    except review.CLIError:
        pass
    console = Console(client, a.port, repo)
    try:
        httpd = make_server("127.0.0.1", a.port, console, server_class=dev.ThreadingServer,
                            handler_class=dev.QuietHandler)
    except OSError:
        raise review.CLIError(f"Port {a.port} is in use. Is review.py admin already running? Stop it, or pass "
                              f"--port {a.port + 1}.")
    if not (ADMIN_DIR / "index.html").exists():
        print(f"Note: {ADMIN_DIR / 'index.html'} does not exist yet; only the /local/ routes answer.")
    print(f"Admin page for {client.server}: {console.url()}")
    print("Keep this address to yourself: while review.py admin runs, it acts with your admin token. "
          "Stop with Ctrl-C.", flush=True)
    if not a.no_open:
        # The browser gets a one-time code, never the key, since its command line is open to every account.
        webbrowser.open(console.once_url())
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
