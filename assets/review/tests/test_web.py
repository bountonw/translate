"""Checks of the page's files in web/: the module list of the service worker, the imports, the words,
and the rules the page keeps for older phones and for the strict CSP; and, for every file of this folder, that no
note points to a report kept outside the repository and that no file names a person's login."""
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
MODULE_DIRS = ("core", "features")


def modules():
    """Every ES module of the page, as a path relative to web/."""
    return sorted(str(p.relative_to(WEB)) for d in MODULE_DIRS for p in (WEB / d).glob("*.js"))


def scripts():
    return [WEB / "app.js", WEB / "sw.js"] + [WEB / m for m in modules()]


def preloads():
    """The modules index.html names in modulepreload links: the one list of the page's modules."""
    return re.findall(r'<link rel="modulepreload" href="([^"]+)">', (WEB / "index.html").read_text())


def shell():
    """The files sw.js keeps: its BASE and the modules of index.html that its pattern accepts."""
    text = (WEB / "sw.js").read_text()
    base = re.findall(r'"([^"]+)"', re.search(r"const BASE = \[(.*?)\];", text, re.S).group(1))
    pattern = re.search(r"const MODULE_LINK = /(.*)/g;", text).group(1).replace("\\/", "/")
    return base + re.findall(pattern, (WEB / "index.html").read_text())


def code_only(text):
    """The text without comments and string literals, for checks of the syntax."""
    out, i, n = [], 0, len(text)
    while i < n:
        two = text[i:i + 2]
        if two == "/*":
            j = text.find("*/", i + 2)
            i = n if j < 0 else j + 2
        elif two == "//":
            i = text.find("\n", i)
            i = n if i < 0 else i
        elif text[i] in "\"'`":
            q, i = text[i], i + 1
            while i < n and text[i] != q:
                i += 2 if text[i] == "\\" else 1
            i += 1
            out.append('""')
        elif text[i] == "/" and re.search(r"[(,=:!&|?{};]\s*$", "".join(out[-20:])):
            m = re.match(r"/(\\.|\[(\\.|[^\]])*\]|[^/\\\n])+/[a-z]*", text[i:])   # a regular expression
            if m:
                out.append("/x/")
                i += m.end()
            else:
                out.append("/")
                i += 1
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


class ServiceWorkerList(unittest.TestCase):
    def test_index_names_every_module_once(self):
        self.assertEqual(sorted(preloads()), modules())
        self.assertEqual(len(preloads()), len(set(preloads())), "a module is listed twice")
        self.assertEqual(preloads()[0], "core/main.js")

    def test_shell_holds_every_module_and_page_file(self):
        expected = ["./", "app.css", "app.js", "ui-strings.json", "languages.json"] + modules()
        self.assertEqual(sorted(shell()), sorted(expected))

    def test_every_listed_file_exists(self):
        for p in shell():
            self.assertTrue((WEB / ("index.html" if p == "./" else p)).is_file(), p)

    def test_fonts_are_not_in_the_shell(self):
        self.assertFalse([p for p in shell() if p.startswith("fonts/")])


class Imports(unittest.TestCase):
    def test_every_import_resolves_to_a_listed_module(self):
        listed = set(shell())
        for m in modules():
            text = (WEB / m).read_text()
            for spec in re.findall(r'^\s*(?:import|export)\b[^;]*?from\s+"([^"]+)"|^\s*import\s+"([^"]+)"', text, re.M):
                spec = spec[0] or spec[1]
                self.assertTrue(spec.startswith("./") or spec.startswith("../"), f"{m}: {spec}")
                target = (WEB / m).parent.joinpath(spec).resolve().relative_to(WEB.resolve())
                self.assertIn(str(target), listed, f"{m} imports {spec}")

    def test_main_imports_every_core_module_and_no_feature(self):
        """Core modules are imported by main.js. A feature is named only in index.html: main.js loads each
        one with its own import(), so a feature that fails as it loads never stops the page."""
        main = (WEB / "core" / "main.js").read_text()
        for m in modules():
            if m == "core/main.js":
                continue
            rel = "./" + m.split("/", 1)[1]
            if m.startswith("features/"):
                self.assertNotIn('"../' + m + '"', main, m)
                continue
            self.assertRegex(main, r'from "' + re.escape(rel) + '"|import "' + re.escape(rel) + '"', m)
        for m in modules():
            if m.startswith("core/"):
                self.assertNotRegex((WEB / m).read_text(), r'(from|import) "\.\./features/', m)
        self.assertIn('querySelectorAll(\'link[rel="modulepreload"]\')', main)
        self.assertIn("loadFeatures(document)", main)

    def test_app_js_is_the_entry_point(self):
        html = (WEB / "index.html").read_text()
        self.assertEqual(re.findall(r"<script[^>]*>", html), ['<script src="app.js" defer>'])
        self.assertIn('import("./core/main.js")', (WEB / "app.js").read_text())


