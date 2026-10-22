"""Production entry point: run the API under waitress on 127.0.0.1.

systemd starts it as "python3 -m server.prod" from the code folder
(deploy/review.service). REVIEW_DATA names the data directory and
REVIEW_PORT the port (default 8087). Apache serves web/ itself and
proxies /api/ here. waitress comes from the Debian package python3-waitress
and is imported only here, never by tests or the dev server.
"""
import os

import waitress

from .app import App


def main():
    data = os.environ.get("REVIEW_DATA")
    if not data:
        raise SystemExit("REVIEW_DATA is not set")
    port = int(os.environ.get("REVIEW_PORT", "8087"))
    # 4.5 MiB: a chapter upload (4 MiB of JSON) with room to spare. Apache refuses more than
    # 64 KiB on every other path before the request reaches waitress.
    waitress.serve(App(data), host="127.0.0.1", port=port, threads=8, connection_limit=200,
                   channel_timeout=30, max_request_body_size=4718592,
                   clear_untrusted_proxy_headers=True, ident="review")


if __name__ == "__main__":
    main()
