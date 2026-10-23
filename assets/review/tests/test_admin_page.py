"""Tests for the admin page in admin/: every local route the admin contract lists is reachable from the page and
answered by review_admin.py, every option of the command line is sent by some control of the page, the page keeps
the rules of the CSP and puts data in as text only, its modules resolve, its words all come from admin/strings.json,
and review.py admin, started as the translator starts it, answers a refused or failed command as JSON.
tests/admin_browser.py drives the page itself in headless Firefox."""
import io
import json
import re
import shlex
import shutil
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
from wsgiref.util import setup_testing_defaults

from helpers import REPO, ROOT, sample_chapter

import review
import review_admin
from server import db, dev, text
from server.app import App

ADMIN = ROOT / "admin"
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
# The local routes of 41-admin-contract.md: those of 31-admin-contract.md with open and close for grant and ungrant,
# and the routes for devices, review rounds and deleting one reader's comments; and trade, which gives the page its
# key for the one-time code of the address the browser is opened at. Round 4a (61-admin-contract.md) adds the routes
# of signing in: auth (review.py signin), sessions, identities, requests and general-links to read, and signin
# (check, test-mail), link-signs-in, session, signout, identity, unbind, request and general-link to change.
CONTRACT = {
    "info": "GET", "chapters": "GET", "readers": "GET", "groups": "GET", "features": "GET", "exports": "GET",
    "source": "GET", "rounds": "GET", "devices": "GET",
    "auth": "GET", "sessions": "GET", "identities": "GET", "requests": "GET", "general-links": "GET",
    "signin": "POST", "link-signs-in": "POST", "session": "POST", "signout": "POST", "identity": "POST",
    "unbind": "POST", "request": "POST", "general-link": "POST",
    "publish": "POST", "withdraw": "POST", "align-packet": "POST",
    "invite": "POST", "open": "POST", "close": "POST", "revoke": "POST", "restore": "POST", "relink": "POST",
    "english": "POST", "feature": "POST", "group": "POST", "round": "POST", "device": "POST",
    "delete-comments": "POST",
    "export": "POST", "processed": "POST", "triage": "POST", "replies": "POST",
    "backup": "POST", "new-token": "POST", "trade": "POST",
}
# Round 3b built the server first and the admin page after it, from 41-admin-contract.md; these sets held the routes
# the page did not call yet, and the two it no longer names. The page now calls every route of the contract and
# names no retired one, so both are empty, and the tests below check every route.
NOT_YET_ON_THE_PAGE = set()
RETIRED_FROM_THE_PAGE = set()
# Every option of the command line, as the field of its local route (41-admin-contract.md section 5), which the page
# must send from some control: "Every command and every option of the command line has a control on the admin page."
OPTIONS = {
    "publish": {"book", "chapters", "ref"}, "withdraw": {"book", "chapters"},
    "align-packet": {"book", "chapter", "ref", "out"}, "source": {"book", "ref"},
    "invite": {"name", "grant", "group", "english", "link_signs_in", "csv"},
    "readers": {"name", "link", "group", "book", "inactive", "revoked", "devices", "identity"},
    "open": {"names", "spec"}, "close": {"names", "spec"}, "revoke": {"names"}, "restore": {"names"},
    "relink": {"names", "group", "confirm", "unbind"}, "english": {"names", "state"},
    "feature": {"names", "feature", "state"},
    "group": {"action", "group", "args", "grant", "english", "csv"},
    "devices": {"name", "all"}, "device": {"action", "ids"},
    "rounds": {"book"}, "round": {"book", "name"},
    "export": {"all", "round", "before_first_round", "out", "book", "ch", "reader", "unprocessed"},
    "processed": {"ids", "export", "undo"}, "triage": {"export", "ref"}, "replies": {"csv", "json"},
    "delete-comments": {"name", "from", "to", "yes", "upto"}, "backup": {"keep"}, "trade": {"code"},
    # signing in (61-admin-contract.md section 6)
    "signin": {"action", "to"}, "link-signs-in": {"names", "state"}, "sessions": {"name", "all"},
    "session": {"action", "ids"}, "signout": {"names"}, "identities": {"name"}, "identity": {"action", "name", "address"},
    "unbind": {"ids"}, "requests": {"state"},
    "request": {"action", "id", "name", "grant", "group", "english", "reader"},
    "general-links": {"group"}, "general-link": {"action", "group", "days", "uses"},
}
CALL_RE = re.compile(r'\b(get|post)\("([a-z-]+)"')
WORDS = ADMIN / "strings.json"
IMPORT_RE = re.compile(r'import\s*(?:\{([^}]*)\}|\*\s+as\s+\w+)\s*from\s*"([^"]+)"')