class OlderPhones(unittest.TestCase):
    """Safari for iOS 12 reads ES modules and import(), but not ?., ??, class fields or top-level await."""

    def test_no_newer_syntax(self):
        for path in scripts():
            code = code_only(path.read_text())
            self.assertNotRegex(code, r"\?\.(?!\d)", f"{path.name}: optional chaining")
            self.assertNotIn("??", code, f"{path.name}: nullish coalescing")
            self.assertNotRegex(code, r"\bclass\s+[A-Za-z_$][\w$]*\s*(extends\b[^{]*)?\{", f"{path.name}: a class, which may hold fields")
            self.assertNotRegex(code, r"^await\b", f"{path.name}: top-level await")

    def test_every_sticky_rule_names_the_older_safari_form_first(self):
        """Safari before version 13, as on iOS 12, knows position: sticky only as -webkit-sticky; without it the bar,
        with A- and A+, would scroll away with the text."""
        css = (WEB / "app.css").read_text()
        sticky = [r for r in re.findall(r"\{([^{}]*)\}", css) if re.search(r"position:\s*sticky", r)]
        self.assertTrue(sticky)
        for rule in sticky:
            self.assertRegex(rule, r"position:\s*-webkit-sticky;\s*position:\s*sticky", " ".join(rule.split())[:80])

    @unittest.skipIf(shutil.which("node") is None, "node is not installed")
    def test_every_script_parses(self):
        for path in scripts():
            r = subprocess.run(["node", "--check", str(path)], capture_output=True, text=True, timeout=60)
            self.assertEqual(r.returncode, 0, f"{path.name}: {r.stderr}")


class StrictPage(unittest.TestCase):
    def test_index_has_no_inline_code_and_no_font_preload(self):
        html = (WEB / "index.html").read_text()
        self.assertNotRegex(html, r"<script(?![^>]*\bsrc=)[^>]*>")
        self.assertNotRegex(html, r"<style\b|\sstyle=|\son\w+=")
        self.assertNotRegex(html, r'rel="preload"')        # fonts come from the registry, not from index.html

    def test_fonts_come_from_the_registry(self):
        css = (WEB / "app.css").read_text()
        self.assertNotIn("@font-face", css)
        self.assertNotIn(":lang(", css.split("*/", 1)[1])
        for path in scripts():
            self.assertNotIn("Sarabun", code_only(path.read_text()), path.name)

    def test_nothing_loads_from_another_host(self):
        for path in scripts() + [WEB / "index.html", WEB / "app.css"]:
            self.assertNotRegex(code_only(path.read_text()) if path.suffix == ".js" else path.read_text(),
                                r"(?<![\w.])(https?:)?//[\w-]+\.[\w.-]+/", path.name)


class ShowSpaces(unittest.TestCase):
    """The dots of "Show spaces" are generated content, so selecting or copying the book text gives its words only."""

    def test_the_dot_is_generated_content_that_cannot_be_selected(self):
        css = (WEB / "app.css").read_text()
        rule = re.search(r"\.sp::after\s*\{([^}]*)\}", css)
        self.assertIsNotNone(rule)
        self.assertRegex(rule.group(1), r'content:\s*"\\00B7"')
        self.assertIn("position: absolute", rule.group(1))
        self.assertIn("user-select: none", rule.group(1))
        self.assertIn("pointer-events: none", rule.group(1))

    def test_the_span_holds_the_space_itself(self):
        dom = (WEB / "core" / "dom.js").read_text()
        self.assertIn('h("span", { class: "sp" }, " ")', dom)


