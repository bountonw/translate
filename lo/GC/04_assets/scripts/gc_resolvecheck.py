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
# The textlint job's list of known-wrong Lao spellings, in "wrong # correct" rows.
# Section 10 of the glossary and this file are two lists of the same kind, and a
# form held only here used to reach a commit and come back as a CI failure.
FORBIDDEN = ROOT / ".tooling" / "forbidden_terms" / "lao.txt"

CLASSES = "OMISSION ADDITION FACT REF NOTE ALIGN SPELL TERM GRAM CLARITY FIX REVERT REWORD".split()
MIN_SPELL_LEN = 4

# A whole, well-formed marker. Passes 1 to 3 hunt for the debris a half-deleted
# marker leaves behind — a close bracket, an arrow, a pipe, a note fragment —
# and every one of those is also a normal part of an intact marker. Reporting
# them against an intact marker produced six BROKEN lines describing a marker
# that was perfectly sound, which buries the one line that matters when a
# marker really has been torn open. So an intact marker is masked out of those
# passes and reported once, on its own line, as still standing.
MARKER_FULL = re.compile(
    r"\[\[(?:" + "|".join(CLASSES) + r") (?:HIGH|MED|LOW) #(\d+[a-z]?)\|([^|]*)\|.*?\]\]",
    re.S)


def mask_markers(text):
    """The text with every intact marker blanked, and the markers found.

    Blanks are the same length as what they replace, so every character offset
    taken from the masked text still points at the right place in the original
    and anchor_of keeps working.
    """
    found = []

    def blank(m):
        found.append((m.group(1), m.start()))
        return " " * len(m.group())

    return MARKER_FULL.sub(blank, text), found


def resolve_markers(line):
    """One line with each intact marker replaced by the span it stands over.

    Blanking would leave a run of spaces that the doubled-space check reports,
    and deleting would close two words up against each other. Putting the old
    side back gives the line the shape it has once the marker is resolved,
    which is the text these line-by-line passes are meant to judge.
    """
    return MARKER_FULL.sub(lambda m: m.group(2).split(" -> ")[0], line)

# Section 10 candidates Brian has already adjudicated, keyed by {GC ###.#}
# anchor. A section 10 row can be context-dependent -- ທ່ານ is a wrong form
# only of the Pope, and correct as an ordinary honorific before a personal
# name -- so a site that is right in its own context would otherwise be
# re-offered on every run and cost a pass to re-clear each time. Add a ref
# here only once the site has been judged, never to quiet a live finding.
SETTLED = {
    "281.3": {"ທ່ານ"},  # honorific before a personal name: ທ່ານ ໂວນແຕ (Voltaire)
    "299.1": {"ທ່ານ"},  # same honorific: ທ່ານ ເອນົກ (Enoch), ທ່ານ ໂຢບ (Job)
    "370.2": {"ທ່ານ"},  # second person in Matthew 24 and Revelation 3, and of Jesus; not the Pope
    "494.1": {"ທ່ານ"},  # "Thou hast said" of Isaiah 14:13, addressed to Lucifer; not the Pope
    "559.1": {"ທ່ານ"},  # second person inside the Isaiah 8:19 quotation; not the Pope
}
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
    """The {GC ###.#} heading governing a character offset.

    Only a heading line counts. A marker note cites other paragraphs by
    anchor, and counting those made a finding at {GC 494.1} report itself as
    {GC 45.1}, a paragraph in another chapter, because that ref stood inside
    the note. A wrong anchor is worse than none: it sends the reader to real
    text that has nothing to do with the finding.
    """
    heads = [(m.start(), m.group(1))
             for m in re.finditer(r"^##\s*\{GC (\d+\.\d+)\}\s*$", text, re.M)]
    if not heads:
        heads = [(m.start(), m.group(1)) for m in re.finditer(r"\{GC (\d+\.\d+)\}", text)]
    cur = "?"
    for pos, a in heads:
        if pos > idx:
            break
        cur = a
    return cur


def incorrect_forms():
    """Known-incorrect spellings from the glossary's spelling table.

    The table is located the way gc_termcheck.py locates it, by its header row rather
    than by a section number. Anchoring on "## 10." meant that renumbering or retitling
    the section made this return nothing at all, and a spelling pass that checks no
    forms reports clean — a silent pass rather than an error.

    Guards match gc_termcheck.py, which already settled this: only [CHECK] rows count,
    and forms shorter than MIN_SPELL_LEN are skipped because a short Lao string sits
    inside unrelated words (ພະ inside ພະຍານາກ). Prefix rules need a whitelist and
    belong in a dedicated grep session, not here.
    """
    if not GLOSSARY.exists():
        return []
    forms, in_spelling = [], False
    for row in GLOSSARY.read_text(encoding="utf-8").splitlines():
        row = row.strip()
        if not row.startswith("|"):
            continue
        cells = [c.strip() for c in row.strip("|").split("|")]
        if not cells or not cells[0] or set(cells[0]) <= set("-: "):
            continue
        head = cells[0].lower()
        if head in ("english", "word"):
            in_spelling = head == "word"
            continue
        if not in_spelling or len(cells) < 4:
            continue
        if "[CHECK]" not in cells[3].upper():
            continue
        for bad in re.split(r"\s*/\s*", cells[2]):
            bad = bad.strip()
            if len(bad) >= MIN_SPELL_LEN and LAO.search(bad):
                forms.append((bad, cells[1]))
    seen = {bad for bad, _ in forms}
    for bad, good in linter_forms():
        if bad not in seen:
            forms.append((bad, good))
    return forms


