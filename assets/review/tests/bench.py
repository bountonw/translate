"""Load test of the API: many readers with many comments, many clients at once, under waitress.

It builds a data directory in a temporary folder: SC01 to SC08 from main of the
translation repository (or made-up chapters when the repository is not found),
--readers readers in groups of 50, and --comments comments for each reader.
It then runs the API with server/prod.py's waitress settings in a second
process and sends --clients clients at it at once, each repeating a reader's
requests with no pause, for --seconds seconds. One more client is the
translator, asking for the reader list and the full export now and then. It
prints the median and the 95th percentile of each route in milliseconds.

    python3 tests/bench.py [--readers 500] [--comments 20] [--clients 60] [--seconds 20]

waitress must be installed (Debian: python3-waitress). This file is not a unit
test; unittest does not run it.
"""
import argparse
import http.client
import json
import multiprocessing
import os
import random
import socket
import sqlite3
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from helpers import REPO, SC_BOOK, Site, git_reader, sample_chapter  # noqa: E402

import parsers  # noqa: E402
from server import db  # noqa: E402

GROUP_SIZE = 50
WEIGHTS = [("me", 20), ("chapter", 15), ("chapter_304", 10), ("comments", 15), ("post", 12), ("patch", 5),
           ("place", 18), ("finished", 5)]


def build(data, readers, comments):
    """The data directory: chapters, groups, readers and comments. Returns [(code, [(ch, [anchors])])]."""
    site = Site.__new__(Site)
    token_path, _ = db.setup(data, "https://review.example.org")
    # The test measures speed, not the limits: a few readers write far more than 10 new comments a minute.
    cfg = Path(data) / db.CONFIG
    cfg.write_text(json.dumps(dict(json.loads(cfg.read_text()), limits={
        "comments_per_minute": 100000, "comments_per_day": 1000000, "writes_per_minute": 100000}), indent=2) + "\n")
    site.data, site.admin = Path(data), token_path.read_text().strip()
    from server.app import App
    site.app = App(data)
    chapters = {}
    for n in range(1, 9):
        if REPO:
            ch = parsers.load_chapter(SC_BOOK, n, git_reader(REPO))
            body = dict({k: ch[k] for k in ("n", "title", "title_en", "paragraphs")}, language="th",
                        commit="abc1234", book_title_en="Steps to Christ")
        else:
            body = sample_chapter(n, count=18)
        site.publish(body)
        chapters[f"SC{n:02d}"] = [p["a"] for p in body["paragraphs"]]
    groups = max(1, readers // GROUP_SIZE)
    for g in range(groups):
        r = site.admin_call("POST", "/api/admin/groups", {"name": f"G{g:02d}", "grants": ["SC01-08"],
                                                          "english": g % 3 == 0})
        assert r.status == 201, r.body
    rows = [{"name": f"Reader {i:04d}", "groups": [f"G{i % groups:02d}"], "grants": ["SC"] if i % 2 else [],
             "english": i % 5 == 0} for i in range(readers)]
    made = site.admin_call("POST", "/api/admin/readers/batch", {"readers": rows})
    assert made.status == 201, made.body[:300]
    made = made.json["readers"]
    con = sqlite3.connect(Path(data) / db.DB_NAME)
    stamp = db.now()
    rng = random.Random(1)
    ids = list(chapters)
    con.executemany(
        "INSERT INTO comment (client_id, reader, book, ch, a, kind, quote, text, version, created, updated)"
        " VALUES (?, ?, 'SC', ?, ?, 'flag', '', ?, '', ?, ?)",
        [(f"seed-{r['id']}-{k}", r["id"], ch, rng.choice(chapters[ch]), "ความเห็นทดลอง " * 8, stamp, stamp)
         for r in made for k in range(comments) for ch in [rng.choice(ids)]])
    con.executemany("INSERT INTO place (reader, book, ch, a, updated) VALUES (?, 'SC', 'SC01', ?, ?)",
                    [(r["id"], chapters["SC01"][0], stamp) for r in made])
    con.commit()
    con.close()
    return site.admin, [r["code"] for r in made], chapters


def prod_threads():
    """The thread count server/prod.py gives waitress, read without importing waitress here."""
    import re
    return int(re.search(r"threads=(\d+)", (ROOT / "server" / "prod.py").read_text()).group(1))


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Conn:
    def __init__(self, port):
        self.port = port
        self.c = None

    def call(self, method, path, code, body=None, etag=None):
        # One device per reader: every reader's link works on the first devices that open it.
        headers = {"Authorization": "Bearer " + code, "X-Review-Device": "bench-device-0000001"}
        data = None
        if body is not None:
            data = json.dumps(body, ensure_ascii=False).encode()
            headers["Content-Type"] = "application/json"
        if etag:
            headers["If-None-Match"] = etag
        for attempt in (1, 2):
            if self.c is None:
                self.c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=60)
            try:
                self.c.request(method, path, data, headers)
                r = self.c.getresponse()
                payload = r.read()
                return r.status, payload, r.getheader("ETag")
            except (http.client.HTTPException, OSError):
                self.c.close()
                self.c = None
                if attempt == 2:
                    return 0, b"", None


