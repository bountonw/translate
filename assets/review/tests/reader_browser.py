"""The reader's page in headless Firefox at phone width, against a dev server of this folder under $TMPDIR.

    python3 tests/reader_browser.py [--keep]

It runs the dev server in this process, with the stand-in for LINE and the file mailer (server/dev.py), on a data
folder under $TMPDIR/reader-browser, and drives Firefox through Marionette, Firefox's own remote control, with
real clicks and key presses, in a window 360 pixels wide. It checks the screens of signing in that round 4a fixed
(69-fixes.md):

    old-link     an old personal link opens the chapter list on a browser signed in, and the sign-in screen on
                 another, where LINE signs the reader in (68-reader.md item 1)
    closed-join  a general link that takes no more requests shows the sign-in screen with its line, and the
                 person approved signs in there (66-adversarial.md ADV4-02, 68-reader.md item 2)
    not-now      "Not now" on another reader's link keeps the reader signed in on the browser (ADV4-07, item 3)
    long-address a long email address keeps the code screen and "Your devices" within the phone's width, and the
                 code step has Cancel (items 4 and 10)
    stopped      the stopped screen's "Try again" opens the chapter list once the reader is let back in (item 5)
    blocked      a browser that blocks the site's data names the setting and has "Try again" (item 6)
    spent-link   a used link's sign-in screen says what to do without the lead that says to open the link (item 7)

Every line it prints is "ok ...", "FAIL ..." or a note; it ends with PASS or FAIL and exits 1 on a failure.
unittest does not run it; it needs Firefox. No line holds a reader's link.
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
import urllib.request
from pathlib import Path

BUILD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BUILD))
from server import db, dev  # noqa: E402
from server.app import App  # noqa: E402

WIDTH, HEIGHT = 360, 740
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
PREFS = """user_pref("devtools.console.stdout.content", true);
user_pref("browser.shell.checkDefaultBrowser", false);
user_pref("datareporting.policy.dataSubmissionEnabled", false);
user_pref("toolkit.telemetry.reportingpolicy.firstRun", false);
user_pref("browser.startup.homepage_override.mstone", "ignore");
user_pref("app.update.enabled", false);
user_pref("network.proxy.type", 0);
user_pref("browser.aboutwelcome.enabled", false);
user_pref("marionette.port", %d);
user_pref("remote.prefs.recommended", true);
"""
FAILS = []


def check(cond, what):
    print(("ok " if cond else "FAIL ") + what, flush=True)
    if not cond:
        FAILS.append(what)
    return cond


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Firefox:
    """Headless Firefox driven through Marionette: navigation, scripts, and trusted clicks and key presses."""

    def __init__(self, folder, prefs=""):
        self.port = free_port()
        folder.mkdir(parents=True)
        (folder / "user.js").write_text(PREFS % self.port + prefs)
        self.log = folder.parent / (folder.name + ".log")
        self.logf = open(self.log, "w")
        self.proc = subprocess.Popen(["firefox", "--headless", "--no-remote", "--marionette", "-remote-allow-system-access",
                                      "--profile", str(folder),
                                      f"--window-size={WIDTH + 200},{HEIGHT + 100}", "about:blank"],
                                     env=dict(os.environ, MOZ_HEADLESS="1"), stdout=self.logf,
                                     stderr=subprocess.STDOUT)
        deadline = time.time() + 60
        while True:
            try:
                self.sock = socket.create_connection(("127.0.0.1", self.port), timeout=120)
                break
            except OSError:
                if time.time() > deadline:
                    raise
                time.sleep(0.3)
        self.buf = b""
        self.read()
        self.n = 0
        self.cmd("WebDriver:NewSession", {"capabilities": {"alwaysMatch": {"acceptInsecureCerts": True}}})
        self.narrow()

    def read(self):
        while b":" not in self.buf:
            self.buf += self.sock.recv(65536)
        size, _, rest = self.buf.partition(b":")
        size = int(size)
        while len(rest) < size:
            rest += self.sock.recv(65536)
        self.buf = rest[size:]
        return json.loads(rest[:size])

    def cmd(self, name, params=None):
        self.n += 1
        data = json.dumps([0, self.n, name, params or {}]).encode()
        self.sock.sendall(str(len(data)).encode() + b":" + data)
        while True:
            r = self.read()
            if r[0] == 1 and r[1] == self.n:
                break
        if r[2]:
            raise RuntimeError(f"{name}: {r[2].get('error')}: {r[2].get('message')}")
        res = r[3]
        return res.get("value", res) if isinstance(res, dict) else res

    def narrow(self):
        """The page's own width is WIDTH pixels, as a phone's: Firefox's window cannot be that narrow, so the
        browser element inside it is."""
        self.cmd("Marionette:SetContext", {"value": "chrome"})
        self.js("let b = gBrowser.selectedBrowser; for (const el of [b, b.parentNode]) { el.style.maxWidth = '%dpx'; "
                "el.style.minWidth = '%dpx'; el.style.width = '%dpx'; el.style.flex = 'none'; "
                "el.style.maxHeight = '%dpx'; el.style.minHeight = '%dpx'; el.style.height = '%dpx'; }"
                % ((WIDTH,) * 3 + (HEIGHT,) * 3))
        self.cmd("Marionette:SetContext", {"value": "content"})

    def js(self, script, *args):
        return self.cmd("WebDriver:ExecuteScript", {"script": script, "args": list(args)})

    def go(self, url):
        self.cmd("WebDriver:Navigate", {"url": url})
        self.wait("return document.readyState === 'complete'", 15)
        time.sleep(0.4)

    def wait(self, script, timeout=15, *args):
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                v = self.js(script, *args)
            except RuntimeError:
                v = None
            if v:
                return v
            time.sleep(0.15)
        return None

    def click(self, css, text=None, timeout=10):
        """Click the first element of css whose text holds text, with a trusted click."""
        t0 = time.time()
        while time.time() - t0 < timeout:
            found = self.js("""
              for (const e of document.querySelectorAll('[data-probe]')) e.removeAttribute('data-probe');
              const el = Array.from(document.querySelectorAll(arguments[0])).find(e => arguments[1] === null ||
                e.textContent.indexOf(arguments[1]) >= 0);
              if (!el) return false;
              el.setAttribute('data-probe', '1');
              el.scrollIntoView({block: 'center'});
              return true;""", css, text)
            if found:
                try:
                    el = self.cmd("WebDriver:FindElement", {"using": "css selector", "value": '[data-probe="1"]'})
                    self.cmd("WebDriver:ElementClick", {"id": el["element-6066-11e4-a52e-4f735466cecf"]})
                    return True
                except RuntimeError:
                    pass
            time.sleep(0.15)
        print(f"   could not click {css} {text!r}", flush=True)
        return False

    def type(self, css, text):
        if not self.wait("return !!document.querySelector(arguments[0])", 10, css):
            return False
        el = self.cmd("WebDriver:FindElement", {"using": "css selector", "value": css})
        self.js("document.querySelector(arguments[0]).value = '';", css)
        self.cmd("WebDriver:ElementSendKeys", {"id": el["element-6066-11e4-a52e-4f735466cecf"], "text": text})
        return True

    def text(self, css="#main"):
        return self.js("const e = document.querySelector(arguments[0]); return e ? e.innerText : '';", css) or ""

    def flat(self, css="#main"):
        """The text of css on one line, for a check's message."""
        return " ".join(self.text(css).split())

    def sees(self, words, timeout=15, css="#main"):
        return bool(self.wait("const e = document.querySelector(arguments[1]); return !!e && "
                              "e.innerText.indexOf(arguments[0]) >= 0;", timeout, words, css))

    def fits(self):
        """Whether the page fits its width, with no sideways scrolling."""
        return self.js("return document.documentElement.scrollWidth <= window.innerWidth + 0.5 && "
                       "window.innerWidth <= arguments[0] + 0.5;", WIDTH)

    def close(self):
        try:
            self.cmd("Marionette:Quit", {"flags": ["eForceQuit"]})
        except Exception:
            pass
        try:
            self.proc.wait(10)
        except Exception:
            self.proc.kill()
        self.logf.close()


