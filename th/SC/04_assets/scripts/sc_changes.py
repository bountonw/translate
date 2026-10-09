#!/usr/bin/env python3
"""Changes file for one SC Thai chapter: every paragraph that differs from a
base commit. Reads the repository; writes one file under ~/claude-sandbox/.

    python3 th/SC/04_assets/scripts/sc_changes.py --chapter 01 --base 8490e626~1
    python3 th/SC/04_assets/scripts/sc_changes.py --chapter 01 --base COMMIT --out PATH

Compares the chapter at the base commit, searched under th/SC/03_public,
02_edit and 01_raw, with the chapter in the working tree, paragraph by
"// {SC ###.#}" anchor, and writes one block per changed paragraph:

    EN       the English paragraph
    BASE     the Thai at the base commit
    CURRENT  the Thai now, any marker masked to its old side
    CHANGED  each differing line, the old run in [- -] and the new in {+ +},
             widened to the nearest space or punctuation so a run never
             splits a Thai word

Paragraphs that differ only in punctuation or spacing are listed by anchor at
the end and get no block. The base for the qa3 reader is the parent of the
chapter's QA1 commit. Writes ~/claude-sandbox/sc-audit/scNN-changes.md unless
--out is given.
"""
import argparse
import difflib
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sc_common import (ROOT, SANDBOX, STAGES, chapter_path, source_path,  # noqa: E402
                       parse_thai, parse_english, mask_markers)

PUNCT_ONLY = re.compile(r"[\s.,;:!?\"'()\[\]“”‘’…\-–—*_#^/]+")
BOUNDARY = set(" \t.,;:!?\"'()[]“”‘’…-–—*_")


def base_text(base, nn):
    name = f"SC{nn}_th.typ"
    for stage in STAGES:
        rel = f"th/SC/{stage}/{name}"
        r = subprocess.run(["git", "-C", str(ROOT), "cat-file", "-p", f"{base}:{rel}"],
                           capture_output=True, text=True)
        if r.returncode == 0:
            return rel, r.stdout
    sys.exit(f"{name} not found at {base} under th/SC/01_raw, 02_edit or 03_public")


def body(para):
    return [ln.rstrip() for ln in para.lines if ln.strip()]


def norm(s):
    return PUNCT_ONLY.sub("", s)


def widen(s, lo, hi):
    while lo > 0 and s[lo - 1] not in BOUNDARY:
        lo -= 1
    while hi < len(s) and s[hi] not in BOUNDARY:
        hi += 1
    return lo, hi


def inline_diff(o, n):
    """One old/new line pair as [-old-]{+new+} runs on phrase boundaries."""
    ops = difflib.SequenceMatcher(None, o, n, autojunk=False).get_opcodes()
    ranges = []
    for tag, i1, i2, j1, j2 in ops:
        if tag == "equal":
            continue
        a1, a2 = widen(o, i1, i2)
        b1, b2 = widen(n, j1, j2)
        left = min(i1 - a1, j1 - b1)
        right = min(a2 - i2, b2 - j2)
        ranges.append([i1 - left, i2 + right, j1 - left, j2 + right])
    merged = []
    for r in ranges:
        if merged and r[0] <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], r[1])
            merged[-1][3] = max(merged[-1][3], r[3])
        else:
            merged.append(r)
    out, po = [], 0
    for i1, i2, j1, j2 in merged:
        out.append(o[po:i1])
        old, new = o[i1:i2], n[j1:j2]
        if old:
            out.append("[-" + old + "-]")
        if new:
            out.append("{+" + new + "+}")
        po = i2
    out.append(o[po:])
    return "".join(out)


def changed_lines(base_lines, cur_lines):
    out = []
    sm = difflib.SequenceMatcher(None, base_lines, cur_lines, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        olds, news = base_lines[i1:i2], cur_lines[j1:j2]
        for k in range(max(len(olds), len(news))):
            if k < len(olds) and k < len(news):
                out.append(inline_diff(olds[k], news[k]))
            elif k < len(olds):
                out.append("[-" + olds[k] + "-]")
            else:
                out.append("{+" + news[k] + "+}")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--chapter", required=True)
    ap.add_argument("--base", required=True, help="commit whose chapter text is the earlier state")
    ap.add_argument("--out")
    args = ap.parse_args()
    nn = f"{int(args.chapter):02d}"

    chapter = chapter_path(nn)
    cur_rel = chapter.relative_to(ROOT).as_posix()
    base_rel, base_src = base_text(args.base, nn)
    _, base_paras = parse_thai(base_src)
    _, cur_paras = parse_thai(mask_markers(chapter.read_text(encoding="utf-8")))
    english = parse_english(source_path(nn).read_text(encoding="utf-8"))
    base_by = {p.anchor: p for p in base_paras}

    out_path = Path(args.out).expanduser() if args.out else SANDBOX / f"sc{nn}-changes.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [f"# SC{nn} changes — base {args.base} ({base_rel}) against {cur_rel}", ""]
    changed, punct_only, missing = 0, [], []
    for cur in cur_paras:
        base = base_by.get(cur.anchor)
        if base is None:
            missing.append(cur.anchor)
            continue
        b, c = body(base), body(cur)
        if b == c:
            continue
        if norm("\n".join(b)) == norm("\n".join(c)):
            punct_only.append(cur.anchor)
            continue
        changed += 1
        lines += [f"## {{SC {cur.anchor}}}", "",
                  "EN", english.get(cur.anchor, "NO ENGLISH PARAGRAPH at this anchor"), "",
                  "BASE", *b, "",
                  "CURRENT", *c, "",
                  "CHANGED", *changed_lines(b, c), ""]
    lines += ["## Punctuation or spacing only", "",
              ", ".join(f"{{SC {a}}}" for a in punct_only) or "none", ""]
    if missing:
        lines += ["## Anchors absent at the base", "", ", ".join(f"{{SC {a}}}" for a in missing), ""]
    out_path.write_text("\n".join(lines), encoding="utf-8")
    summary = f"paragraphs {len(cur_paras)}; changed {changed}; punctuation only {len(punct_only)}; absent at base {len(missing)}"
    print(summary)
    print(f"written {out_path}")


if __name__ == "__main__":
    main()