def client_thread(port, codes, chapters, deadline, seed, out, think=0):
    rng = random.Random(seed)
    conn = Conn(port)
    actions = [a for a, w in WEIGHTS for _ in range(w)]
    mine, etags, n = [], {}, 0
    while time.monotonic() < deadline:
        code = rng.choice(codes)
        ch = rng.choice(list(chapters))
        a = rng.choice(chapters[ch])
        act = rng.choice(actions)
        t0 = time.perf_counter()
        if act == "me":
            st, _, _ = conn.call("GET", "/api/me", code)
        elif act in ("chapter", "chapter_304"):
            # A returning device holds the chapter's ETag: the version, with ".en" when English is on.
            tag = etags.get(ch) if act == "chapter_304" else None
            if act == "chapter_304" and not tag:
                act = "chapter"
            st, _, got = conn.call("GET", f"/api/chapter/SC/{ch}", code,
                                   etag=f'{tag}, {tag[:-1]}.en"' if tag else None)
            if got and not got.endswith('.en"'):
                etags[ch] = got
        elif act == "comments":
            st, _, _ = conn.call("GET", f"/api/comments?book=SC&ch={ch}", code)
        elif act == "post":
            n += 1
            cid = f"b{seed}-{n}"
            st, body, _ = conn.call("POST", "/api/comments", code, {
                "client_id": cid, "book": "SC", "ch": ch, "a": a, "kind": "wording", "quote": "พระเจ้า",
                "text": "ลองใช้คำว่า " * 10})
            if st == 201:
                mine.append((code, cid))
        elif act == "patch":
            if not mine:
                continue
            c, cid = rng.choice(mine)
            st, _, _ = conn.call("PATCH", f"/api/comments/{cid}", c, {"text": f"แก้ไข {rng.random()}"})
        elif act == "place":
            st, _, _ = conn.call("PUT", "/api/place", code, {"book": "SC", "ch": ch, "a": a})
        else:
            st, _, _ = conn.call("PUT", "/api/finished", code, {"book": "SC", "ch": ch, "finished": rng.random() < .5})
        out.append((act, (time.perf_counter() - t0) * 1000, st))
        if think:
            time.sleep(rng.uniform(0, 2 * think))


def admin_thread(port, token, deadline, out):
    conn = Conn(port)
    turn = 0
    while time.monotonic() < deadline:
        turn += 1
        route = ("admin_export", "/api/admin/export") if turn % 3 == 0 else ("admin_readers", "/api/admin/readers")
        t0 = time.perf_counter()
        st, _, _ = conn.call("GET", route[1], token)
        out.append((route[0], (time.perf_counter() - t0) * 1000, st))
        time.sleep(1)


def client_process(port, codes, chapters, seconds, threads, seed, token, queue, think=0):
    deadline = time.monotonic() + seconds
    out = []
    ts = [threading.Thread(target=client_thread, args=(port, codes, chapters, deadline, seed * 1000 + i, out, think))
          for i in range(threads)]
    if token:
        ts.append(threading.Thread(target=admin_thread, args=(port, token, deadline, out)))
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    queue.put(out)


