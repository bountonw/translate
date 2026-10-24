"""The content model of a published paragraph, shared by the parsers and the server.

A parser returns each paragraph as {"a", "text", "fn", "en"}: a is the anchor
("SC 9.1"), text the paragraph in the book's language (books.json "language":
th Thai, lo Lao, ium Mien) as HTML, fn its footnotes as a list of HTML strings,
en the English source as HTML. The HTML may hold only these tags, written
exactly so:

    <em> <strong> <i> <b> <sup> <sub> <p> <br> <span>, each with an optional class="..."
    and their closing tags; class holds lower-case words such as "fn" or "verse".

A marked span is reserved for later features, such as a Bible reference or a
glossary term. It carries what it marks in data-kind and, if needed, a value:

    <span data-kind="bible" data-value="John 3:16">ยอห์น 3:16</span>
    <span class="term" data-kind="glossary" data-value="grace">พระคุณ</span>

data-kind is a lower-case word; data-value is at most 200 characters with no
quote mark or angle bracket (an ampersand only as &amp;). The attributes come
in the order class, data-kind, data-value. The server accepts this form now;
no parser writes it yet.
"""
import html
import re

TAGS = "em|strong|i|b|sup|sub|p|br|span"
CLASS = r'(?: class="[a-z][a-z0-9 -]{0,63}")?'
VALUE = r'(?:[^"<>&\x00-\x1f]|&amp;){0,200}'
ALLOWED_TAG = re.compile(
    rf"<(?:{TAGS}){CLASS}\s*/?>"                                          # an opening tag, or <br/>
    rf'|<span{CLASS} data-kind="[a-z][a-z0-9-]{{0,31}}"(?: data-value="{VALUE}")?>'   # a marked span
    rf"|</(?:{TAGS})>")                                                    # a closing tag
MARKED = re.compile(r'<span[^>]* data-kind="([a-z][a-z0-9-]*)"(?: data-value="([^"]*)")?>')


def safe_html(text):
    """True when text holds no tag or attribute outside the content model."""
    rest = ALLOWED_TAG.sub("", text)
    return "<" not in rest and ">" not in rest


def marks(fragment):
    """The marked spans of a fragment as (kind, value) pairs, value unescaped."""
    return [(k, html.unescape(v or "")) for k, v in MARKED.findall(fragment)]


def align_text(fragment):
    """Published HTML as the text the page shows, for sentence alignment (EXTENDING.md, "Sentence
    alignment"): footnote numbers and every tag dropped, entities decoded, and nothing else changed, so no
    line break is added for <br> and no space is trimmed. A range [start, end) counts code points in it."""
    t = re.sub(r'<sup class="fn">.*?</sup>', "", fragment)
    return html.unescape(re.sub(r"<[^>]+>", "", t))


def words_html(fragment):
    """Published HTML without its span tags, which carry no wording: two versions of a paragraph whose
    words_html is the same show the reader the same words. A marked span an annotator adds changes nothing."""
    return re.sub(r"</?span\b[^>]*>", "", fragment)


def plain(fragment):
    """Published HTML to plain text, without footnote numbers."""
    t = re.sub(r'<sup class="fn">.*?</sup>', "", fragment)
    t = re.sub(r"<br\s*/?>", "\n", t)
    t = re.sub(r"</p>\s*<p[^>]*>", "\n\n", t)
    t = re.sub(r"<[^>]+>", "", t)
    return html.unescape(t).strip()


# The pieces of published HTML as align_text() reads them: a footnote number, a tag, an entity, a run of plain
# text, and a lone "<" or "&". Every piece but the first two gives align_text() the text it unescapes to.
_PIECES = re.compile(r'<sup class="fn">.*?</sup>|<[^>]+>|&(?:#[0-9]+;?|#[xX][0-9a-fA-F]+;?|[^\t\n\f <&#;]{1,32};?)'
                     r'|[^<&]+|[<&]')
_MARK = "\ue000"   # a character of the private use area, which book text never holds


def plain_offset(fragment, at):
    """Where the character at offset `at` of align_text(fragment) stands in plain(fragment), in code points: the
    export gives a comment's `at` (counted in the reading text, without line breaks) as a place in the paragraph
    text it shows beside the comment, which has a line break for each <br> and its ends trimmed. None when `at` is
    not within the text, or the character is one that plain() leaves out."""
    if not isinstance(fragment, str) or type(at) is not int or at < 0 or _MARK in fragment:
        return None
    pos = 0
    for m in _PIECES.finditer(fragment):
        piece = m.group(0)
        if piece.startswith("<") and len(piece) > 1:
            continue
        n = len(html.unescape(piece))
        if pos + n > at:
            # Inside a run of plain text the place is exact; an entity is one character of the text.
            cut = m.start() + (at - pos if n == len(piece) else 0)
            k = plain(fragment[:cut] + _MARK + fragment[cut:]).find(_MARK)
            return k if k >= 0 else None
        pos += n
    return None
