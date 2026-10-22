"""Checks of the page's files in web/: the module list of the service worker, the imports, the words,
and the rules the page keeps for older phones and for the strict CSP."""
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
            if path.name == "refusals.js":
                for a, b in re.findall(r'\?\s*"(\w+)"\s*:\s*"(\w*)"', text):
                    keys |= {a, b} - {""}
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
                     "text_too_long", "too_large", "comment_limit", "no_comment", "slow_down"):
            self.assertIn(f'"{code}"', refusals, code)
        strings = self.strings()
        for key in ("failed_closed", "failed_paragraph", "failed_quote_required", "failed_quote_long",
                    "failed_text_required", "failed_text_long", "failed_limit", "failed_deleted", "failed_refused",
                    "wait_slow", "long_quote", "long_text", "limit_reached", "count_chars"):
            self.assertIn(key, strings)
        for key in ("failed_quote_long", "failed_text_long", "failed_limit", "long_quote", "long_text", "limit_reached"):
            self.assertIn("{n}", strings[key]["en"], key)

    def test_every_string_has_english_and_a_thai_field(self):
        for k, v in self.strings().items():
            self.assertLessEqual({"en", "th"}, set(v), k)
            self.assertTrue(v["en"], k)


if __name__ == "__main__":
    unittest.main()