class Run:
    def __init__(self, tmp):
        self.tmp = tmp
        self.port = free_port()
        self.url = f"http://127.0.0.1:{self.port}"
        self.data = tmp / "data"
        token_path, _ = db.setup(self.data, self.url)
        self.token = token_path.read_text().strip()
        self.app = App(self.data, public_url=self.url)
        self.httpd = dev.make(self.app, BUILD / "web", self.port, quiet=True)
        self.standin = self.httpd.standin
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.browsers = []
        self.codes = []
        self.users = {}
        for n in (1, 2):
            paras = [{"a": f"SC {100 + n}.{i}", "text": f"Paragraph {i} of chapter {n}.", "fn": [],
                      "en": f"<p>English {i}</p>"} for i in range(1, 4)]
            status, _ = self.admin("PUT", f"/api/admin/chapters/SC/SC0{n}", {
                "n": n, "title": f"Chapter {n}", "title_en": f"Chapter {n}", "paragraphs": paras, "commit": "abc1234",
                "book_title_en": "Steps to Christ", "language": "th"})
            assert status in (200, 201), status

    def admin(self, method, path, body=None):
        req = urllib.request.Request(self.url + path, method=method,
                                     data=None if body is None else json.dumps(body).encode(),
                                     headers={"Authorization": "Bearer " + self.token,
                                              "Content-Type": "application/json"})
        try:
            with OPENER.open(req, timeout=20) as r:
                return r.status, json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            with e:
                return e.code, json.loads(e.read() or b"{}")

    def invite(self, name, **extra):
        status, r = self.admin("POST", "/api/admin/readers", dict({"name": name, "grants": ["SC"]}, **extra))
        assert status == 201, (status, r)
        self.codes.append(r["code"])
        return r

    def line_user(self, name):
        """A LINE test user of the stand-in for one reader: its number."""
        self.standin.users.append((f"U{len(self.standin.users):032d}", name))
        return len(self.standin.users) - 1

    def browser(self, name, prefs=""):
        ff = Firefox(self.tmp / f"profile-{name}", prefs)
        self.browsers.append(ff)
        return ff

    def link(self, code, mark="k"):
        return f"{self.url}/#{mark}={code}"

    def english(self, ff):
        """Open the site's plain address and switch the page to English, which the device then keeps."""
        ff.go(self.url + "/")
        ff.wait("return !!document.querySelector('.lang-btn')", 15)
        if ff.js("return document.documentElement.lang") != "en":
            ff.click(".lang-btn[lang=en]")
            ff.wait("return document.documentElement.lang === 'en'", 5)

    def line(self, ff, user):
        """On the stand-in's page, sign in as the test user numbered user."""
        if not ff.wait("return location.href.indexOf('/authorize?') >= 0", 15):
            return False
        return ff.click("a", "Sign in as " + self.standin.users[user][1])

    def on_list(self, ff, name, timeout=20):
        return bool(ff.wait("return document.querySelectorAll('.ch-row').length > 0 && "
                            "((document.querySelector('.hello') || {}).textContent || '').indexOf(arguments[0]) >= 0;",
                            timeout, name))

    def code_for(self, address, after):
        """The six digits of the newest mail to address written after the time after."""
        folder = self.data / "mail"
        for _ in range(100):
            files = sorted(folder.glob("*.eml"), key=lambda p: p.stat().st_mtime) if folder.exists() else []
            for p in reversed(files):
                if p.stat().st_mtime < after:
                    break
                text = p.read_text(errors="replace")
                if re.search(r"^To: " + re.escape(address), text, re.M | re.I):
                    m = re.search(r"\b(\d{6})\b", text)
                    return m.group(1) if m else None
            time.sleep(0.1)
        return None

    def signed_in_with_line(self, ff, reader, user):
        """Open the reader's link in ff and sign in with LINE as user: whether the chapter list opened."""
        ff.go(self.link(reader["code"]))
        ff.click("button.line-btn")
        self.line(ff, user)
        return self.on_list(ff, reader["name"])

    def errors(self):
        """Script errors and CSP refusals in the browsers' logs, with every link code masked."""
        out = []
        for ff in self.browsers:
            for line in ff.log.read_text(errors="replace").splitlines():
                if re.search(r"JavaScript error|Content-Security-Policy|Content Security|TypeError|SyntaxError|"
                             r"ReferenceError", line) and "chrome://" not in line and "resource://" not in line:
                    for code in self.codes:
                        line = line.replace(code, "<code>")
                    out.append(line)
        return out

    def close(self):
        for ff in self.browsers:
            ff.close()
        self.httpd.shutdown()
        self.httpd.server_close()


