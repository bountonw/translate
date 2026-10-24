"""The reader's page in headless Firefox at phone width, against a dev server of this folder under $TMPDIR.

    python3 tests/reader_browser.py [--keep]

It runs the dev server in this process, with the stand-in for LINE and the file mailer (server/dev.py), on a data
folder under $TMPDIR/reader-browser, and drives Firefox through Marionette, Firefox's own remote control, with
real clicks and key presses, in a window 360 pixels wide unless a part says otherwise. It checks the screens of
signing in that need a browser, and the paragraph's panel on the chapter of tests/panel_chapter.json, which has real
Thai and English with their sentence pairs:

    old-link     an old personal link opens the chapter list on a browser signed in, and the sign-in screen on
                 another, where LINE signs the reader in
    closed-join  a general link that takes no more requests shows the sign-in screen with its line, and the
                 person approved signs in there
    other-reader another reader's link asks first "Continue as" the reader signed in or "Sign in as" the link's
                 reader; "Continue as" keeps the reader signed in
    long-address a long email address keeps the code screen and "Your devices" within the phone's width, and the
                 code step has Cancel
    stopped      the stopped screen's "Try again" opens the chapter list once the reader is let back in
    blocked      a browser that blocks the site's data names the setting and has "Try again"
    spent-link   a used link's sign-in screen says what to do without the lead that says to open the link
    panel-phone  the sheet on a phone held upright, 360 by 740: a tapped sentence and its English lit, the text
                 moved only to uncover it, the heights, Pick words, Save, Close moving nothing, Next sentence, the
                 dragged height, A- and A+, and a resting selection that opens the comment box
    panel-sideways   the column on a phone held sideways, 740 by 380: the reading column never moves
    panel-computer   the column on a computer, 1280 by 800, and the English beside each paragraph
    panel-no-english a reader with English off gets the comment box alone
    panel-reading    the words the panel keeps in view (picked words, a selection, A- and A+, the line read, the
                     offline note), the sheet after typing, a low sheet, the drag by the head, a shared English
                     sentence, a pick in another paragraph, and picks on the right edge of a word's last letter,
                     on a tone mark and on the middle of a letter
    panel-keys       the panel from the keyboard on a computer, and the note in the middle
    panel-resize     a turn of the screen and a resize while typing
    panel-versions   the earlier wording kept open, a new version drawn on Close, and a chapter that closes with
                     its panel open; it publishes versions of SC03 and withdraws SC02, so it
                     runs last

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
TAB, ENTER, SHIFT, ESCAPE = "\ue004", "\ue007", "\ue008", "\ue00c"   # WebDriver's keys
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
    """Headless Firefox driven through Marionette: navigation, scripts, and trusted clicks and key presses. size is
    the page's width and height in pixels, a phone's by default."""

    def __init__(self, folder, prefs="", size=(WIDTH, HEIGHT)):
        self.width, self.height = size
        self.port = free_port()
        folder.mkdir(parents=True)
        (folder / "user.js").write_text(PREFS % self.port + prefs)
        self.log = folder.parent / (folder.name + ".log")
        self.logf = open(self.log, "w")
        self.proc = subprocess.Popen(["firefox", "--headless", "--no-remote", "--marionette", "-remote-allow-system-access",
                                      "--profile", str(folder),
                                      f"--window-size={self.width + 200},{self.height + 100}", "about:blank"],
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
        """The page's own size is self.width by self.height pixels, as a phone's: Firefox's window cannot be that
        narrow, so the browser element inside it is."""
        self.cmd("Marionette:SetContext", {"value": "chrome"})
        self.js("let b = gBrowser.selectedBrowser; for (const el of [b, b.parentNode]) { el.style.maxWidth = '%dpx'; "
                "el.style.minWidth = '%dpx'; el.style.width = '%dpx'; el.style.flex = 'none'; "
                "el.style.maxHeight = '%dpx'; el.style.minHeight = '%dpx'; el.style.height = '%dpx'; }"
                % ((self.width,) * 3 + (self.height,) * 3))
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

    def tap_at(self, x, y):
        """A trusted click at a point of the page's window, as a finger's tap lands."""
        self.cmd("WebDriver:PerformActions", {"actions": [{"type": "pointer", "id": "finger", "parameters": {"pointerType": "mouse"},
                                                           "actions": [{"type": "pointerMove", "x": int(x), "y": int(y), "origin": "viewport"},
                                                                       {"type": "pointerDown", "button": 0},
                                                                       {"type": "pointerUp", "button": 0}]}]})
        self.cmd("WebDriver:ReleaseActions")

    def keys(self, *keys):
        """Trusted key presses, each pressed and let go in turn; a tuple presses its keys together, as
        (SHIFT, TAB)."""
        actions = []
        for k in keys:
            group = k if isinstance(k, tuple) else (k,)
            actions += [{"type": "keyDown", "value": x} for x in group]
            actions += [{"type": "keyUp", "value": x} for x in reversed(group)]
        self.cmd("WebDriver:PerformActions", {"actions": [{"type": "key", "id": "keyboard", "actions": actions}]})
        self.cmd("WebDriver:ReleaseActions")
        time.sleep(0.3)

    def resize(self, width, height):
        """Give the page another size, as a window resized or a phone turned: the page gets its resize event."""
        self.width, self.height = width, height
        self.narrow()
        self.wait("return innerWidth === arguments[0] && innerHeight === arguments[1]", 5, width, height)
        time.sleep(0.5)

    def offline(self, on):
        """Take the browser off the network, or bring it back, as a phone that loses its signal."""
        self.cmd("Marionette:SetContext", {"value": "chrome"})
        self.js("Services.io.offline = arguments[0];", bool(on))
        self.cmd("Marionette:SetContext", {"value": "content"})
        time.sleep(0.3)

    def refresh(self):
        """Make the page ask for the chapter list again now, as it does when it becomes visible a minute after it
        last asked: the page's clock moves two minutes on, and the page hears that it became visible. A test
        script's import() would load a second copy of the page's modules, which shares nothing with the page."""
        self.js("window.Date.now = (now => () => now() + 120000)(window.Date.now); "
                "document.dispatchEvent(new Event('visibilitychange'));")
        time.sleep(1.5)

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
                       "window.innerWidth <= arguments[0] + 0.5;", self.width)

    def shot(self, path):
        """A picture of the page as it shows now, for a person to look at."""
        import base64
        data = self.cmd("WebDriver:TakeScreenshot", {"full": False, "hash": False})
        Path(path).write_bytes(base64.b64decode(data))

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
        # The chapter of the panel's parts: five paragraphs of SC with their English and sentence pairs.
        ch = json.loads((BUILD / "tests" / "panel_chapter.json").read_text(encoding="utf-8"))
        status, _ = self.admin("PUT", "/api/admin/chapters/SC/SC03", dict(ch, n=3, commit="abc1234",
                                                                          book_title_en="Steps to Christ", language="th"))
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

    def browser(self, name, prefs="", size=(WIDTH, HEIGHT)):
        ff = Firefox(self.tmp / f"profile-{name}", prefs, size)
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
    check(c.sees("Ask to join the proofreading", css="#main h1"), "closed-join: the general link asks to join")
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


def other_reader(run):
    mali = run.invite("Mali")
    dao = run.invite("Dao")
    e = run.browser("other-e")
    run.english(e)
    check(run.signed_in_with_line(e, mali, run.line_user("Mali LINE")), "other-reader: Mali signs in with LINE")
    e.go(run.link(dao["code"]))
    check(e.sees("This link is for Dao", css="#main h1") and e.sees("This browser is signed in as Mali."),
          "other-reader: step one says whose link it is and who is signed in: " + e.flat()[:160])
    check(not e.js("return !!document.querySelector('#main button.line-btn')"), "other-reader: step one has no LINE button")
    e.click("#main .auth-choices button", "Continue as Mali")
    check(run.on_list(e, "Mali"), "other-reader: Continue as Mali keeps Mali signed in and opens her chapter list")
    check(e.js("return localStorage.getItem('rv.code')") is None, "other-reader: the device keeps no link of Dao's")
    e.go(run.url + "/")
    check(run.on_list(e, "Mali"), "other-reader: the plain address still opens Mali's chapter list")
    check(bool(e.js("return !!document.querySelector('#devices-btn')")), "other-reader: Your devices is there for Mali")
    # The second pass: "Sign in as Dao" shows the welcome screen, which says that Mali is signed out on this browser.
    e.go(run.link(dao["code"]))
    e.click("#main .auth-choices button", "Sign in as Dao")
    check(e.sees("Welcome, Dao", css="#main h1") and e.sees("When you sign in, Mali is signed out on this browser.")
          and bool(e.js("return !!document.querySelector('#main button.line-btn')")),
          "other-reader: Sign in as Dao shows the welcome screen with LINE: " + e.flat()[:200])
    check(e.click("button.skip-btn", "Continue as Mali") and run.on_list(e, "Mali"),
          "other-reader: the welcome screen's small button keeps Mali signed in")
    # A browser signed in as nobody: Dao's link alone still works, so its small button goes on without signing in.
    f = run.browser("other-f")
    run.english(f)
    f.go(run.link(dao["code"]))
    check(f.sees("Welcome, Dao", css="#main h1") and f.click("button.skip-btn", "Continue without signing in")
          and run.on_list(f, "Dao"), "other-reader: Continue without signing in opens Dao's chapter list with the link")


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


# ---------- the paragraph's panel ----------

PANEL = """const p = document.getElementById('panel'), r = p && !p.hidden ? p.getBoundingClientRect() : null;
  const bar = document.getElementById('bar').getBoundingClientRect().bottom;
  const lit = Array.from(document.querySelectorAll('#main .para-text .al-s.hl')).map(x => x.getBoundingClientRect());
  const en = document.querySelector('#panel .face-en .al-e.hl'), body = document.querySelector('#panel .panel-body');
  const q = document.querySelector('#panel input[name=quote]');
  return {open: !!r, cls: p ? p.className : '', top: r ? r.top : null, h: r ? r.height : 0, left: r ? r.left : null,
    area: innerHeight - bar, y: scrollY, para: (document.querySelector('#main .para.open') || {}).id || null,
    face: (document.querySelector('#panel .face-btn[aria-pressed=true]') || {}).getAttribute ?
      document.querySelector('#panel .face-btn[aria-pressed=true]').getAttribute('data-face') : null,
    litTop: lit.length ? Math.min(...lit.map(x => x.top)) : null, litBottom: lit.length ? Math.max(...lit.map(x => x.bottom)) : null,
    enLit: en ? en.getBoundingClientRect().top - body.getBoundingClientRect().top : null,
    quote: q ? q.value : null, at: q && q.dataset.at !== undefined ? Number(q.dataset.at) : null};"""

# The reading text of a paragraph, as the page and the server count it: its text without footnote numbers.
READING = """const bt = document.querySelector('.para[data-a="' + arguments[0] + '"] .para-text > .bt');
  const w = document.createTreeWalker(bt, NodeFilter.SHOW_TEXT); let out = '';
  for (let n = w.nextNode(); n; n = w.nextNode()) if (!n.parentNode.closest('sup.fn')) out += n.data;
  return out;"""


# The box on the screen of the characters from arguments[1] to arguments[2] of a paragraph's reading text, all in
# one text node: [left, top, right, bottom].
BOX = """const bt = document.querySelector('.para[data-a="' + arguments[0] + '"] .para-text > .bt');
  const w = document.createTreeWalker(bt, NodeFilter.SHOW_TEXT); let pos = 0;
  for (let n = w.nextNode(); n; n = w.nextNode()) {
    if (n.parentNode.closest('sup.fn')) continue;
    const cs = Array.from(n.data);
    if (arguments[1] < pos + cs.length) {
      const r = document.createRange();
      r.setStart(n, cs.slice(0, arguments[1] - pos).join('').length);
      r.setEnd(n, cs.slice(0, arguments[2] - pos).join('').length);
      const b = r.getClientRects()[0];
      return [b.left, b.top, b.right, b.bottom];
    }
    pos += cs.length;
  }
  return null;"""


def sentence(a, i):
    return f'.para[data-a="{a}"] .para-text .al-s[data-value="{i}"]'


def bring(ff, css, part):
    """Scroll the page so that the top of css stands at this part of the window's height."""
    ff.js("const e = document.querySelector(arguments[0]); window.scrollBy(0, e.getBoundingClientRect().top - "
          "innerHeight * arguments[1]);", css, part)
    time.sleep(0.3)


