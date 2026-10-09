#!/usr/bin/env python3
"""Resolution sheet and run check for a DA Thai chapter.

    python3 th/DA/04_assets/scripts/da_resolution_sheet.py --chapter 12
    python3 th/DA/04_assets/scripts/da_resolution_sheet.py --chapter 12 --round draft

Writes ~/claude-sandbox/da-audit/daNN-resolution-sheet.md: one block per
[[...]] marker with its number, class, severity, anchor, old and new sides,
note, and the full English paragraph, so the translator resolves from the
sheet. Damaged markers are listed under RESIDUE; the translator's {{Q|...}}
questions under QUESTIONS; editor's choices ((A/B)) under CHOICES.

With --round it is also the run check: every marker well formed; numbers each
once (letter families #12a #12b allowed); classes allowed in the round (draft:
VERSE TERM FACT OMISSION ADDITION REF NOTE SPELL GRAM CLARITY PRINT SUBTITLE;
flags: FLAG; check: FIX); severity HIGH, MED or LOW on FACT, OMISSION,
ADDITION, TERM and CLARITY and on no other class; no marker inside the
#chapter header, an #EGW tag or an anchor comment; every old side present in
the chapter as committed at HEAD; nothing under th/DA modified or untracked
except this chapter. It prints the counts table and a VERDICT line, and exits
1 on FAIL. Chapter 0 is the preface.
"""
import argparse
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

from da_common import (chapter_path, source_path, parse_thai, parse_english, committed_text,
                       MARKER, SANDBOX, ROOT, ROUND_CLASSES, WITH_SEVERITY, EDITOR_CHOICE)

ANY_MARKER = re.compile(r"\[\[(.*?)\]\]", re.S)
QUESTION = re.compile(r"\{\{Q(?P<num>#\d+[a-z]?)?\s*\|?(?P<q>.*?)\}\}", re.S)


