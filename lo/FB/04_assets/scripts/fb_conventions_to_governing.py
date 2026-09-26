#!/usr/bin/env python3
"""One-time conversion of the translator's web-project conventions into the Lao governing files.

    python3 lo/FB/04_assets/scripts/fb_conventions_to_governing.py [--force]

Reads sections 5 and 6 of lo/FB/04_assets/planning/web-instructions.txt and writes
lo/assets/translation_profile/lao-profile.txt and lao-glossary.txt on the model of
th/assets/translation_profile/thai-profile.txt and thai-glossary.txt, copying every Lao form out
of the source file. It refuses to overwrite an existing output unless --force is given, because
the translator edits those files after adjudication.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "lo/FB/04_assets/planning/web-instructions.txt"
PROFILE = ROOT / "lo/assets/translation_profile/lao-profile.txt"
GLOSSARY = ROOT / "lo/assets/translation_profile/lao-glossary.txt"
BOOKS_EN = ["Genesis", "Exodus", "Psalms", "Isaiah", "Acts", "Colossians", "Hebrews", "Revelation"]


def items(text, start, end):
    """{item number: text} for the numbered items between two headings, continuation lines joined."""
    block = text[text.index(start):text.index(end)]
    out, cur = {}, None
    for line in block.splitlines():
        m = re.match(r"^(\d\.[A-Z](?:\.\d+)?)\s+(.*)$", line)
        if m:
            cur = m.group(1)
            out[cur] = m.group(2).strip()
        elif cur and line.startswith(" ") and line.strip():
            out[cur] += " " + line.strip()
    return out


def entries6(text):
    """(english, lao, note) for every locked term of section 6."""
    block = text[text.index("6. Locked terminology"):text.index("7. Output rules")]
    rows = []
    for line in block.splitlines()[1:]:
        s = line.strip()
        if not s or s.startswith("otherwise;"):
            continue
        if s.startswith("("):
            en, lao, note = rows[-1]
            rows[-1] = (en, lao, (note + " " + s.strip("()")).strip())
            continue
        for entry in s.split(" | "):
            en, _, rest = entry.partition(" — ")
            note = ""
            m = re.match(r"^(.*?)\s+\((.*)\)$", rest)
            if m:
                rest, note = m.group(1), m.group(2)
            pairs = [q.strip() for q in rest.split("; ")]
            lao = pairs[0]
            for extra in pairs[1:]:
                label, _, form = extra.partition(" — ")
                lao += " / " + form.strip()
                note = (note + "; " if note else "") + f"{label.strip()}: {form.strip()}"
            rows.append((en.strip(), lao, note))
    return rows


def main():
    force = "--force" in sys.argv
    for p in (PROFILE, GLOSSARY):
        if p.exists() and not force:
            print(f"{p} exists; pass --force to overwrite")
            return 1
    text = SRC.read_text(encoding="utf-8")
    it = items(text, "5. Binding conventions", "6. Locked terminology")

    P = ["# Lao translation profile", "",
         "Read this file and lao-glossary.txt before drafting or auditing Lao. Where they are silent, the translator's finished books are the precedent, the published GC first; precedent guides, it never rules. A line that opens with a book code binds that book and guides the others until the translator widens it.",
         "", "## 1. Philosophy", "",
         "1.A. Ellen White's books are translated dynamically. FB: statements of belief are translated formally, close to the wording; assert no more and no less than the English.",
         "", "## 2. Orthography", ""]
    for i, key in enumerate(["5.A.1", "5.A.2", "5.A.3", "5.A.4", "5.A.5", "5.A.6", "5.A.7"]):
        P.append(f"2.{chr(65 + i)}. FB: {it[key]}")
    P += ["", "## 3. Punctuation and style", ""]
    for i, key in enumerate(["5.B.1", "5.B.2", "5.B.3", "5.B.4", "5.B.5"]):
        P.append(f"3.{chr(65 + i)}. FB: {it[key]}")
    P += ["", "## 4. Scripture quotations", "", f"4.A. FB: {it['5.C.1']}",
          "", "## 5. Reference line", "", f"5.A. FB: {it['5.D.1']}", f"5.B. FB: {it['5.D.2']}",
          "", "## 6. Text", "",
          "6.A. Western numerals only.",
          "6.B. No invisible characters; a zero-width space is never written into a manuscript. Line breaking is decided at typesetting time, never in a manuscript.",
          ""]
    PROFILE.parent.mkdir(parents=True, exist_ok=True)
    PROFILE.write_text("\n".join(P), encoding="utf-8")

    G = ["# Lao Glossary — shared by every Lao project (GC, AA, FB, ...)", "",
         "<!-- Being built. A row enters this file only after the translator adjudicates it. The GC rows stay in lo/GC/04_assets/translation_profile/GC-glossary.txt until the glossary rework moves them here. A row's Notes name the book that ruled it and the anchor of its evidence; [CHECK] means an agent marks any other form in that book; a row is silent otherwise. A row guides and never rules. -->",
         "", "## 1. Theological terms", "", "| English | Lao | Notes |", "|---|---|---|"]
    for en, lao, note in entries6(text):
        notes = "[CHECK] FB 6.1" + (f". {note}" if note else "")
        G.append(f"| {en} | {lao} | {notes} |")
    names = re.search(r"\):\s*(.*?)\.\s*Extend", it["5.D.2"]).group(1).split(", ")
    G += ["", "## 2. Proper nouns", "", "| English | Lao | Notes |", "|---|---|---|"]
    for en, lao in zip(BOOKS_EN, names):
        G.append(f"| {en} | {lao} | [CHECK] FB reference line; LCV-compatible |")
    G.append("")
    GLOSSARY.write_text("\n".join(G), encoding="utf-8")
    print(f"wrote {PROFILE.relative_to(ROOT)} ({len(' '.join(P).split())} words) and {GLOSSARY.relative_to(ROOT)} ({len(entries6(text))} term rows, {len(names)} book rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