def tap(ff, css, dx=18, dy=10):
    """A tap inside the first box of css, dx and dy pixels from its top left corner."""
    r = ff.js("const r = document.querySelector(arguments[0]).getClientRects()[0]; return [r.left, r.top, r.right];", css)
    ff.tap_at(min(r[0] + dx, r[2] - 4), r[1] + dy)
    time.sleep(0.5)


def panel(ff):
    return ff.js(PANEL)


def near(x, y, slack=3):
    return x is not None and y is not None and abs(x - y) <= slack


def drag(ff, dy, css="#panel .grab-zone"):
    """Drag the sheet by css (its bar, or a place on its head) dy pixels down (up when negative), with mouse events,
    as tests cannot move a finger."""
    ff.js("""const g = document.querySelector(arguments[1]), r = g.getBoundingClientRect();
      const ev = (t, y) => (t === 'mousedown' ? g : document).dispatchEvent(new MouseEvent(t, {bubbles: true, clientX: r.left + 20, clientY: y}));
      ev('mousedown', r.top + 5); ev('mousemove', r.top + 5 + arguments[0] / 2); ev('mousemove', r.top + 5 + arguments[0]);
      ev('mouseup', r.top + 5 + arguments[0]);""", dy, css)
    time.sleep(0.3)


def bar_bottom(ff):
    return ff.js("return document.getElementById('bar').getBoundingClientRect().bottom")


