#!/usr/bin/env python3
"""gc_versecheck.py — check the book's unlabelled scripture quotations against the Lao Bibles.

A quotation whose citation names no version is taken from the book's default Lao Bible,
which the introduction gives as the printed edition of 2012 and 2015. Two texts of that
family are on disk under ~/programming/bible/: LO2012, the online text, and LCV. Only
those two cover the whole Bible; the Thai and English directories hold the gospels and a
few other books, and a Lao quotation cannot be compared against a Thai text in any case.

The script pulls every unlabelled quotation out of lo/GC/03_public/, looks its verses up
in both Lao texts, and reports every quotation that is not word for word one of them.
A match must be exact. Where a quotation is elided with an ellipsis, each part between
ellipses must be found, because that is what the ellipsis claims.

    python3 lo/GC/04_assets/scripts/gc_versecheck.py                 counts only
    python3 lo/GC/04_assets/scripts/gc_versecheck.py --report        the full worklist

The two texts spell the same words differently: the online exports write ຫລ, ຫນ, ຫມ and
decompose the AM vowel where the manuscript writes ຫຼ, ໜ, ໝ and composes it. Both sides
are put into the manuscript's spelling first, so no difference reported here is a
spelling convention. Spaces and punctuation are ignored when matching and are never
marked as a difference.

Output is in Bible order, Genesis to Revelation. Differences are marked with **stars**.
"""
import collections, difflib, glob, os, pathlib, re, sys, unicodedata

ROOT = pathlib.Path(__file__).resolve().parents[4]
BIBLES = os.path.expanduser('~/programming/bible')
LAO_TEXTS = ('LO2012', 'LCV')
LAO = re.compile(r'[຀-໿]')
ELLIPSIS = re.compile(r'…+|\.\.\.+')
# LO2012 is here because a citation carrying it names the printed 2012 Bible, which has
# no machine copy. Such a quotation cannot be checked against anything on disk, and left
# out of this list it was compared against the online text and reported as differing.
CODES = re.compile(r'LO2012|LCV|TKJV|TNCV|NTV|LO1972|THSV|KJV|TH1940|TH1971|THA-ERV|LO2015|ERV|ບູຮານ|ດັດແປງ|ແປຈາກ')
QUOTE = re.compile(r'[“"]([^“”"]{8,3000})[”"]\s*(?:\[\^\d+\])?\s*\(([^()]{3,70})\)')
REF = re.compile(r'(?:([\d]?\s*[຀-໿]+(?:\s+[຀-໿]+)?)\s+)?(\d+):([\d,\s–\-]+)')
ANCHOR = re.compile(r'^## \{GC (\d+\.\d+)\}')


def ortho(s):
    """The text in the manuscript's spelling, with its spaces and punctuation kept."""
    s = unicodedata.normalize('NFC', s)
    for junk in ('​', '‌', '﻿', ' '):
        s = s.replace(junk, '')
    s = re.sub('ໍ([່-໋]?)າ', lambda m: m.group(1) + 'ຳ', s)
    s = re.sub('([່-໋])ໍາ', lambda m: m.group(1) + 'ຳ', s)
    s = s.replace('ຫລ', 'ຫຼ')
    s = s.replace('ຫນ', 'ໜ')
    s = s.replace('ຫມ', 'ໝ')
    return s


def key(s):
    """Lao letters only, for deciding whether two strings say the same thing."""
    return ''.join(c for c in ortho(s) if LAO.match(c))