# ---------- the parts ----------

def old_link(run):
    eko = run.invite("Eko")
    user = run.line_user("Eko LINE")
    a = run.browser("old-a")
    run.english(a)
    check(run.signed_in_with_line(a, eko, user), "old-link: Eko signs in with LINE through the link")
    status, fresh = run.admin("POST", f"/api/admin/readers/{eko['id']}/code")
    run.codes.append(fresh.get("code", ""))
    check(status == 200, "old-link: Eko gets a new link")
    a.go(run.link(eko["code"]))
    check(run.on_list(a, "Eko"), "old-link: the old link opens Eko's chapter list on the browser signed in")
    b = run.browser("old-b")
    run.english(b)
    b.go(run.link(eko["code"]))
    check(b.sees("This link does not work") and b.sees("Sign in", css="#main h1") and
          bool(b.js("return !!document.querySelector('#main button.line-btn')")),
          "old-link: a new browser shows the sign-in screen with the line and LINE: " + b.flat()[:160])
    check(b.js("return localStorage.getItem('rv.code')") is None, "old-link: the device forgets the old link")
    b.click("button.line-btn")
    run.line(b, user)
    check(run.on_list(b, "Eko"), "old-link: LINE signs Eko in on the new browser")


def closed_join(run):
    run.admin("POST", "/api/admin/groups", {"name": "Pastors69", "grants": ["SC"]})
    status, first = run.admin("POST", "/api/admin/general-links", {"group": "Pastors69"})
    run.codes.append(first.get("code", ""))
    user = run.line_user("Asker69")
    c = run.browser("join-c")
    run.english(c)
    c.go(run.link(first["code"], "join"))
    check(c.sees("Ask to read", css="#main h1"), "closed-join: the general link asks to read")
    c.click("button.line-btn")
    run.line(c, user)
    check(c.sees("Your request went to the translator."), "closed-join: the request went: " + c.flat()[:120])
    status, second = run.admin("POST", "/api/admin/general-links", {"group": "Pastors69"})
    run.codes.append(second.get("code", ""))
    _, reqs = run.admin("GET", "/api/admin/requests")
    qid = next(q["id"] for q in reqs["requests"] if q["display"] == "Asker69")
    status, _ = run.admin("POST", f"/api/admin/requests/{qid}/approve", {"name": "Approved69"})
    check(status == 200, "closed-join: the translator approves the request")
    d = run.browser("join-d")
    run.english(d)
    d.go(run.link(first["code"], "join"))
    check(d.sees("This link no longer takes requests. If you asked already, sign in") and
          bool(d.js("return !!document.querySelector('#main button.line-btn')")),
          "closed-join: the closed link shows the sign-in screen with its line and LINE: " + d.flat()[:200])
    check("The first time, open the personal link" not in d.text(), "closed-join: no lead about a personal link")
    d.click("button.line-btn")
    run.line(d, user)
    check(run.on_list(d, "Approved69"), "closed-join: the approved person signs in and reads")


