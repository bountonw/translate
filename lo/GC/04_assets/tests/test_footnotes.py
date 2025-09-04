from scripts.helpers import md_footnotes_to_tex as foot
import re

def test_find_orphan_def_ids():
    assert foot.find_orphan_def_ids("tests/test_footnotes.md") == ["2"]

def test_find_orphan_marker_ids():
    assert foot.find_orphan_marker_ids("tests/test_footnotes.md") == ["3"]

def test_inline_marker_order_characterization():
    """Asserts behavior of RE_MARKER_INLINE; no public API"""

    md_text = foot.read_md_text("tests/test_footnotes.md")
    first_match = foot.RE_MARKER_INLINE.search(md_text)
    inline_ids = [
            match.group(1) for match in 
            foot.RE_MARKER_INLINE.finditer(md_text)
            ]
    
    assert first_match
    assert first_match.group(0) == "[^1]"
    assert first_match.group(1) == "1"
    assert inline_ids == ["1","3","x"]

def test_defs_map_single_line():
    defs_by_id = foot.get_defs_by_id("tests/test_footnotes.md")
    ids = defs_by_id.keys()
    
    assert ids == {"1","2","x"}

# TODO: Find out the set of the last character of all footnotes in GC (all rounds). For those that aren't ".", found out why and fix. Do we need a rule that forces "." as a footnote line ending?

#       Create a helper file that is for pre-module1 and create a pre-module1. 
#       Find out what the current 

# def get_defs_by_id(file_path: str | Path) -> dict:
#     md_text = read_md_text(file_path)
#     def_pairs = RE_DEF_LINE.findall(md_text)
#     defs_by_id = {def_id[0]: def_id[1].strip() for def_id in def_pairs}
# 
#     return defs_by_id
# 
#    1.2) Work: read the text, use `RE_DEF_LINE.findall(...)` to get `(id, text)` pairs, strip the text.
#    1.3) Output: a `dict[id -> single-line definition text]`.
#    1.4) Policy: **single-line** defs only; “last definition wins” if duplicates.
# 
# 2. What the A2 test should prove (two checks only).
#    2.1) The **set of keys** equals `{"1","2","x"}`.
#    2.2) The **value for "1"** equals `"This one is used."`.
# 
# 3. Why these checks (and not more).
#    3.1) Keys confirm that your regex is finding all definition **heads** correctly.
#    3.2) The value check proves you’re extracting the **text after the colon** cleanly (and that `.strip()` works as intended).
# 
# 4. Common pitfalls if A2 fails (how to think).
#    4.1) **FileNotFoundError** → confirm the exact path string is `tests/test_footnotes.md` (with the “s”).
#    4.2) **Wrong keys** → print the keys once with `-s` to see what your regex captured; check your `RE_DEF_LINE` anchors (`^` and `re.MULTILINE`).
#    4.3) **Wrong value** → look for trailing punctuation or spaces in the fixture; `.strip()` should remove spaces, not punctuation.
# 
# 5. Tiny docstring improvement (optional, no code change required right now).
#    5.1) Clarify the return type: “`dict[str, str]` mapping ID → single-line def text.”
#    5.2) Note limitation: “single-line only; multi-line handled in p10.”
# 
# 6. Acceptance for A2.
#    6.1) Add the two assertions described in (2) to a new test named `test_defs_map_single_line`.
#    6.2) Run your usual pytest command.
#    6.3) Expected: **4 passed**. If not, share the last \~10 lines and we’ll fix exactly that.
# 
# 7. When A2 is green, we’ll take the next atom: write a **RED** test for p8 (calling a not-yet-existing `replace_first_matching_marker_in_text(...)` and checking `used_id == "1"` + only that first occurrence replaced). One assertion at a time—no code from me until you’re ready.

######
#SANDBOX
######
def test_finditer_digits():
    text = "ab12cd034ef56"
    pattern = r"\d+"
    my_list = [match.group(0) for match in re.finditer(pattern, text)]
    my_list_span = [match.span() for match in re.finditer(pattern, text)]

    assert my_list == ["12", "034", "56"]
    assert my_list_span == [(2, 4), (6, 9), (11, 13)]

def test_finditer_captured_pairs():
    text = "x12 y34 z56"
    pattern = r"(\d)(\d)"
    whole_match = [match.group(0) for match in re.finditer(pattern, text)]
    first_capture = [match.group(1) for match in re.finditer(pattern, text)]
    match_spans = [match.span() for match in re.finditer(pattern, text)]

    assert whole_match == ["12", "34", "56"]
    assert first_capture == ["1", "3", "5"]
    assert match_spans == [(1,3), (5,7), (9,11)]

def test_replace_first_only():
    text = "a foo b foo c"
    pattern = r"\bfoo\b"
    first_match = [match.group(0) for match in re.finditer(pattern, text)][0]
    match_spans = [match.span() for match in re.finditer(pattern, text)][0]
    replaced_text = f"{text[0:match_spans[0]]}FOO{text[match_spans[1]:]}"


    assert replaced_text == "a FOO b foo c"
    assert replaced_text.count("FOO") == 1
    assert replaced_text.count("foo") == 1

# https://docs.python.org/3/library/exceptions.html#exception-hierarchy
