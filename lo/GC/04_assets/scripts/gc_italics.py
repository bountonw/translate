#!/usr/bin/env python3
"""gc_italics.py — bring the White Estate's italics into the English source of GC, and list them.

The White Estate's own copy of the book (the EGW Writings download under ~/programming/bible/,
book 132) marks italics with <em>. The English source in lo/GC/00_source/ has none. This
script reads every <em> span of the book's paragraphs and finds it in the paragraph of the
same {GC n.n} anchor.

    python3 lo/GC/04_assets/scripts/gc_italics.py               counts only
    python3 lo/GC/04_assets/scripts/gc_italics.py --report F    every span as a TSV in F
    python3 lo/GC/04_assets/scripts/gc_italics.py --apply       write the italics into 00_source
    python3 lo/GC/04_assets/scripts/gc_italics.py --packet DIR N   the paragraphs for N readers
    python3 lo/GC/04_assets/scripts/gc_italics.py --verify OUT F...  check the readers' rows

The readers pair each English italic span with the Lao words that render it; --verify then
reads from the Lao file, not from the reader, whether those words are italic.

A span is written as *span*, with a trailing comma, full stop, colon or semicolon left outside
the asterisks. --apply writes only a span whose text occurs exactly once in its paragraph and
is not already italic; every other span is reported with its status and left alone.

The TSV has one row per span: anchor, kind (citation for a work's title or Ibid. inside a
source reference, text otherwise), the span, its status in the English (italic, applied,
plain, absent, ambiguous), and the number of italic spans in the Lao paragraph of the same
anchor in lo/GC/03_public/.
"""
import collections, glob, html, json, os, re, sys, zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
EN = os.path.join(ROOT, 'lo', 'GC', '00_source')
LO = os.path.join(ROOT, 'lo', 'GC', '03_public')
ZIP = os.path.expanduser('~/programming/bible/egw-download/egw-data/PWBRSPX93T.com.whiteestate.library/'
                         'Application Support/zips/en/2/4/132.zip')
EM = re.compile(r'<em>(.*?)</em>', re.S)
ANCHOR = re.compile(r'^## \{GC ([^}]+)\}\s*$', re.M)
TRAIL = ',.;:'


def spans():
    """(anchor, span text, words before, words after, paragraph text) for every <em> span."""
    out = []
    with zipfile.ZipFile(ZIP) as z:
        names = sorted((n for n in z.namelist() if re.match(r'132\.\d+\.json$', n)),
                       key=lambda n: int(n.split('.')[1]))
        for n in names:
            for p in json.loads(z.read(n)):
                ref = p.get('refcode_short') or ''
                if not ref.startswith('GC ') or '<em>' not in p['content']:
                    continue
                marked = p['content'].replace('<em>', '\x01').replace('</em>', '\x02')
                marked = html.unescape(re.sub(r'<[^>]+>', '', marked))
                plain = marked.replace('\x01', '').replace('\x02', '')
                for m in re.finditer('\x01([^\x02]*)\x02', marked):
                    s = m.group(1).strip().rstrip(TRAIL + ' ')
                    if s:
                        before = marked[:m.start()].replace('\x01', '').replace('\x02', '')
                        after = marked[m.start() + 1 + m.group(1).find(s) + len(s):]
                        after = after.replace('\x01', '').replace('\x02', '')
                        out.append((ref[3:], s, before, after, plain))
    return out


def locate(body, span, before, after):
    """Offsets of the span in body: every occurrence if the context is not needed, else the
    one occurrence whose neighbouring words match the White Estate's."""
    for form in (span, span.replace("'", '’')):
        hits = [m.start() for m in re.finditer(re.escape(form), body)]
        if len(hits) == 1:
            return hits, form
        if hits:
            for n in (30, 20, 12, 6):
                left = before[-n:].replace("'", '’')
                right = after[:n].replace("'", '’')
                for both in (True, False):
                    ctx = []
                    for h in hits:
                        # an asterisk already written beside the span does not count
                        k, e = h - (body[h - 1:h] == '*'), h + len(form) + (body[h + len(form):h + len(form) + 1] == '*')
                        lm, rm = body[max(0, k - len(left)):k].endswith(left), body[e:].startswith(right)
                        if (lm and rm) if both else (lm or rm):
                            ctx.append(h)
                    if len(ctx) == 1:
                        return ctx, form
            return hits, form
    return [], span


def paragraphs(folder, suffix):
    """{anchor: (path, start, end)} for every paragraph body of the files in folder."""
    out = {}
    for path in sorted(glob.glob(os.path.join(folder, '*' + suffix))):
        t = open(path, encoding='utf-8').read()
        heads = list(ANCHOR.finditer(t))
        for i, h in enumerate(heads):
            end = heads[i + 1].start() if i + 1 < len(heads) else len(t)
            out.setdefault(h.group(1), (path, h.end(), end))
    return out


def kind(span, plain):
    """citation when the span is Ibid. or a title inside a source reference after a dash."""
    if span.startswith('Ibid'):
        return 'citation'
    i = plain.find(span)
    before = plain[max(0, i - 4):i]
    return 'citation' if ('—' in before or '(See' in plain[max(0, i - 6):i]) else 'text'


IT = re.compile(r'\*([^*\n]+)\*')


