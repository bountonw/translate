#!/usr/bin/env python3
"""Corpus-wide punctuation check over the GC Lao manuscripts.

Reads only; writes nothing. Run from the repository root:

    python3 lo/GC/04_assets/scripts/gc_punctcheck.py
    python3 lo/GC/04_assets/scripts/gc_punctcheck.py --chapter 14
    python3 lo/GC/04_assets/scripts/gc_punctcheck.py --chapter 14 --range 250.4 260.1
    python3 lo/GC/04_assets/scripts/gc_punctcheck.py --list-checks

Each finding prints the {GC ###.#} anchor, the file and line, and the text at
issue. Lines carrying an unresolved [[ audit marker are skipped, because a
marker's note is English prose and punctuates by its own rules.

A batch auditor passes --chapter with the --range of the batch it was given, so
that each batch reports only its own paragraphs and consecutive batches do not
report the same finding twice. The quote rule is Brian's and not inferred from
the corpus: where English leaves a quotation open across the paragraphs of a
multi-paragraph quote, Lao closes it in every paragraph, so any paragraph whose
quotation marks do not balance is a defect.
"""

import argparse
import glob
import os
import re
import sys
import unicodedata

PUBLIC = 'lo/GC/03_public'

ANCHOR = re.compile(r'## (\{GC [\d.]+\})')
REF = re.compile(r'\s*\{GC\s+[\d.]+\}\s*$')
FOOTREF = re.compile(r'(\[\^\d+\])+\s*$')
FOOTDEF = re.compile(r'^\[\^\d+\]:')
CITATION = re.compile(r'\([^()]*\)$')
# An audit marker holds English prose in its note, which punctuates by its own
# rules. Replace each marker with the old side it stands in front of, so the rest
# of the paragraph is still checked; skipping the whole line hides real defects
# for as long as any marker remains on it.
MARKER = re.compile(r'\[\[[A-Z]+ [A-Z]+ #\d+[a-z]?\|([^|]*)\|.*?\]\]', re.S)

TERMINAL = '.!?…'
CLOSERS = '”’)»*'
# A quote may run across paragraphs; each continuing paragraph reopens it.
LQUOTE, RQUOTE = '“', '”'
# The inner quotation. RSINGLE doubles as the apostrophe, which is why only an
# excess of LSINGLE is ever reported; see check 3b.
LSINGLE, RSINGLE = '‘', '’'


def ref_key(anchor):
    """Sort key for a {GC 250.4} anchor, as the pair (250, 4)."""
    match = re.search(r'(\d+)\.(\d+)', anchor or '')
    return (int(match.group(1)), int(match.group(2))) if match else (0, 0)


def paragraphs(path, first=None, last=None):
    """Yield (line_number, text, anchor) for every body paragraph.

    first and last are {GC ###.#} refs written bare, as 250.4; when given, only
    paragraphs inside that inclusive range are yielded.
    """
    low = ref_key(first) if first else None
    high = ref_key(last) if last else None
    anchor = ''
    in_frontmatter = False
    with open(path, encoding='utf-8') as fh:
        for num, raw in enumerate(fh.read().split('\n'), 1):
            line = raw.rstrip()
            if line == '---' and num <= 2:
                in_frontmatter = True
                continue
            if in_frontmatter:
                if line == '---':
                    in_frontmatter = False
                continue
            match = ANCHOR.match(line)
            if match:
                anchor = match.group(1)
                continue
            if '[[' in line:
                line = MARKER.sub(lambda m: m.group(1).split(' -> ')[0], line)
            if not line or line.startswith('#'):
                continue
            if low or high:
                key = ref_key(anchor)
                if low and key < low:
                    continue
                if high and key > high:
                    continue
            yield num, line, anchor


def strip_trailing(text):
    """Drop the {GC ref} and any trailing footnote markers."""
    return FOOTREF.sub('', REF.sub('', text)).rstrip()


# A hyphen is legitimate where it joins two letters, and a finding anywhere else.
# It joins Latin letters in an acronym or name such as THA-ER, and Lao letters in
# a compound of two proper nouns, as at {GC 515.2} where Syrophenician is written
# ຊາວຊີເຣຍ-ໂຟນີເຊຍ; Brian ruled on 14 August that the Lao compound stands. The
# \nbsp{}-\nbsp{} construction is the typesetting pipeline's and is also allowed.
# An em dash is legitimate only inside an italic English title.
WORD_HYPHEN = re.compile(r'[A-Za-z຀-໿]-[A-Za-z຀-໿]')
NBSP_DASH = re.compile(r'\\nbsp\{\}-\\nbsp\{\}')


