#!/usr/bin/env python3
"""Turn the remaining [[...]] markers of an SC chapter into editor parentheses.

    python3 th/SC/04_assets/scripts/sc_editor_markers.py --chapter 12
    python3 th/SC/04_assets/scripts/sc_editor_markers.py --chapter 12 --markers 12 14

Run only on the translator's "editor SCNN". Each marker becomes a parenthesis in
his own convention, the current wording first: (old/new), or (old/new1/new2)
where the note carried a second candidate as new2. An insertion (empty old)
becomes (/new) and a proposed deletion (empty new) becomes (old/). A marker
whose note begins verify: offers no wording and is left standing. The chapter
is rewritten in place; the translator reviews the diff.
"""
import argparse
import re
import sys

from sc_common import chapter_path, MARKER

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
    if not cands:
        return f"({old}/)", num
    return "(" + "/".join([old] + cands) + ")", num


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--chapter", type=int, required=True)
    ap.add_argument("--markers", nargs="*", default=[], help="marker numbers to convert; all remaining when omitted")
    a = ap.parse_args()
    wanted = {m.lstrip("#") for m in a.markers}
    path = chapter_path(a.chapter)
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