def scripts():
    return sorted(ADMIN.glob("*.js"))


def request(console, method, path, body=None, key=True):
    environ = {}
    setup_testing_defaults(environ)
    path, _, query = path.partition("?")
    raw = b"" if body is None else json.dumps(body).encode()
    environ.update({"REQUEST_METHOD": method, "PATH_INFO": path, "QUERY_STRING": query, "HTTP_HOST": "127.0.0.1:8088",
                    "CONTENT_LENGTH": str(len(raw)), "wsgi.input": io.BytesIO(raw)})
    if key:
        environ["HTTP_X_ADMIN_KEY"] = console.key
    got = {}
    out = b"".join(console(environ, lambda s, h, e=None: got.update(status=int(s.split()[0]), headers=dict(h))))
    return got["status"], (json.loads(out) if got["headers"]["Content-Type"].startswith("application/json") else out)


class Routes(unittest.TestCase):
    def test_the_server_answers_the_routes_of_the_contract(self):
        self.assertEqual(review_admin.routes(), CONTRACT)

    def test_every_route_exists_with_its_method(self):
        # The wrong method answers 405, which shows the route is there without running a command.
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        console = review_admin.Console(review.Client("http://127.0.0.1:9", Path(tmp.name) / "admin-token"), 8088)
        for route, method in CONTRACT.items():
            status, answer = request(console, "POST" if method == "GET" else "GET", "/local/" + route)
            self.assertEqual((status, answer["error"]), (405, "bad_method"), route)
        self.assertEqual(request(console, "GET", "/local/nothing")[0], 404)

    def test_the_page_lists_every_route_with_its_method(self):
        block = re.search(r"export const ROUTES = \{(.*?)\};", (ADMIN / "api.js").read_text(), re.S).group(1)
        listed = {k: v for k, v in re.findall(r'"?([a-z-]+)"?: "(GET|POST)"', block) if k not in RETIRED_FROM_THE_PAGE}
        self.assertEqual(listed, {k: v for k, v in CONTRACT.items() if k in listed or k not in NOT_YET_ON_THE_PAGE})

    def test_the_page_calls_every_route(self):
        called = {}
        for path in scripts():
            for method, route in CALL_RE.findall(path.read_text()):
                called.setdefault(route, set()).add(method.upper())
        for route, method in CONTRACT.items():
            if route in NOT_YET_ON_THE_PAGE and route not in called:
                continue
            self.assertIn(route, called, f"no module of admin/ calls /local/{route}")
            self.assertEqual(called[route], {method}, route)
        self.assertEqual(set(called) - set(CONTRACT) - RETIRED_FROM_THE_PAGE, set())

    def test_every_option_of_the_command_line_is_sent_by_the_page(self):
        # A route's options are the keys of the bodies and queries of the modules that call it.
        modules = {}
        for path in scripts():
            for method, route in CALL_RE.findall(path.read_text()):
                modules.setdefault(route, set()).add(path)
        for route, fields in OPTIONS.items():
            code = "\n".join(p.read_text() for p in modules.get(route, ()))
            for name in sorted(fields):
                self.assertRegex(code, r'(?:\b|")' + re.escape(name) + r'"?\s*:', f"/local/{route} never sends {name}")
        self.assertEqual(set(OPTIONS) | {"info", "chapters", "groups", "features", "exports", "new-token", "auth"},
                         set(CONTRACT))
        # Each action of review.py group is named by the Groups section, which sends it as the action.
        groups_code = (ADMIN / "groups.js").read_text()
        for action in review.GROUP_ACTIONS:
            self.assertIn(f'"{action}"', groups_code, f"no control of the Groups section sends group {action}")
        # The options of relink are checked per route above; relink --group G --unbind is one combination, which the
        # Groups section sends itself (70-verify.md item 5).
        sent = re.findall(r'post\("relink", \{([^}]*)\}', groups_code)
        self.assertTrue(sent, "the Groups section sends no relink")
        for body in sent:
            self.assertRegex(body, r"\bgroup:", body)
            self.assertRegex(body, r"\bunbind:", body)

    def test_only_api_js_talks_to_the_server(self):
        for path in scripts():
            if path.name != "api.js":
                self.assertNotIn("fetch(", path.read_text(), path.name)
                self.assertNotIn("/local/", path.read_text(), path.name)