def not_now(run):
    mali = run.invite("Mali")
    dao = run.invite("Dao")
    e = run.browser("notnow-e")
    run.english(e)
    check(run.signed_in_with_line(e, mali, run.line_user("Mali LINE")), "not-now: Mali signs in with LINE")
    e.go(run.link(dao["code"]))
    check(e.sees("Welcome, Dao") and e.sees("You are signed in as Mali on this browser."),
          "not-now: Dao's link says that the browser is signed in as Mali")
    e.click("button.skip-btn", "Not now")
    check(run.on_list(e, "Mali"), "not-now: Not now keeps Mali signed in and opens her chapter list")
    check(e.js("return localStorage.getItem('rv.code')") is None, "not-now: the device keeps no link of Dao's")
    e.go(run.url + "/")
    check(run.on_list(e, "Mali"), "not-now: the plain address still opens Mali's chapter list")
    check(bool(e.js("return !!document.querySelector('#devices-btn')")), "not-now: Your devices is there for Mali")


def long_address(run):
    nok = run.invite("Nok")
    address = "somchai.wongsawatpaiboon.pastor.bangkok@example.org"
    f = run.browser("long-f")
    run.english(f)
    f.go(run.link(nok["code"]))
    f.click("button", "Use your email instead")
    f.type("input[name=email]", address)
    after = time.time() - 1
    f.click("button", "Send a code")
    check(f.sees("A six-digit code went to"), "long-address: the code step shows")
    check(f.fits(), "long-address: the code step fits 360 px: " + str(f.js("return document.documentElement.scrollWidth")))
    # Cancel on the code step goes back to the choices.
    check(f.click("#main .auth-form button", "Cancel"), "long-address: the code step has Cancel")
    check(bool(f.wait("return !document.querySelector('#main .auth-form') && "
                      "!!document.querySelector('#main button.line-btn')", 5)),
          "long-address: Cancel closes the form and shows LINE again")
    f.click("button", "Use your email instead")
    f.type("input[name=email]", address)
    after = time.time() - 1
    f.click("button", "Send a code")
    code = run.code_for(address, after)
    f.type("input[name=code]", code or "")
    f.click("#main .auth-form button[type=submit]")
    check(run.on_list(f, "Nok"), "long-address: the code signs Nok in")
    f.click("#devices-btn")
    check(f.sees(address), "long-address: Your devices lists the address")
    check(f.fits(), "long-address: Your devices fits 360 px: " + str(f.js("return document.documentElement.scrollWidth")))