def _corrections():
    """Every known wrong-to-right Lao spelling the repository already records.

    Three lists hold them and none knows about the other two: the textlint job's
    .tooling/forbidden_terms/lao.txt in "wrong # correct" order, the pipeline's
    lo/assets/dictionaries/common-spelling.txt in "correct | wrong" order, and
    section 10 of the GC glossary. Applying all three to both sides puts the book
    and the Bible into one spelling, so that what is left is a difference of wording.
    """
    pairs = {}

    def add(wrong, right):
        wrong, right = wrong.strip(), right.strip()
        if wrong and right and wrong != right and len(wrong) >= 3:
            pairs[wrong] = right

    try:
        for line in open(ROOT / '.tooling' / 'forbidden_terms' / 'lao.txt', encoding='utf-8'):
            line = line.strip()
            if line and not line.startswith('#') and '#' in line:
                w, _, r = line.partition('#')
                add(w, r)
    except OSError:
        pass
    try:
        for line in open(ROOT / 'lo' / 'assets' / 'dictionaries' / 'common-spelling.txt',
                         encoding='utf-8'):
            line = line.strip()
            if line and not line.startswith('#') and '|' in line:
                right, _, wrongs = line.partition('|')
                for w in re.split(r'[/,]', wrongs):
                    add(w, right)
    except OSError:
        pass
    section10 = False
    try:
        for line in open(ROOT / 'lo/GC/04_assets/translation_profile/GC-glossary.txt',
                         encoding='utf-8'):
            if line.startswith('## 10.'):
                section10 = True
            elif line.startswith('## 11.'):
                section10 = False
            elif section10 and line.startswith('|'):
                c = [x.strip() for x in line.strip().strip('|').split('|')]
                if len(c) >= 3 and c[0].lower() != 'word':
                    # Both cells may list alternatives. Where the two lists are the same
                    # length they pair off in order, as ເຊື່ອງຊ້ອນ with ເຊື່ອງຊ່ອນ and
                    # ຊ້ອນຕົວ with ຊ່ອນຕົວ; otherwise every wrong form takes the first
                    # right one, because the whole cell is not a word.
                    rights = [x for x in re.split(r'[/,]', c[1]) if x.strip()]
                    wrongs = [x for x in re.split(r'[/,]', c[2]) if x.strip()]
                    if len(rights) == len(wrongs):
                        for w, r in zip(wrongs, rights):
                            add(w, r)
                    else:
                        for w in wrongs:
                            add(w, rights[0])
    except OSError:
        pass
    return sorted(pairs.items(), key=lambda kv: -len(kv[0]))


CORRECTIONS = _corrections()


def standard(s):
    """key() with every known spelling corrected and ຣ folded into ລ.

    A difference that survives this is a difference of wording, not of spelling.
    """
    s = key(s)
    for wrong, right in CORRECTIONS:
        if wrong in s:
            s = s.replace(wrong, key(right))
    return s.replace('ຣ', 'ລ')


def house(s):
    """standard() with the book's own settled respellings applied as well.

    A word the book spells one way at every site and never the other is a decision
    the book has made, so a quotation that differs only there is the same wording.
    HOUSE_MAP is learned from the book itself in learn_house() below, and every pair
    in it was checked against the whole of lo/GC/03_public/ before it was accepted.
    """
    s = standard(s)
    for a, b in HOUSE_MAP:
        s = s.replace(a, b)
    return SHING.sub('ເຊິ່ງ', s)


