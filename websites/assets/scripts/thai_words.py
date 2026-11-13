"""Keep listed Thai words whole at the end of a line on the web pages.

A browser ends a Thai line where its own word list says a word ends, and every
browser's list cuts some words in two: Chrome's ends a line inside การกระทำ as
การก|ระ|ทำ, and Firefox's inside หิวกระหาย as หิวก|ระหาย. The Thai books keep a
list of the words print must never split, th/assets/typeset/thai-breaks.txt.
This module puts each of those words, where it stands on a page, in
<span class="w">, which the stylesheet keeps whole, as it keeps the Lao words
of lao_words.py whole. A line may end before such a word or after it, but
never inside it. A span adds no letter.

The rules are those of the review site's Thai annotator (thai_keep.py in the
review site's code), so a word breaks the same way on both sites:
- A listed word may break only where print breaks it, at each hyphen of its
  parts, as in box|พระวิญญาณบริสุทธิ์|พระ-วิญ-ญาณ-บริ-สุทธิ์; there a soft
  hyphen, &shy;, stands between two spans. A word whose parts are "none" has
  no break point. A line with a fourth cell counts only for the book it names.
- A match is refused when the letter after it is a vowel sign or tone mark, or
  when the letter before it is a vowel written before its consonant, so ทาส is
  not kept in ทาสี. Of two matches that overlap, the longer is kept.
- The words of HELD_OUT are never kept, because their letters stand across
  the boundary of two other words too often.
- กระ with the letter after it is one span wherever it stands, because
  browsers cut words that begin with กระ after their ก.
- A closing mark (” ’ … ) ] ๆ) never starts a line: it goes into one span with
  the letter before it. A verse range, as 26:36–45, is one span, and so is a
  footnote number with the letter before it.

Only the page's body is marked; the title and the head are left as they are.
The list is short, so the marking takes under a second and keeps no cache.
"""
import html
import os
import re

ASSETS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(ASSETS))
BREAKS = os.path.join(REPO, 'th', 'assets', 'typeset', 'thai-breaks.txt')

# words of the list that are never kept, as on the review site
HELD_OUT = frozenset(('กว่า', 'ทั้งมวล', 'กิจการ'))

OPEN, CLOSE = '<span class="w">', '</span>'
SOFT_HYPHEN = '&shy;'     # a place a listed word may break, as print breaks it

# A Thai word never begins with one of these: the vowel signs and tone marks written above, below or after the
# letter before them (U+0E30 to U+0E3A, U+0E45, U+0E47 to U+0E4D).
NO_START = frozenset(chr(c) for c in [*range(0x0E30, 0x0E3B), 0x0E45, *range(0x0E47, 0x0E4E)])
# A Thai word never ends with one of these: the vowels written before their consonant (U+0E40 to U+0E44).
BEFORE_VOWELS = frozenset(chr(c) for c in range(0x0E40, 0x0E45))
# The signs that belong to the letter before them: above or below it, or written after it.
AFTER_SIGNS = frozenset(chr(c) for c in [0x0E30, 0x0E31, 0x0E32, 0x0E33, *range(0x0E34, 0x0E3B), 0x0E45,
                                         *range(0x0E47, 0x0E4F)])
# The marks that never start a line: ” ’ … ) ] and ๆ (U+0E46).
CLOSING_RUN = re.compile("[\u201d\u2019\u2026)\\]\u0e46]+")
# กระ and the letter after it: a vowel written before it, the consonant, and the signs that belong to the consonant.
KRA = re.compile("\u0e01\u0e23\u0e30(?:[\u0e40-\u0e44]?[\u0e01-\u0e2e][\u0e30-\u0e3a\u0e45\u0e47-\u0e4e]*)?")
VERSE_RANGE = re.compile(r"(?<![0-9:])[0-9]+(?::[0-9]+)?[-\u2010\u2011\u2013][0-9]+(?::[0-9]+)?(?![0-9])")

TAG = re.compile(r'(<[^>]*>)')
# One character of the text as the HTML writes it: an entity such as &amp; or a single character.
UNIT = re.compile(r'&(?:#[0-9]{1,7}|#[xX][0-9a-fA-F]{1,6}|[A-Za-z][A-Za-z0-9]{0,31});|.', re.S)
# A tag after which the text starts a new line, so the letters on its two sides are not neighbours.
LINE_TAG = re.compile(r'</?(?:p|h[1-6]|li|ol|ul|div|nav|header|footer|hr)\b|<br\b', re.I)
WORD_END = ''   # the key that marks the end of a word in the tree of words below; no letter is empty