class Words(unittest.TestCase):
    def strings(self):
        return json.loads((WEB / "ui-strings.json").read_text())

    def used_keys(self):
        keys = set()
        for path in scripts():
            text = path.read_text()
            keys |= set(re.findall(r'\bt\(\s*"(\w+)"', text))
            for a, b in re.findall(r'\bplural\([^,]+,\s*"(\w+)",\s*"(\w+)"', text):
                keys |= {a, b}
            keys |= set(re.findall(r'\b(?:key|hint):\s*"(\w+)"', text))
            if path.name in ("refusals.js", "auth.js", "account.js", "signin.js"):
                for a, b in re.findall(r'\?\s*"(\w+)"\s*:\s*"(\w*)"', text):
                    keys |= {a, b} - {""}
            if path.name == "auth.js":
                keys |= set(re.findall(r'\bline\(\s*"(\w+)"', text))
        langs = re.search(r"UI_LANGS = \[(.*?)\]", (WEB / "core" / "words.js").read_text()).group(1)
        keys |= {"lang_" + code for code in re.findall(r'"(\w+)"', langs)}
        return keys

    def test_every_key_the_page_uses_has_english(self):
        strings = self.strings()
        missing = sorted(k for k in self.used_keys() if not (strings.get(k) or {}).get("en"))
        self.assertEqual(missing, [])

    def test_every_refusal_has_its_own_message(self):
        refusals = (WEB / "core" / "refusals.js").read_text()
        for code in ("no_chapter", "no_paragraph", "quote_required", "quote_too_long", "text_required",
                     "text_too_long", "too_large", "comment_limit", "no_comment", "slow_down", "daily_limit",
                     "round_closed"):
            self.assertIn(f'"{code}"', refusals, code)
        strings = self.strings()
        for key in ("failed_closed", "failed_paragraph", "failed_quote_required", "failed_quote_long",
                    "failed_text_required", "failed_text_long", "failed_limit", "failed_deleted", "failed_refused",
                    "wait_slow", "wait_daily", "long_quote", "long_text", "limit_reached", "count_chars",
                    "failed_round", "wait_daily_in"):
            self.assertIn(key, strings)
        for key in ("failed_quote_long", "failed_text_long", "failed_limit", "long_quote", "long_text", "limit_reached",
                    "wait_daily"):
            self.assertIn("{n}", strings[key]["en"], key)
        self.assertIn('"wait_daily"', refusals)

    def test_dates_have_their_words(self):
        """A date is written with the keys date and months: twelve names, separated by commas."""
        strings = self.strings()
        self.assertEqual(len(strings["months"]["en"].split(",")), 12)
        self.assertTrue(set(re.findall(r"\{(\w+)\}", strings["date"]["en"])) <= {"d", "month", "y", "be"})
        if strings["months"]["th"]:
            self.assertEqual(len(strings["months"]["th"].split(",")), 12)

    def test_every_string_has_english_and_a_thai_field(self):
        for k, v in self.strings().items():
            self.assertLessEqual({"en", "th"}, set(v), k)
            self.assertTrue(v["en"], k)