class Page(unittest.TestCase):
    def test_index_holds_no_inline_code_and_names_files_that_exist(self):
        html = (ADMIN / "index.html").read_text()
        self.assertNotIn("<style", html)
        self.assertNotRegex(html, r"\sstyle=")
        self.assertNotRegex(html, r"\son[a-z]+=")
        for m in re.finditer(r"<script([^>]*)>(.*?)</script>", html, re.S):
            self.assertIn("src=", m.group(1))
            self.assertEqual(m.group(2).strip(), "")
        self.assertIn('<script type="module" src="admin.js"></script>', html)
        for ref in re.findall(r'(?:src|href)="([^"]+)"', html):
            if ref.startswith("#") or ref.startswith("data:"):
                continue
            self.assertNotRegex(ref, r"^[a-z]+:|^//", "nothing loads from another host")
            self.assertTrue((ADMIN / ref).is_file(), ref)
        preloaded = set(re.findall(r'<link rel="modulepreload" href="([^"]+)">', html))
        self.assertEqual(preloaded, {p.name for p in scripts()} - {"admin.js"}, "every module is fetched at once")

    def test_every_import_resolves_to_an_export(self):
        exports = {p.name: set(re.findall(r"export (?:async )?(?:function|const|let) (\w+)", p.read_text()))
                   for p in scripts()}
        for path in scripts():
            for names, target in IMPORT_RE.findall(path.read_text()):
                self.assertTrue(target.startswith("./"), target)
                name = target[2:]
                self.assertIn(name, exports, f"{path.name} imports {target}, which is not in admin/")
                for n in (x.strip() for x in names.split(",") if x.strip()):
                    self.assertIn(n, exports[name], f"{path.name} imports {n} from {name}")

    def test_data_goes_in_as_text(self):
        for path in scripts():
            code = path.read_text()
            for word in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval(", "new Function",
                         ".style.", "setAttribute(\"style\"", "http://", "https://", "localStorage"):
                self.assertNotIn(word, code, f"{path.name} uses {word}")

    def test_no_thai_digit_and_no_invisible_character(self):
        for path in [ADMIN / "index.html", ADMIN / "admin.css", WORDS, *scripts()]:
            body = path.read_text()
            self.assertIsNone(text.forbidden_char(body), path.name)

    @unittest.skipIf(shutil.which("node") is None, "node is not installed")
    def test_every_script_parses(self):
        for path in [*scripts(), ROOT / "tests" / "admin_probe.js"]:
            r = subprocess.run(["node", "--check", str(path)], capture_output=True, text=True, timeout=60)
            self.assertEqual(r.returncode, 0, f"{path.name}: {r.stderr}")


