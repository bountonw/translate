"""Tests for the dev server's static files, the chapter and grant specifications, the code layout
and the deploy files."""
import io
import re
import tempfile
import unittest
from pathlib import Path
from wsgiref.util import setup_testing_defaults

from helpers import ROOT, Site

from server import specs
from server.text import forbidden_char
from server.dev import Site as DevSite


class Static(unittest.TestCase):
    def setUp(self):
        self.api = Site()
        self.addCleanup(self.api.close)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.web = Path(tmp.name) / "web"
        (self.web / "fonts").mkdir(parents=True)
        (self.web / "index.html").write_text("<!doctype html><p>home</p>")
        (self.web / "app.js").write_text("console.log(1)")
        (self.web / "fonts" / "Sarabun-Regular.ttf").write_bytes(b"\0\1")
        (self.web / ".secret").write_text("no")
        (Path(tmp.name) / "outside.txt").write_text("no")
        self.site = DevSite(self.api.app, self.web)

    def get(self, path, method="GET"):
        environ = {}
        setup_testing_defaults(environ)
        environ.update({"REQUEST_METHOD": method, "PATH_INFO": path, "wsgi.input": io.BytesIO(b"")})
        got = {}

        def start_response(status, headers, exc_info=None):
            got["status"], got["headers"] = int(status.split()[0]), dict(headers)

        body = b"".join(self.site(environ, start_response))
        return got["status"], got["headers"], body

    def test_files_and_types(self):
        status, headers, body = self.get("/")
        self.assertEqual((status, body), (200, b"<!doctype html><p>home</p>"))
        self.assertEqual(headers["Content-Type"], "text/html; charset=utf-8")
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        self.assertEqual(headers["X-Robots-Tag"], "noindex")
        self.assertEqual(self.get("/app.js")[1]["Content-Type"], "text/javascript; charset=utf-8")
        self.assertEqual(self.get("/fonts/Sarabun-Regular.ttf")[1]["Content-Type"], "font/ttf")
        self.assertEqual(self.get("/", method="HEAD")[2], b"")

    def test_refuses_outside_hidden_and_writes(self):
        for path in ("/../outside.txt", "/fonts/../../outside.txt", "/.secret", "/missing.html", "/\0",
                     "/index.html\0.txt"):
            self.assertEqual(self.get(path)[0], 404, repr(path))
        self.assertEqual(self.get("/index.html", method="POST")[0], 405)

    def test_api_goes_to_the_app(self):
        status, headers, body = self.get("/api/health")
        self.assertEqual((status, body), (200, b'{"ok":true}'))
        self.assertEqual(headers["Cache-Control"], "no-store")


class Specs(unittest.TestCase):
    def test_numbers(self):
        self.assertEqual(specs.parse_numbers("01-03"), [1, 2, 3])
        self.assertEqual(specs.parse_numbers("1,3,5-6"), [1, 3, 5, 6])
        for bad in ("3-1", "a", "1-", ""):
            with self.assertRaises(specs.SpecError):
                specs.parse_numbers(bad)

    def test_grants(self):
        self.assertEqual(specs.parse_grant("SC"), [("SC", "*")])
        self.assertEqual(specs.parse_grant("sc03"), [("SC", "SC03")])
        self.assertEqual(specs.parse_grant("SC01-03"), [("SC", "SC01"), ("SC", "SC02"), ("SC", "SC03")])
        self.assertEqual(specs.parse_grant("SC01-SC02,SC05"), [("SC", "SC01"), ("SC", "SC02"), ("SC", "SC05")])
        for bad in ("SC01-GC02", "SC03-01", "S C!", "01"):
            with self.assertRaises(specs.SpecError):
                specs.parse_grant(bad)

    def test_compact(self):
        self.assertEqual(specs.compact(["SC", "SC01", "SC02", "SC03", "SC05", "GC10"]), "SC, GC10, SC01-03, SC05")
        self.assertEqual(specs.compact([]), "")


class FromEnvironment(unittest.TestCase):
    def test_application_reads_review_data(self):
        from unittest import mock
        from server import app as app_module
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        environ = {}
        setup_testing_defaults(environ)
        environ.update({"PATH_INFO": "/api/health", "wsgi.input": io.BytesIO(b"")})
        got = {}
        application = app_module._FromEnvironment()
        with mock.patch.dict("os.environ", {"REVIEW_DATA": tmp.name}):
            body = b"".join(application(environ, lambda s, h, e=None: got.update(status=s)))
        self.assertEqual((got["status"], body), ("200 OK", b'{"ok":true}'))
        self.assertTrue((Path(tmp.name) / "review.sqlite3").exists())
        self.assertIsInstance(app_module.application, app_module._FromEnvironment)


