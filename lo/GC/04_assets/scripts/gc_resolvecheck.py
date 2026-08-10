#!/usr/bin/env python3
"""Mechanical passes of a GC resolve-check, done deterministically instead of by an agent.

Covers gc-resolve-check passes 1, 2 and 3 — marker residue, splice leftovers, spacing,
stray ASCII, known-incorrect spellings, and the footnote chain. What it cannot do is
pass 4, the judgment read: whether the Lao still parses and still reads aloud. Run this
first, fix what it lists, and dispatch the agent only for the judgment read on the
paragraphs it reports as changed.

    python3 lo/GC/04_assets/scripts/gc_resolvecheck.py 11
    python3 lo/GC/04_assets/scripts/gc_resolvecheck.py 11 --base HEAD

Exit status is 0 when clean, 1 when it found something.
"""
import argparse, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
GLOSSARY = ROOT / "lo/GC/04_assets/translation_profile/GC-glossary.txt"

CLASSES = "OMISSION ADDITION FACT REF NOTE ALIGN SPELL TERM GRAM CLARITY FIX".split()
MIN_SPELL_LEN = 4
LAO = re.compile(r"[຀-໿]")


def git(*args):
    return subprocess.run(["git", "-C", str(ROOT), *args],
                          capture_output=True, text=True, check=True).stdout


def changed_lines(rel, base):
    """Added lines in the working tree, as (line_number, text)."""
    diff = git("diff", "-U0", base, "--", rel)
    out, ln = [], 0
    for line in diff.splitlines():
        m = re.match(r"^@@ -\S+ \+(\d+)(?:,(\d+))? @@", line)
        if m:
            ln = int(m.group(1))
            continue
        if line.startswith("+") and not line.startswith("+++"):
            out.append((ln, line[1:]))
            ln += 1
    return out


def anchor_of(text, idx):
    """The {GC ###.#} heading governing a character offset."""
    heads = [(m.start(), m.group(1)) for m in re.finditer(r"\{GC (\d+\.\d+)\}", text)]
    cur = "?"
    for pos, a in heads:
        if pos > idx:
            break
        cur = a
    return cur


