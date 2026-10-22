"""Character rules shared by the server and the parsers.

invisible(ch) names every character a reader cannot see: format and control
characters (newline and tab excepted), private-use, surrogate and unassigned
code points, line and paragraph separators, variation selectors, tag
characters, and a few blank letters such as the Hangul fillers. Reader text
loses them; published book text that holds one, or a Thai or Lao digit, is
refused. Thai and Lao vowel and tone marks are category Mn and are kept.
"""
import unicodedata

HIDDEN_CATEGORIES = {"Cf", "Cc", "Co", "Cs", "Cn", "Zl", "Zp"}
# Visible-looking nothing: grapheme joiner, Hangul fillers, Khmer inherent vowels, Mongolian selectors.
HIDDEN_CHARS = {0x034F, 0x115F, 0x1160, 0x17B4, 0x17B5, 0x180B, 0x180C, 0x180D, 0x180E, 0x180F, 0x3164, 0xFFA0}
KEEP = {"\n", "\t"}
# Thai digits U+0E50-0E59 and Lao digits U+0ED0-0ED9, with their Western values.
DIGITS = {0x0E50 + i: str(i) for i in range(10)} | {0x0ED0 + i: str(i) for i in range(10)}


def invisible(ch):
    """True for a character that shows nothing on the page (newline and tab excepted)."""
    if ch in KEEP:
        return False
    o = ord(ch)
    return (unicodedata.category(ch) in HIDDEN_CATEGORIES or o in HIDDEN_CHARS
            or 0xFE00 <= o <= 0xFE0F or 0xE0100 <= o <= 0xE01EF)


def strip_invisible(text):
    return "".join(c for c in text if not invisible(c))


def forbidden_char(text):
    """The first character that published book text must not hold, or None."""
    for c in text:
        if invisible(c) or ord(c) in DIGITS:
            return c
    return None