def check_chapter(path, out, first=None, last=None):
    body = [p for p in paragraphs(path, first, last)]
    prose = [(n, t, a) for n, t, a in body if not FOOTDEF.match(t)]
    name = os.path.basename(path)

    for index, (num, line, anchor) in enumerate(prose):
        text = strip_trailing(line)
        if not text:
            continue
        core = text.rstrip(CLOSERS)
        following = prose[index + 1][1].lstrip() if index + 1 < len(prose) else ''

        # 1. sentence-final punctuation, allowing a colon that introduces a block quote
        if core and core[-1] not in TERMINAL:
            if text.endswith(':') and following.startswith(LQUOTE):
                pass
            elif CITATION.search(text):
                out('citation-no-period', anchor, name, num,
                    'paragraph ends with a citation and no period', text[-60:])
            else:
                out('no-final-stop', anchor, name, num,
                    'paragraph ends with no sentence-final punctuation', text[-60:])

        # 2. period belongs inside the closing quote
        # An italic span may close between the period and the quotation mark, as
        # in *ສະພາບນີ້ໄດ້ເກີດຂຶ້ນໃນທຸກຄະນະນິກາຍ.*” — the period is still inside the quote.
        inner = text[:-1].rstrip('*_') if text.endswith(RQUOTE) else ''
        if inner and inner[-1] not in TERMINAL + '’':
            out('quote-no-period', anchor, name, num,
                'closing quote with no period before it', text[-50:])

        # 3. Lao closes a quotation in every paragraph, including a paragraph of a
        # multi-paragraph quote that the English source leaves open.
        depth = line.count(LQUOTE) - line.count(RQUOTE)
        if depth > 0:
            out('quote-unclosed', anchor, name, num,
                'paragraph opens a quotation it does not close', text[-50:])
        if depth < 0:
            out('quote-orphan-close', anchor, name, num,
                'paragraph closes a quotation it did not open', text[:50])

        # 3b. The same rule for the inner single quotation. Only an excess of
        # opening marks is a finding: the closing mark is also the apostrophe, so
        # a paragraph holding more closers than openers is ambiguous rather than
        # wrong, and reporting that direction would bury the real ones.
        singles = line.count(LSINGLE) - line.count(RSINGLE)
        if singles > 0:
            out('single-quote-unclosed', anchor, name, num,
                'paragraph opens an inner quotation it does not close', text[-50:])

        # 4. stray and doubled punctuation
        for match in re.finditer(r'\s+([,.;:!?])', text):
            out('space-before-punct', anchor, name, num,
                'space before punctuation', text[max(0, match.start() - 30):match.end() + 15])
        for match in re.finditer(r'([,.;:!?])\s*\1', text):
            out('doubled-punct', anchor, name, num,
                'punctuation mark repeated', text[max(0, match.start() - 30):match.end() + 15])

        # 5. a colon at the end of a paragraph introduces a block quotation
        if text.endswith(':') and not following.startswith(LQUOTE):
            out('colon-no-quote', anchor, name, num,
                'paragraph ends with a colon but the next one is not a quotation',
                text[-50:])

        # 6. dashes: a hyphen belongs inside a Latin word, an em dash inside a title
        for match in re.finditer(r'-', text):
            window = text[max(0, match.start() - 1):match.end() + 1]
            if WORD_HYPHEN.search(window) or NBSP_DASH.search(text):
                continue
            out('stray-hyphen', anchor, name, num,
                'hyphen not joining two letters',
                text[max(0, match.start() - 30):match.end() + 20])
        for match in re.finditer(r'—', text):
            if '*' in text:
                continue
            out('stray-em-dash', anchor, name, num,
                'em dash outside an italic title',
                text[max(0, match.start() - 30):match.end() + 20])

        # 7. an opened parenthesis must close. A lone ")" is not reported, because
        # the "1)" enumerator style used in nine chapters is indistinguishable
        # from a stray one and would drown the real findings.
        depth = 0
        for char in text:
            if char == '(':
                depth += 1
            elif char == ')' and depth:
                depth -= 1
        if depth:
            out('paren-unbalanced', anchor, name, num,
                'parenthesis opened and never closed', text[:60])
        stripped_footnotes = re.sub(r'\[\^\d+\]', '', text)
        if stripped_footnotes.count('[') != stripped_footnotes.count(']'):
            out('bracket-unbalanced', anchor, name, num,
                'square brackets do not balance', text[:60])

    # 8. footnote definitions
    for num, line, anchor in body:
        if FOOTDEF.match(line) and line[-1] not in TERMINAL + RQUOTE + '’':
            out('footnote-no-stop', anchor, name, num,
                'footnote entry ends with no punctuation', line)

    # 9. characters that must never appear
    forbidden = [
        ('lao-digit', r'[໐-໙]', 'Lao digit'),
        ('thai-digit', r'[๐-๙]', 'Thai digit'),
        ('zero-width', r'[​‌‍﻿]', 'zero-width character'),
        ('nbsp', r' ', 'no-break space'),
        ('tab', r'\t', 'tab'),
        ('straight-quote', r'["\']', 'straight quote or apostrophe'),
    ]
    for num, line, anchor in body:
        for code, pattern, label in forbidden:
            match = re.search(pattern, line)
            if match:
                out(code, anchor, name, num, label,
                    unicodedata.name(match.group(0)[0], 'unnamed'))
        stripped = line.lstrip()
        if '  ' in stripped:
            out('double-space', anchor, name, num, 'two consecutive spaces', stripped[:60])
        if '...' in line:
            out('ascii-ellipsis', anchor, name, num,
                'three periods where the corpus uses a single ellipsis character', line[:60])


