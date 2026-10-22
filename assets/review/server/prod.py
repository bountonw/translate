"""Production entry point: run the API under waitress on 127.0.0.1.

systemd starts it as "python3 -m server.prod" from the code folder
(deploy/review.service). REVIEW_DATA names the data directory and
REVIEW_PORT the port (default 8087). Apache serves web/ itself and
proxies /api/ here. waitress comes from the Debian package python3-waitress
and is imported only here, never by tests or the dev server; tests/bench.py
runs the same settings when it measures the site under load.
"""
import logging
import os

import waitress

from .app import App

# threads: requests answered at once, each with its own SQLite connection. Python runs one thread at a
# time, so more threads only take turns: under 60 clients at once (tests/bench.py), 4 threads answered
# about 45% more requests a second than 8, and 2 only about 15% more than 4. Four leaves three free while
# one does slow work, such as the full export.
# 4.5 MiB bodies: a chapter upload or hundreds of readers at once (4 MiB of JSON) with room to spare.
# Apache refuses more than 64 KiB on every path outside /api/admin/ before the request reaches waitress.
WAITRESS = dict(threads=4, connection_limit=200, channel_timeout=30, max_request_body_size=4718592,
                clear_untrusted_proxy_headers=True, ident="review")


# waitress logs "Task queue depth is N" whenever a request waits for a thread, which at normal load is
# thousands of lines an hour and can crowd an error out of the journal. Only its errors are kept;
# deploy/DEPLOY.md gives a check of the site's speed instead.
QUIET_LOGGERS = ("waitress.queue",)


def main():
    for name in QUIET_LOGGERS:
        logging.getLogger(name).setLevel(logging.ERROR)
    data = os.environ.get("REVIEW_DATA")
    if not data:
        raise SystemExit("REVIEW_DATA is not set")
    port = int(os.environ.get("REVIEW_PORT", "8087"))
    waitress.serve(App(data), host="127.0.0.1", port=port, **WAITRESS)


if __name__ == "__main__":
    main()