class Words(unittest.TestCase):
    """The page's words live in admin/strings.json, so that an admin page in Thai, Lao or Mien needs only that file
    filled in (README.md, "The translator's rulings")."""

    @classmethod
    def setUpClass(cls):
        cls.words = json.loads(WORDS.read_text(encoding="utf-8"))
        cls.code = {p.name: p.read_text() for p in scripts()}
        cls.html = (ADMIN / "index.html").read_text()

    def used(self):
        """The keys the page names directly: t("key"), t(a ? "key" : "key"), plural(n, "word") for word_1 and
        word_n, and data-t and data-t-label in index.html."""
        keys = set()
        for code in self.code.values():
            keys |= set(re.findall(r'\bt\(\s*"([a-z0-9_]+)"', code))
            for m in re.finditer(r'\bt\(([^()]*?\?[^()]*?)[,)]', code):
                keys |= set(re.findall(r'"([a-z0-9_]+)"', m.group(1)))
            for word in re.findall(r'\bplural\((?:[^,()]|\([^()]*\))+,\s*"([a-z0-9_]+)"\)', code):
                keys |= {word + "_1", word + "_n"}
        return keys | set(re.findall(r'data-t(?:-label)?="([a-z0-9_]+)"', self.html))

    def test_every_word_has_its_english_and_a_place_for_each_language(self):
        self.assertGreater(len(self.words), 100)
        for key, value in self.words.items():
            self.assertRegex(key, r"^[a-z][a-z0-9_]*$")
            self.assertIsInstance(value, dict, key)
            self.assertTrue(isinstance(value.get("en"), str) and value["en"].strip(), key)
            self.assertTrue(all(isinstance(v, str) for v in value.values()), key)
            for lang, v in value.items():
                if v:
                    self.assertLessEqual(set(re.findall(r"\{(\w+)\}", v)), set(re.findall(r"\{(\w+)\}", value["en"])),
                                         f"{key} {lang} names a value the English does not")

    def test_every_word_the_page_names_is_in_the_file(self):
        missing = sorted(self.used() - set(self.words))
        self.assertEqual(missing, [], "keys the page uses that admin/strings.json lacks")

    def test_every_word_in_the_file_is_used(self):
        named = set(re.findall(r'"([a-z][a-z0-9_]*)"', "\n".join(self.code.values()))) | self.used()
        plurals = {k for k in self.words if re.sub(r"_[1n]$", "", k) in named}
        self.assertEqual(sorted(set(self.words) - named - plurals), [], "keys no module names")

    def test_no_english_sentence_is_left_in_the_code(self):
        # A sentence starts with a capital letter, ends with a stop, or runs to four words; a list of CSS classes
        # does none of these.
        found = []
        for name, code in self.code.items():
            for i, line in enumerate(code.splitlines(), 1):
                if line.lstrip().startswith("//"):
                    continue
                for lit in re.findall(r'"((?:[^"\\\n]|\\.)*)"', line):
                    if " " in lit.strip() and (re.match(r"[A-Z][a-z]", lit) or re.search(r"[a-z][.?:!]$", lit)
                                               or len(lit.split()) >= 4):
                        found.append(f"{name}:{i}: {lit}")
        self.assertEqual(found, [])

    def test_the_english_speaks_to_the_reader_as_you(self):
        for key, value in self.words.items():
            self.assertNotRegex(value["en"], r"\b(I|me|my|My|we|We|us|our|Our)\b", key)

    @unittest.skipIf(shutil.which("node") is None, "node is not installed")
    def test_the_page_reads_names_as_review_py_quotes_them(self):
        # The line after group off or group close names review.py close with each name quoted by shlex.quote; the
        # page's button sends those names, so it must read them back exactly.
        names = ["Anan", "Mali Boon", "O'Brien", "Somchai  Jaidee", "a\"b", "ทดสอบ ผู้อ่าน"]
        line = " ".join(shlex.quote(n) for n in names) + " SC01"
        script = (f"import {{ shellWords }} from {json.dumps((ADMIN / 'ui.js').as_uri())};\n"
                  f"console.log(JSON.stringify(shellWords({json.dumps(line)})));")
        r = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), names + ["SC01"])


    @unittest.skipIf(shutil.which("node") is None, "node is not installed")
    def test_the_menu_marks_site_while_the_last_mail_failed(self):
        # 67-operations.md OPS4-10: a mail outage shows from every section, not only in Site.
        self.assertIn('<span id="mailbad" class="badge" hidden></span>', (ADMIN / "index.html").read_text())
        self.assertIn("loadAuth();", (ADMIN / "admin.js").read_text())
        self.assertIn("showMail(last);", (ADMIN / "site.js").read_text())
        script = ("const el = { textContent: '', hidden: true };\n"
                  "globalThis.document = { getElementById: id => (id === 'mailbad' ? el : null) };\n"
                  f"const words = await import({json.dumps((ADMIN / 'words.js').as_uri())});\n"
                  f"words.setWords({WORDS.read_text(encoding='utf-8')});\n"
                  f"const shared = await import({json.dumps((ADMIN / 'shared.js').as_uri())});\n"
                  "const seen = [];\n"
                  "for (const last of [{ ok: false, detail: 'x' }, { ok: true }, null, { ok: false }]) {\n"
                  "  shared.showMail(last); seen.push([el.hidden, el.textContent]);\n"
                  "}\n"
                  "console.log(JSON.stringify(seen));")
        r = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), [[False, "mail fails"], [True, ""], [True, ""], [False, "mail fails"]])