CHECKS = {
    'no-final-stop': 'paragraph ends with no sentence-final punctuation',
    'citation-no-period': 'paragraph ends with a citation and no period after it',
    'quote-no-period': 'closing quote with no period before it',
    'quote-unclosed': 'quote opens, is never closed, and the next paragraph does not reopen it',
    'quote-orphan-close': 'closing quote with no opening quote',
    'single-quote-unclosed': 'inner quotation opens and is never closed',
    'space-before-punct': 'whitespace before a punctuation mark',
    'doubled-punct': 'the same punctuation mark twice',
    'colon-no-quote': 'paragraph ends with a colon but no quotation follows',
    'stray-hyphen': 'hyphen not joining two letters, Latin or Lao',
    'stray-em-dash': 'em dash outside an italic title',
    'paren-unbalanced': 'parentheses do not balance',
    'bracket-unbalanced': 'square brackets do not balance',
    'footnote-no-stop': 'footnote entry ends with no punctuation',
    'lao-digit': 'Lao digit, forbidden by CLAUDE.md 5.A',
    'thai-digit': 'Thai digit, forbidden by CLAUDE.md 5.A',
    'zero-width': 'zero-width character, forbidden by CLAUDE.md 5.B',
    'nbsp': 'no-break space',
    'tab': 'tab character',
    'straight-quote': 'straight quote where the corpus uses curly quotes',
    'double-space': 'two consecutive spaces inside a paragraph',
    'ascii-ellipsis': 'three periods instead of the ellipsis character',
}


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--chapter', help='restrict to one chapter, as 14 or GC14')
    parser.add_argument('--range', nargs=2, metavar=('FIRST', 'LAST'),
                        help='restrict to a ref range within the chapter, as 250.4 260.1')
    parser.add_argument('--check', action='append',
                        help='report only this check; repeatable')
    parser.add_argument('--list-checks', action='store_true',
                        help='print the check names and exit')
    args = parser.parse_args()

    if args.list_checks:
        for code, description in CHECKS.items():
            print('%-20s %s' % (code, description))
        return 0

    files = sorted(glob.glob(os.path.join(PUBLIC, 'GC*_lo.md')))
    files = [f for f in files if 'introduction' not in f]
    if args.chapter:
        digits = re.sub(r'\D', '', args.chapter).zfill(2)
        files = [f for f in files if os.path.basename(f).startswith('GC' + digits + '_')]
    if not files:
        print('no chapter files matched; run from the repository root', file=sys.stderr)
        return 2
    if args.range and len(files) != 1:
        print('--range needs --chapter, so that the refs name one chapter', file=sys.stderr)
        return 2
    first, last = args.range if args.range else (None, None)

    wanted = set(args.check) if args.check else None
    findings = []

    def record(code, anchor, name, num, description, evidence):
        if wanted and code not in wanted:
            return
        findings.append((code, anchor, name, num, description, evidence))

    for path in files:
        check_chapter(path, record, first, last)

    for code, anchor, name, num, description, evidence in findings:
        print('%-20s %-14s %s:%d\n    %s\n    %s' %
              (code, anchor or '(no anchor)', name, num, description, evidence))

    print('\n%d finding%s across %d chapter%s.' %
          (len(findings), '' if len(findings) == 1 else 's',
           len(files), '' if len(files) == 1 else 's'))
    return 1 if findings else 0


if __name__ == '__main__':
    sys.exit(main())
