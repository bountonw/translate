#!/usr/bin/env python3
"""gc_versemark.py — write the Bible quotation findings into the chapters as markers.

gc_versecheck.py reports every unlabelled quotation whose wording is not one of the two
Lao Bibles. Reading that report beside the manuscript is slow. This puts each finding
where it belongs, inside the quotation it is about, as an ordinary audit marker:

    [[REF MED #7|<the book's wording> -> <the Lao Bible's wording>|note]]

The marker stands in place of the span that differs, so the whole finding is settled at
the cursor: keep the left side and label the citation, take the right side, or write a
third wording. Numbering runs straight through the book from GC01, not per chapter, so
that the translator can work down one list.

    python3 lo/GC/04_assets/scripts/gc_versemark.py            what it would write
    python3 lo/GC/04_assets/scripts/gc_versemark.py --apply    write it

The right-hand side is given in the book's own spelling, not the Bible export's, so that
accepting a marker never brings a foreign spelling into the manuscript.

Run this on chapters that carry no markers. Marker text sits inside the quotations, so a
second run over a marked chapter would compare the marker against the Bible and get
nonsense. Use --undo first, which puts every marker back to its left-hand side and
leaves the chapters exactly as they were.
"""
import difflib, os, re, sys, types

HERE = os.path.dirname(os.path.abspath(__file__))

# gc_versecheck.py does its work at module level and then prints a report. Only the
# work is wanted here, so its source is run up to the point where the report begins.
_src = open(os.path.join(HERE, 'gc_versecheck.py'), encoding='utf-8').read()
vc = types.ModuleType('gc_versecheck')
vc.__file__ = os.path.join(HERE, 'gc_versecheck.py')
_argv, sys.argv = sys.argv, [sys.argv[0]]
exec(compile(_src[:_src.index('counts = collections.Counter')], vc.__file__, 'exec'), vc.__dict__)
sys.argv = _argv

APPLY = '--apply' in sys.argv

if '--undo' in sys.argv:
    # Put every marker back to its left-hand side, so the chapters return to the
    # wording they had before this script ran and it can be run again.
    import glob as _glob
    _pat = re.compile(r'\[\[REF MED #\d+\|(.*?) -> .*?\|.*?\]\]', re.S)
    _n = 0
    for _f in sorted(_glob.glob('lo/GC/03_public/GC[0-9][0-9]_lo.md')):
        _t = open(_f, encoding='utf-8').read()
        _t2, _k = _pat.subn(lambda m: m.group(1), _t)
        if _k:
            open(_f, 'w', encoding='utf-8').write(_t2)
            _n += _k
    print(f'restored {_n} markers to the book wording')
    sys.exit(0)
EDGE = ' \t“”‘’"\',.;:'


def to_book(s):
    """A Bible span written the way the book writes it."""
    s = vc.ortho(s)
    for a, b in vc.HOUSE_MAP:
        s = s.replace(a, b)
    s = vc.SHING.sub('ເຊິ່ງ', s)
    # Joining verses leaves the odd doubled space or stranded comma.
    s = re.sub(r'\s+', ' ', s)
    s = re.sub(r'\.\s*,', '.', s).replace(' ,', ',')
    return s.strip()


def tight(quote, verse):
    """The stretch of the verse the quotation actually covers, and no more.

    vc.window() pads its result so that a reader can see the context. Padding is wrong
    here, because the marker's right-hand side is text the translator may accept into
    the book, and a pad would carry in words the quotation never quoted.
    """
    v = to_book(verse)
    sm = difflib.SequenceMatcher(lambda c: not vc.LAO.match(c), quote, v, autojunk=False)
    blocks = [b for b in sm.get_matching_blocks() if b.size > 1]
    if not blocks:
        return v
    # The window is pulled back by however much of the quotation sits before its first
    # matching block, and pushed on by however much sits after the last, so that a word
    # the quotation opens or closes with is never left outside it.
    # The lead and the tail are counted in Lao letters, so that a quotation ending in
    # a full stop does not drag the verse's next clause into the window.
    lead = sum(1 for c in quote[:blocks[0].a] if vc.LAO.match(c))
    tail = sum(1 for c in quote[blocks[-1].a + blocks[-1].size:] if vc.LAO.match(c))
    lo = max(0, blocks[0].b - lead)
    hi = min(len(v), blocks[-1].b + blocks[-1].size + tail)
    while lo > 0 and v[lo - 1] not in vc.BOUNDARY:
        lo -= 1
    while hi < len(v) and v[hi] not in vc.BOUNDARY:
        hi += 1
    return v[lo:hi]


