"""The language registry, web/languages.json, as the server and review.py read it.

The page reads the same file for its fonts. Each language is keyed by its
code (th), the code books.json names. Book text may not hold a character in
every_book.refuse (the project's ban on Thai and Lao digits) or in its own
language's refuse list; text.forbidden_char applies both. In reader text the
digits among those characters become Western digits (text.DIGITS).
"""
import json
import re
import unicodedata
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "web" / "languages.json"
CODE_RE = re.compile(r"[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*")
RANGE_RE = re.compile(r"U\+([0-9A-Fa-f]{4,6})(?:-U\+([0-9A-Fa-f]{4,6}))?")


class RegistryError(ValueError):
    """web/languages.json cannot be used."""


def parse_range(text):
    """'U+0E50-U+0E59' or 'U+00AD' to (first, last) code points."""
    m = RANGE_RE.fullmatch(text) if isinstance(text, str) else None
    if not m:
        raise RegistryError(f"cannot read the range {text!r}; write U+0E50-U+0E59 or U+00AD")
    lo = int(m.group(1), 16)
    hi = int(m.group(2) or m.group(1), 16)
    if hi < lo or hi > 0x10FFFF:
        raise RegistryError(f"the range {text} runs backwards or past U+10FFFF")
    return lo, hi


def _ranges(entries, where):
    if not isinstance(entries, list):
        raise RegistryError(f"{where}.refuse must be a list")
    out = []
    for e in entries:
        if not isinstance(e, dict):
            raise RegistryError(f"{where}.refuse holds an entry that is not an object")
        out.append(parse_range(e.get("range")))
    return tuple(out)


class Registry:
    """The parsed registry: codes, names, fonts and the characters refused in book text."""

    def __init__(self, data):
        if not isinstance(data, dict) or not isinstance(data.get("languages"), dict) or not data["languages"]:
            raise RegistryError("languages.json must hold a languages object with at least one language")
        self.data = data
        self.every_book = _ranges(data.get("every_book", {}).get("refuse", []), "every_book")
        self.refuse = {}
        for code, entry in data["languages"].items():
            if not CODE_RE.fullmatch(code):
                raise RegistryError(f"{code!r} is not a language code such as th or lo")
            if not isinstance(entry, dict) or not isinstance(entry.get("name"), str) or not entry["name"]:
                raise RegistryError(f"language {code} needs a name in its own script")
            font = entry.get("font")
            if not isinstance(font, dict) or not isinstance(font.get("family"), str) \
                    or not isinstance(font.get("files"), list):
                raise RegistryError(f"language {code} needs a font with a family and its files")
            self.refuse[code] = self.every_book + _ranges(entry.get("refuse", []), f"languages.{code}")

    @property
    def codes(self):
        return sorted(self.refuse)

    def refused(self, ch, language=None):
        """True when book text in this language may not hold ch; an unknown or missing language
        applies every_book alone."""
        o = ord(ch)
        return any(lo <= o <= hi for lo, hi in self.refuse.get(language, self.every_book))

    def digits(self):
        """str.translate table: every refused digit of any language to its Western digit."""
        out = {}
        for lo, hi in set(self.every_book).union(*self.refuse.values()):
            for o in range(lo, hi + 1):
                value = unicodedata.decimal(chr(o), None)
                if value is not None:
                    out[o] = str(value)
        return out


def load(path=PATH):
    try:
        return Registry(json.loads(Path(path).read_text(encoding="utf-8")))
    except (OSError, ValueError) as e:
        if isinstance(e, RegistryError):
            raise
        raise RegistryError(f"cannot read {path}: {e}")


REGISTRY = load()
