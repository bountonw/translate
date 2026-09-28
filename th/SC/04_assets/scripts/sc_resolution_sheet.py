#!/usr/bin/env python3
"""Resolution sheet and run check for an SC Thai chapter.

    python3 th/SC/04_assets/scripts/sc_resolution_sheet.py --chapter 12
    python3 th/SC/04_assets/scripts/sc_resolution_sheet.py --chapter 12 --round qa1

Writes ~/claude-sandbox/sc-audit/scNN-resolution-sheet.md: one block per
[[...]] marker with its number, class, severity, anchor, old and new sides,
note, and the full English paragraph, so the translator resolves from the
sheet. Damaged markers are listed under RESIDUE; the translator's {{Q|...}}
questions under QUESTIONS.

With --round it is also the run check: every marker well formed; numbers 1..N
each once (letter families #12a #12b allowed); classes and severities allowed
in the round; no marker inside the #chapter header, an #EGW tag or an anchor
comment; every old side present in the chapter as committed at HEAD; nothing
under th/SC modified or untracked except this chapter. It prints the counts
table and a VERDICT line, and exits 1 on FAIL.
"""
import argparse
import re
import subprocess
import sys
from collections import Counter

from sc_common import (chapter_path, source_path, parse_thai, parse_english,
                       committed_text, MARKER, SANDBOX, ROOT)

ANY_MARKER = re.compile(r"\[\[(.*?)\]\]", re.S)
QUESTION = re.compile(r"\{\{Q(?P<num>#\d+[a-z]?)?\s*\|?(?P<q>.*?)\}\}", re.S)
NO_SEV = {"SPELL", "GRAM", "REF", "NOTE", "READ", "CHOICE", "FIX"}
ROUND_CLASSES = {
    "qa1": {"SPELL", "GRAM", "REF", "NOTE", "FACT", "OMISSION", "ADDITION", "ALIGN"},
    "qa2": {"SPELL", "GRAM", "REF", "NOTE", "FACT", "OMISSION", "ADDITION", "ALIGN", "TERM", "CLARITY", "READ", "CHOICE"},
    "check": {"FIX"},
}


def git_status():
    try:
        out = subprocess.run(["git", "-C", str(ROOT), "status", "--short", "--", "th/SC"],
                             capture_output=True, text=True, check=True)
        return out.stdout.splitlines()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--chapter", type=int, required=True)
    ap.add_argument("--round", choices=sorted(ROUND_CLASSES), help="also run the run check for this round")
    a = ap.parse_args()
    chapter = chapter_path(a.chapter)
    text = chapter.read_text(encoding="utf-8")
    head, paras = parse_thai(text)
    english = parse_english(source_path(a.chapter).read_text(encoding="utf-8"))
    committed = committed_text(chapter)
    rel = chapter.resolve().relative_to(ROOT)

    blocks, residue, questions, problems, notes = [], [], [], [], []
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
                problems.append(f"#{num} {{SC {p.anchor}}}: old side not in the committed chapter")
            line = body[:m.start()].rsplit("\n", 1)[-1]
            if line.lstrip().startswith("//") or "#EGW[" in body[m.start():m.end()] or "#EGW[" in line and "]" not in line:
                problems.append(f"#{num} {{SC {p.anchor}}}: marker inside an anchor comment or #EGW tag")
            if a.round:
                allowed = ROUND_CLASSES[a.round]
                if cls not in allowed:
                    problems.append(f"#{num} {{SC {p.anchor}}}: class {cls} is not allowed in {a.round}")
                if cls in NO_SEV and sev:
                    problems.append(f"#{num} {{SC {p.anchor}}}: {cls} carries no severity")
                if cls not in NO_SEV and not sev:
                    problems.append(f"#{num} {{SC {p.anchor}}}: {cls} needs HIGH or MED")
                if sev == "LOW":
                    problems.append(f"#{num} {{SC {p.anchor}}}: LOW is never written")
            if not new and not note.strip():
                problems.append(f"#{num} {{SC {p.anchor}}}: empty new side with an empty note")
            blocks.append(
                f"## #{num} {cls}{' ' + sev if sev else ''} — {{SC {p.anchor}}}\n\n"
                f"OLD: {old or '(insertion)'}\n\nNEW: {new or '(deletion, or an open question where the note begins verify:)'}\n\n"
                f"NOTE: {note}\n\n"
                + ("WARNING: the old side is not in the committed chapter.\n\n" if missing else "")
                + f"EN {{SC {p.anchor}}}: {english.get(p.anchor, '(no English paragraph carries this anchor)')}\n")
        for m in ANY_MARKER.finditer(body):
            if not any(s <= m.start() < e for s, e in seen):
                residue.append(f"- {{SC {p.anchor}}} damaged: [[{m.group(1)[:80]}")
        if body.count("[[") != body.count("]]"):
            residue.append(f"- {{SC {p.anchor}}} unterminated: {body.count('[[')} opening and {body.count(']]')} closing")
        for m in QUESTION.finditer(body):
            questions.append(f"- {{SC {p.anchor}}} {m.group('num') or ''} {m.group('q').strip()}")

    # Numbering: bare numbers once each, 1..N; a lettered family counts as one number.
    bare = [int(n) for n in numbers if n.isdigit()]
    families = {}
    for n in numbers:
        if not n.isdigit():
            families.setdefault(int(n[:-1]), []).append(n[-1])
    dup = [n for n, c in Counter(bare).items() if c > 1]
    both = [n for n in families if n in bare]
    all_nums = set(bare) | set(families)
    top = max(all_nums) if all_nums else 0
    gaps = [n for n in range(1, top + 1) if n not in all_nums]
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
                if path == rel.as_posix():
                    continue
                if line.startswith("??"):
                    problems.append(f"repo: untracked {path}")
                else:
                    notes.append(f"repo: {line.strip()} is modified; another session's work unless it is yours")

    SANDBOX.mkdir(parents=True, exist_ok=True)
    out = SANDBOX / f"sc{a.chapter:02d}-resolution-sheet.md"
    parts = [f"# SC{a.chapter:02d} resolution sheet — {rel}\n"] + (blocks or ["No intact markers.\n"])
    if residue:
        parts.append("## RESIDUE\n\n" + "\n".join(residue) + "\n")
    if questions:
        parts.append("## QUESTIONS\n\n" + "\n".join(questions) + "\n")
    out.write_text("\n".join(parts), encoding="utf-8")

    print(f"sheet: {out}")
    print("| Class | HIGH | MED | Total |")
    print("|---|---|---|---|")
    for cls in sorted({c for c, _ in counts}):
        h, m_ = counts[(cls, "HIGH")], counts[(cls, "MED")]
        print(f"| {cls} | {h} | {m_} | {sum(v for (c, _), v in counts.items() if c == cls)} |")
    print(f"| Total | {sum(v for (_, s), v in counts.items() if s == 'HIGH')} | "
          f"{sum(v for (_, s), v in counts.items() if s == 'MED')} | {sum(counts.values())} |")
    for n in notes:
        print(f"NOTE: {n}")
    for pr in problems:
        print(f"PROBLEM: {pr}")
    print(f"markers: {len(numbers)} intact, top number #{top}, {len(residue)} damaged")
    if a.round:
        print(f"VERDICT: {'PASS' if not problems else 'FAIL — %d problem(s)' % len(problems)}")
        return 1 if problems else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
