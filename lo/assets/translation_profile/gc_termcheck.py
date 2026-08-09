#!/usr/bin/env python3
"""Mechanical glossary check for the GC Lao translation audit.

Compares an English batch and a Lao batch, paragraph by
paragraph via {GC ###.#} anchors, against GC-glossary.txt.
Emits candidate TERM findings for human adjudication. The
output is not a finding list; it is a shortlist.

Glossary conventions read by this script:
  bare Notes cell   reference only; never reported
  [CHECK]           enforce: report English present, Lao absent
  [FLAG]            report every occurrence, matched or not
  '/' in Lao cell   any listed option satisfies a [CHECK] row
  (parenthetical)   instruction, not Lao text; skipped

Rows are silent until tagged. Coverage grows as terms are
adjudicated: each decision session adds [CHECK] rows.

Usage:
  gc_termcheck.py --en EN.md --lo LO.md
  gc_termcheck.py --en EN.md --lo LO.md --from 39.1 --to 65.2
  gc_termcheck.py --en EN.md --lo LO.md --reverse
"""
import argparse
import re
import unicodedata
import sys

DEFAULT_GLOSSARY = '/mnt/project/GC-glossary.txt'
ANCHOR = re.compile(r'^## \{GC ([0-9]+\.[0-9]+)\}\s*$', re.M)
INLINE_ANCHOR = re.compile(r'\{GC [0-9]+\.[0-9]+\}')
FOOTNOTE_MARK = re.compile(r'\[\^[0-9]+\]')
FRONTMATTER = re.compile(r'^---$.*?^---$', re.M | re.S)
PAREN_ONLY = re.compile(r'^\(.*\)$')
TRAIL_PAREN = re.compile(r'\s*\([^)]*\)\s*$')
LAO_RANGE = re.compile(r'[\u0E80-\u0EFF]')

# English glossary heads too short or too common to match
# usefully; matching them produces noise, not findings.
STOPTERMS = {'diet', 'mass', 'lamb', 'beast', 'dragon', 'council',
             'stake', 'seal of god', 'chapter', 'book'}

MAX_PER_ROW = 15
MIN_SPELL_LEN = 4


class Row:
    def __init__(self, en, lo, notes, kind, line_no):
        self.en_variants = split_variants(en)
        self.lo_variants = split_variants(lo)
        self.notes = notes
        self.kind = kind
        self.line_no = line_no
        self.label = en.strip()

    @property
    def mode(self):
        up = self.notes.upper()
        if '[FLAG]' in up:
            return 'FLAG'
        if '[CHECK]' in up:
            return 'CHECK'
        return 'REF'

    def usable(self):
        if self.mode == 'REF':
            return False
        if not self.en_variants or not self.lo_variants:
            return False
        if any(PAREN_ONLY.match(v) for v in self.lo_variants):
            return False
        if not any(LAO_RANGE.search(v) for v in self.lo_variants):
            return False
        return True


def split_variants(cell):
    """Glossary cells list alternatives with '/'. Trailing
    parentheses are disambiguating glosses, not part of the
    term, so they are stripped before matching."""
    out = []
    for part in cell.split('/'):
        part = TRAIL_PAREN.sub('', part).strip().strip('"').strip('“”')
        if part:
            out.append(part)
    return out


def parse_glossary(path):
    rows, spelling = [], []
    kind = 'term'
    for n, line in enumerate(open(path, encoding='utf-8'), 1):
        s = line.strip()
        if not s.startswith('|'):
            continue
        if re.match(r'^\|[\s:|-]+\|$', s):
            continue
        cells = [c.strip() for c in s.strip('|').split('|')]
        if not cells or not cells[0]:
            continue
        head = cells[0].lower()
        if head in ('english', 'word'):
            kind = 'spelling' if head == 'word' else 'term'
            continue
        if kind == 'spelling' and len(cells) >= 3:
            spelling.append((cells[0], cells[1], cells[2],
                             cells[3] if len(cells) > 3 else '', n))
            continue
        lo = cells[1] if len(cells) > 1 else ''
        notes = cells[2] if len(cells) > 2 else ''
        rows.append(Row(cells[0], lo, notes, kind, n))
    return rows, spelling


def parse_paragraphs(path):
    text = open(path, encoding='utf-8').read()
    parts = ANCHOR.split(text)
    out = {}
    for i in range(1, len(parts), 2):
        body = FRONTMATTER.sub(' ', parts[i + 1])
        body = FOOTNOTE_MARK.sub(' ', body)
        body = INLINE_ANCHOR.sub(' ', body)
        out.setdefault(parts[i], []).append(body)
    return {k: re.sub(r'\s+', ' ', ' '.join(v)) for k, v in out.items()}


def refkey(ref):
    page, para = ref.split('.')
    return (int(page), int(para))


def in_range(ref, lo_ref, hi_ref):
    k = refkey(ref)
    if lo_ref and k < refkey(lo_ref):
        return False
    if hi_ref and k > refkey(hi_ref):
        return False
    return True


def fold(text):
    """Source spells cited authors without diacritics and with
    typographic apostrophes (D'Aubigne for D'Aubigné). Fold both
    sides so glossary rows still match."""
    text = text.replace('\u2019', "'").replace('\u2018', "'")
    norm = unicodedata.normalize('NFKD', text)
    return ''.join(c for c in norm if not unicodedata.combining(c))