def linter_forms():
    """Known-wrong forms from the textlint job's list, as (wrong, correct) pairs.

    Every row there is a settled correction, so no [CHECK] gate applies. The
    MIN_SPELL_LEN guard still does, because a short Lao string sits inside
    unrelated words and would report a correct word as misspelled.
    """
    if not FORBIDDEN.exists():
        return []
    out = []
    for row in FORBIDDEN.read_text(encoding="utf-8").splitlines():
        row = row.strip()
        if not row or row.startswith("#"):
            continue
        bad, _, good = row.partition("#")
        bad, good = bad.strip(), good.strip()
        if len(bad) >= MIN_SPELL_LEN and good and LAO.search(bad):
            out.append((bad, good))
    return out


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

    # --- pass 0: Lao and Thai digits, chapter-wide ---
    # Numerals are always Western (root CLAUDE.md 5.A). The substitution is invisible
    # in print — the Lao digit zero closely resembles a vowel — so it is swept
    # mechanically here rather than left to a reader's eye. Costs milliseconds.
    for m in re.finditer(r"[\u0ED0-\u0ED9\u0E50-\u0E59]", text):
        flag("BROKEN", anchor_of(text, m.start()),
             f"Lao or Thai digit character U+{ord(m.group()):04X}; numerals must be Western",
             text[max(0, m.start() - 25):m.start() + 25].replace("\n", " "))

    # --- pass 0b: zero-width spaces, chapter-wide ---
    # A verse pasted from an online Bible arrives with U+200B between every
    # word. It is invisible in the editor and survives into print, so the file
    # must carry none before it is committed.
    for m in re.finditer("\u200B", text):
        flag("BROKEN", anchor_of(text, m.start()),
             "zero-width space U+200B; strip before committing",
             text[max(0, m.start() - 25):m.start() + 25].replace("\n", " "))

    # --- pass 0c: Thai letters, chapter-wide ---
    # A wrong keyboard produces Thai where Lao was meant, and the two scripts
    # resemble each other closely enough that the eye slides over it. Thai
    # inside \thai{...} is deliberate — GC09 cites the Thai spelling of a word
    # in a footnote — so that span is masked, length preserved so offsets hold.
    # Thai digits are excluded here; pass 0 already reports them.
    masked = re.sub(r"\\thai\{[^}]*\}", lambda m: " " * len(m.group()), text)
    for m in re.finditer(r"[\u0E00-\u0E4F\u0E5A-\u0E7F]", masked):
        flag("BROKEN", anchor_of(text, m.start()),
             f"Thai character U+{ord(m.group()):04X} in Lao text; wrong keyboard",
             text[max(0, m.start() - 25):m.start() + 25].replace("\n", " "))

    # --- intact markers: reported once each, then masked out of passes 1 to 3 ---
    swept, standing = mask_markers(text)
    swept_changed = [(ln, resolve_markers(line), line) for ln, line in changed]
    for num, pos in standing:
        flag("BROKEN", anchor_of(text, pos),
             f"marker #{num} still standing; resolve it before this check")

    # --- pass 1: marker residue, chapter-wide ---
    for pat, msg in [(r"\[\[", "unresolved or half-deleted marker"),
                     (r"\]\]", "marker close bracket"),
                     (r"\{\{", "inline question to the conductor"),
                     (r"\}\}", "inline question close"),
                     (r"verify:", "marker note fragment"),
                     (r"\b(" + "|".join(CLASSES) + r") (HIGH|MED|LOW) #", "marker header fragment")]:
        for m in re.finditer(pat, swept):
            flag("BROKEN", anchor_of(text, m.start()), msg,
                 text[max(0, m.start() - 25):m.start() + 25].replace("\n", " "))

    # --- pass 2: splice leftovers, changed lines only ---
    for ln, line, raw in swept_changed:
        for pat, msg in [(r"->", "splice arrow left in the text"),
                         (r"\|", "stray pipe from a marker field")]:
            if re.search(pat, line):
                flag("BROKEN", anchor_of(text, text.find(raw)), msg, line[:60])

    # --- pass 3: mechanical, changed lines only ---
    bad_forms = incorrect_forms()
    for ln, line, raw in swept_changed:
        anchor = anchor_of(text, text.find(raw)) if line.strip() else "?"
        if "  " in line:
            flag("FIX", anchor, "doubled space")
        if re.search(r"\s+[,.;:!?]", line):
            flag("FIX", anchor, "space before punctuation")
        # A digit before the mark means a scripture citation or a thousands
        # separator (4:18, 1,000), neither of which takes a following space.
        # A closing quotation mark or an ellipsis after the mark is likewise
        # correct and takes no space -- ,” and ;… are how a quoted clause ends
        # -- so they are excluded rather than re-offered on every run.
        # A footnote marker attaches directly to the punctuation it follows
        # (ຊາເລັມ,[^16]), which is correct typography and takes no space.
        if re.search(r"(?<!\d)[,;:](?=[^\s”’\"'…\[])", line):
            flag("FIX", anchor, "punctuation with no following space")
        stripped = re.sub(r"\([^)]*\)", "", line)
        # A cited periodical or work title is given as the Lao kind-word plus
        # the full English title in Latin script, italicised. That English is
        # deliberate, so an italicised span is exempt from the ASCII rule.
        stripped = re.sub(r"\*[^*\n]+\*", "", stripped)
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
                if bad in SETTLED.get(anchor, ()):
                    continue
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
