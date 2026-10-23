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
from .db import TooNew

# threads: requests answered at once, each with its own SQLite connection. Python runs one thread at a
# time, so more threads only take turns: under 60 clients at once (tests/bench.py), 4 threads answered
# about 45% more requests a second than 8, and 2 only about 15% more than 4. Four leaves three free while
# one does slow work, such as the full export.
# 4.5 MiB bodies: a chapter upload or hundreds of readers at once (4 MiB of JSON) with room to spare. Such
# requests come only through the SSH tunnel that review.py opens, straight to 127.0.0.1; Apache refuses
# /api/admin/ from the internet and more than 64 KiB on every other path before a request reaches waitress.
# trusted_proxy: Apache on this machine passes each request on with the reader's address appended to
# X-Forwarded-For; waitress takes that last address as REMOTE_ADDR, so the limits on signing in count each
# address on the internet (server/auth.py, client_key). Every other proxy header is removed.
WAITRESS = dict(threads=4, connection_limit=200, channel_timeout=30, max_request_body_size=4718592,
                trusted_proxy="127.0.0.1", trusted_proxy_count=1, trusted_proxy_headers={"x-forwarded-for"},
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
    try:
        app = App(data)
    except TooNew as e:
        # Older code on a database that newer code moved: the service stops with this line in its journal.
        raise SystemExit(str(e))
    except ValueError as e:
        # A wrong setting in config.json (a limit, auth, mail, notify or invite): one plain sentence that names
        # the file and the setting, in the journal, and the service does not start.
        raise SystemExit(f"{e}\nThe API did not start.")
    waitress.serve(app, host="127.0.0.1", port=port, **WAITRESS)


if __name__ == "__main__":
    main()