class Layout(unittest.TestCase):
    def test_python_files_have_docstrings_and_no_waitress_outside_prod(self):
        for path in list((ROOT / "server").rglob("*.py")) + list((ROOT / "parsers").rglob("*.py")) + [ROOT / "review.py"]:
            text = path.read_text()
            body = text.split("\n", 1)[1] if text.startswith("#!") else text
            self.assertTrue(body.lstrip().startswith('"""'), path)
            if path.name != "prod.py":
                self.assertNotIn("import waitress", text, path)

    def test_no_thai_digits_or_invisible_characters_in_code(self):
        found = []
        for path in ROOT.rglob("*"):
            if path.suffix in (".py", ".json", ".md", ".sql", ".conf", ".service", ".timer", ".js", ".css", ".html"):
                bad = forbidden_char(path.read_text())
                if bad:
                    found.append(f"{path.relative_to(ROOT)}: U+{ord(bad):04X}")
        self.assertEqual(found, [])


class Deploy(unittest.TestCase):
    """The deploy files keep the limits, the sandbox and the safe paths the reviews asked for."""

    def read(self, name):
        return (ROOT / "deploy" / name).read_text()

    def settings(self, name):
        return {line.split("=", 1)[0] for line in self.read(name).splitlines() if re.match(r"[A-Z]\w+=", line)}

    def test_admin_token_and_staging_paths(self):
        text = self.read("DEPLOY.md")
        self.assertNotIn("claude-sandbox/review-prod/admin-token", text)
        self.assertIn("~/.config/review/admin-token", text)
        self.assertNotIn("/tmp/", text)

    def test_body_limits(self):
        site = self.read("review-site.conf")
        self.assertIn("LimitRequestBody 65536", site)
        # Apache refuses an admin request without a bearer token of the server's form before it reads the body.
        block = re.search(r'<Location "/api/admin/">(.*?)</Location>', site, re.S).group(1)
        self.assertIn("LimitRequestBody 4718592", block)
        rule = re.search(r'<If "%\{HTTP:Authorization\} !~ m#(.*)#">\s*Require all denied\s*</If>', block)
        self.assertTrue(rule, block)
        token = re.compile(rule.group(1))
        self.assertTrue(token.search("Bearer " + "a" * 43))
        for bad in ("", "Bearer short", "Basic " + "a" * 43, "Bearer " + "a" * 43 + " x"):
            self.assertFalse(token.search(bad), bad)
        self.assertIn("max_request_body_size=4718592", (ROOT / "server" / "prod.py").read_text())
        self.assertIn("font/ttf", re.search(r"AddOutputFilterByType DEFLATE.*", site).group())

    def test_connections_memory_and_logs(self):
        # Apache stops using an idle connection before waitress closes it (channel_timeout=30).
        self.assertRegex(re.search(r"^ProxyPass .*", self.read("review-site.conf"), re.M).group(), r"\bttl=20\b")
        self.assertIn("channel_timeout=30", (ROOT / "server" / "prod.py").read_text())
        self.assertIn("Environment=MALLOC_ARENA_MAX=2", self.read("review.service"))
        # waitress's queue warnings are silenced; tests never import waitress, so the text is checked.
        prod = (ROOT / "server" / "prod.py").read_text()
        self.assertIn('QUIET_LOGGERS = ("waitress.queue",)', prod)
        self.assertIn("logging.getLogger(name).setLevel(logging.ERROR)", prod)

    def test_vhost_only_includes_the_site(self):
        vhost = self.read("review-apache.conf")
        body = re.search(r"<VirtualHost \*:80>(.*)</VirtualHost>", vhost, re.S).group(1)
        lines = [l.strip() for l in body.splitlines() if l.strip() and not l.strip().startswith("#")]
        self.assertEqual([l.split()[0] for l in lines], ["ServerName", "Include", "ErrorLog", "CustomLog"])

    def test_backup_unit_is_sandboxed_like_the_service(self):
        missing = self.settings("review.service") - self.settings("review-backup.service")
        expected = {"Type", "Restart", "RestartSec", "TimeoutStopSec", "ExecStart", "Environment", "StateDirectory",
                    "StateDirectoryMode", "IPAddressDeny", "IPAddressAllow", "After", "Description", "WantedBy"}
        self.assertEqual(missing - expected, set())
        self.assertIn("PrivateNetwork=yes", self.read("review-backup.service"))


if __name__ == "__main__":
    unittest.main()