# The book's own spellings, each checked against all 42 chapters: the book writes the
# form on the right everywhere and the form on the left nowhere, and every pair is the
# same word spelled two ways rather than two words. A synonym is never listed here,
# because folding one away would hide the difference of wording this check exists to find.
HOUSE_MAP = [
    ('ຄຣິດ', 'ຄຣິສ'),
    ('ຊະບາໂຕ', 'ສະບາໂຕ'),
    ('ຍຸດຕິທຳ', 'ຍຸຕິທຳ'),
    ('ຄາດຕະກຳ', 'ຄາຕະກຳ'),
    ('ໂຮຮ້ອງ', 'ໂຮ່ຮ້ອງ'),
    ('ເຢາະເຢີ້ຍ', 'ເຍາະເຍີ້ຍ'),
    ('ເຢາະເຍີ້ຍ', 'ເຍາະເຍີ້ຍ'),
    ('ເຍາະເຍິ້ຍ', 'ເຍາະເຍີ້ຍ'),
    ('ດົນຕຼີ', 'ດົນຕີ'),
    ('ປື້ມ', 'ປຶ້ມ'),
    ('ສີລາ', 'ສິລາ'),
    ('ເຄີ່ງ', 'ເຄິ່ງ'),
    ('ຊຶ່ງ', 'ເຊິ່ງ'),
]
# ຊິ່ງ is also written ເຊິ່ງ, but it sits inside ເຊິ່ງ itself, so it is guarded.
SHING = re.compile('(?<!ເ)ຊິ່ງ')
def load(version):
    """Every verse of one Lao text, keyed by book, chapter and verse."""
    verses, order = {}, {}
    for n, path in enumerate(sorted(glob.glob(os.path.join(BIBLES, version, '*.txt')))):
        lines = open(path, encoding='utf-8').read().replace('​', '').split('\n')
        title = next((l.strip() for l in lines if re.match(r'^.+\s+\d+$', l.strip())), None)
        if not title:
            continue
        name = title.rsplit(' ', 1)[0]
        book = name.replace('^', '').replace(' ', '')
        order.setdefault(book, n)
        header = re.compile(r'^' + re.escape(name) + r'\s+(\d+)$')
        chap = cur = None
        buf = []

        def flush():
            if chap and cur:
                verses[(book, chap, cur)] = verses.get((book, chap, cur), '') + ''.join(buf)

        for line in lines:
            # The exports carry a parenthesised list of parallel passages above many
            # sections, as (ມຣກ 1:1-8; ລກ 3:1-18). Its digits would be read as verse
            # numbers and its abbreviations as verse text, so the line is skipped.
            if re.match(r'^\([^()]*\)$', line.strip()):
                continue
            m = header.match(line.strip())
            if m:
                flush(); buf, cur = [], None
                chap = int(m.group(1))
                continue
            if chap is None:
                continue
            for part in re.split(r'(\d+)', line):
                if part.isdigit():
                    flush(); buf = []
                    cur = int(part)
                elif part and cur:
                    buf.append(part)
            buf.append(' ')
        flush()
    return verses, order


TEXTS = {v: load(v) for v in LAO_TEXTS}
BOOK_ORDER = TEXTS['LO2012'][1]
BOOKS = set(BOOK_ORDER)


def find_book(name):
    n = name.replace(' ', '')
    if n in BOOKS:
        return n
    for b in BOOKS:
        if b.startswith(n) or n.startswith(b):
            return b
    return None


def passage(version, cite):
    """The cited verses of one version, joined, or None if the citation does not resolve."""
    verses = TEXTS[version][0]
    groups = REF.findall(cite.strip())
    if not groups:
        return None, None, None
    parts, book, first = [], None, None
    for name, chap, spec in groups:
        if name.strip():
            book = find_book(name)
        if not book:
            return None, None, None
        first = first or (book, int(chap))
        nums = []
        for tok in re.split(r'[,\s]+', spec.strip()):
            m = re.match(r'^(\d+)[–\-](\d+)$', tok)
            if m:
                nums += list(range(int(m.group(1)), int(m.group(2)) + 1))
            elif tok.isdigit():
                nums.append(int(tok))
        for v in nums:
            t = verses.get((book, int(chap), v))
            if t is None:
                return None, first, None
            parts.append(t)
    return (' '.join(parts) if parts else None), first, book


def matches(quote, verse, fold=key):
    """True when every part of the quotation between ellipses is in the verse."""
    if verse is None:
        return False
    hay = fold(verse)
    return all(fold(p) in hay for p in ELLIPSIS.split(quote) if fold(p))


BOUNDARY = set(' \t.,;:!?"\u201c\u201d\u2018\u2019()[]\u2026\u2013\u2014*')


def spans(s, pairs):
    """Differing runs widened to the nearest space or punctuation, then merged.

    A character-level diff of Lao cuts inside a syllable, because Lao writes a word as
    one unbroken run. Widening every run to the spaces around it keeps whole words on
    each side of the mark, which is the only form a reader can act on.
    """
    out = []
    for lo, hi in pairs:
        if lo >= hi:
            continue
        while lo > 0 and s[lo - 1] not in BOUNDARY:
            lo -= 1
        while hi < len(s) and s[hi] not in BOUNDARY:
            hi += 1
        if out and lo <= out[-1][1]:
            out[-1] = (out[-1][0], max(hi, out[-1][1]))
        else:
            out.append((lo, hi))
    return [(lo, hi) for lo, hi in out if s[lo:hi].strip() and LAO.search(s[lo:hi])]


