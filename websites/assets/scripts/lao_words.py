"""Mark Lao words on the web pages so lines break only where the print does.

Lao has no spaces between words, so a browser breaks lines with its own word
list, and that list splits names and long words the print keeps whole. This
module splits each run of Lao letters with the dictionaries the GC print build
uses (lo/assets/dictionaries and the book's own), wraps every piece in
<span class="w">, which the stylesheet keeps whole, and puts a <wbr> break
point between pieces. A piece is a dictionary word, or the part of one up to
a break the dictionary allows (~~~, ~~~~, ~~~~~). In a word of 11 or more
characters, the dictionary's soft hyphens also stay, as &shy; between pieces,
so a long word can break with a hyphen as in the print.

Splitting takes a few minutes for a whole book, so chapters are split side by
side, and the results are kept in websites/assets/temp/ (ignored by git) and
reused until a dictionary file changes.
"""
import contextlib
import hashlib
import io
import json
import multiprocessing
import os
import re
import sys
import warnings

ASSETS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(ASSETS))
HELPERS = os.path.join(REPO, 'lo', 'GC', '04_assets', 'scripts', 'helpers')
DICTIONARIES = [os.path.join(REPO, 'lo', 'assets', 'dictionaries'),
                os.path.join(REPO, 'lo', 'GC', '04_assets', 'scripts', 'dictionaries')]
CACHE = os.path.join(ASSETS, 'temp', 'words-lo.json')

LAO_RUN = re.compile('[\u0E80-\u0EFF]+')
MARK = re.compile('~S~|!!|!|~+|\u00ad|\\\\p\\{(-?\\d+)\\}')
ALLOWED = {'~~~', '~~~~', '~~~~~', '~S~'}
# A word of at least this many characters (vowel and tone marks included)
# keeps the dictionary's soft hyphens, where the print breaks with a hyphen;
# shorter words, such as the common names of God, stay whole
SOFT_HYPHEN_MIN = 11


def signature():
    """Changes whenever a dictionary file or the splitting rules change."""
    h = hashlib.sha1(f'{SOFT_HYPHEN_MIN} {MARK.pattern} {sorted(ALLOWED)} pieces-v2'.encode())
    for folder in DICTIONARIES:
        for name in sorted(os.listdir(folder)):
            h.update(name.encode())
            with open(os.path.join(folder, name), 'rb') as f:
                h.update(f.read())
    return h.hexdigest()


def pieces(segments, run):
    """The run cut at every break the book allows, or None when the split
    does not give back the run exactly. A piece that ends in a soft hyphen
    breaks with a hyphen; the others break without one."""
    out = []
    for seg in segments:
        if seg['type'] != 'dict':
            out.append(seg['text'])
            continue
        coded = seg['coded']
        long_word = len(MARK.sub('', coded)) >= SOFT_HYPHEN_MIN
        cur, i = '', 0
        while i < len(coded):
            m = MARK.match(coded, i)
            if not m:
                cur += coded[i]
                i += 1
                continue
            mark = m.group()
            if m.group(1) is not None:  # a print penalty such as \p{0}; 0 or below allows a break
                mark = '~~~' if int(m.group(1)) <= 0 else '~'
            if mark in ALLOWED and cur:
                out.append(cur)
                cur = ''
            elif mark == '\u00ad' and long_word and cur:
                out.append(cur + '\u00ad')
                cur = ''
            i = m.end()
        if cur:
            out.append(cur)
    return out if ''.join(out).replace('\u00ad', '') == run else None


def split_chapter(job):
    """Split one chapter's runs with that chapter's dictionaries."""
    chapter, book, runs = job
    sys.path[:0] = [HELPERS, os.path.dirname(HELPERS)]
    warnings.simplefilter('ignore')
    from dict_loader import load_hierarchical_dictionaries
    from lao_word_processor import parse_chunk_with_lookahead
    with contextlib.redirect_stdout(io.StringIO()):
        dictionary = load_hierarchical_dictionaries(chapter=chapter, book=book)[0]
        return chapter, {run: pieces(parse_chunk_with_lookahead(run, dictionary), run) for run in runs}


# a script or style element, whose contents are code and never marked
CODE = re.compile(r'(<(?:script|style)\b[^>]*>.*?</(?:script|style)\s*>)', re.S | re.I)


def body_parts(body):
    """The body cut into tags, whole script and style elements, and the
    text between them. Only a part that does not start with < is text."""
    for i, chunk in enumerate(CODE.split(body)):
        if i % 2:
            yield chunk
        else:
            yield from re.split(r'(<[^>]+>)', chunk)


def body_runs(page):
    body = page.split('<body>', 1)[1]
    return {run for part in body_parts(body) if not part.startswith('<')
            for run in LAO_RUN.findall(part)}


def mark_page(page, table):
    head, body = page.split('<body>', 1)

    def wrap(m):
        parts = table.get(m.group())
        if not parts:
            return m.group()
        # a soft hyphen goes between the spans, where the line may break with a
        # hyphen; the newline inside <wbr> keeps the page file in short lines,
        # which editors and diffs need, and is not text, so the page shows no space
        return ''.join(f'<span class="w">{p[:-1]}</span>&shy;' if p.endswith('\u00ad')
                       else f'<span class="w">{p}</span><wbr\n>' for p in parts[:-1]) + f'<span class="w">{parts[-1]}</span>'

    body = ''.join(part if part.startswith('<') else LAO_RUN.sub(wrap, part)
                   for part in body_parts(body))
    return head + '<body>' + body


def mark(pages, book, cache_path=CACHE):
    """pages: {page id such as GC01, or home for the site's home page: page html}.
    Returns the pages marked. Each page is split with the dictionaries of its id
    and of the book; with book None, with the Lao dictionaries alone. The cache
    keeps, for each page given, only the runs it uses now, and leaves the entries
    of every other page as they are, so marking the home page keeps the book's
    chapters in the cache."""
    sig = signature()
    cache = {}
    if os.path.exists(cache_path):
        with open(cache_path, encoding='utf-8') as f:
            saved = json.load(f)
        if saved.get('signature') == sig:
            cache = saved['chapters']
    runs = {cid: body_runs(page) for cid, page in pages.items()}
    need = [(cid, book, sorted(r - cache.get(cid, {}).keys())) for cid, r in runs.items()]
    need = [job for job in need if job[2]]
    if need:
        print(f'splitting Lao words in {len(need)} chapters...')
        # fork: workers start as copies of this process, with no server socket
        ctx = multiprocessing.get_context('fork' if sys.platform.startswith('linux') else None)
        with ctx.Pool(min(len(need), os.cpu_count() or 1)) as pool:
            for cid, result in pool.imap_unordered(split_chapter, need):
                cache.setdefault(cid, {}).update(result)
    # keep only what the pages given use now; every other page keeps its entries
    used = dict(cache)
    used.update({cid: {r: cache[cid][r] for r in runs[cid]} for cid in pages})
    if need or used != cache:
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        # written beside the cache and then put in its place, so a build
        # stopped while writing leaves the old cache whole
        with open(cache_path + '.part', 'w', encoding='utf-8') as f:
            json.dump({'signature': sig, 'chapters': used}, f, ensure_ascii=False)
        os.replace(cache_path + '.part', cache_path)
    cache = used
    return {cid: mark_page(page, cache[cid]) for cid, page in pages.items()}
