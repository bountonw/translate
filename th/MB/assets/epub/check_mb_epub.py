#!/usr/bin/env python3
"""Check a Thai MB EPUB against th/MB/03_public, and list how the hand-made EPUBs differ.

Usage, from the repository's top folder:
    python3 -B th/MB/assets/epub/check_mb_epub.py ~/MB_th.epub [--hand A.epub B.epub]
Compares the letters and digits of each chapter with its chapter file, paragraph by
paragraph; counts each paragraph anchor once; refuses Thai digits, soft hyphens and every
invisible format character; parses every XML file; follows every internal link; looks for
each word of the translator field of metadata.yaml. Exits 1 on any problem.
"""
import argparse
import difflib
import html
import os
import posixpath
import re
import sys
import unicodedata
import zipfile
from xml.etree import ElementTree as ET

sys.dont_write_bytecode = True
# th/MB/assets/epub/check_mb_epub.py -> the repository's top folder
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..'))
p = argparse.ArgumentParser()
p.add_argument('epub')
p.add_argument('--repo', default=REPO, help='the repository; default the one holding this script')
p.add_argument('--hand', nargs='*', default=[])
args = p.parse_args()


def letters(s):
    return ''.join(c for c in s if unicodedata.category(c)[0] in 'LMN')


def visible(xhtml):
    return html.unescape(re.sub(r'<[^>]+>', '', xhtml))


book = os.path.join(args.repo, 'th/MB')
meta = open(os.path.join(book, 'metadata.yaml'), encoding='utf-8').read()
withheld = [w for line in meta.split('translator:')[1].split('book:')[0].split('\n')
            for w in line.partition(':')[2].split() if len(w) > 2]

z = zipfile.ZipFile(args.epub)
names = z.namelist()
problems = []
if names[0] != 'mimetype' or z.getinfo('mimetype').compress_type != zipfile.ZIP_STORED:
    problems.append('mimetype is not first and stored')
docs = {n: z.read(n).decode('utf-8') for n in names if n.endswith(('.xhtml', '.opf', '.ncx', '.xml', '.css'))}
for n, s in docs.items():
    if not n.endswith('.css'):
        try:
            ET.fromstring(s.encode('utf-8'))
        except ET.ParseError as e:
            problems.append(f'{n}: not well formed: {e}')
    for label, pat in (('Thai digits', '[\u0e50-\u0e59]'), ('soft hyphens', '\u00ad|&shy;|&#173;'),
                       ('format characters', '[\u200b-\u200f\u2060\ufeff]')):
        if re.search(pat, s):
            problems.append(f'{n}: {label}')
    for w in withheld:
        if w in s:
            problems.append(f'{n}: a word of the translator field')

# paragraphs: every anchor of 03_public once, and the letters of each chapter in order
source_paras = {}
anchors_seen = {}
compared = 0
for name in sorted(os.listdir(os.path.join(book, '03_public'))):
    if not name.endswith('.md'):
        continue
    raw = open(os.path.join(book, '03_public', name), encoding='utf-8').read()
    _, head, body = raw.split('---', 2)
    n = int(re.search(r'number:\s*(\d+)', head).group(1))
    page = docs.get(f'OEBPS/text/MB{n:02d}.xhtml')
    if page is None:
        problems.append(f'chapter {n} missing')
        continue
    compared += 1
    main_md = re.sub(r'^\[\^\w+\]:.*$', '', body, flags=re.M)
    notes_md = ' '.join(re.findall(r'^\[\^\w+\]:(.*)$', body, flags=re.M))
    main_md = re.sub(r'^## \{[^}]+\}\s*$', '', main_md, flags=re.M)
    main_md = re.sub(r'\[\^\w+\]', '', main_md)
    for section in re.split(r'^(?=## \{MB )', body, flags=re.M)[1:]:
        anchor = re.match(r'## \{MB ([^}]+)\}', section)[1]
        source_paras[anchor] = (n, re.sub(r'^## .*$|^###.*$|^\[\^\w+\]:.*$|\[\^\w+\]|\{MB [^}]+\}', '', section, flags=re.M))
    text = page.split('</h1>', 1)[1]
    main_x, _, notes_x = text.partition('<section class="notes"')
    notes_x = re.sub(r'<a href="#nr\d+">\d+</a>', '', notes_x)
    main_x = re.sub(r'<sup>.*?</sup>', '', main_x)
    for label, a, b in (('TEXT', main_md, visible(main_x)), ('NOTES', notes_md, visible('<x ' + notes_x) if notes_x else '')):
        a, b = letters(a), letters(b)
        if a != b:
            i = next((k for k in range(min(len(a), len(b))) if a[k] != b[k]), min(len(a), len(b)))
            problems.append(f'{label} differs in chapter {n} at letter {i}: file {a[i-20:i+20]!r} EPUB {b[i-20:i+20]!r}')
    for anchor in re.findall(r'\bid="MB([^"]+)"', page):
        anchors_seen[anchor] = anchors_seen.get(anchor, 0) + 1
    refs = re.findall(r'^## \{MB ([^}]+)\}', body, flags=re.M)
    for r in refs:
        if anchors_seen.get(r) != 1:
            problems.append(f'paragraph {{MB {r}}} appears {anchors_seen.get(r, 0)} times as an id')

