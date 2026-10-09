#!/usr/bin/env python3
"""Turn the remaining [[...]] markers of a DA chapter into editor parentheses.

    python3 th/DA/04_assets/scripts/da_editor_markers.py --chapter 12
    python3 th/DA/04_assets/scripts/da_editor_markers.py --chapter 12 --markers 12 14

Run only on the translator's "editor DANN". Each marker becomes a parenthesis
in the editor's convention, the standing wording labelled original: and first:
((original:old/new)), or ((original:old/new1/new2)) where the note carried a
second candidate as new2. An insertion (empty old) becomes ((original:/new))
and a proposed deletion (empty new) becomes ((original:old/)). A marker whose
note begins verify: offers no wording and is left standing. An editor's choice
already in the chapter, ((A/B)) from da-fixer, stands as it is. The label
"original:" appears only in editor parentheses, never in a marker. The chapter
is rewritten in place; the translator reviews the diff.
"""
import argparse
import re
import sys
from pathlib import Path

from da_common import chapter_path, MARKER

NEW2 = re.compile(r"new2:\s*([^|;]+)")


def convert(m, wanted):
    num = m.group("num")
    if wanted and num not in wanted:
        return m.group(0), None
    note = m.group("note")
    if note.strip().lower().startswith("verify:"):
        return m.group(0), None
    old, new = m.group("old"), m.group("new")
    cands = [new] if new else []
    n2 = NEW2.search(note)
    if n2:
        cands.append(n2.group(1).strip())
    return "((original:" + "/".join([old] + cands) + "))", num


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--chapter", type=int, required=True, help="chapter number; 0 is the preface")
    ap.add_argument("--markers", nargs="*", default=[], help="marker numbers to convert; all remaining when omitted")
    ap.add_argument("--file", help="a chapter file to rewrite in place of the chapter's own file (testing)")
    a = ap.parse_args()
    wanted = {m.lstrip("#") for m in a.markers}
    path = Path(a.file) if a.file else chapter_path(a.chapter)
    text = path.read_text(encoding="utf-8")
    done, left = [], []

    def sub(m):
        out, num = convert(m, wanted)
        (done if num else left).append(m.group("num"))
        return out

    new_text = MARKER.sub(sub, text)
    if done:
        path.write_text(new_text, encoding="utf-8")
    print(f"converted {len(done)} marker(s): {' '.join('#' + n for n in done) or 'none'}")
    print(f"left standing {len(left)} marker(s): {' '.join('#' + n for n in left) or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
