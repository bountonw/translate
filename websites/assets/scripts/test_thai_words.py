"""Tests for the Thai word marks of thai_words.py.

Run from the repository root:
    python3 -m pytest websites/assets/scripts/test_thai_words.py

The words come from the real Thai break list, th/assets/typeset/thai-breaks.txt,
or from a list written to a temporary folder; nothing in the repository is
written.
"""
import thai_words

LIST = open(thai_words.BREAKS, encoding='utf-8').read()
WORDS = thai_words.listed_words(LIST, 'MB', thai_words.BREAKS)
# a listed word that print may break, with its break points, and one it may not
SPLIT = next(w for w, points in WORDS.items() if len(points) == 1 and w not in thai_words.HELD_OUT)
WHOLE = next(w for w, points in WORDS.items() if not points and w not in thai_words.HELD_OUT)
SARA_I = '\u0e34'      # a vowel sign written above its letter, which no word begins with


def page(text):
    return f'<html><head><title>{text}</title></head><body>\n<p>{text}</p>\n</body></html>'


def marked(text, breaks=thai_words.BREAKS):
    return thai_words.mark({'page': page(text)}, 'MB', breaks)['page']


def test_a_listed_word_breaks_only_where_print_breaks_it_and_the_title_is_left_alone():
    cut = WORDS[SPLIT][0]
    out = marked(SPLIT)
    assert f'<title>{SPLIT}</title>' in out
    assert f'<p><span class="w">{SPLIT[:cut]}</span>&shy;<span class="w">{SPLIT[cut:]}</span></p>' in out
    assert f'<p><span class="w">{WHOLE}</span></p>' in marked(WHOLE)


def test_a_word_followed_by_a_vowel_sign_or_held_out_is_not_kept():
    assert f'<p>{WHOLE}{SARA_I}</p>' in marked(WHOLE + SARA_I)
    for word in thai_words.HELD_OUT & WORDS.keys():
        assert f'<p>{word}</p>' in marked(word)


def test_a_footnote_number_stays_with_the_letter_before_it():
    number = '<sup id="fnref:1"><a class="footnote-ref" href="#fn:1">1</a></sup>'
    out = marked(WHOLE + number)
    assert f'<p><span class="w">{WHOLE}{number}</span></p>' in out


def test_a_line_naming_a_book_counts_for_that_book_only(tmp_path):
    breaks = tmp_path / 'breaks.txt'
    breaks.write_text(f'box|{WHOLE}|none\nbox|{SPLIT}|none|MB\n', encoding='utf-8')
    assert f'<p><span class="w">{SPLIT}</span></p>' in marked(SPLIT, str(breaks))
    other = thai_words.mark({'page': page(SPLIT)}, 'SC', str(breaks))['page']
    assert f'<p>{SPLIT}</p>' in other