def press_in_place(ff, css):
    """A tap on css where it stands, without scrolling it into view first as ff.click does."""
    r = ff.js("const r = document.querySelector(arguments[0]).getBoundingClientRect(); return [r.left + r.width / 2, "
              "r.top + r.height / 2];", css)
    ff.tap_at(*r)
    time.sleep(0.4)


def marks_of(ff, css):
    """[top, bottom] around the boxes of css on the screen, or None."""
    return ff.js("const r = Array.from(document.querySelectorAll(arguments[0])).flatMap(x => Array.from(x.getClientRects()))"
                 ".filter(x => x.height); return r.length ? [Math.min(...r.map(x => x.top)), Math.max(...r.map(x => x.bottom))]"
                 " : null;", css)


def drafts(ff):
    """The drafts this browser keeps: {key: draft}."""
    return ff.js("const out = {}; for (let i = 0; i < localStorage.length; i++) { const k = localStorage.key(i); "
                 "if (k.indexOf('rv.draft:') === 0) out[k] = JSON.parse(localStorage.getItem(k)); } return out;")


def open_panel_chapter(run, name, size, english=True, window=None):
    """A reader of the panel's chapter, signed in with the dev server's "Enter as" in a browser of this size (LINE's
    limit of 10 sign-ins a minute from one address would stop a full run), with the chapter open. window, when
    given, is the larger size the browser starts with, so that the page can be resized up to it later."""
    reader = run.invite(name, english=english)
    ff = run.browser(name.lower(), size=window or size)
    if window:
        ff.resize(*size)
    run.english(ff)
    check(ff.click("#main .dev-box button", "Enter as " + name) and run.on_list(ff, name), f"{name}: signs in")
    ff.go(run.url + "/#SC/SC03")
    check(bool(ff.wait("return document.querySelectorAll('#main .para').length === 5", 15)), f"{name}: the chapter opens")
    time.sleep(0.5)
    return ff, reader