ids = {n: re.findall(r'\bid="([^"]+)"', s) for n, s in docs.items() if n.endswith('.xhtml')}
links = 0
for n, s in docs.items():
    if not n.endswith('.xhtml'):
        continue
    if len(ids[n]) != len(set(ids[n])):
        problems.append(f'{n}: a repeated id')
    for href in re.findall(r'\b(?:href|src)="([^"]+)"', s):
        if href.startswith(('http://', 'https://')):
            continue
        links += 1
        path, _, frag = href.partition('#')
        target = posixpath.normpath(posixpath.join(posixpath.dirname(n), path)) if path else n
        if target not in names or (frag and frag not in ids.get(target, ())):
            problems.append(f'{n}: broken link {href}')

allx = ''.join(s for n, s in docs.items() if n.endswith('.xhtml'))
print(f'{args.epub}: files {len(names)}; {os.path.getsize(args.epub)} bytes; chapters compared {compared}')
print(f'paragraph anchors in 03_public {sum(1 for _ in source_paras)}; ids in the EPUB {sum(anchors_seen.values())}; '
      f'note references {allx.count("epub:type=\"noteref\"")}; notes {allx.count("epub:type=\"footnote\"")}; '
      f'subheadings {allx.count("<h2>")}; poem blocks {allx.count("<div class=\"poem\"")}; internal links {links}')
print(f'kept-whole spans {allx.count("<span class=\"nb\">")}; <wbr/> {allx.count("<wbr/>")}')
for x in problems[:40]:
    print('PROBLEM', x)
print(f'{len(problems)} problems')

# the hand-made EPUBs: is each paragraph of 03_public there, word for word in its letters?
for hand in args.hand:
    hz = zipfile.ZipFile(hand)
    pages = [hz.read(n).decode('utf-8') for n in sorted(hz.namelist()) if n.endswith('.xhtml') and 'toc' not in n]
    blocks = []
    for pg in pages:
        for m in re.finditer(r'<(p|h\d)\b[^>]*>(.*?)</\1>', pg, re.S):
            t = letters(visible(m[2]))
            if t:
                blocks.append(t)
    whole = '|'.join(blocks)
    same, changed, missing, doubled = 0, [], [], []
    for anchor, (n, md) in source_paras.items():
        a = letters(md)
        if not a:
            continue
        k = whole.count(a)
        if k == 1:
            same += 1
        elif k > 1:
            doubled.append(anchor)
        else:
            best = max(blocks, key=lambda b: difflib.SequenceMatcher(None, a[:400], b[:400], autojunk=False).quick_ratio()
                       if abs(len(b) - len(a)) < len(a) else 0)
            r = difflib.SequenceMatcher(None, a, best, autojunk=False).ratio()
            (changed if r > 0.6 else missing).append((anchor, round(r, 3)))
    print(f'\nHAND {os.path.basename(hand)}: same {same}; changed since {len(changed)}; not found {len(missing)}; '
          f'found twice {len(doubled)}; {{MB refs shown: {"yes" if "{MB" in "".join(pages) else "no"}}}')
    print('  changed:', ' '.join(f'{a}({r})' for a, r in changed))
    print('  not found:', ' '.join(f'{a}({r})' for a, r in missing))
    print('  twice:', ' '.join(doubled))
sys.exit(1 if problems else 0)
