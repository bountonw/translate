"""Tests for the Lao word cache of lao_words.py.

Run from the repository root:
    python3 -m pytest websites/assets/scripts/test_lao_words.py

The cache is a temporary file, filled before each call, so no word is split
again and nothing in the repository is written. The Lao words come from the
real layout's labels.txt.
"""
import json
import os

import lao_words
from build_book import LAYOUT, read_yaml

LABELS = read_yaml(open(os.path.join(LAYOUT, 'lo', 'labels.txt'), encoding='utf-8'))
WORD, OTHER = LABELS['toc'], LABELS['chapter']


def page(text):
    return f'<html><head><title>{text}</title></head><body>\n<p>{text}</p>\n</body></html>'


def test_marking_one_page_keeps_every_other_page_in_the_cache(tmp_path):
    cache = tmp_path / 'words.json'
    chapters = {'GC01': {OTHER: [OTHER]}, 'GC02': {OTHER: [OTHER[:2], OTHER[2:]]}}
    saved = {'signature': lao_words.signature(),
             'chapters': dict(chapters, home={WORD: [WORD[:4], WORD[4:]], OTHER: [OTHER]})}
    cache.write_text(json.dumps(saved, ensure_ascii=False), encoding='utf-8')
    marked = lao_words.mark({'home': page(WORD)}, None, str(cache))['home']
    # the page is marked from the cache, its head left as it was
    assert f'<p><span class="w">{WORD[:4]}</span><wbr\n><span class="w">{WORD[4:]}</span></p>' in marked
    assert marked.startswith(f'<html><head><title>{WORD}</title></head><body>')
    # the chapters stay; the home page keeps only the words it uses now
    after = json.loads(cache.read_text(encoding='utf-8'))
    assert after['chapters'] == dict(chapters, home={WORD: [WORD[:4], WORD[4:]]})
    # the cache is written beside itself first, and nothing of that is left
    assert not os.path.exists(str(cache) + '.part')


def test_marking_leaves_an_unchanged_cache_file_as_it_is(tmp_path):
    cache = tmp_path / 'words.json'
    saved = {'signature': lao_words.signature(),
             'chapters': {'GC01': {OTHER: [OTHER]}, 'home': {WORD: [WORD]}}}
    cache.write_text(json.dumps(saved, ensure_ascii=False), encoding='utf-8')
    before = os.stat(cache).st_mtime_ns, cache.read_bytes()
    lao_words.mark({'home': page(WORD)}, None, str(cache))
    lao_words.mark({'GC01': page(OTHER)}, None, str(cache))
    assert (os.stat(cache).st_mtime_ns, cache.read_bytes()) == before


def test_a_new_signature_drops_every_entry(tmp_path):
    cache = tmp_path / 'words.json'
    saved = {'signature': 'an older dictionary', 'chapters': {'GC01': {OTHER: [OTHER]}, 'home': {WORD: [WORD]}}}
    cache.write_text(json.dumps(saved, ensure_ascii=False), encoding='utf-8')
    # the page holds no Lao, so nothing is split
    lao_words.mark({'home': page('laoegw.com')}, None, str(cache))
    after = json.loads(cache.read_text(encoding='utf-8'))
    assert after == {'signature': lao_words.signature(), 'chapters': {'home': {}}}


def test_script_and_style_contents_are_never_marked(tmp_path):
    cache = tmp_path / 'words.json'
    saved = {'signature': lao_words.signature(), 'chapters': {'home': {WORD: [WORD[:4], WORD[4:]]}}}
    cache.write_text(json.dumps(saved, ensure_ascii=False), encoding='utf-8')
    script = f"<script>\nvar words = '{OTHER} {WORD}'; if (1 < 2) {{ words += '<b>'; }}\n</script>"
    style = f"<style>p::after {{ content: '{OTHER}'; }}</style>"
    source = f'<html><head></head><body>\n{script}\n<p>{WORD}</p>\n{style}\n</body></html>'
    marked = lao_words.mark({'home': source}, None, str(cache))['home']
    # the script and the style stand as they were; the text around them is marked
    assert script in marked and style in marked
    assert f'<p><span class="w">{WORD[:4]}</span><wbr\n><span class="w">{WORD[4:]}</span></p>' in marked
    # and no word of the script or the style is split or kept in the cache
    assert lao_words.body_runs(source) == {WORD}
    after = json.loads(cache.read_text(encoding='utf-8'))
    assert after['chapters'] == {'home': {WORD: [WORD[:4], WORD[4:]]}}
