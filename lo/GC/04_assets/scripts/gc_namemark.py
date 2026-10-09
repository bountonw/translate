#!/usr/bin/env python3
"""gc_namemark.py — mark the divine-name quotations in lo/GC/03_public/ for review.

The book renders the divine name three ways: ພຣະເຈົ້າຢາເວ inside quotations taken from
the online 2012 text, ອົງພຣະຜູ້ເປັນເຈົ້າ in the narrative and in quotations whose verse
carries the Hebrew title, and ພຣະເຢໂຮວາ in quotations taken from TKJV and the old Lao
version. Only the first of those is at issue here. Whether a quotation keeps it depends
on what the printed 2012 Bible has at that verse, which no machine copy holds, so every
site has to be read off the page one at a time.

This script wraps each such quotation, together with the reference that names its verse,
in a numbered mark of the form [[#NNN … ]], and puts << >> round the words at issue
inside it, so that the whole set can be worked through in one pass:

    python3 lo/GC/04_assets/scripts/gc_namemark.py            list the marks it would write
    python3 lo/GC/04_assets/scripts/gc_namemark.py --apply    write them into the chapters
    python3 lo/GC/04_assets/scripts/gc_namemark.py --undo     take every mark out again

A mark runs from the opening quotation mark of the first flagged quotation to the closing
bracket of the reference that follows it, because a decision about the divine name is a
decision about which text the whole quotation comes from, and the reference is what sends
the reader to the right page. Where one reference governs several quotations the mark
covers them all, since there is only one reference to act on.

--undo strips [[#NNN, ]], << and >> and nothing else, so it restores the chapters exactly.
Run it before any check that reads the manuscripts, and never run --apply on a chapter that
already carries marks of another kind.
"""
import glob
import os
import re
import sys

QUOTE = re.compile(r'[“][^“”]{5,3000}[”]')
CITE = re.compile(r'\([^()]*\d+:\d[^()]*\)')
ANCHOR = re.compile(r'^## \{GC (\d+\.\d+)\}')
NAME = 'ພຣະເຈົ້າຢາເວ'
TITLE = 'ອົງພຣະຜູ້ເປັນເຈົ້າ'

# Two sites in GC15 read the title where the online text reads the name, under a citation
# that carries no version code and therefore claims the online text. They are flagged in
# the same run so that they are decided alongside it. At {GC 286.1} the second quotation
# also ends a word short of the online text, which ends at ກະທຳມາ, so ກະທຳ is flagged too.
EXTRA = {
    ('GC15', '285.2'): [TITLE],
    ('GC15', '286.1'): [TITLE, 'ກະທຳ.'],
}


def undo():
    for path in sorted(glob.glob('lo/GC/03_public/GC[0-9][0-9]_lo.md')):
        before = open(path, encoding='utf-8').read()
        after = re.sub(r'\[\[#\d{3}', '', before)
        for junk in (']]', '<<', '>>'):
            after = after.replace(junk, '')
        if after != before:
            open(path, 'w', encoding='utf-8').write(after)
            print('cleaned', path)


def run(apply):
    n = 0
    plan = []
    for path in sorted(glob.glob('lo/GC/03_public/GC[0-9][0-9]_lo.md')):
        chapter = os.path.basename(path)[:4]
        lines = open(path, encoding='utf-8').read().split('\n')
        anchor = ''
        for index, line in enumerate(lines):
            m = ANCHOR.match(line)
            if m:
                anchor = m.group(1)
                continue
            words = EXTRA.get((chapter, anchor)) or ([NAME] if NAME in line else [])
            if not words or not any(w in line for w in words):
                continue
            cites = [(c.start(), c.end()) for c in CITE.finditer(line)]
            groups = {}
            for q in QUOTE.finditer(line):
                if not any(w in q.group(0) for w in words):
                    continue
                after = next((c for c in cites if c[0] >= q.end()), None)
                end = after[1] if after else q.end()
                group = groups.setdefault(end, [q.start(), end])
                group[0] = min(group[0], q.start())
            out, last = [], 0
            for end in sorted(groups):
                lo, hi = groups[end]
                n += 1
                body = line[lo:hi]
                for w in words:
                    body = body.replace(w, '<<' + w + '>>')
                out.append(line[last:lo])
                out.append(f'[[#{n:03d}{body}]]')
                last = hi
                cm = CITE.search(line, lo)
                plan.append((n, chapter, anchor, cm.group(0) if cm else '(no reference)',
                             sum(body.count('<<' + w + '>>') for w in words)))
            out.append(line[last:])
            lines[index] = ''.join(out)
        if apply:
            open(path, 'w', encoding='utf-8').write('\n'.join(lines))

    print(f'marks: {len(plan)}\n')
    for number, chapter, anchor, cite, flagged in plan:
        print(f'  #{number:03d}  {chapter} {{GC {anchor}}}  {cite}   flagged: {flagged}')


if __name__ == '__main__':
    if '--undo' in sys.argv:
        undo()
    else:
        run('--apply' in sys.argv)