def panel_phone(run):
    ff, reader = open_panel_chapter(run, "Upright", (360, 740))
    # A tap on a sentence low on the screen: the sheet rises at half the reading area, on the English, with the
    # sentence lit in both, and the text moves just enough to keep the sentence above the sheet.
    bring(ff, sentence("SC 18.1", 5), 0.8)
    tap(ff, sentence("SC 18.1", 5))
    st = panel(ff)
    check(st["open"] and "sheet" in st["cls"] and st["face"] == "en", "panel-phone: a sentence tap opens the sheet on the English: " + str(st))
    check(near(st["h"], round(st["area"] * 0.5), 2), f"panel-phone: the sheet rests at half the reading area ({st['h']} of {st['area']})")
    check(st["litBottom"] is not None and st["litBottom"] <= st["top"] - 7, "panel-phone: the lit sentence stands above the sheet")
    check(st["enLit"] is not None and 0 <= st["enLit"] <= 30, "panel-phone: its English is lit at the top of the panel: " + str(st["enLit"]))
    check(ff.fits(), "panel-phone: the page fits 360 px with the sheet open")
    # A tap on a sentence already above the sheet moves nothing.
    bring(ff, sentence("SC 18.1", 1), 0.2)
    y1 = ff.js("return scrollY")
    tap(ff, sentence("SC 18.1", 1))
    st = panel(ff)
    check(near(st["y"], y1, 1) and st["litTop"] is not None and st["litTop"] < st["top"],
          "panel-phone: a sentence above the sheet lights without moving the text")
    # The comment box: 62 percent, the quote box empty, the sentence still above the sheet.
    ff.click("#panel .face-btn[data-face=note]")
    time.sleep(0.4)
    st = panel(ff)
    check(st["face"] == "note" and near(st["h"], round(st["area"] * 0.62), 2) and st["quote"] == "",
          f"panel-phone: the comment box rests at 62 percent with an empty quote box ({st['h']} of {st['area']})")
    check(st["litBottom"] <= st["top"] - 7, "panel-phone: the sentence stays above the comment box")
    # Pick words: the sheet drops to a strip; two taps fill the quote box with the words from the first to the last.
    ff.click("#panel .pick-btn")
    time.sleep(0.4)
    st = panel(ff)
    check("strip" in st["cls"] and st["h"] < 120 and ff.sees("Tap the first word, then the last word.", css="#panel"),
          "panel-phone: Pick words drops the sheet to a strip with its line: " + str(st["h"]))
    bring(ff, sentence("SC 18.1", 1), 0.3)
    tap(ff, sentence("SC 18.1", 1), dx=12)
    check(bool(ff.js("return !!document.querySelector('#main .para.open .qm.pk')")), "panel-phone: the first word is marked")
    tap(ff, sentence("SC 18.1", 1), dx=150, dy=48)
    st = panel(ff)
    text = ff.js(READING, "SC 18.1")
    picked = " ".join(text[st["at"]:].split())[:len(st["quote"])] if st["at"] is not None else None
    check(st["face"] == "note" and "strip" not in st["cls"] and bool(st["quote"]) and picked == st["quote"],
          f"panel-phone: the quote box holds the picked words, which start at `at`: {st['quote']!r} at {st['at']}")
    # The text box makes the sheet whole; Save keeps the comment with its place and brings the sheet back.
    ff.click("#panel textarea[name=text]")
    time.sleep(0.3)
    st = panel(ff)
    check(near(st["h"], st["area"], 2), "panel-phone: the sheet fills the reading area while the reader types")
    room = ff.js("return parseFloat(document.getElementById('main').style.paddingBottom) || 0")
    check(room < st["area"], f"panel-phone: the whole sheet asks for no room at the chapter's foot ({room} under {st['area']})")
    ff.type("#panel textarea[name=text]", "A comment from the panel")
    at, quote = st["at"], st["quote"]
    ff.click("#panel form button[type=submit]")
    check(bool(ff.wait("return (document.querySelector('#panel .face-btn[data-face=note]') || {}).textContent.indexOf('· 1') > 0", 10)),
          "panel-phone: the comment button counts the comment")
    saved = ff.wait("const s = document.querySelector('#panel .saved-line'); return s && !s.hidden && s.textContent === 'Saved' && "
                    "s.getBoundingClientRect().top < document.getElementById('panel').getBoundingClientRect().bottom", 6)
    check(bool(saved), "panel-phone: after Save the top of the comment box says Saved")
    st = panel(ff)
    check(near(st["h"], round(st["area"] * 0.62), 2) and st["quote"] == "", "panel-phone: after Save the sheet rests again, the quote box empty")
    check(bool(ff.wait("return !!document.querySelector('#main .para.open .qm.q1') && !document.querySelector('#main .qm.pk')", 5)),
          "panel-phone: the quoted words get the soft background")
    _, ex = run.admin("GET", "/api/admin/export?reader=Upright")
    mine = [c for c in ex.get("comments", []) if c["text"] == "A comment from the panel"]
    check(len(mine) == 1 and mine[0]["at"] == at and mine[0]["quote"] == quote,
          "panel-phone: the export carries the comment's quote and at: " + str([(c["quote"], c["at"]) for c in mine]))
    # Close moves nothing, and the paragraph keeps a soft background.
    y0 = ff.js("return scrollY")
    ff.click("#panel .panel-close")
    time.sleep(0.4)
    st = panel(ff)
    check(not st["open"] and near(st["y"], y0, 1) and bool(ff.js("return document.querySelector('#p-SC-18-1').classList.contains('was')")),
          "panel-phone: Close moves nothing and the paragraph keeps its soft background")
    # A tap on a sentence opens; a second tap on the lit sentence closes, and moves nothing.
    bring(ff, sentence("SC 17.2", 0), 0.3)
    tap(ff, sentence("SC 17.2", 0))
    y0 = ff.js("return scrollY")
    tap(ff, sentence("SC 17.2", 0))
    st = panel(ff)
    check(not st["open"] and near(st["y"], y0, 1), "panel-phone: a second tap on the lit sentence closes the panel")
    # Next sentence steps through the pairs and on into the next paragraph; the focus stays on Next.
    bring(ff, sentence("SC 17.2", 11), 0.3)
    tap(ff, sentence("SC 17.2", 11))
    seen = []
    for _ in range(3):
        ff.click('#panel .step-btn[data-focus="next"]')
        time.sleep(0.4)
        seen.append(ff.js("return [document.querySelector('#main .para.open').id, document.querySelector('#panel .step-count').textContent]"))
    st = panel(ff)
    check(seen == [["p-SC-17-2", "13 / 13"], ["p-SC-18-1", "1 / 10"], ["p-SC-18-1", "2 / 10"]],
          "panel-phone: Next sentence steps into the next paragraph: " + str(seen))
    check(st["litBottom"] <= st["top"] - 7 and st["litTop"] >= ff.js("return document.getElementById('bar').getBoundingClientRect().bottom"),
          "panel-phone: the lit sentence stays in view above the sheet")
    check(ff.js("return document.activeElement && document.activeElement.getAttribute('data-focus')") == "next",
          "panel-phone: the focus stays on Next sentence")
    ff.click('#panel .step-btn[data-focus="prev"]')
    time.sleep(0.4)
    check(ff.js("return document.querySelector('#panel .step-count').textContent") == "1 / 10", "panel-phone: Previous sentence steps back")
    # The bar: dragged up, the sheet stays at that height on both faces; dragged below 15 percent, it closes.
    def drag(dy):
        ff.js("""const g = document.querySelector('#panel .grab-zone'), r = g.getBoundingClientRect();
          const ev = (t, y) => (t === 'mousedown' ? g : document).dispatchEvent(new MouseEvent(t, {bubbles: true, clientX: r.left + 20, clientY: y}));
          ev('mousedown', r.top + 5); ev('mousemove', r.top + 5 + arguments[0] / 2); ev('mousemove', r.top + 5 + arguments[0]); ev('mouseup', r.top + 5 + arguments[0]);""", dy)
        time.sleep(0.3)
    h0 = panel(ff)["h"]
    drag(-150)
    h1 = panel(ff)["h"]
    ff.click("#panel .face-btn[data-face=note]")
    time.sleep(0.3)
    h2 = panel(ff)["h"]
    check(near(h1, h0 + 150, 3) and near(h2, h1, 2), f"panel-phone: the dragged height stays for both faces ({h0}, {h1}, {h2})")
    drag(h2 - 40)
    check(not panel(ff)["open"], "panel-phone: dragged below 15 percent, the sheet closes")
    # A- and A+: the size of the text, kept on the device.
    size0 = ff.js("return parseFloat(getComputedStyle(document.querySelector('#main .para-text')).fontSize)")
    ff.click("#bar-larger")
    ff.click("#bar-larger")
    size1 = ff.js("return parseFloat(getComputedStyle(document.querySelector('#main .para-text')).fontSize)")
    check(size1 > size0 * 1.25 and ff.js("return localStorage.getItem('rv.size')") == "3",
          f"panel-phone: A+ twice makes the text larger and the device keeps it ({size0} to {size1})")
    ff.go(run.url + "/#SC/SC03")
    ff.wait("return document.querySelectorAll('#main .para').length === 5", 15)
    size2 = ff.js("return parseFloat(getComputedStyle(document.querySelector('#main .para-text')).fontSize)")
    ff.click("#bar-smaller")
    ff.click("#bar-smaller")
    size3 = ff.js("return parseFloat(getComputedStyle(document.querySelector('#main .para-text')).fontSize)")
    check(near(size2, size1, 0.5) and near(size3, size0, 0.5), "panel-phone: the size stays after a reload, and A- brings it back")
    check(ff.fits(), "panel-phone: the bar with A- and A+ fits 360 px")
    # A selection that rests in a closed paragraph opens the comment box with the words, and stays.
    bring(ff, sentence("SC 19.1", 2), 0.3)
    ff.js("""const s = document.querySelector(arguments[0]), n = s.firstChild, r = document.createRange();
      r.setStart(n, 2); r.setEnd(n, 14); const sel = getSelection(); sel.removeAllRanges(); sel.addRange(r);""", sentence("SC 19.1", 2))
    words = ff.js("return getSelection().toString()")
    check(bool(ff.wait("const p = document.getElementById('panel'); return !!p && !p.hidden && "
                       "document.querySelector('#main .para.open').id === 'p-SC-19-1'", 5)),
          "panel-phone: a resting selection opens the panel of its paragraph")
    st = panel(ff)
    text = ff.js(READING, "SC 19.1")
    check(st["face"] == "note" and st["quote"] == " ".join(words.split()) and isinstance(st["at"], int)
          and text[st["at"]:].startswith(st["quote"]),
          f"panel-phone: the comment box holds the selected words, which start at `at`: {st['quote']!r} at {st['at']}")
    check(not ff.js("return getSelection().isCollapsed"), "panel-phone: the selection stays visible")
    ff.js("document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', bubbles: true}))")
    time.sleep(0.3)
    check(not panel(ff)["open"], "panel-phone: Escape closes the panel")
    # The selected words alone are not the reader's comment: no draft keeps them, and the next comment box of the
    # paragraph starts empty.
    ff.js("getSelection().removeAllRanges()")
    time.sleep(0.8)
    kept = [d for d in drafts(ff).values() if d.get("quote") == st["quote"]]
    check(not kept, "panel-phone: a selection made only to read leaves no draft: " + str(kept))
    bring(ff, sentence("SC 19.1", 0), 0.3)
    tap(ff, sentence("SC 19.1", 0))
    ff.click("#panel .face-btn[data-face=note]")
    time.sleep(0.3)
    check(panel(ff)["quote"] == "", "panel-phone: the comment box of that paragraph starts empty again")
    ff.click("#panel .panel-close")