def packets(folder, n):
    """Write the paragraphs whose English has italics into n JSONL files for the readers, in
    book order: anchor, the English with its italic spans listed, the Lao with its footnotes."""
    en, lo = paragraphs(EN, '_en.md'), paragraphs(LO, '_lo.md')
    recs = []
    for anchor, (path, a, b) in en.items():
        body = open(path, encoding='utf-8').read()[a:b].strip()
        if not IT.search(body) or anchor not in lo:
            continue
        lp, la, lb = lo[anchor]
        recs.append({'anchor': anchor, 'chapter': os.path.basename(lp)[:4], 'en': body,
                     'en_italics': IT.findall(body),
                     'lo': open(lp, encoding='utf-8').read()[la:lb].strip()})
    size = -(-len(recs) // n)
    for i in range(n):
        with open(os.path.join(folder, f'batch{i + 1}.jsonl'), 'w', encoding='utf-8') as f:
            for r in recs[i * size:(i + 1) * size]:
                f.write(json.dumps(r, ensure_ascii=False) + '\n')
    print(f'{len(recs)} paragraphs in {n} batches of up to {size}')


def verify(files, out):
    """Check the readers' rows (anchor, English span, Lao words) against the Lao paragraph: the
    Lao words must occur in it as written, and whether they are italic is read from the file."""
    lo = paragraphs(LO, '_lo.md')
    count = collections.Counter()
    with open(out, 'w', encoding='utf-8') as w:
        w.write('anchor\tenglish\tlao\tstatus\tnote\n')
        for f in files:
            for line in open(f, encoding='utf-8').read().splitlines()[1:]:
                parts = line.split('\t')
                anchor, span, lao = parts[0], parts[1], parts[2] if len(parts) > 2 else ''
                note = parts[3] if len(parts) > 3 else ''
                if anchor not in lo:
                    status = 'no-paragraph'
                elif not lao:
                    status = 'no-lao'
                else:
                    path, a, b = lo[anchor]
                    t = open(path, encoding='utf-8').read()[a:b]
                    hits = [m.start() for m in re.finditer(re.escape(lao), t)]
                    # a common word occurs more than once; it counts as italic when one of
                    # its occurrences is
                    inside = any(m.start() <= i and i + len(lao) <= m.end()
                                 for i in hits for m in IT.finditer(t))
                    if inside:
                        status = 'italic'
                    elif hits:
                        status = 'plain'
                    elif lao in t.replace('*', ''):
                        # the words are there with asterisks inside them: italic in parts
                        status = 'split'
                    else:
                        status = 'not-found'
                count[status] += 1
                w.write('\t'.join((anchor, span, lao, status, note)) + '\n')
    for k, v in sorted(count.items()):
        print(f'{k:12} {v}')


def main():
    if '--packet' in sys.argv:
        i = sys.argv.index('--packet')
        return packets(sys.argv[i + 1], int(sys.argv[i + 2]))
    if '--verify' in sys.argv:
        i = sys.argv.index('--verify')
        return verify(sys.argv[i + 2:], sys.argv[i + 1])
    apply = '--apply' in sys.argv
    report = sys.argv[sys.argv.index('--report') + 1] if '--report' in sys.argv else None
    en, lo = paragraphs(EN, '_en.md'), paragraphs(LO, '_lo.md')
    texts = {}
    rows, count = [], collections.Counter()
    edits = collections.defaultdict(set)
    found = spans()
    times = collections.Counter((a, s) for a, s, *_ in found)
    for anchor, span, before, after, plain in found:
        if anchor not in en:
            # the appendix notes and the front matter have no paragraph in 00_source
            status = 'no-paragraph'
        else:
            path, a, b = en[anchor]
            body = texts.setdefault(path, open(path, encoding='utf-8').read())[a:b]
            # a word that occurs several times is placed by the words around it; the download
            # writes a straight apostrophe where the source has a curly one
            hits, form = locate(body, span, before, after)
            if not hits:
                status = 'absent'
            elif body[max(0, hits[0] - 1)] == '*':
                status = 'italic'
            elif len(hits) > 1 and len(hits) != times[(anchor, span)]:
                status = 'ambiguous'
            else:
                # several hits left only when the text is italic at every occurrence,
                # as two "Ibid." in one paragraph
                status = 'applied' if apply else 'plain'
                for h in hits:
                    edits[path].add((a + h, a + h + len(form)))
        lo_count = 0
        if anchor in lo:
            path, a, b = lo[anchor]
            lo_count = len(re.findall(r'\*[^*\n]+\*', open(path, encoding='utf-8').read()[a:b]))
        k = kind(span, plain)
        count[(k, status)] += 1
        rows.append((anchor, k, span, status, str(lo_count)))
    if apply:
        for path, spans_ in edits.items():
            t = texts[path]
            for s, e in sorted(spans_, reverse=True):
                t = t[:s] + '*' + t[s:e] + '*' + t[e:]
            open(path, 'w', encoding='utf-8').write(t)
    if report:
        with open(report, 'w', encoding='utf-8') as f:
            f.write('anchor\tkind\tspan\tenglish\tlao_italic_spans\n')
            for r in rows:
                f.write('\t'.join(r) + '\n')
    for (k, status), n in sorted(count.items()):
        print(f'{k:9} {status:10} {n}')
    print(f'spans: {len(rows)}; files written: {len(edits) if apply else 0}')


if __name__ == '__main__':
    main()