class NextSteps(unittest.TestCase):
    """The buttons the page offers for the commands that a command's lines name, read from lines review.py makes."""

    class Client:
        """Answers the three reads of review.still_open."""

        def __init__(self, readers):
            self.readers = readers

        def call(self, method, path, body=None, query=None):
            if path == "/api/admin/chapters":
                return {"chapters": [{"book": "SC", "id": f"SC{n:02d}", "published": True} for n in range(1, 9)]}
            if path == "/api/admin/groups":
                return {"groups": [{"id": 1, "name": "Pastors", "active": False, "grants": ["SC01", "SC03"]}]}
            return {"readers": self.readers}

    def steps(self, lines, members=None):
        script = (f"import {{ nextSteps }} from {json.dumps((ADMIN / 'ui.js').as_uri())};\n"
                  f"import {{ setWords }} from {json.dumps((ADMIN / 'words.js').as_uri())};\n"
                  f"setWords({WORDS.read_text(encoding='utf-8')});\n"
                  f"console.log(JSON.stringify(nextSteps({json.dumps(lines)}, {json.dumps(members)}).map(s => [s.label, s.names || null, s.spec || null, s.go || null])));")
        r = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def group(self, readers):
        return {"id": 1, "name": "Pastors", "members": [{"id": r["id"], "active": True} for r in readers]}

    @unittest.skipIf(shutil.which("node") is None, "node is not installed")
    def test_the_close_that_a_group_off_names_closes_for_the_readers_named(self):
        readers = [{"id": 1, "name": "Mali Boon", "grants": ["SC01", "SC03"], "groups": ["Pastors"]},
                   {"id": 2, "name": "O'Brien", "grants": ["SC"], "groups": ["Pastors"]}]
        lines = review.still_open(self.Client(readers), self.group(readers), {("SC", "SC01"), ("SC", "SC03")}, False)
        self.assertIn("review.py close 'Mali Boon' 'O'\"'\"'Brien' SC01,SC03", lines[0])
        self.assertEqual(self.steps(lines), [["Close SC01,SC03 for these 2 readers", ["Mali Boon", "O'Brien"], "SC01,SC03", None]])

    @unittest.skipIf(shutil.which("node") is None, "node is not installed")
    def test_with_more_than_twenty_readers_the_page_takes_the_members(self):
        readers = [{"id": i, "name": f"Reader {i:02d}", "grants": ["SC02"], "groups": ["Pastors"]} for i in range(1, 26)]
        lines = review.still_open(self.Client(readers), self.group(readers), {("SC", "SC02")}, False)
        self.assertIn("review.py close NAME [NAME ...] SC02, with their names", lines[0])
        self.assertEqual(self.steps(lines), [["Close SC02 for the members of Pastors who hold it as their own", None, "SC02", None]])
        # After group remove the group has no members to read, so the page uses those it read before the change.
        gone = [x["name"] for x in readers]
        self.assertEqual(self.steps(lines, gone), [["Close SC02 for the members of Pastors who hold it as their own", gone, "SC02", None]])

    @unittest.skipIf(shutil.which("node") is None, "node is not installed")
    def test_the_group_commands_and_the_lists_the_lines_name(self):
        lines = ["Anan opens SC09 only through the group Pastors. To close it for the whole group: review.py group close Pastors SC09",
                 "The group Pastors is now off: its chapters and settings no longer reach its 2 members, until: review.py group on Pastors",
                 "SC09 is no longer among the own chapters of Anan; a group still opens it to Anan (review.py groups).",
                 "The group Youth is created and on; it has no members yet (review.py group add Youth NAME)."]
        self.assertEqual(self.steps(lines), [["Close SC09 for the whole group Pastors", None, None, None],
                                             ["Switch the group Pastors on", None, None, None],
                                             ["Show the groups", None, None, "#groups"]])

    @unittest.skipIf(shutil.which("node") is None, "node is not installed")
    def test_the_commands_the_lines_of_signing_in_name(self):
        # 61-admin-contract.md: a reader with no way left to sign in needs a new link; a declined request is forgotten;
        # the requests and general links are in the Requests section. A relink in the middle of a line offers nothing.
        used = review.describe({"name": "Mali Boon", "active": True, "grants": [], "groups": [], "settings": {},
                                "english": False, "comments": 0, "last_active": None, "identities": [],
                                "link_used": "2026-10-23T02:21:18Z"})
        full = review.describe({"name": "Anan", "active": True, "grants": [], "groups": [], "settings": {},
                                "english": False, "comments": 0, "last_active": None, "identities": [],
                                "devices": {"total": 12, "waiting": 10, "full": True}},
                               auth={"routes": {"line": True, "email": False}, "require_identity": False})
        self.assertIn("review.py relink Anan; has not signed in with LINE yet", full)
        lines = [used, full,
                 "Request 4 of kanya@example.org is declined; that address cannot ask again until: review.py request forget 4",
                 "The general link of Pastors no longer takes requests; a new one is made with: review.py general-link "
                 "Pastors --new",
                 "2 requests waiting for you; 1 browser signed in. List them with: review.py requests"]
        self.assertEqual(self.steps(lines), [["Give Mali Boon a new link", ["Mali Boon"], None, None],
                                             ["Forget request 4", [], None, None],
                                             ["Show the requests and general links", None, None, "#requests"]])