class RoundThreeB(unittest.TestCase):
    """The reader page's parts of round 3b that a static check can see."""

    def test_every_request_in_link_mode_carries_the_device_key(self):
        net = (WEB / "core" / "net.js").read_text()
        self.assertIn('"X-Review-Device": deviceKey()', net)
        self.assertIn('device: "rv.device"', (WEB / "core" / "store.js").read_text())
        # A sign-in as another reader clears what the device keeps for reading, never the device key, the link
        # numbers, the outbox or the drafts.
        forget = re.search(r"export function forgetReader\(\) \{(.*?)\n\}", net, re.S).group(1)
        self.assertNotRegex(forget, r"device|links|draft|outbox")

    def test_show_spaces_sits_in_the_bar(self):
        html = (WEB / "index.html").read_text()
        bar = re.search(r'<header class="bar".*?</header>', html, re.S).group(0)
        self.assertIn('<button id="bar-spaces"', bar)
        self.assertNotIn("show_spaces", (WEB / "core" / "chapter.js").read_text())

    def test_the_english_comes_before_the_earlier_wording(self):
        order = lambda path, name: int(re.search(r'name: "' + name + r'",[^}]*?order: (\d+)', (WEB / path).read_text(), re.S).group(1))
        self.assertLess(order("features/english.js", "english"), order("core/updates.js", "earlier"))

    def test_the_page_checks_no_lifetime_limit(self):
        model = (WEB / "core" / "model.js").read_text()
        self.assertNotRegex(re.search(r"DEFAULT_LIMITS = \{(.*?)\}", model).group(1), r"\bcomments:")
        self.assertNotIn('"limit_reached"', (WEB / "core" / "refusals.js").read_text())

    def test_extending_names_every_module(self):
        text = (ROOT / "EXTENDING.md").read_text()
        side = text[text.index("### The page side"):text.index("#### A feature's page part")]
        self.assertEqual(sorted(re.findall(r"^\| ((?:core|features)/[a-z0-9_-]+\.js) \|", side, re.M)), modules())


class RoundFourA(unittest.TestCase):
    """The reader page's parts of signing in that a static check can see."""

    def test_every_request_says_it_comes_from_the_page(self):
        net = (WEB / "core" / "net.js").read_text()
        self.assertIn('const headers = { "X-Review-Page": "1" };', net)
        self.assertIn('credentials: link ? "omit" : "same-origin"', net)
        # Only api() talks to the API; getFile() fetches the page's own files without the cookies.
        for path in scripts():
            if path.name in ("net.js", "sw.js"):
                continue
            self.assertNotRegex(code_only(path.read_text()), r"\bfetch\(", path.name)

    def test_the_page_keeps_nothing_that_signs_in(self):
        """The session lives in an HttpOnly cookie: no script reads cookies, and no key of the device holds a token."""
        for path in scripts():
            self.assertNotIn("document.cookie", path.read_text(), path.name)
        keys = re.search(r"export const K = \{(.*?)\};", (WEB / "core" / "store.js").read_text(), re.S).group(1)
        self.assertNotRegex(keys, r"(?i)token|session|cookie")

    def test_a_link_code_travels_only_in_a_body(self):
        """The sign-in routes take the link's code in the body of the request (core/auth.js, startBody); the page goes
        to LINE's address as the site gives it."""
        signin = (WEB / "core" / "signin.js").read_text()
        self.assertIn("location.href = r.data.url;", signin)
        self.assertNotRegex(code_only(signin), r"api/auth/[a-z/]*\?")
        self.assertNotIn("location.href", code_only((WEB / "core" / "account.js").read_text()))

    def test_plain_modules_hold_no_dom(self):
        for name in ("auth.js", "outbox.js", "model.js", "refusals.js", "ext.js", "changes.js", "store.js", "quotes.js"):
            code = code_only((WEB / "core" / name).read_text())
            self.assertNotRegex(code, r"\b(document|window|navigator|location)\b", name)

    def test_enter_as_shows_only_on_the_dev_server(self):
        signin = (WEB / "core" / "signin.js").read_text()
        self.assertIn("S.auth.dev !== true", signin)

    def test_new_words_have_english_and_a_thai_field(self):
        strings = json.loads((WEB / "ui-strings.json").read_text())
        for key in ("welcome_title", "line_continue", "email_use", "skip_now", "signin_title", "line_link_used",
                    "line_signed_out", "line_no_account", "email_send", "code_label", "wrong_code_one", "wrong_code_many",
                    "code_used_up", "code_expired", "request_title", "request_sent", "request_waiting",
                    "request_declined", "join_closed", "stopped", "blocked", "devices_title", "this_browser", "sign_out",
                    "ways_title", "add_line", "add_email", "dev_enter", "home_hint", "home_hint_hide", "link_for",
                    "signed_in_as", "continue_as", "signin_as", "signs_out_other"):
            self.assertIn(key, strings)
            self.assertTrue(strings[key]["en"], key)
            self.assertIn("th", strings[key], key)
        for key in ("wrong_code_one", "wrong_code_many"):
            self.assertIn("{n}", strings[key]["en"], key)

    def test_english_speaks_to_the_reader_as_you(self):
        """The ruling: English interface text speaks to the reader as "you" or uses no pronoun; "My wording" is the
        one exception."""
        strings = json.loads((WEB / "ui-strings.json").read_text())
        for key, value in strings.items():
            if key == "kind_wording":
                continue
            self.assertNotRegex(value["en"], r"\b(I|me|my|mine|myself)\b", key)

    def test_a_limit_the_page_names_is_one_the_server_applies(self):
        """A comment of the page that names a constant of server/auth.py, in parentheses after the file's name, names
        one the file defines; the code button's comment names the daily limits of codes."""
        defined = set(re.findall(r"^([A-Z][A-Z0-9_]*) *=", (ROOT / "server" / "auth.py").read_text(), re.M))
        cited = set()
        for path in scripts():
            for window in re.findall(r"server/auth\.py[^)]*\)", path.read_text()):
                cited |= set(re.findall(r"\b[A-Z][A-Z0-9_]{4,}\b(?![.\w])", window))
        self.assertLessEqual({"CODES_PER_CLIENT_DAY", "CODES_PER_DAY", "RESULTS"}, cited)
        self.assertEqual(sorted(cited - defined), [])
        self.assertNotIn("five an hour", (WEB / "core" / "signin.js").read_text())