def mark(pages, code, breaks=BREAKS):
    """The pages, {name: html}, with the listed words of each page's body kept whole. code names the book, such as
    MB, for the list's lines that count for one book only."""
    tree = word_tree(open(breaks, encoding='utf-8').read(), code, breaks)
    out = {}
    for name, page in pages.items():
        head, tag, body = page.partition('<body>')
        out[name] = head + tag + keep_whole(body, tree) if tag else keep_whole(page, tree)
    return out


def word_tree(text, book_id, where):
    """The listed words, without the held-out ones, as a tree of letters: tree[letter][letter]... holds the key
    WORD_END where a word ends, with the word's break points as its value."""
    tree = {}
    for word, breaks in listed_words(text, book_id, where).items():
        if word in HELD_OUT:
            continue
        node = tree
        for letter in word:
            node = node.setdefault(letter, {})
        node[WORD_END] = breaks
    return tree


def break_points(word, parts, where):
    """The places inside word where print may break it, from its parts: พระ-วิญ-ญาณ of พระวิญญาณ gives (3, 6);
    "none" gives none."""
    if parts == 'none':
        return ()
    pieces = parts.split('-')
    if ''.join(pieces) != word or not all(pieces):
        raise SystemExit(f'{where}: the parts {parts} do not spell the word {word}')
    out, at = [], 0
    for piece in pieces[:-1]:
        at += len(piece)
        out.append(at)
    return tuple(out)


def listed_words(text, book_id, where):
    """{word: its break points} of the list for one book. Each line is kind|word|parts, with kind box or soft; "#"
    lines and blank lines are notes. A line with a fourth cell counts only for the book it names, and there it
    takes the place of the general line of its word."""
    words, own = {}, set()
    for n, line in enumerate(text.split('\n'), 1):
        s = line.strip()
        if not s or s.startswith('#'):
            continue
        cells = s.split('|')
        if len(cells) not in (3, 4) or cells[0] not in ('box', 'soft') or not cells[1] or any(c.isspace() for c in cells[1]):
            raise SystemExit(f'{where}:{n}: expected kind|word|parts or kind|word|parts|BOOK, with kind box or soft '
                             'and a word without spaces')
        if len(cells) == 4 and cells[3].upper() != book_id.upper():
            continue
        if cells[1] in own and len(cells) == 3:
            continue            # the book's own line for the word stands
        words[cells[1]] = break_points(cells[1], cells[2], f'{where}:{n}')
        if len(cells) == 4:
            own.add(cells[1])
    return words


def keep_whole(fragment, tree):
    """An HTML fragment with each listed word, each กระ with the letter after it, each closing mark with its letter,
    each verse range, and each footnote number with the letter before it in a span of class w, and a soft hyphen at
    each break point of a listed word, between two spans. Only spans and soft hyphens are added."""
    parts = TAG.split(fragment)            # text, tag, text, tag, ..., text
    for k, before, after in reading_runs(parts):
        units = UNIT.findall(parts[k])
        letters = ''.join(letter_of(u) for u in units)
        words = kept_words(letters, tree, before, after)
        breaks = {i + b for i, _, points in words for b in points}
        stretches = merged([(i, j) for i, j, _ in words] + marks_with_letters(letters)
                           + [m.span() for m in KRA.finditer(letters)]
                           + [m.span() for m in VERSE_RANGE.finditer(letters)])
        number_end = footnote_number_after(parts, k)
        if number_end is not None:
            start = last_letter_start(letters)
            if start is not None:
                stretches = merged(stretches + [(start, len(letters))])
                # The span closes after the number's </sup>, not at the end of this piece of text.
                parts[k] = wrapped(units, stretches, breaks)[:-len(CLOSE)]
                parts[number_end] += CLOSE
                continue
        if stretches:
            parts[k] = wrapped(units, stretches, breaks)
    return ''.join(parts)


def footnote_number_after(parts, k):
    """The index of the </sup> of the footnote number that stands right after the text piece k of parts, as the
    footnote extension writes it: <sup id="fnref:1"><a class="footnote-ref" href="#fn:1">1</a></sup>. None when no
    footnote number follows the piece."""
    i = k + 1
    if i >= len(parts) or not parts[i].startswith('<sup id="fnref'):
        return None
    for j in range(i + 2, len(parts), 2):     # the tags after the <sup>
        if parts[j].startswith('</sup'):
            return j
    return None


