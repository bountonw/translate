"""Tests for the link to the home page at the top of every book page.

Run from the repository root:
    python3 -m pytest websites/assets/scripts/test_build_book.py

Only the real chapter layout and the committed GC pages are read; the link
check runs in a temporary folder, and nothing in the repository is written.
"""
import os
import re

import check_book
from build_book import LAYOUT, SITE

HEADER = os.path.join(LAYOUT, 'lo', 'chapter_header.html')


def home_link(root):
    return f'    <header class="site-header"><a href="{root}">laoegw.com</a></header>\n'


def test_chapter_header_opens_the_body_with_the_home_link():
    header = open(HEADER, encoding='utf-8').read()
    # a chapter page lives in <site>/<BOOK>/chapters/, two folders below the site's root,
    # as the header's own stylesheet link, from the root that the build fills in, says
    assert '<link rel="stylesheet" href="{{root}}css/style.css">' in header
    assert header.split('<body>\n', 1)[1] == home_link('{{root}}')


def test_home_link_leads_to_the_site_root_from_a_chapter_and_the_contents_page(tmp_path):
    (tmp_path / 'GC' / 'chapters').mkdir(parents=True)
    chapter = str(tmp_path / 'GC' / 'chapters' / '01_a_chapter.html')
    contents = str(tmp_path / 'GC' / 'index.html')
    assert check_book.broken_links(chapter, ['../../']) == ['../../']
    assert check_book.broken_links(contents, ['../']) == ['../']
    (tmp_path / 'index.html').write_text('', encoding='utf-8')
    assert check_book.broken_links(chapter, ['../../']) == []
    assert check_book.broken_links(contents, ['../']) == []


def test_every_committed_gc_page_opens_with_the_home_link():
    folder = os.path.join(SITE, 'lo', 'GC')
    chapters = sorted(os.listdir(os.path.join(folder, 'chapters')))
    pages = [('index.html', '../../')] + [(os.path.join('chapters', name), '../../../') for name in chapters]
    assert len(chapters) == 43
    for rel, root in pages:
        page = open(os.path.join(folder, rel), encoding='utf-8').read()
        assert re.split(r'<body>\n', page, maxsplit=1)[1].startswith(home_link(root)), rel
        assert page.count('class="site-header"') == 1, rel


def test_settings_reads_the_list_of_a_metadata_file(tmp_path):
    from build_book import settings
    meta = tmp_path / 'metadata.yaml'
    meta.write_text('---\nlang: th-TH\nsettings:\n  - strip_reference_codes_on_output\n...\n', encoding='utf-8')
    assert settings(str(meta)) == ['strip_reference_codes_on_output']
    meta.write_text('---\nlang: lo-LA\nbook:\n  title:\n    lo: ກ\n', encoding='utf-8')
    assert settings(str(meta)) == []


def test_a_hidden_code_leaves_the_paragraph_its_id_and_no_code():
    from build_book import to_html
    text = 'ก ข {LBF 7.1}\n\n> ค  \n> ง {LBF 28.3}\n'
    shown, hidden = to_html(text), to_html(text, strip_codes=True)
    assert '<p id="LBF7.1">ก ข <span class="egw"><a href="#LBF7.1">{LBF 7.1}</a></span></p>' in shown
    assert '<p id="LBF7.1">ก ข</p>' in hidden
    assert '<p id="LBF28.3">ค<br>\nง</p>' in hidden
    assert '{LBF' not in hidden and 'class="egw"' not in hidden


def test_a_note_in_a_comment_is_left_off_the_page_and_out_of_the_check():
    from build_book import prepare
    body = '## {LBF 15.1}\n\nก<!--a note\nto the translator-->ข {LBF 15.1}\n'
    assert '<!--' not in prepare(body) and 'note' not in prepare(body)
    assert check_book.letters(check_book.md_parts(body)[0]) == 'กขLBF151'