class RoundFourB(unittest.TestCase):
    """The reader page's parts of the panel, and of the screens of another reader's link, that a static check can
    see."""

    def test_the_panel_s_words_have_english_and_a_thai_field(self):
        strings = json.loads((WEB / "ui-strings.json").read_text())
        for key in ("prev_sentence", "next_sentence", "pick_words", "pick_hint", "reply", "text_smaller", "text_larger",
                    "english_beside"):
            self.assertTrue(strings[key]["en"], key)
            self.assertIn("th", strings[key], key)
        # The two-step screen for another reader's link, with the words the translator ruled for it.
        self.assertEqual(strings["continue_as"]["th"], "ดำเนินการต่อในชื่อคุณ{name}")
        self.assertEqual(strings["skip_now"], {"en": "Continue without signing in", "th": "ทำต่อโดยไม่เข้าสู่ระบบ"})
        for key in ("link_for", "signed_in_as", "continue_as", "signin_as", "signs_out_other"):
            self.assertIn("{name}", strings[key]["en"], key)
            self.assertIn("{name}", strings[key]["th"], key)

    def test_closing_the_panel_moves_nothing(self):
        """The trial ruling: nothing moves when the panel closes, so closePanel scrolls nothing."""
        panel = (WEB / "core" / "panel.js").read_text()
        body = re.search(r"export function closePanel\(\w*\) \{(.*?)\n\}", panel, re.S).group(1)
        self.assertNotRegex(code_only(body), r"scroll(By|To|IntoView)|scrollTop")
        self.assertNotIn("closeDrawer", (WEB / "core" / "para.js").read_text())

    def test_the_panel_keys_its_layout_on_the_window_s_shape(self):
        panel = (WEB / "core" / "panel.js").read_text()
        self.assertIn('const SIDE = "(min-width: 640px) and (orientation: landscape)";', panel)
        css = (WEB / "app.css").read_text()
        for rule in ("html.panel-side body.reading", ".panel.sheet", ".panel.column", "calc(1.2rem * var(--ts))",
                     ".qm.q1", ".qm.q2", ".qm.pk", ".para.was"):
            self.assertIn(rule, css, rule)

    def test_the_word_picker_says_what_it_does_without_a_segmenter(self):
        quotes = (WEB / "core" / "quotes.js").read_text()
        self.assertIn("Intl.Segmenter", (WEB / "core" / "panel.js").read_text())
        self.assertIn("a run of characters between white space", quotes)