def panel_sideways(run):
    ff, _ = open_panel_chapter(run, "Sideways", (740, 380))
    bring(ff, sentence("SC 18.1", 4), 0.5)
    before = ff.js("const r = document.getElementById('p-SC-18-1').getBoundingClientRect(); return [r.left, r.right, scrollY];")
    tap(ff, sentence("SC 18.1", 4))
    st = panel(ff)
    after = ff.js("const r = document.getElementById('p-SC-18-1').getBoundingClientRect(); return [r.left, r.right, scrollY];")
    check(st["open"] and "column" in st["cls"] and st["face"] == "en", "panel-sideways: a sentence tap opens the column at the right")
    check(before == after, f"panel-sideways: the reading column and the text do not move ({before} and {after})")
    check(st["left"] >= after[1], "panel-sideways: the column covers none of the text")
    lines = ff.js("return [document.getElementById('bar').getBoundingClientRect().bottom, "
                  "document.querySelector('#panel .panel-head').getBoundingClientRect().bottom]")
    check(near(lines[0], lines[1], 0.5), f"panel-sideways: the line under the column's head meets the bar's line ({lines})")
    bar = ff.js("const d = id => getComputedStyle(document.getElementById(id)).display; return [d('back-word'), d('bar-place'), "
                "document.getElementById('bar-title').getBoundingClientRect().width]")
    check(bar[0] == "none" and bar[1] == "none" and bar[2] >= 110,
          f"panel-sideways: beside the column the bar drops the word Chapters and the place, so the title keeps {bar[2]:.0f} px")
    ff.click("#panel .face-btn[data-face=note]")
    ff.click("#panel .pick-btn")
    time.sleep(0.3)
    strip = ff.js("const s = document.querySelector('#panel .pick-strip').getBoundingClientRect(); return [s.top, s.height];")
    check(strip[1] > 0 and strip[0] < 120, "panel-sideways: while picking, the strip's line shows at the column's top: " + str(strip))
    ff.click("#panel .pick-cancel")
    check(ff.fits(), "panel-sideways: the page fits 740 px")
    ff.go(run.url + "/")
    ff.wait("return !!document.querySelector('.ch-row')", 15)
    check(ff.js("const b = document.getElementById('beside-btn'); return !!b && getComputedStyle(b).display === 'none'"),
          "panel-sideways: English beside the text is not offered on a screen this narrow")


def panel_computer(run):
    ff, _ = open_panel_chapter(run, "Computer", (1280, 800))
    bring(ff, sentence("SC 17.2", 3), 0.6)
    y0 = ff.js("return scrollY")
    left0 = ff.js("return document.getElementById('p-SC-17-2').getBoundingClientRect().left")
    tap(ff, sentence("SC 17.2", 3))
    st = panel(ff)
    check(st["open"] and "column" in st["cls"] and near(st["y"], y0, 1) and
          near(ff.js("return document.getElementById('p-SC-17-2').getBoundingClientRect().left"), left0, 0.5),
          "panel-computer: the column opens and nothing moves")
    check(ff.fits(), "panel-computer: the page fits 1280 px")
    ff.click("#panel .panel-close")
    ff.go(run.url + "/")
    ff.wait("return !!document.querySelector('.ch-row')", 15)
    check(ff.click("#beside-btn", "English beside the text"), "panel-computer: English beside the text is offered")
    check(ff.js("return document.getElementById('beside-btn').getAttribute('aria-pressed')") == "true", "panel-computer: the switch is on")
    ff.go(run.url + "/#SC/SC03")
    ff.wait("return document.querySelectorAll('#main .side-en').length === 5", 15)
    check(ff.js("return document.querySelectorAll('#main .para.with-side .side-en').length") == 5,
          "panel-computer: each paragraph shows its English beside it")
    tops = ff.js("const a = document.getElementById('p-SC-17-2'); return [a.querySelector('.para-text').getBoundingClientRect().top, "
                 "a.querySelector('.side-en').getBoundingClientRect().top];")
    check(abs(tops[0] - tops[1]) < 12, "panel-computer: the English stands at the top of its paragraph: " + str(tops))
    bring(ff, sentence("SC 17.2", 3), 0.5)
    tap(ff, sentence("SC 17.2", 3))
    st = panel(ff)
    lit_side = ff.js("return Array.from(document.querySelectorAll('#p-SC-17-2 .side-en .al-e.hl')).length")
    check(st["open"] and st["face"] == "note" and "one-face" in st["cls"] and lit_side > 0 and st["litTop"] is not None,
          "panel-computer: a sentence tap lights its English in place and the panel holds the comment box")
    check(not ff.js("return !!document.querySelector('#panel .steps')"), "panel-computer: no steps under the comment box")
    check(ff.fits(), "panel-computer: the page fits 1280 px side by side")


def panel_no_english(run):
    ff, _ = open_panel_chapter(run, "Plain", (360, 740), english=False)
    check(not ff.js("return !!document.querySelector('#main .al-s')"), "panel-no-english: the text has no sentence spans")
    bring(ff, "#p-SC-18-1 .para-text", 0.4)
    tap(ff, "#p-SC-18-1 .para-text", dy=40)
    st = panel(ff)
    check(st["open"] and st["face"] == "note" and "one-face" in st["cls"] and
          not ff.js("return !!document.querySelector('#panel .en')"),
          "panel-no-english: a tap opens the comment box alone, with no English")
    check(ff.js("return document.querySelector('#panel .face-btn[data-face=en]').hidden") is True,
          "panel-no-english: the panel has no English button")