def span(book, bible):
    """The smallest stretch of each that holds every difference between them."""
    sm = difflib.SequenceMatcher(lambda c: not vc.LAO.match(c), book, bible, autojunk=False)
    ops = [o for o in sm.get_opcodes()
           if o[0] != 'equal' and vc.standard(book[o[1]:o[2]]) != vc.standard(bible[o[3]:o[4]])]
    # Verse text the quotation never reached is not a difference. A quotation may begin
    # or end in the middle of a verse, and the words outside it are simply not quoted.
    while ops and ops[0][1] == ops[0][2] == 0:
        ops.pop(0)
    while ops and ops[-1][1] == ops[-1][2] == len(book):
        ops.pop()
    if not ops:
        return None
    i1, i2 = ops[0][1], ops[-1][2]
    j1, j2 = ops[0][3], ops[-1][4]
    # Both sides are widened together, so that the two halves of the marker stay
    # aligned and neither ends in the middle of a Lao word.
    while i1 > 0 and j1 > 0 and book[i1 - 1] == bible[j1 - 1] and book[i1 - 1] not in vc.BOUNDARY:
        i1 -= 1
        j1 -= 1
    while (i2 < len(book) and j2 < len(bible) and book[i2] == bible[j2]
           and book[i2] not in vc.BOUNDARY):
        i2 += 1
        j2 += 1
    if i1 == i2 or j1 == j2:
        # One side is empty, so the finding is a word the book added or dropped and the
        # two halves cannot be shown side by side. The whole quotation is marked instead,
        # which is longer to read but never ambiguous about what is being replaced.
        i1, i2, j1, j2 = 0, len(book), 0, len(bible)
    old, new = book[i1:i2], bible[j1:j2].strip(EDGE)
    # The marker has to be true: putting its right side in place of its left must give
    # the Bible's wording. Where the alignment produced a pair that does not, the whole
    # quotation is marked instead, which always does.
    if vc.standard(book[:i1] + new + book[i2:]) != vc.standard(bible):
        i1, i2, old, new = 0, len(book), book, bible.strip(EDGE)
    return i1, i2, old, new


sites = []
for r in vc.rows:
    if r['verdict'] != 'NEITHER':
        continue
    name = 'LO2012' if r['texts']['LO2012'] else 'LCV'
    bible = tight(r['quote'], r['texts'][name])
    s = span(r['quote'], bible)
    if s is None:
        continue
    i1, i2, old, new = s
    path = f"lo/GC/03_public/{r['ch']}_lo.md"
    text = open(path, encoding='utf-8').read()
    at = text.find(r['quote'])
    if at < 0 or text.find(r['quote'], at + 1) >= 0 or not old.strip() or not new.strip():
        print(f"SKIP {r['ch']} {{GC {r['anchor']}}} ({r['cite']}) — quotation not located once")
        continue
    sites.append(dict(path=path, ch=r['ch'], anchor=r['anchor'], cite=r['cite'],
                      start=at + i1, end=at + i2, old=old, new=new, text=name))

sites.sort(key=lambda s: (s['ch'], s['start']))
for n, s in enumerate(sites, 1):
    s['num'] = n
    s['marker'] = (f"[[REF MED #{n}|{s['old']} -> {s['new']}|{s['cite']} does not match "
                   f"{s['text']}. Take the {s['text']} wording on the right, or keep the "
                   f"book's on the left and add a version label to the citation.]]")

for s in sites:
    print(f"#{s['num']:3d}  {s['ch']} {{GC {s['anchor']}}}  ({s['cite']})")
    print(f"       book   : {s['old']}")
    print(f"       {s['text']:<7}: {s['new']}\n")

if APPLY:
    byfile = {}
    for s in sites:
        byfile.setdefault(s['path'], []).append(s)
    for path, items in byfile.items():
        text = open(path, encoding='utf-8').read()
        for s in sorted(items, key=lambda x: -x['start']):
            assert text[s['start']:s['end']] == s['old'], (path, s['num'])
            text = text[:s['start']] + s['marker'] + text[s['end']:]
        open(path, 'w', encoding='utf-8').write(text)
    print(f"wrote {len(sites)} markers into {len(byfile)} chapters")
else:
    print(f"{len(sites)} markers would be written into "
          f"{len({s['path'] for s in sites})} chapters")