class PanelFixes(unittest.TestCase):
    """The panel's rules of style and layout that a static check can see; tests/reader_browser.py drives the rest."""

    def css_rule(self, selector):
        css = (WEB / "app.css").read_text()
        m = re.search(r"(?m)^" + re.escape(selector) + r" \{([^}]*)\}", css)
        self.assertIsNotNone(m, selector)
        return m.group(1)

    def test_a_minus_and_a_plus_are_44_pixels_wide_and_keep_the_focus_at_the_ends(self):
        """A- and A+ at an end of the sizes are aria-disabled, not disabled, which would take the focus away."""
        self.assertIn("min-width: 44px", self.css_rule(".size-btn"))
        self.assertIn("background: none", self.css_rule('.size-btn[aria-disabled="true"]:hover'))
        self.assertNotIn(".size-btn:disabled", (WEB / "app.css").read_text())
        screens = code_only((WEB / "core" / "screens.js").read_text())
        self.assertNotRegex(screens, r"\b(down|up)\.disabled\b")
        self.assertEqual((WEB / "core" / "screens.js").read_text().count('setAttribute("aria-disabled"'), 2)

    def test_the_sheet_drags_by_its_head_too(self):
        """The head of a sheet takes the drag too, never from one of its buttons."""
        panel = (WEB / "core" / "panel.js").read_text()
        self.assertIn("wireDrag(grab, head)", panel)
        self.assertIn('closest("button")', panel)
        self.assertIn("touch-action: none", self.css_rule(".panel.sheet .panel-head"))

    def test_the_focus_ring_shows_inside_the_switches(self):
        """.faces and .lang clip what stands outside their buttons, so the focus ring is drawn inside them."""
        self.assertIn("outline-offset: -4px", self.css_rule(".face-btn:focus-visible, .lang-btn:focus-visible"))

    def test_the_note_at_the_foot_stands_in_the_middle_and_on_one_line(self):
        """The note no longer keeps to the left half of the screen, and moves left of the column only in a
        chapter."""
        rule = self.css_rule(".sync")
        self.assertNotIn("translateX", rule)
        self.assertIn("max-content", rule)
        self.assertNotIn("--panel-w", rule)
        self.assertIn("--panel-w", self.css_rule("html.panel-side body.reading .sync"))
        self.assertIn('$("sync")', (WEB / "core" / "panel.js").read_text())   # freeArea counts the note

    def test_the_column_head_meets_the_bar_and_the_bar_drops_words_beside_it(self):
        """The column's head stands level with the bar, and beside the column on a screen up to 900 pixels wide the
        bar leaves out "Chapters" and the reader's place, so the chapter's title keeps its room."""
        rule = self.css_rule(".panel.column .panel-head")
        self.assertIn("padding-top: 0", rule)
        self.assertIn("padding-bottom: 0", rule)
        css = (WEB / "app.css").read_text()
        block = re.search(r"@media \(max-width: 900px\) \{(.*?)\n\}", css, re.S).group(1)
        self.assertIn("html.panel-side body.reading .back-word, html.panel-side body.reading .bar-place", block)

    def test_previous_and_next_follow_the_english_in_a_low_sheet(self):
        """In a sheet dragged low, Previous and Next sentence follow the English instead of covering it."""
        self.assertIn("position: static", self.css_rule(".panel.short .steps"))
        self.assertIn('el.classList.toggle("short"', (WEB / "core" / "panel.js").read_text())

    def test_the_hint_names_selecting_and_pick_words(self):
        """The hint under a chapter's title names Pick words and no longer says "select them first"."""
        strings = json.loads((WEB / "ui-strings.json").read_text())
        for key in ("hint", "hint_english"):
            self.assertIn(strings["pick_words"]["en"], strings[key]["en"], key)
            self.assertNotIn("first", strings[key]["en"], key)
            self.assertIn("th", strings[key], key)

    def test_a_closed_chapter_gives_back_the_room_of_the_column(self):
        """The message that a chapter closed gives back the room the column kept at the right."""
        chapter = (WEB / "core" / "chapter.js").read_text()
        body = re.search(r"export function showChapterMessage\(.*?\n\}", chapter, re.S).group(0)
        self.assertIn('document.body.classList.remove("reading", "beside")', body)

    def test_a_shared_english_range_names_both_pairs(self):
        """An English sentence that two Thai sentences share lights for either: quotes.js englishRanges
        (tests/core_test.js) is what sentences.js wraps and lights."""
        sentences = (WEB / "features" / "sentences.js").read_text()
        self.assertIn("wrapRanges(el, englishRanges(al), englishSpan)", sentences)
        self.assertIn('holdsPair(x.getAttribute("data-s"), i)', sentences)
        self.assertIn('"aria-describedby": "step-count"', sentences)

    def test_no_note_names_the_drawer_the_panel_replaced(self):
        for path in scripts() + [WEB / "app.css", WEB / "index.html"]:
            self.assertNotRegex(path.read_text(), r"(?i)drawer", path.name)