def panel_reading(run):
    """The words the panel keeps in view, the sheet's behaviour and Pick words on a phone."""
    ff, _ = open_panel_chapter(run, "Reading", (360, 740))
    widths = ff.js("return ['bar-smaller', 'bar-larger'].map(i => document.getElementById(i).getBoundingClientRect().width)")
    check(min(widths) >= 44, f"panel-reading: A- and A+ are at least 44 pixels wide ({widths})")
    # Picked words lower on the screen come back above the comment box.
    bring(ff, sentence("SC 18.1", 0), 0.15)
    tap(ff, sentence("SC 18.1", 0))
    ff.click("#panel .face-btn[data-face=note]")
    ff.click("#panel .pick-btn")
    time.sleep(0.4)
    bring(ff, sentence("SC 18.1", 5), 0.7)
    tap(ff, sentence("SC 18.1", 5), dx=12)
    tap(ff, sentence("SC 18.1", 5), dx=150)
    st, pk = panel(ff), marks_of(ff, "#main .para.open .qm.pk")
    check(st["face"] == "note" and pk is not None and pk[0] >= bar_bottom(ff) and pk[1] <= st["top"] - 4,
          f"panel-reading: the picked words stand above the comment box ({pk}, sheet at {st['top']})")
    ff.click("#panel .panel-close")
    # A selection that rests while the English shows opens the comment box and stays above it.
    bring(ff, sentence("SC 18.1", 0), 0.15)
    tap(ff, sentence("SC 18.1", 0))
    bring(ff, sentence("SC 18.1", 3), 0.48)
    ff.js("""const n = document.querySelector(arguments[0]).firstChild, r = document.createRange();
      r.setStart(n, 2); r.setEnd(n, 9); getSelection().removeAllRanges(); getSelection().addRange(r);""", sentence("SC 18.1", 3))
    ff.wait("return (document.querySelector('#panel .face-btn[aria-pressed=true]') || {}).getAttribute('data-face') === 'note'", 5)
    time.sleep(0.4)
    st = panel(ff)
    sel = ff.js("const r = getSelection().getRangeAt(0).getBoundingClientRect(); return [r.top, r.bottom];")
    check(st["face"] == "note" and sel[1] <= st["top"] - 4 and sel[0] >= bar_bottom(ff),
          f"panel-reading: a resting selection stands above the comment box it opens ({sel}, sheet at {st['top']})")
    ff.js("getSelection().removeAllRanges()")
    ff.click("#panel .panel-close")
    time.sleep(0.7)   # a tap just after a selection went away is taken as taking it away (para.js)
    # A- and A+ with the panel open keep the lit sentence and its English in view.
    bring(ff, sentence("SC 18.1", 5), 0.8)
    tap(ff, sentence("SC 18.1", 5))
    for _ in range(2):
        press_in_place(ff, "#bar-larger")
    st = panel(ff)
    check(st["litTop"] >= bar_bottom(ff) and (st["litBottom"] <= st["top"] - 4 or st["litTop"] <= bar_bottom(ff) + 12)
          and st["enLit"] is not None and 0 <= st["enLit"] <= 30,
          f"panel-reading: after A+ twice the lit sentence stands above the sheet and its English at the top "
          f"({st['litTop']} to {st['litBottom']}, sheet at {st['top']}, English at {st['enLit']})")
    for _ in range(2):
        press_in_place(ff, "#bar-smaller")
    ff.click("#panel .panel-close")
    # With the panel closed, A- and A+ keep the line under the bar where it stands.
    bring(ff, sentence("SC 17.2", 6), 0.12)
    y = bar_bottom(ff) + 60
    before = ff.js("""const c = document.caretPositionFromPoint(60, arguments[0]); if (!c) return null;
      window.rbProbe = [c.offsetNode, c.offset]; const r = document.createRange(); r.setStart(c.offsetNode, c.offset);
      return r.getBoundingClientRect().top;""", y)
    where = """const c = window.rbProbe, r = document.createRange(); r.setStart(c[0], c[1]); return r.getBoundingClientRect().top;"""
    for _ in range(2):
        press_in_place(ff, "#bar-larger")
    after = ff.js(where)
    for _ in range(2):
        press_in_place(ff, "#bar-smaller")
    back = ff.js(where)
    check(before is not None and abs(after - before) < 80 and abs(back - before) < 30,
          f"panel-reading: A+ twice and A- twice keep the line read in place ({before}, then {after}, then {back})")
    # The sheet rests again once the text box loses the focus, but not after a tap on the bar made it whole.
    bring(ff, sentence("SC 18.1", 1), 0.3)
    tap(ff, sentence("SC 18.1", 1))
    ff.click("#panel .face-btn[data-face=note]")
    ff.click("#panel textarea[name=text]")
    time.sleep(0.3)
    whole = panel(ff)["h"]
    ff.js("document.activeElement.blur()")
    time.sleep(0.7)
    st = panel(ff)
    check(near(whole, st["area"], 2) and near(st["h"], round(st["area"] * 0.62), 2) and st["litBottom"] <= st["top"] - 4,
          f"panel-reading: the sheet rests again after the text box loses the focus ({whole}, then {st['h']})")
    tap_bar = """const g = document.querySelector('#panel .grab-zone'), r = g.getBoundingClientRect();
      for (const t of ['mousedown', 'mouseup']) (t === 'mousedown' ? g : document).dispatchEvent(new MouseEvent(t,
        {bubbles: true, clientX: r.left + 20, clientY: r.top + 5}));"""
    ff.js(tap_bar)
    ff.click("#panel textarea[name=text]")
    ff.js("document.activeElement.blur()")
    time.sleep(0.7)
    st = panel(ff)
    check(near(st["h"], st["area"], 2), "panel-reading: a sheet made whole by a tap on its bar stays whole")
    ff.js(tap_bar)
    time.sleep(0.3)
    ff.click("#panel .panel-close")
    # Dragged low, the English keeps its lit sentence at the top, and Previous and Next follow it.
    bring(ff, sentence("SC 18.1", 3), 0.2)
    tap(ff, sentence("SC 18.1", 3))
    st = panel(ff)
    drag(ff, st["h"] - round(st["area"] * 0.25))
    st = panel(ff)
    steps = ff.js("return getComputedStyle(document.querySelector('#panel .steps')).position")
    check("short" in st["cls"] and steps == "static" and st["enLit"] is not None and 0 <= st["enLit"] <= 30,
          f"panel-reading: in a low sheet the lit English shows at the top and the steps follow it ({st['enLit']}, {steps})")
    # Dragged by its head, outside the buttons, the sheet takes the new height.
    h0 = st["h"]
    drag(ff, -120, "#panel .panel-where")
    check(near(panel(ff)["h"], h0 + 120, 3), f"panel-reading: the sheet drags by its head ({h0} to {panel(ff)['h']})")
    drag(ff, panel(ff)["h"] - 40)
    check(not panel(ff)["open"], "panel-reading: dragged below 15 percent, the sheet closes")
    # A Thai sentence whose English another sentence shares lights that English.
    bring(ff, sentence("SC 18.2", 1), 0.3)
    tap(ff, sentence("SC 18.2", 1))
    ff.click('#panel .step-btn[data-focus="next"]')
    time.sleep(0.4)
    st = panel(ff)
    count = ff.js("return document.querySelector('#panel .step-count').textContent")
    check(count == "3 / 9" and st["enLit"] is not None and 0 <= st["enLit"] <= 30,
          f"panel-reading: {count} of SC 18.2 lights the English it shares with 1 / 9 ({st['enLit']})")
    names = ff.js("return Array.from(document.querySelectorAll('#panel .step-btn')).map(b => [b.getAttribute('aria-describedby'), "
                  "(b.querySelector('[aria-hidden=true]') || {textContent: ''}).textContent.trim()])")
    check(names == [["step-count", "‹"], ["step-count", "›"]] and ff.js("return !!document.getElementById('step-count')"),
          "panel-reading: the step buttons hide their arrows from screen readers and are described by the count: " + str(names))
    ff.click("#panel .panel-close")
    # A first tap in another paragraph while picking moves the panel there.
    bring(ff, sentence("SC 18.1", 0), 0.15)
    tap(ff, sentence("SC 18.1", 0))
    ff.click("#panel .face-btn[data-face=note]")
    ff.click("#panel .pick-btn")
    time.sleep(0.3)
    bring(ff, sentence("SC 18.2", 3), 0.35)
    tap(ff, sentence("SC 18.2", 3), dx=12)
    st = panel(ff)
    first = ff.js("return document.querySelectorAll('#p-SC-18-2 .qm.pk').length")
    check(st["para"] == "p-SC-18-2" and "strip" in st["cls"] and first > 0,
          f"panel-reading: a tap in another paragraph while picking moves the panel there ({st['para']}, {st['cls']})")
    tap(ff, sentence("SC 18.2", 3), dx=150)
    st = panel(ff)
    text = ff.js(READING, "SC 18.2")
    check(st["para"] == "p-SC-18-2" and st["face"] == "note" and bool(st["quote"]) and isinstance(st["at"], int)
          and " ".join(text[st["at"]:].split())[:len(st["quote"])] == st["quote"],
          f"panel-reading: the second tap fills that paragraph's quote box: {st['quote']!r} at {st['at']}")
    ff.click("#panel .panel-close")
    # Pick words takes the word under the finger. Thai has no spaces between words, and a tap on the right half of
    # a word's last letter puts the browser's caret where the next word starts. The first tap lands on the right
    # edge of ง, the last letter of สร้าง, and the last tap on the tone mark above ขึ้ of ขึ้น.
    text = ff.js(READING, "SC 17.1")
    at = text.index("สร้างมนุษย์ขึ้น")
    bring(ff, sentence("SC 17.1", 0), 0.15)
    tap(ff, sentence("SC 17.1", 0))
    ff.click("#panel .face-btn[data-face=note]")
    ff.click("#panel .pick-btn")
    time.sleep(0.4)
    b = ff.js(BOX, "SC 17.1", at + 4, at + 5)
    ff.tap_at(b[2] - 1, (b[1] + b[3]) / 2)
    time.sleep(0.5)
    b = ff.js(BOX, "SC 17.1", at + 11, at + 14)
    ff.tap_at((b[0] + b[2]) / 2, b[1] + (b[3] - b[1]) * 0.2)
    time.sleep(0.5)
    st = panel(ff)
    check(st["quote"] == "สร้างมนุษย์ขึ้น" and st["at"] == at,
          f"panel-reading: taps on the right edge of a word's last letter and on a tone mark pick those words: "
          f"{st['quote']!r} at {st['at']}")
    ff.click("#panel .panel-close")
    # Two taps on the middle of ร in (โรม 7:24 TNCV) pick โรม, not the number after it.
    text = ff.js(READING, "SC 19.1")
    at = text.index("(โรม 7:24 TNCV)") + 1
    b = ff.js(BOX, "SC 19.1", at + 1, at + 2)
    ff.js("window.scrollBy(0, arguments[0] - innerHeight * 0.3)", b[1])
    time.sleep(0.3)
    b = ff.js(BOX, "SC 19.1", at + 1, at + 2)
    ff.tap_at((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
    time.sleep(0.5)
    ff.click("#panel .face-btn[data-face=note]")
    ff.click("#panel .pick-btn")
    time.sleep(0.4)
    for _ in range(2):
        b = ff.js(BOX, "SC 19.1", at + 1, at + 2)
        ff.tap_at((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
        time.sleep(0.5)
    st = panel(ff)
    check(st["quote"] == "โรม" and st["at"] == at,
          f"panel-reading: two taps on the middle of a letter pick its word: {st['quote']!r} at {st['at']}")
    ff.click("#panel .panel-close")
    # Offline, the note stands on one line above the sheet, and the lit sentence above the note.
    bring(ff, sentence("SC 18.1", 5), 0.8)
    tap(ff, sentence("SC 18.1", 5))
    ff.click("#panel .face-btn[data-face=note]")
    ff.offline(True)
    ff.type("#panel textarea[name=text]", "Written without a signal")
    ff.click("#panel form button[type=submit]")
    shown = ff.wait("const s = document.getElementById('sync'); return !s.hidden && s.textContent.indexOf('Offline') >= 0", 10)
    time.sleep(0.5)
    st = panel(ff)
    note = ff.js("const r = document.getElementById('sync').getBoundingClientRect(); return [r.top, r.bottom, r.left, r.right];")
    check(bool(shown) and note[1] - note[0] < 40 and note[1] <= st["top"] and st["litBottom"] <= note[0],
          f"panel-reading: the offline note stands on one line above the sheet, and the lit sentence above it "
          f"(note {note}, sheet at {st['top']}, sentence ends at {st['litBottom']})")
    ff.offline(False)
    check(bool(ff.wait("return document.getElementById('sync').hidden", 15)), "panel-reading: back online, the comment goes out")
    ff.click("#panel .panel-close")


def panel_keys(run):
    """The panel from the keyboard on a computer, 1280 by 800, and the note at the foot in the middle."""
    ff, _ = open_panel_chapter(run, "Keys", (1280, 800))
    bring(ff, "#p-SC-17-2", 0.2)
    y0 = ff.js("return scrollY")
    ff.js("document.getElementById('p-SC-17-2').focus()")
    ff.keys(ENTER)
    st = panel(ff)
    first = ff.js("const a = document.activeElement; return [a.getAttribute('data-face'), !!a.closest('#panel')]")
    check(st["open"] and st["para"] == "p-SC-17-2" and first == ["en", True],
          f"panel-keys: Enter on a paragraph opens its panel with the focus on its first button ({first})")
    ff.keys((SHIFT, TAB))
    check(ff.js("return document.activeElement.id") == "p-SC-17-2", "panel-keys: Shift+Tab goes back to the paragraph")
    ff.keys(TAB)
    ring = ff.js("const a = document.activeElement; return [a.getAttribute('data-face'), a.matches(':focus-visible'), "
                 "getComputedStyle(a).outlineOffset]")
    check(ring[0] == "en" and near(ff.js("return scrollY"), y0, 1),
          f"panel-keys: Tab on the open paragraph goes to the panel, and the page does not scroll ({ring})")
    check(ring[1] and ring[2] == "-4px", f"panel-keys: the focus ring of English is drawn inside the button ({ring})")
    # Pick words from the keyboard waits on Cancel; Escape brings the focus back to Pick words.
    ff.js("document.querySelector('#panel .face-btn[data-face=note]').focus()")
    ff.keys(ENTER)
    ff.js("document.querySelector('#panel .pick-btn').focus()")
    ff.keys(ENTER)
    check(ff.js("return document.activeElement.classList.contains('pick-cancel')"),
          "panel-keys: Pick words pressed from the keyboard puts the focus on Cancel")
    ff.keys(ESCAPE)
    check(ff.js("return document.activeElement.classList.contains('pick-btn') && !document.body.classList.contains('picking')"),
          "panel-keys: Escape stops picking and gives the focus back to Pick words")
    # A+ at the largest size keeps the focus and says it does nothing more.
    ff.js("document.getElementById('bar-larger').focus()")
    for _ in range(4):
        ff.keys(ENTER)
    end = ff.js("const b = document.getElementById('bar-larger'); return [document.activeElement === b, "
                "b.getAttribute('aria-disabled'), localStorage.getItem('rv.size')]")
    check(end == [True, "true", "4"], f"panel-keys: A+ keeps the focus at the largest size ({end})")
    ff.js("document.getElementById('bar-smaller').focus()")
    for _ in range(3):
        ff.keys(ENTER)
    check(ff.js("return localStorage.getItem('rv.size')") == "1", "panel-keys: A- brings the usual size back")
    # The offline note stands in the middle of the reading column in a chapter, and of the screen on the list.
    ff.offline(True)
    ff.type("#panel textarea[name=text]", "Waiting for the network")
    ff.click("#panel form button[type=submit]")
    ff.wait("return !document.getElementById('sync').hidden", 10)
    mid = """const r = document.getElementById(arguments[0]).getBoundingClientRect(); return (r.left + r.right) / 2;"""
    in_chapter = [ff.js(mid, "sync"), ff.js(mid, "main")]
    ff.click("#panel .panel-close")
    ff.click("#back")
    ff.wait("return !!document.querySelector('.ch-row')", 15)
    on_list = [ff.js(mid, "sync"), ff.js(mid, "main")]
    check(near(*in_chapter, 2) and near(*on_list, 2) and ff.js("return !document.getElementById('sync').hidden"),
          f"panel-keys: the note stands in the middle of the reading column, then of the chapter list ({in_chapter}, {on_list})")
    ff.offline(False)
    ff.wait("return document.getElementById('sync').hidden", 15)


def panel_resize(run):
    """A window resized, or a phone turned, with the panel open."""
    ff, _ = open_panel_chapter(run, "Turning", (360, 740), window=(1280, 800))
    bring(ff, sentence("SC 18.1", 3), 0.3)
    tap(ff, sentence("SC 18.1", 3))
    ff.resize(1280, 800)
    ff.resize(360, 740)
    st = panel(ff)
    check(st["open"] and "sheet" in st["cls"] and st["litTop"] is not None and st["litTop"] >= bar_bottom(ff)
          and st["litTop"] < st["top"], f"panel-resize: after a turn and back the lit sentence shows ({st['litTop']}, sheet at {st['top']})")
    # Typing on a phone, then a wide window: Save leaves a column of its full width.
    ff.click("#panel .face-btn[data-face=note]")
    ff.type("#panel textarea[name=text]", "Typed while the window grew")
    ff.resize(1280, 800)
    ff.click("#panel form button[type=submit]")
    time.sleep(0.6)
    w = ff.js("return [document.getElementById('panel').getBoundingClientRect().width, "
              "document.documentElement.classList.contains('panel-side')]")
    check(w[0] > 300 and w[1], f"panel-resize: Save after the window grew leaves the column {w[0]:.0f} px wide")
    # Typing in the column, then a phone's width: the reading column takes the whole width again.
    ff.type("#panel textarea[name=text]", "Typed while the window shrank")
    ff.resize(360, 740)
    ff.click("#panel .face-btn[data-face=en]")
    time.sleep(0.6)
    st = panel(ff)
    room = ff.js("return [document.documentElement.classList.contains('panel-side'), getComputedStyle(document.body).paddingRight]")
    check("sheet" in st["cls"] and room == [False, "0px"] and ff.fits(),
          f"panel-resize: after the window shrank the panel is a sheet and no room is kept at the right ({room})")
    ff.click("#panel .panel-close")


def panel_versions(run):
    """A new version while the reader compares, waits or writes. It publishes new versions of SC03 and withdraws
    SC02, so it runs last."""
    ff, _ = open_panel_chapter(run, "Versions", (360, 740))
    ff.wait("return !JSON.parse(localStorage.getItem('rv.outbox') || '[]').some(o => o.type === 'opened')", 10)
    ch = json.loads((BUILD / "tests" / "panel_chapter.json").read_text(encoding="utf-8"))

    def publish(a, commit):
        p = next(x for x in ch["paragraphs"] if x["a"] == a)
        p["text"] = p["text"].replace("ร", "ล", 1)   # one letter for another: the sentence pairs still fit
        status, _ = run.admin("PUT", "/api/admin/chapters/SC/SC03", dict(ch, n=3, commit=commit,
                                                                        book_title_en="Steps to Christ", language="th"))
        return status in (200, 201)

    check(publish("SC 18.1", "abc1235"), "panel-versions: a new version of SC03 changes SC 18.1")
    ff.go(run.url + "/")
    ff.go(run.url + "/#SC/SC03")
    check(bool(ff.wait("const u = document.querySelector('#p-SC-18-1 .upd'); return !!u && !u.hidden", 15)),
          "panel-versions: SC 18.1 is marked as changed")
    bring(ff, sentence("SC 18.1", 2), 0.3)
    tap(ff, sentence("SC 18.1", 2))
    ff.click("#panel .earlier-btn")
    ff.wait("return !!document.querySelector('#panel .earlier-out .earlier-text')", 10)
    is_open = "return !!document.querySelector('#panel .earlier-out .earlier-text') && " \
              "document.querySelector('#panel .earlier-btn').getAttribute('aria-expanded') === 'true'"
    ff.click('#panel .step-btn[data-focus="next"]')
    time.sleep(0.4)
    after_next = ff.js(is_open)
    bring(ff, sentence("SC 18.1", 6), 0.3)
    tap(ff, sentence("SC 18.1", 6))
    check(after_next and ff.js(is_open) and panel(ff)["para"] == "p-SC-18-1",
          "panel-versions: the earlier wording stays open through Next sentence and a tap on another sentence")
    # A newer version waits while the panel is open; on Close it is drawn, and the paragraph keeps its soft background.
    check(publish("SC 17.2", "abc1236"), "panel-versions: another version changes SC 17.2")
    ff.refresh()
    check(panel(ff)["para"] == "p-SC-18-1", "panel-versions: the panel stays open while the new version waits")
    ff.click("#panel .panel-close")
    time.sleep(1)
    marked = ff.js("const u = document.querySelector('#p-SC-17-2 .upd'); return !!u && !u.hidden")
    check(marked and ff.js("return document.getElementById('p-SC-18-1').classList.contains('was')"),
          "panel-versions: on Close the new version is drawn and SC 18.1 keeps its soft background")
    # A chapter that closes while its panel is open gives back the column's room on a phone held sideways.
    g, _ = open_panel_chapter(run, "Closing", (740, 380))
    g.go(run.url + "/#SC/SC02")
    g.wait("return document.querySelectorAll('#main .para').length === 3", 15)
    time.sleep(0.4)
    tap(g, "#main .para .para-text", dy=12)
    check(panel(g)["open"], "panel-versions: the panel of SC02 is open")
    status, _ = run.admin("DELETE", "/api/admin/chapters/SC/SC02")
    check(status == 200, "panel-versions: the translator withdraws SC02")
    g.refresh()
    closed = g.wait("return document.getElementById('main').innerText.toLowerCase().indexOf('closed') >= 0", 15)
    room = g.js("return [document.body.className, getComputedStyle(document.body).paddingRight]")
    check(bool(closed) and "reading" not in room[0].split() and room[1] == "0px",
          f"panel-versions: the message that the chapter closed keeps no room for the panel ({room})")


PARTS = {"old-link": old_link, "closed-join": closed_join, "other-reader": other_reader, "long-address": long_address,
         "stopped": stopped, "blocked": blocked, "spent-link": spent_link, "panel-phone": panel_phone,
         "panel-sideways": panel_sideways, "panel-computer": panel_computer, "panel-no-english": panel_no_english,
         "panel-reading": panel_reading, "panel-keys": panel_keys, "panel-resize": panel_resize,
         "panel-versions": panel_versions}


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