class Source(unittest.TestCase):
    """GET /local/source: the commit publish will read, and every chapter of the book in the repository."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        data = root / "data"
        db.setup(data, "https://review.example.org")
        cls.httpd = dev.make(App(data), root, 0, quiet=True)
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()
        client = review.Client(f"http://127.0.0.1:{cls.httpd.server_address[1]}", data / "admin-token")
        client.call("PUT", "/api/admin/chapters/SC/SC01", sample_chapter(1))
        cls.console = review_admin.Console(client, 8088, REPO, root)

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.tmp.cleanup()

    def test_the_chapter_list_gives_the_commit_each_chapter_came_from(self):
        status, answer = request(self.console, "GET", "/local/chapters")
        self.assertEqual(answer["result"]["chapters"][0]["commit"], "abc1234")

    @unittest.skipIf(REPO is None, "the translation repository is not found; set REVIEW_REPO")
    def test_source_names_the_commit_and_the_chapters_of_main(self):
        status, answer = request(self.console, "GET", "/local/source?book=sc")
        self.assertEqual(status, 200)
        self.assertTrue(answer["ok"], answer)
        book = answer["result"]["books"][0]
        tip = subprocess.run(["git", "-C", str(REPO), "log", "-1", "--format=%h", "main"], capture_output=True,
                             text=True).stdout.strip()
        self.assertEqual((book["book"], book["ref"], book["commit"]), ("SC", "main", tip))
        self.assertEqual(answer["lines"], [book["line"]])
        self.assertTrue(book["line"].startswith(f"Reading main at {tip}, {book['date']}, "))
        ids = [c["id"] for c in book["chapters"]]
        self.assertEqual(ids[:8], [f"SC{n:02d}" for n in range(1, 9)])
        first = book["chapters"][0]
        last = subprocess.run(["git", "-C", str(REPO), "log", "-1", "--format=%h", "main", "--", first["source"],
                               first["english"]], capture_output=True, text=True).stdout.strip()
        self.assertEqual(first["commit"], last, "the commit publish would record")
        self.assertTrue(first["english_found"])

    @unittest.skipIf(REPO is None, "the translation repository is not found; set REVIEW_REPO")
    def test_source_refuses_a_ref_that_is_not_there(self):
        answer = request(self.console, "GET", "/local/source?ref=no-such-branch")[1]
        self.assertFalse(answer["ok"])
        self.assertIn("has no no-such-branch", answer["error"])
        self.assertEqual(request(self.console, "GET", "/local/source?ref=-x")[0], 400)
        self.assertIn("Unknown book XX", request(self.console, "GET", "/local/source?book=XX")[1]["error"])

    def test_source_without_a_repository_says_how_to_start(self):
        console = review_admin.Console(self.console.client, 8088, None)
        answer = request(console, "GET", "/local/source")[1]
        self.assertFalse(answer["ok"])
        self.assertIn("--repo", answer["error"])


class Served(unittest.TestCase):
    """review.py admin as the translator starts it, in front of a dev server."""

    def test_a_refusal_and_a_fault_come_back_as_json(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        data = root / "data"
        db.setup(data, "https://review.example.org")
        httpd = dev.make(App(data), root, 0, quiet=True)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        self.addCleanup(httpd.server_close)
        self.addCleanup(httpd.shutdown)
        with socket.socket() as s:
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
        key = line.strip().rsplit("#key=", 1)[1]

        def post(route, body):
            req = urllib.request.Request(f"http://127.0.0.1:{port}/local/{route}", data=json.dumps(body).encode(),
                                         method="POST", headers={"X-Admin-Key": key, "Content-Type": "application/json"})
            with OPENER.open(req, timeout=20) as r:
                return r.status, json.loads(r.read())

        # A refusal of the site is ok false with the command's message, never a 500.
        status, answer = post("open", {"names": ["Nobody Here"], "spec": "SC01"})
        self.assertEqual(status, 200)
        self.assertFalse(answer["ok"])
        self.assertIn("No reader named Nobody Here", answer["error"])
        # A fault, here an export into a path under a file, is ok false with one plain line.
        blocker = root / "a-file"
        blocker.write_text("x")
        status, answer = post("export", {"out": str(blocker / "x.json")})
        self.assertEqual(status, 200)
        self.assertFalse(answer["ok"])
        self.assertTrue(answer["error"].startswith("The command stopped on a fault: "), answer["error"])
        with OPENER.open(f"http://127.0.0.1:{port}/", timeout=10) as r:
            self.assertIn(b'<script type="module" src="admin.js"></script>', r.read())
        with OPENER.open(f"http://127.0.0.1:{port}/admin.js", timeout=10) as r:
            self.assertEqual(r.headers["Content-Type"], "text/javascript; charset=utf-8")
            self.assertIn("default-src 'self'", r.headers["Content-Security-Policy"])


if __name__ == "__main__":
    unittest.main()