def pct(values, p):
    values = sorted(values)
    return values[min(len(values) - 1, int(round(p / 100 * (len(values) - 1))))]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--readers", type=int, default=500)
    ap.add_argument("--comments", type=int, default=20)
    ap.add_argument("--clients", type=int, default=60)
    ap.add_argument("--seconds", type=int, default=20)
    ap.add_argument("--processes", type=int, default=6, help="client processes; the clients are shared among them")
    ap.add_argument("--threads", type=int, help="waitress threads (default: server/prod.py's)")
    ap.add_argument("--think", type=float, default=0, help="seconds each client waits between requests")
    a = ap.parse_args()
    tmp = tempfile.TemporaryDirectory()
    data = Path(tmp.name) / "data"
    t0 = time.perf_counter()
    token, codes, chapters = build(data, a.readers, a.comments)
    print(f"Built {a.readers} readers, {a.readers * a.comments} comments, {len(chapters)} chapters "
          f"({'from main' if REPO else 'made up'}) in {time.perf_counter() - t0:.1f} s.")
    port = free_port()
    env = dict(os.environ, REVIEW_DATA=str(data), REVIEW_PORT=str(port))
    # The server's log goes to a file: a pipe nobody reads fills up and stops waitress at its next warning.
    log = open(Path(tmp.name) / "server.log", "w+")
    run = "from server import prod; prod.WAITRESS['threads'] = int(sys.argv[1]) or prod.WAITRESS['threads']; prod.main()"
    server = subprocess.Popen([sys.executable, "-c", "import sys; " + run, str(a.threads or 0)], cwd=ROOT, env=env,
                              stdout=log, stderr=log)
    threads = a.threads or prod_threads()
    try:
        for _ in range(200):
            try:
                socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
                break
            except OSError:
                time.sleep(0.05)
        pause = f"{a.think} s" if a.think else "no"
        print(f"waitress threads={threads}; {a.clients} clients in {a.processes} processes for {a.seconds} s, "
              f"{pause} pause between requests, plus the translator's reader list and export.")
        ctx = multiprocessing.get_context("fork")   # fork needs no socket of its own, unlike forkserver
        queue = ctx.Queue()
        share = [a.clients // a.processes + (1 if i < a.clients % a.processes else 0) for i in range(a.processes)]
        procs = [ctx.Process(target=client_process, args=(port, codes, chapters, a.seconds, n, i + 1,
                                                         token if i == 0 else None, queue, a.think))
                 for i, n in enumerate(share)]
        for p in procs:
            p.start()
        results = [r for _ in procs for r in queue.get()]
        for p in procs:
            p.join()
    finally:
        server.terminate()
        server.wait(timeout=10)
    log.seek(0)
    err = log.read()
    log.close()
    by = {}
    for act, ms, st in results:
        by.setdefault(act, []).append((ms, st))
    total = len(results)
    print(f"{total} requests in {a.seconds} s: {total / a.seconds:.0f} a second.")
    print(f"{'route':<14}{'count':>7}{'median ms':>11}{'p95 ms':>9}{'max ms':>9}  statuses")
    names = {"me": "GET me", "chapter": "GET chapter", "chapter_304": "GET ch 304", "comments": "GET comments",
             "post": "POST comment", "patch": "PATCH comment", "place": "PUT place", "finished": "PUT finished",
             "admin_readers": "admin readers", "admin_export": "admin export"}
    for act in names:
        rows = by.get(act)
        if not rows:
            continue
        ms = [m for m, _ in rows]
        statuses = {}
        for _, st in rows:
            statuses[st] = statuses.get(st, 0) + 1
        print(f"{names[act]:<14}{len(rows):>7}{statistics.median(ms):>11.1f}{pct(ms, 95):>9.1f}{max(ms):>9.1f}  "
              + ", ".join(f"{k}: {v}" for k, v in sorted(statuses.items())))
    warnings = err.count("Task queue depth")
    if warnings:
        print(f"waitress warned {warnings} times that requests waited for a free thread.")
    if "Traceback" in err:
        print("The server logged an error:\n" + err[-3000:])
    tmp.cleanup()


if __name__ == "__main__":
    main()