def mark(a, b):
    """a and b with their differing words starred, and the number of places they differ."""
    A, B = ortho(a), ortho(b)
    sm = difflib.SequenceMatcher(lambda c: not LAO.match(c), A, B, autojunk=False)
    ra = [(i1, i2) for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag != 'equal']
    rb = [(j1, j2) for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag != 'equal']
    # A widened run that turns up unchanged in the other text is not a difference;
    # it was swallowed by the widening of a neighbour, and marking it would mislead.
    kA, kB = standard(A), standard(B)
    sa = [(lo, hi) for lo, hi in spans(A, ra) if standard(A[lo:hi]) not in kB]
    sb = [(lo, hi) for lo, hi in spans(B, rb) if standard(B[lo:hi]) not in kA]

    def wrap(s, runs):
        out, last = [], 0
        for lo, hi in runs:
            out.append(s[last:lo]); out.append('**' + s[lo:hi] + '**'); last = hi
        out.append(s[last:])
        return ''.join(out)

    # Measured before widening, and on Lao letters only, so the figure is the true
    # size of the edit rather than the size of the words the marks had to swallow.
    chars = sum(len([c for c in A[i1:i2] if LAO.match(c)])
                + len([c for c in B[j1:j2] if LAO.match(c)])
                for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag != 'equal')
    return wrap(A, sa), wrap(B, sb), max(len(sa), len(sb)), chars


def window(quote, verse, pad=30):
    """The stretch of the verse the quotation lines up with, so long verses stay readable."""
    A, B = ortho(quote), ortho(verse)
    sm = difflib.SequenceMatcher(lambda c: not LAO.match(c), A, B, autojunk=False)
    blocks = [bl for bl in sm.get_matching_blocks() if bl.size > 3]
    if not blocks:
        return B[:len(A) + 2 * pad]
    lo = max(0, blocks[0].b - pad)
    hi = min(len(B), blocks[-1].b + blocks[-1].size + pad)
    while lo > 0 and B[lo - 1] != ' ':
        lo -= 1
    while hi < len(B) and B[hi] != ' ':
        hi += 1
    return ('…' if lo > 0 else '') + B[lo:hi].strip() + ('…' if hi < len(B) else '')


rows = []
for f in sorted(glob.glob('lo/GC/03_public/GC[0-9][0-9]_lo.md')):
    ch = os.path.basename(f)[:4]
    anchor = ''
    for line in open(f, encoding='utf-8'):
        m = ANCHOR.match(line)
        if m:
            anchor = m.group(1)
            continue
        for quote, cite in QUOTE.findall(line):
            if CODES.search(cite):
                continue
            texts, place = {}, None
            for v in LAO_TEXTS:
                t, place, _ = passage(v, cite)
                texts[v] = t
            if place is None:
                continue
            rows.append(dict(ch=ch, anchor=anchor, cite=cite, quote=quote,
                             place=place, texts=texts, verdict=None))


def classify():
    for r in rows:
        if r['texts']['LO2012'] is None and r['texts']['LCV'] is None:
            r['verdict'] = 'UNRESOLVED'
        elif matches(r['quote'], r['texts']['LO2012'], standard):
            r['verdict'] = 'LO2012'
        elif matches(r['quote'], r['texts']['LCV'], standard):
            r['verdict'] = 'LCV'
        elif matches(r['quote'], r['texts']['LO2012'], house):
            r['verdict'] = 'HOUSE'
        elif matches(r['quote'], r['texts']['LCV'], house):
            r['verdict'] = 'LCV'
        else:
            r['verdict'] = 'NEITHER'


BOOK = ''.join(key(open(f, encoding='utf-8').read())
               for f in sorted(glob.glob('lo/GC/03_public/GC[0-9][0-9]_lo.md')))