def en_present(term, text):
    if term.lower() in STOPTERMS:
        return False
    pat = r'(?<![A-Za-z])' + re.escape(fold(term)).replace(r'\ ', r'\s+')
    pat += r'(?![A-Za-z])'
    return re.search(pat, fold(text), re.I) is not None


def lo_present(term, text):
    return term in text


def excerpt(term, text, pad=40):
    text_f = fold(text)
    i = text_f.find(term)
    if i < 0:
        m = re.search(re.escape(fold(term)), text_f, re.I)
        if not m:
            return ''
        i = m.start()
    return text[max(0, i - pad):i + len(term) + pad].strip()


def run(en_paras, lo_paras, rows, spelling, args):
    refs = sorted(
        (r for r in en_paras if in_range(r, args.start, args.end)),
        key=refkey)
    flag, forward, reverse, spell = [], [], [], []

    for row in rows:
        if not row.usable():
            continue
        hits = 0
        for ref in refs:
            if hits >= MAX_PER_ROW:
                break
            en_text = en_paras.get(ref, '')
            lo_text = lo_paras.get(ref, '')
            has_en = any(en_present(v, en_text)
                         for v in row.en_variants)
            has_lo = any(lo_present(v, lo_text)
                         for v in row.lo_variants)
            if row.mode == 'FLAG':
                if has_en or has_lo:
                    flag.append((ref, row, en_text, lo_text))
                    hits += 1
                continue
            if has_en and not has_lo:
                forward.append((ref, row, en_text, lo_text))
                hits += 1
            elif has_lo and not has_en and args.reverse:
                reverse.append((ref, row, en_text, lo_text))
                hits += 1

    for correct, wrong, notes, _n in (
            (s[1], s[2], s[3], s[4]) for s in spelling):
        if not wrong or not LAO_RANGE.search(wrong):
            continue
        if '[CHECK]' not in notes.upper():
            continue
        # Short forms are substrings of unrelated words (ພະ
        # inside ພະຍານາກ). Prefix rules need a whitelist and
        # are handled in dedicated grep sessions, not here.
        if len(wrong) < MIN_SPELL_LEN:
            continue
        for ref in refs:
            lo_text = lo_paras.get(ref, '')
            if wrong in lo_text:
                spell.append((ref, correct, wrong, lo_text))
    return flag, forward, reverse, spell


def emit(flag, forward, reverse, spell, refs_checked, args):
    def block(title, items, kind):
        print(f'\n### {title} ({len(items)})\n')
        if not items:
            print('none')
            return
        for ref, row, en_text, lo_text in items:
            print(f'{{GC {ref}}}  {row.label}'
                  f'  [glossary line {row.line_no}]')
            if kind in ('flag', 'forward'):
                for v in row.en_variants:
                    if en_present(v, en_text):
                        print(f'    EN: …{excerpt(v, en_text)}…')
                        break
            if kind in ('flag', 'reverse'):
                for v in row.lo_variants:
                    if lo_present(v, lo_text):
                        print(f'    LO: …{excerpt(v, lo_text)}…')
                        break
            if kind == 'forward':
                print(f'    expected: {" / ".join(row.lo_variants)}')
            print()

    print('# gc_termcheck')
    print(f'paragraphs in range: {refs_checked}')
    if args.start or args.end:
        print(f'range: {args.start or "start"}–{args.end or "end"}')

    block('FLAG — report every occurrence', flag, 'flag')
    block('FORWARD — English term present, mapped Lao absent',
          forward, 'forward')
    if args.reverse:
        block('REVERSE — Lao term present, mapped English absent',
              reverse, 'reverse')

    print(f'\n### SPELLING — known-incorrect form found ({len(spell)})\n')
    if not spell:
        print('none')
    for ref, correct, wrong, lo_text in spell:
        print(f'{{GC {ref}}}  {wrong} → {correct}')
        print(f'    LO: …{excerpt(wrong, lo_text)}…\n')

    total = len(flag) + len(forward) + len(reverse) + len(spell)
    print(f'\nTotal candidates: {total}. '
          f'Rows capped at {MAX_PER_ROW} reports each.')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--en', required=True)
    p.add_argument('--lo', required=True)
    p.add_argument('--glossary', default=DEFAULT_GLOSSARY)
    p.add_argument('--from', dest='start', default=None)
    p.add_argument('--to', dest='end', default=None)
    p.add_argument('--reverse', action='store_true')
    args = p.parse_args()

    rows, spelling = parse_glossary(args.glossary)
    en_paras = parse_paragraphs(args.en)
    lo_paras = parse_paragraphs(args.lo)

    missing = [r for r in en_paras
               if in_range(r, args.start, args.end)
               and r not in lo_paras]
    if missing:
        print(f'unaligned (no Lao paragraph): {", ".join(missing)}',
              file=sys.stderr)

    refs_checked = sum(1 for r in en_paras
                       if in_range(r, args.start, args.end))
    out = run(en_paras, lo_paras, rows, spelling, args)
    emit(*out, refs_checked, args)


if __name__ == '__main__':
    main()
