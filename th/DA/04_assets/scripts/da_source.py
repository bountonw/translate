#!/usr/bin/env python3
"""Build the DA English source and the Thai placeholder chapters from the EGW Writings download.

Usage, from the repository root:
    python3 th/DA/04_assets/scripts/da_source.py DA_ZIP

DA_ZIP is The Desire of Ages (book_id 130) as the EGW Writings app downloads it.
Writes th/DA/00_source/DA00_preface_en.md and DA01_en.md to DA87_en.md, one file per
chapter, each paragraph under its anchor, e.g. "## {DA 19.1}", in the PP source format.
Writes th/DA/01_raw/DANN_th.typ as a placeholder for every chapter that has no Thai file
in 01_raw, 02_edit or 03_public; an existing Thai file is never touched.
"""
import html
import json
import re
import sys
import zipfile
from pathlib import Path

BOOK = Path(__file__).resolve().parents[2]
SOURCE = BOOK / '00_source'
RAW = BOOK / '01_raw'
STAGES = ('01_raw', '02_edit', '03_public')

TAGS = [
    (re.compile(r'<span class="page-break"[^>]*></span>'), ''),
    (re.compile(r'<br\s*/?>'), '\n'),
    (re.compile(r'</?(?:em|i)>'), '*'),
    (re.compile(r'</?(?:strong|b)>'), '**'),
    (re.compile(r'<[^>]+>'), ''),
]
NOTE_RE = re.compile(
    r'<sup class="(?:chapterendnote|bookendnote|footnote)">\s*<a[^>]*>(.*?)<span[^>]*>(.*?)</span>\s*</a>\s*</sup>',
    re.S)
CHAPTER_RE = re.compile(r'Chapter (\d+)—(.+)')
# The EGW Writings app's note on its study guide; not part of the printed book.
SKIP = {'DA 17.9'}


def clean(text):
    text = re.sub(r'\s+', ' ', text)
    for rx, rep in TAGS:
        text = rx.sub(rep, text)
    text = html.unescape(text).replace(' ', ' ')
    text = re.sub(r' {2,}', ' ', text)
    return '\n'.join(line.strip() for line in text.strip().split('\n'))


def read_zip(path):
    z = zipfile.ZipFile(path)
    info = json.loads(z.read('info.json'))
    if info['book_id'] != 130:
        sys.exit(f'{path} is book {info["book_id"]} ({info["title"]}), not The Desire of Ages (130)')
    paras = []
    for name in z.namelist():
        if name[0].isdigit() and name.endswith('.json'):
            paras.extend(json.loads(z.read(name)))
    paras.sort(key=lambda p: p['puborder'])
    return paras


def split_chapters(paras):
    """Return [(number, title, heading_para, [paras])]; the preface is number 0."""
    chapters = []
    for p in paras:
        if p['element_type'] in ('h2', 'h3'):
            heading = clean(p['content'])
            m = CHAPTER_RE.match(heading)
            if m:
                chapters.append((int(m.group(1)), m.group(2).strip(), p, []))
            elif heading == 'Preface':
                chapters.append((0, 'Preface', p, []))
            else:
                sys.exit(f'unexpected heading {heading!r} at {p["refcode_short"]}')
        elif chapters:
            chapters[-1][3].append(p)
    return chapters


def write_source(number, title, body):
    basedon = ''
    first_id = page = None
    out = []
    note_no = 0
    for p in body:
        if p['refcode_short'].strip() in SKIP:
            continue
        notes = []

        def take_note(m):
            nonlocal note_no
            note_no += 1
            notes.append(f'[^{note_no}]: {clean(m.group(2))}')
            return f'[^{note_no}]'

        text = clean(NOTE_RE.sub(take_note, p['content']))
        ref = p['refcode_short'].strip()
        if not ref:
            if text.startswith('This chapter is based on'):
                basedon = text
            else:
                out += ['    ' + text, '']
            continue
        if not first_id:
            first_id, page = p['para_id'], ref.split()[1].split('.')[0]
        if '\n' in text:
            text = '\n'.join('    ' + line for line in text.split('\n'))
        out += [f'## {{{ref}}}', '', f'{text} {{{ref}}}', '']
        if notes:
            out += notes + ['']
    header = ['---', 'book:', '  title:', '    en: The Desire of Ages', 'chapter:',
              f'  number: {number or ""}'.rstrip(), '  title:', f'    en: {title}',
              f'  url: https://egwwritings.org/?ref=en_DA.{page}&para={first_id}',
              f'  basedon: {basedon}'.rstrip(), 'author:', '  en: Ellen White', '---', '']
    name = 'DA00_preface_en.md' if number == 0 else f'DA{number:02d}_en.md'
    (SOURCE / name).write_text('\n'.join(header + out).rstrip('\n') + '\n', encoding='utf-8')


def write_placeholder(number, title, heading):
    name = 'DA00_preface_th.typ' if number == 0 else f'DA{number:02d}_th.typ'
    if any((BOOK / stage / name).exists() for stage in STAGES):
        return False
    lines = [f'// Source-url: "https://egwwritings.org/read?panels=p{heading["para_id"]}"',
             f'// English title: {title}', '',
             '#import "../04_assets/template/lib.typ": *',
             '#show: apply-styles.with(proofing: true)', '',
             '#chapter(']
    if number:
        lines.append(f'  number: {number},')
    lines += ['  title: "",', ')', '']
    (RAW / name).write_text('\n'.join(lines), encoding='utf-8')
    return True


def main(zip_path):
    chapters = split_chapters(read_zip(zip_path))
    SOURCE.mkdir(exist_ok=True)
    RAW.mkdir(exist_ok=True)
    made = 0
    for number, title, heading, body in chapters:
        write_source(number, title, body)
        made += write_placeholder(number, title, heading)
    print(f'{len(chapters)} source files written to {SOURCE.relative_to(BOOK.parents[1])}; '
          f'{made} placeholders written to {RAW.relative_to(BOOK.parents[1])}')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