def incorrect_forms():
    """Known-incorrect spellings from glossary section 10.

    Guards match gc_termcheck.py, which already settled this: only [CHECK] rows count,
    and forms shorter than MIN_SPELL_LEN are skipped because a short Lao string sits
    inside unrelated words (ພະ inside ພະຍານາກ). Prefix rules need a whitelist and
    belong in a dedicated grep session, not here.
    """
    if not GLOSSARY.exists():
        return []
    text = GLOSSARY.read_text(encoding="utf-8")
    sec = re.search(r"^##\s*10\..*?$(.*?)^##\s*11\.", text, re.M | re.S)
    if not sec:
        return []
    forms = []
    for row in sec.group(1).splitlines():
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        if len(cells) < 4 or not cells[0] or set(cells[0]) <= set("-: "):
            continue
        if "[CHECK]" not in cells[3].upper():
            continue
        for bad in re.split(r"\s*/\s*", cells[2]):
            bad = bad.strip()
            if len(bad) >= MIN_SPELL_LEN and LAO.search(bad):
                forms.append((bad, cells[1]))
    return forms


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("chapter")
    ap.add_argument("--base", default="HEAD")
    a = ap.parse_args()

    nn = a.chapter.upper().removeprefix("GC").zfill(2)
    rel = f"lo/GC/03_public/GC{nn}_lo.md"
    path = ROOT / rel
    if not path.exists():
        sys.exit(f"no such chapter: {rel}")

    text = path.read_text(encoding="utf-8")
    changed = changed_lines(rel, a.base)
    findings = []

    def flag(kind, anchor, msg, span=""):
        findings.append((kind, anchor, msg, span))

    # --- pass 1: marker residue, chapter-wide ---
    for pat, msg in [(r"\[\[", "unresolved or half-deleted marker"),
                     (r"\]\]", "marker close bracket"),
                     (r"\{\{", "inline question to the conductor"),
                     (r"\}\}", "inline question close"),
                     (r"verify:", "marker note fragment"),
                     (r"\b(" + "|".join(CLASSES) + r") (HIGH|MED|LOW) #", "marker header fragment")]:
        for m in re.finditer(pat, text):
            flag("BROKEN", anchor_of(text, m.start()), msg,
                 text[max(0, m.start() - 25):m.start() + 25].replace("\n", " "))

    # --- pass 2: splice leftovers, changed lines only ---
    for ln, line in changed:
        for pat, msg in [(r"->", "splice arrow left in the text"),
                         (r"\|", "stray pipe from a marker field")]:
            if re.search(pat, line):
                flag("BROKEN", anchor_of(text, text.find(line)), msg, line[:60])

    # --- pass 3: mechanical, changed lines only ---
    bad_forms = incorrect_forms()
    for ln, line in changed:
        anchor = anchor_of(text, text.find(line)) if line.strip() else "?"
        if "  " in line:
            flag("FIX", anchor, "doubled space")
        if re.search(r"\s+[,.;:!?]", line):
            flag("FIX", anchor, "space before punctuation")
        # A digit before the mark means a scripture citation or a thousands
        # separator (4:18, 1,000), neither of which takes a following space.
        if re.search(r"(?<!\d)[,;:](?=\S)", line):
            flag("FIX", anchor, "punctuation with no following space")
        stripped = re.sub(r"\([^)]*\)", "", line)
        stripped = re.sub(r"\[\^\d+\]:?", "", stripped)
        stripped = re.sub(r"\{GC [\d.]+\}", "", stripped)
        for m in re.finditer(r"[A-Za-z]{2,}", stripped):
            flag("FIX", anchor, f"ASCII outside parentheses: {m.group(0)}")
        for bad, good in bad_forms:
            # An incorrect form is often a substring of its own correct form
            # (ພິ່ນ inside ເພິ່ນ). Mask the correct form before looking.
            if bad in line.replace(good, "\x00" * len(good)):
                # CHECK, not FIX: some section 10 rows are context-dependent
                # (ທ່ານ is wrong only of the Pope), so these are candidates.
                flag("CHECK", anchor, f"possible incorrect spelling, row says {good}", bad)

    # --- pass 3b: footnote chain, chapter-wide ---
    body = re.sub(r"^\[\^(\d+)\]:.*$", "", text, flags=re.M)
    refs = [int(n) for n in re.findall(r"\[\^(\d+)\]", body)]
    defs = [int(n) for n in re.findall(r"^\[\^(\d+)\]:", text, flags=re.M)]
    for n in sorted(set(refs) - set(defs)):
        flag("BROKEN", "?", f"footnote [^{n}] referenced but never defined")
    for n in sorted(set(defs) - set(refs)):
        flag("BROKEN", "?", f"footnote [^{n}] defined but never referenced")
    for n in sorted({n for n in defs if defs.count(n) > 1}):
        flag("BROKEN", "?", f"footnote [^{n}] defined more than once")
    if refs != sorted(refs):
        first = next(i for i in range(1, len(refs)) if refs[i] < refs[i - 1])
        flag("BROKEN", "?", f"footnote numbering out of text order at [^{refs[first]}]")

    # --- report ---
    paras = sorted({anchor_of(text, text.find(l)) for _, l in changed if l.strip()},
                   key=lambda s: [float(x) for x in s.split(".")] if s != "?" else [0])
    if not findings:
        print(f"OK  GC{nn} mechanical passes clean — "
              f"{len(changed)} changed lines in {len(paras)} paragraphs")
        print(f"    judgment read still needed: {', '.join(paras)}")
        return 0

    seen, uniq = set(), []
    for f in findings:
        if f[:3] not in seen:
            seen.add(f[:3])
            uniq.append(f)
    for kind, anchor, msg, span in uniq:
        print(f"{kind}  {{GC {anchor}}}  {msg}" + (f"  |  {span}" if span else ""))
    print(f"\n    {len(uniq)} mechanical findings; "
          f"judgment read still needed: {', '.join(paras)}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
