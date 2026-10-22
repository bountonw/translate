"""Development server: one threaded process on 127.0.0.1 serving web/ and the API.

Standard library only (wsgiref). In production Apache serves web/ and
waitress runs the API (server/prod.py); this module is never used there.
"""
import socketserver
from pathlib import Path
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

from .app import SECURITY_HEADERS

TYPES = {
    ".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8", ".json": "application/json; charset=utf-8",
    ".txt": "text/plain; charset=utf-8", ".svg": "image/svg+xml", ".png": "image/png",
    ".ico": "image/x-icon", ".webmanifest": "application/manifest+json",
    ".ttf": "font/ttf", ".otf": "font/otf", ".woff": "font/woff", ".woff2": "font/woff2",
}


class Site:
    """WSGI: /api/ goes to the API app; every other path is a file under web_dir."""

    def __init__(self, app, web_dir):
        self.app = app
        self.web = Path(web_dir).resolve()

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "") or "/"
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


class ThreadingServer(socketserver.ThreadingMixIn, WSGIServer):
    daemon_threads = True
    allow_reuse_address = True


class QuietHandler(WSGIRequestHandler):
    def log_message(self, *args):
        pass


def make(app, web_dir, port=8087, quiet=False):
    """A threaded server on 127.0.0.1:port; call serve_forever() on it."""
    return make_server("127.0.0.1", port, Site(app, web_dir), server_class=ThreadingServer,
                       handler_class=QuietHandler if quiet else WSGIRequestHandler)