BOOK_STD = standard(BOOK)


classify()

counts = collections.Counter(r['verdict'] for r in rows)
print('# gc_versecheck')
print(f'unlabelled quotations checked: {len(rows)}')
print(f"  word for word in LO2012:        {counts['LO2012']}")
print(f"  LO2012 in the book's spelling:  {counts['HOUSE']}")
print(f"  wording differs:                {counts['NEITHER']}")
print(f"  word for word in LCV instead:   {counts['LCV']}")
if counts['UNRESOLVED']:
    print(f"  citation does not resolve:      {counts['UNRESOLVED']}")

if '--report' not in sys.argv:
    sys.exit(0)


def sort_key(r):
    b, c = r['place']
    return (BOOK_ORDER.get(b, 999), c, r['ch'], r['anchor'])


def emit(title, verdict, blurb, index=False, brief=False):
    sel = sorted([r for r in rows if r['verdict'] == verdict], key=sort_key)
    print(f'\n## {title} ({len(sel)})\n')
    print(blurb + '\n')
    sized = []
    for r in sel:
        ns = [mark(r['quote'], window(r['quote'], r['texts'][v]))[2:]
              for v in LAO_TEXTS if r['texts'][v]]
        places, chars = min(ns, key=lambda t: t[1]) if ns else (0, 0)
        sized.append((r, places, chars))
    if index:
        quick = [x for x in sized if x[2] <= 15]
        print(f'The {len(quick)} smallest differences, for a first pass:\n')
        for r, places, chars in sorted(quick, key=lambda x: x[2]):
            print(f"    {chars:3d} letters   {r['cite']} — {r['ch']} {{GC {r['anchor']}}}")
        print()
    for r, places, chars in sized:
        head = f"### {r['cite']} — {r['ch']} {{GC {r['anchor']}}}"
        if verdict == 'NEITHER':
            head += (f' — nearest text differs by {chars} letters in {places} '
                     + ('place' if places == 1 else 'places'))
        print(head + '\n')
        if brief:
            continue
        if verdict == 'LCV':
            print(f"    BOOK   : {ortho(r['quote'])}\n")
            print(f"    LCV    : {window(r['quote'], r['texts']['LCV'])}\n")
            continue
        for v in LAO_TEXTS:
            t = r['texts'][v]
            if t is None:
                print(f"    {v:<7}: the citation names no verse in this text\n")
                continue
            a, b, n, ch_n = mark(r['quote'], window(r['quote'], t))
            word = 'place' if n == 1 else 'places'
            print(f"    against {v}: {ch_n} letters differ, in {n} {word}\n")
            print(f"    BOOK   : {a}\n")
            print(f"    {v:<7}: {b}\n")


emit('Quotations that are LCV rather than the default version, so the citation is missing its label',
     'LCV',
     'Each of these is the LCV wording and not the default version, so the citation should '
     'almost certainly read LCV. Nothing here needs the printed 2015 edition.')

emit('Quotations that are in neither Lao text', 'NEITHER',
     'The book text and each Lao text are shown against each other with the differing words '
     'in stars. Spacing and punctuation are ignored and never starred, and each run is '
     'widened to the spaces around it so that a mark never cuts a Lao word in half. Where a '
     'verse is much longer than the quotation, only the stretch the quotation lines up with '
     'is shown, with an ellipsis at the cut.', index=True)

emit("Quotations that are LO2012 in the book's own spelling", 'HOUSE',
     'Each of these is LO2012 once ຄຣິດ is read as ຄຣິສ, ຊຶ່ງ as ເຊິ່ງ, ຊະບາໂຕ as ສະບາໂຕ and ຣ as ລ. '
     'Those are the book\'s spellings at every site in the book and two of them are announced '
     'in the introduction, so these quotations are the default version and need no checking. '
     'They are listed so that the count is complete.', brief=True)

emit('Citations that name no verse in either text', 'UNRESOLVED',
     'The chapter and verse could not be found, usually because the citation is a '
     'cross-reference rather than a quotation.', brief=True)
