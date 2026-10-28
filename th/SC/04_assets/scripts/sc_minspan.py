#!/usr/bin/env python3
"""Narrow every standing marker of an SC Thai chapter to the words that change. Reads only.

    python3 th/SC/04_assets/scripts/sc_minspan.py --chapter 13
    python3 th/SC/04_assets/scripts/sc_minspan.py --chapter 13 --all 2 --prefix 8=ขาดความอบอุ่นและความ --suffix 7=ช่วยให้เขา

For each [[CLASS #N|old -> new|note]] marker in the chapter (searched under
th/SC/03_public, 02_edit and 01_raw) the script strips the prefix and suffix
common to old and new, backs off so that no cut falls inside a Thai syllable,
and extends old until it is unique in its paragraph. A candidate new2..new5 in
the note that shares the kept prefix and suffix is cut the same way; one that
does not stays whole and the note says it replaces the whole span.

The automatic cut can still fall inside a word, since the script has no word
list; the conductor reads each OLD and NEW and, where a cut splits a word,
re-runs with --prefix N=<text> or --suffix N=<text>, the literal text to keep
outside marker N, copied from the script's own output. --all N makes the prefix
and suffix common to every candidate of marker N as well, so none is marked
whole.

The output, per marker: the anchor, the narrowed OLD and NEW, each candidate,
the sentence around the span, and MARKER2, the full narrowed marker text to
paste over the old one with the Edit tool, prefix and suffix restored outside
the brackets. The script never writes the chapter.
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
LEADING = set('เแโใไ')
COMBINING = set(['ั'] + [chr(c) for c in range(0x0e34, 0x0e3b)] + [chr(c) for c in range(0x0e47, 0x0e4f)])
TRAILING = set('ะำๆฯ')  # ะ ำ ๆ ฯ end a syllable
MARK = re.compile(r'\[\[([A-Z]+(?: [A-Z]+)?) #(\d+)\|([^\[\]|]*?) -> ([^\[\]|]*?)(?:\|((?:(?!\[\[).)*?))?\]\]', re.S)


def chapter_path(nn):
    for stage in ('03_public', '02_edit', '01_raw'):
        p = ROOT / 'th' / 'SC' / stage / f'SC{nn}_th.typ'
        if p.exists():
            return p
    sys.exit(f'no chapter SC{nn} under th/SC')


def cands(note):
    out = []
    for m in re.finditer(r'new(\d): (.*?)(?=; new\d: |$)', note, re.S):
        k, body = m.group(1), m.group(2)
        thai = re.split(r', (?=[A-Za-z])', body, maxsplit=1)[0]
        out.append((int(k), thai, body[len(thai):]))
    return out


def common_prefix(strs):
    p, mn = 0, min(len(s) for s in strs)
    while p < mn and all(s[p] == strs[0][p] for s in strs):
        p += 1
    return p


def common_suffix(strs):
    s, mn = 0, min(len(x) for x in strs)
    while s < mn and all(x[len(x) - 1 - s] == strs[0][len(strs[0]) - 1 - s] for x in strs):
        s += 1
    return s


def unsafe_cut(x, i):
    """True when a cut between x[i-1] and x[i] falls inside a syllable."""
    if i <= 0 or i >= len(x):
        return False
    before, after = x[i - 1], x[i]
    return (after in COMBINING or after in TRAILING or before in LEADING or before in COMBINING)


def safe_prefix(strs, p):
    while p > 0 and any(unsafe_cut(s, p) for s in strs):
        p -= 1
    return p


def safe_suffix(strs, s):
    while s > 0 and any(unsafe_cut(x, len(x) - s) for x in strs):
        s -= 1
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--chapter', required=True)
    ap.add_argument('--all', nargs='*', type=int, default=[], help='marker numbers whose candidates must all fit the span')
    ap.add_argument('--prefix', nargs='*', default=[], help='N=<text>: keep this literal text outside marker N, before it')
    ap.add_argument('--suffix', nargs='*', default=[], help='N=<text>: keep this literal text outside marker N, after it')
    a = ap.parse_args()
    nn = a.chapter.zfill(2)
    pre_ov = {int(k): v for k, v in (x.split('=', 1) for x in a.prefix)}
    suf_ov = {int(k): v for k, v in (x.split('=', 1) for x in a.suffix)}
    path = chapter_path(nn)
    text = path.read_text(encoding='utf-8')
    paras = re.split(r'(?=// \{SC \d+\.\d+\})', text)
    print(f'chapter {path.relative_to(ROOT)}')
    for m in MARK.finditer(text):
        cls, num, old, new, note = m.groups()
        note = note or ''
        n = int(num)
        cs = cands(note)
        base = [old, new] + ([c[1] for c in cs] if n in a.all else [])
        if n in pre_ov:
            pre = pre_ov[n]
            if not all(x.startswith(pre) for x in base):
                sys.exit(f'#{num}: --prefix text is not the start of old, new and the candidates in play')
            p = len(pre)
        else:
            p = safe_prefix(base, common_prefix(base))
        if n in suf_ov:
            suf = suf_ov[n]
            if not all(x.endswith(suf) for x in base):
                sys.exit(f'#{num}: --suffix text is not the end of old, new and the candidates in play')
            s = len(suf)
        else:
            s = safe_suffix([x[p:] for x in base], common_suffix([x[p:] for x in base]))
        para = next((pp for pp in paras if m.group(0) in pp), None)
        if para is None:
            print(f'#{num}: marker not found inside one paragraph; skipped')
            continue
        masked = MARK.sub(lambda mm: mm.group(3), para)
        anchor = re.search(r'// \{SC ([\d.]+)\}', para).group(1)

        def cut(x):
            return x[p:len(x) - s] if s else x[p:]

        old2 = cut(old)
        while (not old2 or masked.count(old2) != 1) and p > 0 and n not in pre_ov:
            p = safe_prefix(base, p - 1)
            old2 = cut(old)
        pre, suf = old[:p], (old[len(old) - s:] if s else '')
        new2 = cut(new)
        note2, whole = note, []
        for k, t, c in cs:
            if t.startswith(pre) and (not suf or t.endswith(suf)) and len(t) >= p + s:
                note2 = note2.replace(f'new{k}: {t}{c}', f'new{k}: {cut(t)}{c}', 1)
            else:
                whole.append(k)
        if whole:
            ks = ', '.join(f'new{k}' for k in whole)
            verb = 'replaces' if len(whole) == 1 else 'replace'
            note2 = note2.replace(f'new{whole[0]}: ', f'{ks} {verb} the whole span {old}; new{whole[0]}: ', 1)
        body = f'{old2} -> {new2}' + (f'|{note2}' if note2 else '')
        marker2 = f'{pre}[[{cls} #{num}|{body}]]{suf}'
        i = masked.find(old2)
        print('=' * 100)
        print(f'#{num} {cls} {{SC {anchor}}} prefix_dropped={p} suffix_dropped={s} whole={whole}')
        print('OLD:', old2)
        print('NEW:', new2)
        for k, t, c in cs:
            print(f'new{k}:', (t + '  [WHOLE]') if k in whole else cut(t), '|', c.strip(', '))
        print('CTX:', masked[max(0, i - 160): i + len(old2) + 160])
        print('MARKER2:', marker2)


if __name__ == '__main__':
    main()
