"""The admin page in headless Firefox, against `review.py admin` in front of a dev server, all under $TMPDIR.

    python3 tests/admin_browser.py [--readers 300] [--keep]

It copies this folder to $TMPDIR/admin-browser/code, adds tests/admin_probe.js to the copy's admin/ as
probe.html, and runs every command with HOME set to $TMPDIR/admin-browser/home, so the dev data, the export
folder, the links files and the alignment packets all land there and nothing of ~/claude-sandbox is touched.
It sets up a dev server, publishes SC01-03 from the translation repository, makes two groups and the readers,
writes three comments and two more by Boon Mee, opens Boon Mee's link on three devices so that the third waits for
approval, starts review.py admin, and opens the probe, which drives every control of every section of the page
(tests/admin_probe.js). It ends with the probe's checks, the timings, and a check that the page called every
local route of review_admin.routes(). unittest does not run it; it needs Firefox and the translation repository.
"""
import argparse
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BUILD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BUILD / "tests"))
from helpers import REPO  # noqa: E402

PROFILE = """user_pref("devtools.console.stdout.content", true);
user_pref("browser.shell.checkDefaultBrowser", false);
user_pref("datareporting.policy.dataSubmissionEnabled", false);
user_pref("toolkit.telemetry.reportingpolicy.firstRun", false);
user_pref("browser.startup.homepage_override.mstone", "ignore");
user_pref("app.update.enabled", false);
user_pref("network.proxy.type", 0);
user_pref("browser.aboutwelcome.enabled", false);
"""
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def browse(url, name, secrets):
    """Open url in headless Firefox until the probe logs P DONE; return the probe's lines and any error lines,
    with the key and the reader codes replaced by <secret>."""
    prof = Path(os.environ.get("TMPDIR", "/tmp")) / "admin-browser" / f"profile-{name}"
    prof.mkdir()
    (prof / "user.js").write_text(PROFILE)
    ff = subprocess.Popen(["firefox", "--headless", "--no-remote", "--profile", str(prof), "--window-size=1280,900", url],
                          env=dict(os.environ, MOZ_HEADLESS="1"), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True)
    lines = []
    threading.Thread(target=lambda: [lines.append(x) for x in ff.stdout], daemon=True).start()
    t0 = time.monotonic()
    while time.monotonic() - t0 < 600 and not any(re.search(r"\bP DONE\"?$", x.strip()) for x in lines):
        time.sleep(0.3)
    ff.terminate()
    ff.wait(10)
    shown = []
    for x in lines:
        if re.search(r"\bP |JavaScript error|Content-Security-Policy|Content Security|TypeError|SyntaxError|"
                     r"ReferenceError|console\.error", x):
            out = re.sub(r"^console\.(log|error): ", "", x.rstrip())
            if out.startswith('"') and out.endswith('"'):
                try:
                    out = json.loads(out)
                except ValueError:
                    pass
            for s in secrets:
                out = out.replace(s, "<secret>")
            shown.append(out)
            print(out[:1500])
    return shown


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--readers", type=int, default=300, help="readers invited from a file besides the four named")
    ap.add_argument("--keep", action="store_true", help="keep $TMPDIR/admin-browser after the run")
    a = ap.parse_args()
    if REPO is None:
        sys.exit("The translation repository is not found; set REVIEW_REPO.")
    tmp = Path(os.environ.get("TMPDIR", "/tmp")) / "admin-browser"
    if tmp.exists():
        shutil.rmtree(tmp)
    home = tmp / "home"
    data = home / "claude-sandbox" / "review-dev"
    code = tmp / "code"
    shutil.copytree(BUILD, code, ignore=shutil.ignore_patterns("__pycache__", "tests", ".claude"))
    page = (code / "admin" / "index.html").read_text()
    script = '<script type="module" src="admin.js"></script>'
    assert script in page
    (code / "admin" / "probe.html").write_text(page.replace(script, '<script src="probe.js"></script>\n' + script))
    shutil.copy(BUILD / "tests" / "admin_probe.js", code / "admin" / "probe.js")
    env = dict(os.environ, HOME=str(home), PYTHONDONTWRITEBYTECODE="1")
    env.pop("REVIEW_TOKEN_FILE", None)
    env.pop("REVIEW_SERVER", None)
    env.pop("REVIEW_DATA", None)
    site_port, admin_port = free_port(), free_port()
    site = f"http://127.0.0.1:{site_port}"
    procs = []

    def cli(*args):
        r = subprocess.run([sys.executable, str(code / "review.py"), "--server", site, "--repo", str(REPO), *args],
                           capture_output=True, text=True, env=env)
        if r.returncode:
            raise SystemExit(f"review.py {' '.join(args)} failed:\n{r.stdout}{r.stderr}")
        return r.stdout

    def call(method, path, body, code_, device="admin-browser-device-01"):
        req = urllib.request.Request(site + path, method=method, data=None if body is None else json.dumps(body).encode(),
                                     headers={"Authorization": "Bearer " + code_, "Content-Type": "application/json",
                                              "X-Review-Device": device})
        try:
            with OPENER.open(req, timeout=10) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            with e:
                return json.loads(e.read())

    def start(args, ready, log):
        """Start a review.py command that keeps running; its output after the line `ready` goes to the file log."""
        p = subprocess.Popen([sys.executable, str(code / "review.py"), *args], stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True, env=env)
        procs.append(p)
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            line = p.stdout.readline()
            if ready in line:
                def drain():
                    with open(tmp / log, "a") as f:
                        for x in p.stdout:
                            f.write(x)
                            f.flush()
                threading.Thread(target=drain, daemon=True).start()
                return line
            if not line and p.poll() is not None:
                break
        raise SystemExit(f"review.py {' '.join(args)} did not start.")

    try:
        real_dev = Path(os.environ.get("HOME", "")) / "claude-sandbox" / "review-dev"
        before = {p: p.stat().st_mtime for p in real_dev.glob("**/*")} if real_dev.is_dir() else {}
        start(["serve", "--dev", "--port", str(site_port)], "Serving", "site.log")
        print(cli("publish", "SC", "01-03").strip().splitlines()[0])
        cli("group", "create", "Pastors", "--grant", "SC01-02", "--english")
        cli("group", "create", "Youth", "--grant", "SC03")
        links = {}
        for name, extra in (("Anan Chaiyo", ["--group", "Pastors"]), ("Mali Srisuk", ["--grant", "SC01"]),
                            ("Somchai Jaidee", ["--group", "Pastors", "--grant", "SC01"]), ("Boon Mee", ["--grant", "SC"])):
            links[name] = re.search(r"(\S+#k=\S+)", cli("invite", name, *extra)).group(1)
        many = tmp / "seed.csv"
        many.write_text("name,groups,grants,english\n" + "".join(f"Reader {i:03d},Youth,SC01,no\n"
                                                                  for i in range(1, a.readers + 1)))
        cli("invite", "--from", str(many))
        codes = {n: l.split("#k=")[1] for n, l in links.items()}
        anchors = [p["a"] for p in call("GET", "/api/chapter/SC/SC01", None, codes["Mali Srisuk"])["paragraphs"]]
        ids = []
        for i, (who, a_) in enumerate((("Anan Chaiyo", anchors[0]), ("Anan Chaiyo", anchors[1]), ("Mali Srisuk", anchors[2]))):
            ids.append(call("POST", "/api/comments", {"client_id": f"probe-{i}", "book": "SC", "ch": "SC01", "a": a_,
                                                      "kind": "flag", "quote": "", "text": f"Comment {i}"}, codes[who])["id"])
        # Junk from a misused link, which the probe deletes; then the link on two more devices: the third waits.
        for i in range(2):
            call("POST", "/api/comments", {"client_id": f"junk-{i}", "book": "SC", "ch": "SC01", "a": anchors[3 + i],
                                           "kind": "flag", "quote": "", "text": f"Junk {i}"}, codes["Boon Mee"])
        call("GET", "/api/me", None, codes["Boon Mee"], "admin-browser-device-02")
        waiting = call("GET", "/api/me", None, codes["Boon Mee"], "admin-browser-device-03")
        if waiting.get("error") != "device_waiting":
            raise SystemExit(f"The third device of Boon Mee did not wait for approval: {waiting}")
        commit = subprocess.run(["git", "-C", str(REPO), "log", "-1", "--format=%h", "main"], capture_output=True,
                                text=True).stdout.strip()
        line = start(["--server", site, "--repo", str(REPO), "admin", "--port", str(admin_port), "--no-open"], "#key=",
                     "admin.log")
        key = line.strip().rsplit("#key=", 1)[1]
        query = urllib.parse.urlencode({
            "mode": "main", "commit": commit, "total": a.readers + 4, "ids": ",".join(map(str, ids)),
            "link": links["Mali Srisuk"], "site": site, "data": str(data), "home": str(home),
            "exports": str(data / "export")})
        secrets = [key] + list(codes.values())
        shown = browse(f"http://127.0.0.1:{admin_port}/probe.html?{query}#key={key}", "main", secrets)

        # The live site: review.py admin through a stand-in for ssh (tests/test_ssh.py) that forwards the tunnel's
        # Unix socket, or its port where no Unix socket can be made, to the dev server, with the token in
        # ~/.config/review as on the translator's computer.
        from test_ssh import STAND_IN
        bindir = tmp / "bin"
        bindir.mkdir()
        (bindir / "ssh").write_text(STAND_IN)
        (bindir / "ssh").chmod(0o755)
        config = home / ".config" / "review"
        config.mkdir(parents=True)
        (config / "admin-token").write_text((data / "admin-token").read_text())
        (config / "admin-token").chmod(0o600)
        env.update(PATH=f"{bindir}{os.pathsep}{os.environ.get('PATH', '')}", FAKE_SSH_LOG=str(tmp / "ssh.log"))
        live = f"ssh://tester@droplet.example?api_port={site_port}"
        live_port = free_port()
        # This run opens the browser as the translator's does: BROWSER is a stand-in that writes down the address it
        # is given, which holds a one-time code, never the key; the probe opens that address and trades the code.
        opened = tmp / "browser-opened.txt"
        (bindir / "browser").write_text(f"#!/bin/sh\nprintf '%s' \"$1\" > '{opened}'\n")
        (bindir / "browser").chmod(0o755)
        env["BROWSER"] = f"{bindir / 'browser'} %s"
        line = start(["--server", live, "--token-file", str(config / "admin-token"), "--repo", str(REPO), "admin",
                      "--port", str(live_port)], "#key=", "admin-live.log")
        live_key = line.strip().rsplit("#key=", 1)[1]
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline and not (opened.exists() and opened.read_text()):
            time.sleep(0.1)
        once = opened.read_text().strip()
        if "#once=" not in once or live_key in once:
            raise SystemExit(f"review.py admin opened the browser at {once!r}, not at a one-time code.")
        print("review.py admin opened the browser at an address with a one-time code, not the key.")
        code_once = once.rsplit("#once=", 1)[1]
        query = urllib.parse.urlencode({"mode": "live", "site": live, "exports": str(home / "claude-sandbox" / "review-prod" / "export")})
        shown += browse(f"http://127.0.0.1:{live_port}/probe.html?{query}#once={code_once}", "live",
                        secrets + [live_key, code_once])
        sys.path.insert(0, str(code))
        import review_admin
        want = sorted(f"{m} {r}" for r, m in review_admin.routes().items())
        got = sorted({r for x in shown if x.startswith("P ROUTES ") for r in x.split("ROUTES ", 1)[1].split(",")})
        missing = sorted(set(want) - set(got))
        failed = sum(1 for x in shown if x.startswith("P FAIL") or not x.startswith("P "))
        print(f"Routes called by the page: {len(set(got) & set(want))} of {len(want)}"
              + (f"; never called: {', '.join(missing)}" if missing else "."))
        modes = [m for m in shown if m.startswith("P DONE ")]
        print(f"Probe runs finished: {', '.join(m[7:] for m in modes) or 'none'}.")
        tunnels = [json.loads(x)["args"] for x in (tmp / "ssh.log").read_text().splitlines()]
        print(f"The stand-in for ssh was started {len(tunnels)} time(s), first as: ssh {' '.join(tunnels[0])}")
        for f in sorted(data.glob("links-*.csv")):
            mode = oct(f.stat().st_mode & 0o777)
            print(f"{f.name}: mode {mode}")
            failed += mode != "0o600"
        after = {p: p.stat().st_mtime for p in real_dev.glob("**/*")} if real_dev.is_dir() else {}
        if after != before:
            print(f"FAIL {real_dev} changed during the run.")
            failed += 1
        else:
            print(f"{real_dev} was not touched.")
        ok = not missing and failed == 0 and len(modes) == 5
        print("PASS" if ok else f"FAIL: {failed} failed checks or lines, {len(missing)} routes never called.")
        return 0 if ok else 1
    finally:
        for p in procs:
            p.terminate()
            try:
                p.wait(10)
            except subprocess.TimeoutExpired:
                p.kill()
        if not a.keep:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