def git_status():
    try:
        out = subprocess.run(["git", "-C", str(ROOT), "status", "--short", "--", "th/DA"],
                             capture_output=True, text=True, check=True)
        return out.stdout.splitlines()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--chapter", type=int, required=True, help="chapter number; 0 is the preface")
    ap.add_argument("--round", choices=sorted(ROUND_CLASSES), help="also run the run check for this round")
    ap.add_argument("--file", help="a chapter file to read in place of the chapter's own file (testing)")
    a = ap.parse_args()
    chapter = Path(a.file) if a.file else chapter_path(a.chapter)
    text = chapter.read_text(encoding="utf-8")
    head, paras = parse_thai(text)
    english = parse_english(source_path(a.chapter).read_text(encoding="utf-8"))
    committed = committed_text(chapter) if not a.file else None
    try:
        rel = chapter.resolve().relative_to(ROOT)
    except ValueError:
        rel = chapter

    blocks, residue, questions, choices, problems, notes = [], [], [], [], [], []
    counts = Counter()
    numbers = []
    if "[[" in "\n".join(head):
        problems.append("a marker sits in the chapter header")
    for p in paras:
        body = p.text
        seen = set()
        for m in MARKER.finditer(body):
            seen.add(m.span())
            cls, sev, num, old, new, note = (m.group(k) for k in ("cls", "sev", "num", "old", "new", "note"))
            numbers.append(num)
            counts[(cls, sev or "")] += 1
            missing = bool(old) and committed is not None and old not in committed
            if missing:
                problems.append(f"#{num} {{DA {p.anchor}}}: old side not in the committed chapter")
            line = body[:m.start()].rsplit("\n", 1)[-1]
            if line.lstrip().startswith("//") or "#EGW[" in body[m.start():m.end()] or "#EGW[" in line and "]" not in line:
                problems.append(f"#{num} {{DA {p.anchor}}}: marker inside an anchor comment or #EGW tag")
            if a.round:
                allowed = ROUND_CLASSES[a.round]
                if cls not in allowed:
                    problems.append(f"#{num} {{DA {p.anchor}}}: class {cls} is not allowed in {a.round}")
            if cls not in WITH_SEVERITY and sev:
                problems.append(f"#{num} {{DA {p.anchor}}}: {cls} carries no severity")
            if cls in WITH_SEVERITY and not sev:
                problems.append(f"#{num} {{DA {p.anchor}}}: {cls} needs HIGH, MED or LOW")
            if "original:" in old or "original:" in new:
                problems.append(f"#{num} {{DA {p.anchor}}}: the word original: belongs in an editor's parenthesis, never in a marker")
            if not new and not note.strip():
                problems.append(f"#{num} {{DA {p.anchor}}}: empty new side with an empty note")
            blocks.append(
                f"## #{num} {cls}{' ' + sev if sev else ''} — {{DA {p.anchor}}}\n\n"
                f"OLD: {old or '(insertion)'}\n\nNEW: {new or '(deletion, or an open question where the note begins verify:)'}\n\n"
                f"NOTE: {note}\n\n"
                + ("WARNING: the old side is not in the committed chapter.\n\n" if missing else "")
                + f"EN {{DA {p.anchor}}}: {english.get(p.anchor, '(no English paragraph carries this anchor)')}\n")
        for m in ANY_MARKER.finditer(body):
            if not any(s <= m.start() < e for s, e in seen):
                residue.append(f"- {{DA {p.anchor}}} damaged: [[{m.group(1)[:80]}")
        if body.count("[[") != body.count("]]"):
            residue.append(f"- {{DA {p.anchor}}} unterminated: {body.count('[[')} opening and {body.count(']]')} closing")
        for m in QUESTION.finditer(body):
            questions.append(f"- {{DA {p.anchor}}} {m.group('num') or ''} {m.group('q').strip()}")
        for m in EDITOR_CHOICE.finditer(body):
            choices.append(f"- {{DA {p.anchor}}} {m.group(0)[:120]}")

    # Numbering: bare numbers once each; a lettered family counts as one number.
    bare = [int(n) for n in numbers if n.isdigit()]
    families = {}
    for n in numbers:
        if not n.isdigit():
            families.setdefault(int(n[:-1]), []).append(n[-1])
    dup = [n for n, c in Counter(bare).items() if c > 1]
    both = [n for n in families if n in bare]
    all_nums = set(bare) | set(families)
    top = max(all_nums) if all_nums else 0
    low = min(all_nums) if all_nums else 0
    gaps = [n for n in range(low, top + 1) if n not in all_nums]
    if dup:
        problems.append(f"duplicated numbers: {' '.join('#%d' % n for n in dup)}")
    if both:
        problems.append(f"numbers both bare and lettered: {' '.join('#%d' % n for n in both)}")
    if gaps:
        problems.append(f"missing numbers: {' '.join('#%d' % n for n in gaps)}")
    for n, letters in families.items():
        if letters != [chr(ord('a') + i) for i in range(len(letters))]:
            problems.append(f"#{n} letters run {' '.join(letters)}, not a b c in order")
    if residue:
        problems.append(f"{len(residue)} damaged or unterminated marker(s)")

    if a.round:
        st = git_status()
        if st is None:
            problems.append("git status could not be read")
        else:
            for line in st:
                path = line[3:].strip()
                if path == rel.as_posix() or "/.claude/" in path:
                    continue
                if line.startswith("??"):
                    problems.append(f"repo: untracked {path}")
                else:
                    notes.append(f"repo: {line.strip()} is modified; another session's work unless it is yours")

    SANDBOX.mkdir(parents=True, exist_ok=True)
    out = SANDBOX / f"da{a.chapter:02d}-resolution-sheet.md"
    parts = [f"# DA{a.chapter:02d} resolution sheet — {rel}\n"] + (blocks or ["No intact markers.\n"])
    if residue:
        parts.append("## RESIDUE\n\n" + "\n".join(residue) + "\n")
    if questions:
        parts.append("## QUESTIONS\n\n" + "\n".join(questions) + "\n")
    if choices:
        parts.append("## CHOICES\n\n" + "\n".join(choices) + "\n")
    out.write_text("\n".join(parts), encoding="utf-8")

    print(f"sheet: {out}")
    print("| Class | HIGH | MED | LOW | Total |")
    print("|---|---|---|---|---|")
    for cls in sorted({c for c, _ in counts}):
        h, m_, l = counts[(cls, "HIGH")], counts[(cls, "MED")], counts[(cls, "LOW")]
        print(f"| {cls} | {h} | {m_} | {l} | {sum(v for (c, _), v in counts.items() if c == cls)} |")
    print(f"| Total | {sum(v for (_, s), v in counts.items() if s == 'HIGH')} | "
          f"{sum(v for (_, s), v in counts.items() if s == 'MED')} | "
          f"{sum(v for (_, s), v in counts.items() if s == 'LOW')} | {sum(counts.values())} |")
    for n in notes:
        print(f"NOTE: {n}")
    for pr in problems:
        print(f"PROBLEM: {pr}")
    print(f"markers: {len(numbers)} intact, numbers #{low} to #{top}, {len(residue)} damaged, {len(choices)} editor's choice(s)")
    if a.round:
        print(f"VERDICT: {'PASS' if not problems else 'FAIL — %d problem(s)' % len(problems)}")
        return 1 if problems else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