def last_letter_start(letters):
    """Where the last letter of a piece of text starts, with a vowel written before it; None when the piece ends in
    a space or holds no letter."""
    k = len(letters) - 1
    while k >= 0 and letters[k] in AFTER_SIGNS:
        k -= 1
    if k < 0 or letters[k].isspace():
        return None
    if k and letters[k - 1] in BEFORE_VOWELS:
        k -= 1
    return k


def reading_runs(parts):
    """The text pieces of parts (TAG.split of a fragment) that the reader reads, as (index, letter before, letter
    after): the letters next to each piece across inline tags such as <em>; "\\n" where a line or a block ends
    between them; "" at the ends of the fragment. The text inside <sup> is left out."""
    order, depth = [], 0          # the index of each piece read, in order, and None where a line ends
    for k, part in enumerate(parts):
        if k % 2:
            if part.startswith('<sup'):
                depth += 1
            elif part.startswith('</sup'):
                depth = max(0, depth - 1)
            elif LINE_TAG.match(part):
                order.append(None)
        elif part and not depth:
            order.append(k)
    before, last = {}, ''
    for k in order:
        if k is None:
            last = '\n'
        else:
            before[k], last = last, letter_of(UNIT.findall(parts[k])[-1])
    after, following = {}, ''
    for k in reversed(order):
        if k is None:
            following = '\n'
        else:
            after[k], following = following, letter_of(UNIT.findall(parts[k])[0])
    return [(k, before[k], after[k]) for k in order if k is not None]


def letter_of(unit):
    """The character a unit of UNIT shows: itself, or the one character its entity stands for (U+FFFD for an entity
    that is not one character, which is never a Thai letter)."""
    if len(unit) == 1:
        return unit
    c = html.unescape(unit)
    return c if len(c) == 1 else '\ufffd'


def kept_words(letters, tree, before, after):
    """The listed words found in letters as (start, end, break points): refused by the letter rule, then kept
    longest first without overlap. before and after are the letters next to this piece of text."""
    found = []
    for i in range(len(letters)):
        node, j = tree, i
        while j < len(letters) and letters[j] in node:
            node = node[letters[j]]
            j += 1
            if WORD_END in node:
                prev = letters[i - 1] if i else before
                nxt = letters[j] if j < len(letters) else after
                if nxt not in NO_START and prev not in BEFORE_VOWELS:
                    found.append((i, j, node[WORD_END]))
    taken = bytearray(len(letters))
    kept = []
    for i, j, points in sorted(found, key=lambda r: (r[0] - r[1], r[0])):
        if not any(taken[i:j]):
            taken[i:j] = b'\x01' * (j - i)
            kept.append((i, j, points))
    return kept


def marks_with_letters(letters):
    """[start, end) of each run of closing marks with the letter before it: the letter, the signs after it, and a
    vowel written before it. A run after a space, or at the start of the piece, is left out."""
    out = []
    for m in CLOSING_RUN.finditer(letters):
        k = m.start() - 1
        while k >= 0 and letters[k] in AFTER_SIGNS:
            k -= 1
        if k < 0 or letters[k].isspace():
            k += 1
        elif k and letters[k - 1] in BEFORE_VOWELS:
            k -= 1
        if k < m.start():
            out.append((k, m.end()))
    return out


def merged(ranges):
    """The ranges with each set of overlapping ones joined into one, in order. Ranges that only touch stay apart."""
    out = []
    for i, j in sorted(ranges):
        if out and i < out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], j))
        else:
            out.append((i, j))
    return out


def wrapped(units, stretches, breaks=()):
    """The units joined again, with OPEN before and CLOSE after each [start, end) of stretches, and at each place of
    breaks inside a stretch the span closed, a soft hyphen, and a span opened again."""
    starts = {i for i, _ in stretches}
    ends = {j for _, j in stretches}
    inside = {b for b in breaks if any(i < b < j for i, j in stretches)}
    out = []
    for k, unit in enumerate(units):
        if k in ends:
            out.append(CLOSE)
        if k in starts:
            out.append(OPEN)
        if k in inside:
            out.append(CLOSE + SOFT_HYPHEN + OPEN)
        out.append(unit)
    if len(units) in ends:
        out.append(CLOSE)
    return ''.join(out)