def stopped(run):
    fon = run.invite("Fon")
    g = run.browser("stopped-g")
    run.english(g)
    check(run.signed_in_with_line(g, fon, run.line_user("Fon LINE")), "stopped: Fon signs in")
    run.admin("PATCH", f"/api/admin/readers/{fon['id']}", {"active": False})
    g.go(run.url + "/")
    check(g.sees("Your access to the site is stopped."), "stopped: the stopped screen shows: " + g.flat()[:120])
    check(g.click("#main button", "Try again"), "stopped: the screen has Try again")
    check(g.sees("Your access to the site is stopped."), "stopped: still stopped, the screen stays")
    run.admin("PATCH", f"/api/admin/readers/{fon['id']}", {"active": True})
    g.click("#main button", "Try again")
    check(run.on_list(g, "Fon"), "stopped: Try again opens the chapter list once Fon is let back in")


def blocked(run):
    # A browser that keeps no data cannot keep the choice of English either, so the screen shows the page's default
    # language, Thai: each check takes the line in either language, read from web/ui-strings.json.
    words = json.loads((BUILD / "web" / "ui-strings.json").read_text(encoding="utf-8"))
    said = [words["blocked"][lang] for lang in ("en", "th") if words["blocked"][lang]]
    again = [words["retry_load"][lang] for lang in ("en", "th") if words["retry_load"][lang]]
    chai = run.invite("Chai")
    h = run.browser("blocked-h", 'user_pref("network.cookie.cookieBehavior", 2);\n')
    h.go(run.link(chai["code"]))
    check(bool(h.wait("const e = document.querySelector('#main'); return !!e && "
                      "arguments[0].some(w => e.innerText.indexOf(w) >= 0);", 15, said)),
          "blocked: the screen names what blocks, in English or Thai: " + h.flat()[:200])
    check(bool(h.js("return Array.from(document.querySelectorAll('#main .row button')).some(b => "
                    "arguments[0].indexOf(b.textContent) >= 0)", again)), "blocked: the screen has Try again")
    h.js("window.__before = 1;")
    h.click("#main .row button")
    check(bool(h.wait("return window.__before === undefined && !!document.querySelector('#main .row button')", 10)),
          "blocked: Try again loads the page again, which shows the screen again")


def spent_link(run):
    anan = run.invite("Anan")
    i = run.browser("spent-i")
    run.english(i)
    check(run.signed_in_with_line(i, anan, run.line_user("Anan LINE")), "spent-link: Anan signs in")
    j = run.browser("spent-j")
    run.english(j)
    j.go(run.link(anan["code"]))
    check(j.sees("This link was already used to sign in. Sign in with the same LINE account or email address."),
          "spent-link: the line says what to do: " + j.flat()[:200])
    check("The first time, open the personal link" not in j.text(), "spent-link: the lead that sends in a circle is gone")
    check(bool(j.js("return !!document.querySelector('#main button.line-btn')")), "spent-link: LINE is offered")


PARTS = {"old-link": old_link, "closed-join": closed_join, "not-now": not_now, "long-address": long_address,
         "stopped": stopped, "blocked": blocked, "spent-link": spent_link}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--keep", action="store_true", help="keep $TMPDIR/reader-browser after the run")
    ap.add_argument("parts", nargs="*", help="the parts to run (default all): " + ", ".join(PARTS))
    a = ap.parse_args()
    tmp = Path(os.environ.get("TMPDIR", "/tmp")) / "reader-browser"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    run = Run(tmp)
    try:
        for name in a.parts or PARTS:
            print(f"--- {name}", flush=True)
            try:
                PARTS[name](run)
            except Exception as e:     # a part that breaks is a failure; the others still run
                check(False, f"{name}: {type(e).__name__}: {e}")
        errors = run.errors()
        for line in errors[:20]:
            print("   " + line[:300], flush=True)
        check(not errors, f"no script error or CSP refusal in the browsers' logs ({len(errors)})")
    finally:
        run.close()
        if not a.keep:
            shutil.rmtree(tmp, ignore_errors=True)
    print("PASS" if not FAILS else f"FAIL: {len(FAILS)} checks failed", flush=True)
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
