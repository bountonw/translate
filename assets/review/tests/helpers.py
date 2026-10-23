"""Shared test helpers: a temporary data directory, in-process WSGI calls, sample chapters,
and the translation repository for the parser tests."""
import io
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from wsgiref.util import setup_testing_defaults

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from server import db  # noqa: E402
from server.app import App  # noqa: E402

SC_COUNTS = {1: 17, 2: 12, 3: 37, 4: 11, 5: 14, 6: 17, 7: 22, 8: 19}
SC_BOOK = {"id": "SC", "language": "th", "parser": "sc_typst", "stages": ["03_public", "02_edit", "01_raw"],
           "source": "th/SC/{stage}/SC{nn}_th.typ", "english": "th/SC/00_source/SC{nn}_en.md"}
# The device key every test reader sends unless a test names another (README.md, "Link signs in").
DEVICE = "test-device-0000000001"


def find_repo():
    """The translation repository: REVIEW_REPO, the repository holding this code, or ~/programming/translate."""
    candidates = [os.environ.get("REVIEW_REPO")]
    r = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if r.returncode == 0:
        candidates.append(r.stdout.strip())
    candidates.append(str(Path.home() / "programming" / "translate"))
    for c in candidates:
        if c and subprocess.run(["git", "-C", c, "cat-file", "-e", "main:th/SC/00_source/SC01_en.md"],
                                capture_output=True).returncode == 0:
            return Path(c)
    return None


REPO = find_repo()


def git_reader(repo, ref="main"):
    def read(path):
        r = subprocess.run(["git", "-C", str(repo), "show", f"{ref}:{path}"], capture_output=True, text=True)
        return r.stdout if r.returncode == 0 else None
    return read


def sample_chapter(n=1, count=3, book="SC", tag="v1"):
    """A small chapter in the upload format, with plain ASCII text."""
    paras = [{"a": f"{book} {100 + n}.{i}", "text": f"Paragraph {i} of chapter {n} ({tag}) <em>word</em>",
              "fn": [f"Note {i}"] if i == 1 else [], "en": f"<p>English {i}</p>"} for i in range(1, count + 1)]
    return {"n": n, "title": f"Title {n}", "title_en": f"English title {n}", "paragraphs": paras,
            "commit": "abc1234", "book_title_en": "Sample book", "language": "th"}


class Response:
    def __init__(self, status, headers, body):
        self.status = int(status.split()[0])
        self.headers = {k.lower(): v for k, v in headers}
        self.body = body

    @property
    def json(self):
        return json.loads(self.body)


class Site:
    """An App over a fresh temporary data directory, called in-process."""

    def __init__(self, **kw):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name) / "data"
        token_path, _ = db.setup(self.data, "https://review.example.org")
        self.token_path = token_path
        self.admin = token_path.read_text().strip()
        self.app = App(self.data, **kw)

    def close(self):
        self.tmp.cleanup()

    def call(self, method, path, body=None, token=None, headers=None, raw=None):
        environ = {}
        setup_testing_defaults(environ)
        path, _, query = path.partition("?")
        data = raw if raw is not None else (b"" if body is None else json.dumps(body).encode())
        environ.update({"REQUEST_METHOD": method, "PATH_INFO": path, "QUERY_STRING": query,
                        "CONTENT_LENGTH": str(len(data)), "wsgi.input": io.BytesIO(data),
                        "wsgi.errors": io.StringIO()})
        if token:
            environ["HTTP_AUTHORIZATION"] = "Bearer " + token
            environ["HTTP_X_REVIEW_DEVICE"] = DEVICE
        for k, v in (headers or {}).items():
            environ["HTTP_" + k.upper().replace("-", "_")] = v
        environ = {k: v for k, v in environ.items() if v is not None}
        captured = {}

        def start_response(status, hdrs, exc_info=None):
            captured["status"], captured["headers"] = status, hdrs

        body_out = b"".join(self.app(environ, start_response))
        return Response(captured["status"], captured["headers"], body_out)

    def admin_call(self, method, path, body=None, **kw):
        return self.call(method, path, body, token=self.admin, **kw)

    def publish(self, chapter, book="SC", cid=None):
        cid = cid or f"{book}{chapter['n']:02d}"
        r = self.admin_call("PUT", f"/api/admin/chapters/{book}/{cid}", chapter)
        assert r.status == 200, r.body
        return r.json

    def invite(self, name, grants, english=False):
        r = self.admin_call("POST", "/api/admin/readers", {"name": name, "grants": grants, "english": english})
        assert r.status == 201, r.body
        return r.json

    def comment(self, code, a, ch="SC01", book="SC", client_id=None, kind="flag", quote="", text="A note"):
        body = {"client_id": client_id or os.urandom(8).hex(), "book": book, "ch": ch, "a": a, "kind": kind,
                "quote": quote, "text": text}
        return self.call("POST", "/api/comments", body, token=code)