def folder_texts():
    """Every text file of this folder that goes with the code, as (path relative to the folder, text); compiled
    Python, fonts and the folders of Claude's own tools are left out."""
    out = []
    for path in sorted(ROOT.rglob("*")):
        rel = path.relative_to(ROOT)
        if not path.is_file() or {"__pycache__", ".claude"} & set(rel.parts) or rel.parts[:2] == ("web", "fonts"):
            continue
        if path.suffix in (".py", ".js", ".json", ".md", ".css", ".html", ".conf", ".service", ".timer", ".sql", ".txt"):
            out.append((str(rel), path.read_text(encoding="utf-8")))
    return out


class PublicFolder(unittest.TestCase):
    """Rules for every file of this folder, which is to be public in a repository of its own: a note gives its reason
    in plain words, and no file names a person."""

    # A report of the build kept outside the repository: its file name (two digits, a hyphen and a name, with .md or
    # another ending), the number of one of its findings (ADV, SEC, OPS or UX, the round, a hyphen and a number), or
    # one of its items or sections by number alone. The pattern and its examples are written so that this file does
    # not match it.
    REPORT = re.compile(r"\b\d{2}[a-z]?-[a-z][a-z0-9-]*\.(md|json|html|diff|patch)\b|\b(ADV|SEC|OPS|UX)\d+-\d+\b|"
                        r"\bround3-pla[n]\b|\b(readme|ui)-rulings\b|review-build-report[s]|\b[Ii]tems? \d|\bspec \d")

    def test_the_pattern_finds_a_report(self):
        n, item, spec = "82", "item", "spec"
        for text in (f"see {n}-fixes.md", f"(46 ADV3-{n})", f"(48 UX3-{n})", f"{n}b-thai-strings-12.md {item} 4",
                     f"the stopped screen ({item} 5)", f"# {item.title()} 2: SPF", f"refused the cookie ({spec} 3.L)"):
            self.assertRegex(text, self.REPORT, text)
        for text in ("assets/read-through.md section 2", "deploy/DEPLOY.md", "SC01-08", "review-site.conf"):
            self.assertNotRegex(text, self.REPORT, text)

    def test_no_note_points_to_a_report_outside_the_repository(self):
        found = [f"{rel}:{n}" for rel, text in folder_texts() for n, line in enumerate(text.splitlines(), 1)
                 if self.REPORT.search(line)]
        self.assertEqual(found, [])

    def test_an_ssh_address_names_no_person_s_login(self):
        """The live site is written ssh://USER@HOST; an example names the login "translator", and the tests use the
        made-up logins tester, a:b and -l, the last two refused."""
        users = {u for _, text in folder_texts() for u in re.findall(r"ssh://([A-Za-z0-9._:\[-]+)@", text)}
        self.assertIn("translator", users)
        self.assertLessEqual(users, {"USER", "[USER", "translator", "tester", "a:b", "-l"})


if __name__ == "__main__":
    unittest.main()
