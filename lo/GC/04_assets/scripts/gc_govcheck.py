#!/usr/bin/env python3
"""Verification checker for the governing-file size reduction.

The reduction moves decision history out of GC-glossary.txt and
GC-open-terms.md into history files that no agent loads. Nothing may be
lost and nothing that the audit tooling depends on may change. This
script proves both mechanically, so that no reviewer has to trust an
agent's judgment about a Lao form or about which entry was which.

It answers one question: between a baseline and the working tree, did
anything change that was supposed to stay fixed?

    GC-glossary.txt   Every row's English head cell and Lao cell stay
                      byte-identical, every bracketed tag is preserved,
                      every {GC ###.#} ref survives somewhere, row count
                      and row order and column count are unchanged, and
                      no Notes cell grows.

    GC-open-terms.md  Entry count unchanged, every entry's type prefix
                      unchanged, every site ref preserved, no entry grows.
                      That file is not a uniform list, so its headings,
                      its GC 11 assembly table and its free prose lines
                      are each watched separately rather than left out.

Two counts come from the audit scripts themselves rather than from this
one, because those scripts fail quiet: gc_termcheck.py skips a row it
cannot parse and gc_resolvecheck.py skips a spelling row without
[CHECK], neither with an error. A clean run of them is not evidence that
anything was checked, so the number of rows each actually loads is
asserted before and after.

Usage, from the repository root, by that exact relative path so the
permission allow-rules match (lo/GC/CLAUDE.md 2.D):

    python3 lo/GC/04_assets/scripts/gc_govcheck.py --snapshot
        Save the current governing files as the baseline. Do this before
        the first edit. Use this rather than --baseline git whenever
        another session has uncommitted rows in those files, which is
        usually.

    python3 lo/GC/04_assets/scripts/gc_govcheck.py
        Compare the working tree against that snapshot and report.

    python3 lo/GC/04_assets/scripts/gc_govcheck.py --baseline git
        Compare against HEAD instead. Only meaningful on a clean tree.

Exit status is 0 when every invariant holds and 1 when any is broken.
"""

import argparse
import importlib.util
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

# The repository root, found the way gc_resolvecheck.py finds it, so the
# script works from a checkout at any path.
DEFAULT_REPO = Path(__file__).resolve().parents[4]

# Run artifacts — the before-edit snapshot — stay in the sandbox, per
# lo/GC/CLAUDE.md 4.B. Only the durable history files are in the repo.
SANDBOX = Path.home() / "claude-sandbox" / "gc-audit"

PROFILE = "lo/GC/04_assets/translation_profile"
GLOSSARY_REL = f"{PROFILE}/GC-glossary.txt"
OPENTERMS_REL = f"{PROFILE}/GC-open-terms.md"

# The history files, tracked in the repository so that the record of how
# each row was decided is versioned and survives the sandbox. No agent
# reads them: lo/GC/CLAUDE.md 2.G puts the directory on the never-read
# list, which is what keeps them off every dispatch.
HISTORY_REL = "lo/GC/04_assets/history"
DEFAULT_HISTORY = [
    DEFAULT_REPO / HISTORY_REL / "GC-glossary-history.md",
    DEFAULT_REPO / HISTORY_REL / "GC-open-terms-history.md",
]

TAG = re.compile(r"\[([A-Z][A-Z ]*)\]")
SEPARATOR = re.compile(r"^\|[\s:|-]+\|$")

# GC-open-terms.md writes a site three ways — {GC 201.1}, {201.1}, and a
# bare 201.1 in the indented site lists under an entry. All three are the
# same site, so they are normalised to one key before anything is counted:
# a ref that changes shape has not been lost, and a ref that disappears
# has been, and only the second is a failure.
REF = re.compile(r"\{GC\s*[0-9]+\.[0-9]+\}|\{[0-9]+\.[0-9]+\}|\b[0-9]{1,3}\.[0-9]{1,3}\b")

# The five entry types the file actually uses. gc-batch-auditor 6.C keys
# on the first three; the other two are Brian's own housekeeping. Any
# line-initial token of this shape that is not in the set is reported, so
# that a sixth type added later cannot slip past unnoticed.
KNOWN_PREFIXES = ("DEFER-TERM", "EXCEPT-TERM", "NOTE-TERM",
                  "NOTE-SPELL", "DEFER-NOTE")
PREFIX = re.compile(r"^(" + "|".join(KNOWN_PREFIXES) + r")\b")
PREFIX_SHAPED = re.compile(r"^([A-Z]{3,}-[A-Z]{3,})\b")

# Codepoints are named rather than printed, per lo/GC/CLAUDE.md 4.G, so
# that a sweep for stray digits does not flag the rule forbidding them.
LAO = re.compile("[\u0E80-\u0EFF]+")
FORBIDDEN_DIGITS = re.compile("[\u0ED0-\u0ED9\u0E50-\u0E59]")
ZWSP = "\u200B"


# ---------------------------------------------------------------- parsing


class Row:
    """One glossary table row, parsed the way the audit scripts parse it.

    The skip rules here match gc_termcheck.parse_glossary and
    gc_resolvecheck.incorrect_forms deliberately: a row this checker
    cannot see is a row those scripts cannot see either, and that is the
    failure the whole exercise is guarding against.
    """

    def __init__(self, index, line_no, section, cells):
        self.index = index
        self.line_no = line_no
        self.section = section
        self.cells = cells

    @property
    def head(self):
        return self.cells[0]

    @property
    def lao(self):
        return self.cells[1] if len(self.cells) > 1 else ""

    @property
    def notes(self):
        return self.cells[-1] if len(self.cells) > 2 else ""

    @property
    def words(self):
        return len(REF.sub("", self.notes).split())

    def __repr__(self):
        return f"row {self.index} line {self.line_no} {self.head!r}"


def parse_glossary(text):
    """Return the table rows, in file order, headers and separators dropped."""
    rows = []
    section = "(main table)"
    for line_no, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("##"):
            section = stripped.lstrip("# ").strip()
            continue
        if not stripped.startswith("|"):
            continue
        if SEPARATOR.match(stripped):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if not cells or not cells[0]:
            continue
        if cells[0].lower() in ("english", "word"):
            continue
        rows.append(Row(len(rows), line_no, section, cells))
    return rows


class Entry:
    """One GC-open-terms.md entry: its prefixed line plus the indented
    continuation lines beneath it, which carry the site lists."""

    def __init__(self, index, line_no, lines):
        self.index = index
        self.line_no = line_no
        self.lines = lines

    @property
    def text(self):
        return "\n".join(self.lines)

    @property
    def prefix(self):
        match = PREFIX.match(self.lines[0])
        return match.group(1) if match else "(none)"

    @property
    def name(self):
        """Enough of the first line to identify the entry to a human."""
        return PREFIX.sub("", self.lines[0]).strip()[:60]

    @property
    def words(self):
        return len(REF.sub("", self.text).split())

    def __repr__(self):
        return f"entry {self.index} line {self.line_no} {self.name!r}"


def classify(line):
    """GC-open-terms.md is not a uniform list. Four kinds of line carry
    content and each needs its own guarantee, so every line is placed in
    exactly one class and none is left unwatched."""
    stripped = line.strip()
    if not stripped:
        return "blank"
    if line[:1] in " \t":
        return "continuation"
    if stripped.startswith("#"):
        return "heading"
    if stripped.startswith("|"):
        return "table"
    if PREFIX.match(stripped):
        return "entry"
    return "prose"


def parse_open_terms(text):
    """Return entries, headings, table rows and free prose lines.

    Every non-blank line lands in one of the four, and the caller checks
    all four. An earlier version of this function saw only the prefixed
    entry lines, which was 27 lines out of 83: the site lists, the GC 11
    assembly table and the pronoun notes at the foot of the file were all
    invisible to it, and could have been deleted without the check
    noticing. That is the exact failure this script exists to prevent.
    """
    entries, headings, tables, prose, unknown = [], [], [], [], []
    current = None
    for line_no, line in enumerate(text.splitlines(), 1):
        kind = classify(line)
        if kind == "entry":
            current = Entry(len(entries), line_no, [line.strip()])
            entries.append(current)
            continue
        if kind == "continuation" and current is not None:
            current.lines.append(line.rstrip())
            continue
        current = None
        if kind == "heading":
            headings.append((line_no, line.strip()))
        elif kind == "table":
            tables.append((line_no, line.strip()))
        elif kind == "prose":
            prose.append((line_no, line.strip()))
            shaped = PREFIX_SHAPED.match(line.strip())
            if shaped:
                unknown.append((line_no, shaped.group(1)))
    return {"entries": entries, "headings": headings, "tables": tables,
            "prose": prose, "unknown_prefixes": unknown}


def refs(text):
    """Count sites by normalised number, so {GC 201.1}, {201.1} and a bare
    201.1 are one key and a change of shape is not read as a loss."""
    return Counter(re.sub(r"[^0-9.]", "", r) for r in REF.findall(text))


def tags(text):
    return Counter(TAG.findall(text))


# ---------------------------------------------------------------- findings


class Report:
    def __init__(self):
        self.violations = []
        self.notes = []

    def fail(self, check, message):
        self.violations.append((check, message))

    def note(self, message):
        self.notes.append(message)

    @property
    def ok(self):
        return not self.violations


# ------------------------------------------------------------- comparisons


def compare_glossary(before_text, after_text, report):
    before = parse_glossary(before_text)
    after = parse_glossary(after_text)

    report.note(
        f"GC-glossary.txt: {len(before)} rows before, {len(after)} rows after; "
        f"Notes hold {sum(r.words for r in before)} words before, "
        f"{sum(r.words for r in after)} after"
    )

    if len(before) != len(after):
        lost = [r.head for r in before if r.head not in {a.head for a in after}]
        gained = [a.head for a in after if a.head not in {r.head for r in before}]
        report.fail(
            "glossary row count",
            f"{len(before)} rows became {len(after)}. "
            f"Missing heads: {lost[:8] or 'none'}. "
            f"New heads: {gained[:8] or 'none'}.",
        )

    for old, new in zip(before, after):
        where = f"row {old.index + 1}, line {new.line_no}, head {old.head!r}"

        if old.head != new.head:
            report.fail(
                "glossary head cell",
                f"{where}: the English head changed to {new.head!r}. "
                "Row order or row identity has moved.",
            )
            # Once the rows are out of alignment every later comparison is
            # noise, so stop rather than print hundreds of false failures.
            report.fail(
                "glossary alignment",
                "Comparison stopped at the first misaligned row; fix that "
                "and run again.",
            )
            return

        if old.lao != new.lao:
            report.fail(
                "glossary Lao cell",
                f"{where}: the Lao cell changed.\n"
                f"      before: {old.lao}\n"
                f"      after:  {new.lao}",
            )

        if len(old.cells) != len(new.cells):
            report.fail(
                "glossary column count",
                f"{where}: {len(old.cells)} columns became {len(new.cells)}. "
                "Both scripts skip a row whose column count is wrong, "
                "silently.",
            )

        lost_tags = tags(old.notes) - tags(new.notes)
        if lost_tags:
            report.fail(
                "glossary tag",
                f"{where}: lost {', '.join('[' + t + ']' for t in lost_tags)}. "
                "A row without [CHECK] is not enforced by gc_termcheck.py and "
                "is skipped by gc_resolvecheck.py, with no error either way.",
            )

        if new.words > old.words:
            report.fail(
                "glossary growth",
                f"{where}: Notes grew from {old.words} to {new.words} words.",
            )

    over = [r for r in after if r.words > 15]
    if over:
        report.note(
            f"GC-glossary.txt: {len(over)} rows still over the 15-word cap, "
            f"largest {max(r.words for r in over)} words "
            f"({max(after, key=lambda r: r.words).head!r})"
        )


def compare_open_terms(before_text, after_text, report):
    before = parse_open_terms(before_text)
    after = parse_open_terms(after_text)

    old_entries, new_entries = before["entries"], after["entries"]

    report.note(
        f"GC-open-terms.md: {len(old_entries)} entries before, "
        f"{len(new_entries)} after; "
        f"{sum(e.words for e in old_entries)} entry words before, "
        f"{sum(e.words for e in new_entries)} after; "
        f"{len(before['headings'])} headings, {len(before['tables'])} table "
        f"rows, {len(before['prose'])} free prose lines watched separately"
    )

    if after["unknown_prefixes"]:
        report.note(
            "GC-open-terms.md: line-initial tokens that look like an entry "
            "type but are not in KNOWN_PREFIXES — "
            + "; ".join(f"line {n} {t}" for n, t in after["unknown_prefixes"])
            + ". Add them to KNOWN_PREFIXES if they are entries."
        )

    if len(old_entries) != len(new_entries):
        lost = [e.name for e in old_entries
                if e.name not in {n.name for n in new_entries}]
        report.fail(
            "open-terms entry count",
            f"{len(old_entries)} entries became {len(new_entries)}. "
            f"Missing: {lost[:6] or 'none'}. gc-batch-auditor 6.C keys on "
            "these entries; losing one changes what future audits report.",
        )

    for old, new in zip(old_entries, new_entries):
        where = f"entry {old.index + 1}, line {new.line_no}, {old.name!r}"

        if old.prefix != new.prefix:
            report.fail(
                "open-terms prefix",
                f"{where}: prefix {old.prefix} became {new.prefix}. "
                "gc-batch-auditor 6.C never reports EXCEPT-TERM and does not "
                "re-mark occurrences logged under DEFER-TERM, so this changes "
                "audit behaviour silently.",
            )

        lost_refs = refs(old.text) - refs(new.text)
        if lost_refs:
            report.fail(
                "open-terms refs",
                f"{where}: dropped {sum(lost_refs.values())} site ref(s) — "
                f"{', '.join(sorted(lost_refs))}. A deferral's site list is "
                "what stops a family being re-marked in every chapter.",
            )

        if new.words > old.words:
            report.fail(
                "open-terms growth",
                f"{where}: grew from {old.words} to {new.words} words.",
            )

    # The three line classes that are not entries. Their prose is covered
    # by the whole-file ref, Lao and English checks; what is checked here
    # is that none of them silently disappeared.
    if [h for _, h in before["headings"]] != [h for _, h in after["headings"]]:
        report.fail(
            "open-terms headings",
            f"the heading list changed. Before: "
            f"{[h for _, h in before['headings']]}. After: "
            f"{[h for _, h in after['headings']]}.",
        )

    old_tables = [t for _, t in before["tables"]]
    new_tables = [t for _, t in after["tables"]]
    if len(old_tables) != len(new_tables):
        report.fail(
            "open-terms table rows",
            f"{len(old_tables)} table rows became {len(new_tables)}. The GC 11 "
            "assembly table names four bodies that must not be collapsed.",
        )
    else:
        for old_row, new_row in zip(old_tables, new_tables):
            if SEPARATOR.match(old_row):
                continue
            old_cells = [c.strip() for c in old_row.strip("|").split("|")]
            new_cells = [c.strip() for c in new_row.strip("|").split("|")]
            if old_cells[:-1] != new_cells[:-1]:
                report.fail(
                    "open-terms table row",
                    f"a table row's identifying cells changed.\n"
                    f"      before: {old_cells[:-1]}\n"
                    f"      after:  {new_cells[:-1]}",
                )

    if len(after["prose"]) < len(before["prose"]):
        report.fail(
            "open-terms prose lines",
            f"{len(before['prose'])} free prose lines became "
            f"{len(after['prose'])}. These sit under a heading rather than "
            "under an entry, so nothing else in this check guards them.",
        )


def compare_refs_whole_file(before_text, after_text, history_text, label, report):
    """A ref may legitimately move from a row to the history file, but it
    may never simply vanish. Checked across the whole file rather than
    per row, because relocation is the point of the exercise."""
    lost = refs(before_text) - refs(after_text) - refs(history_text)
    if lost:
        report.fail(
            f"{label} refs",
            f"{sum(lost.values())} ref(s) left the file and are not in the "
            f"history file either: {', '.join(sorted(lost))}",
        )


def compare_lao_content(before_text, after_text, history_text, label, report):
    """Every Lao form removed from a governing file has to reappear in the
    history file. A Lao form is evidence and is never rewordable, so its
    disappearance is a hard failure rather than something to review."""
    lost = Counter(LAO.findall(before_text))
    lost -= Counter(LAO.findall(after_text))
    lost -= Counter(LAO.findall(history_text))
    if lost:
        sample = list(lost)[:10]
        report.fail(
            f"{label} Lao content",
            f"{sum(lost.values())} Lao form(s) removed and not found in the "
            f"history file. First few: {' '.join(sample)}",
        )


def compare_english_content(before_text, after_text, history_text, label, report):
    """English prose is rewordable, so a word that vanishes is something to
    look at rather than a failure on its face. Reported as a note with a
    sample, and it is the reviewer's judgment whether a ruling went with it."""
    lost = Counter(w.lower() for w in re.findall(r"[A-Za-z']{3,}", before_text))
    lost -= Counter(w.lower() for w in re.findall(r"[A-Za-z']{3,}", after_text))
    lost -= Counter(w.lower() for w in re.findall(r"[A-Za-z']{3,}", history_text))
    if lost:
        sample = ", ".join(sorted(lost)[:15])
        report.note(
            f"{label}: {sum(lost.values())} English word(s) removed and not "
            f"present in the history file. Reword or ruling? Check these: "
            f"{sample}"
        )


def check_characters(text, label, report):
    for match in FORBIDDEN_DIGITS.finditer(text):
        report.fail(
            f"{label} characters",
            f"Lao or Thai digit U+{ord(match.group()):04X} at offset "
            f"{match.start()}. Root CLAUDE.md 5.A forbids both sets.",
        )
    if ZWSP in text:
        report.fail(
            f"{label} characters",
            f"{text.count(ZWSP)} zero-width space(s) U+200B. "
            "Root CLAUDE.md 5.B forbids them.",
        )


# ------------------------------------------------ counts from the scripts


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def script_counts(repo, glossary_path, report, label):
    """Ask gc_termcheck.py and gc_resolvecheck.py how many rows they can
    actually see. These are the numbers that matter: this checker's own
    parse is a second opinion, not the authority."""
    scripts = repo / "lo/GC/04_assets/scripts"
    try:
        termcheck = load_module(scripts / "gc_termcheck.py", "gc_termcheck")
        rows, spelling = termcheck.parse_glossary(str(glossary_path))
        usable = sum(1 for r in rows if r.usable())
    except Exception as exc:  # a parse that dies is itself the finding
        report.fail("gc_termcheck.py", f"{label}: parse failed — {exc}")
        return None

    try:
        resolvecheck = load_module(scripts / "gc_resolvecheck.py", "gc_resolvecheck")
        resolvecheck.GLOSSARY = Path(glossary_path)
        forms = len(resolvecheck.incorrect_forms())
    except Exception as exc:
        report.fail("gc_resolvecheck.py", f"{label}: incorrect_forms failed — {exc}")
        return None

    return {
        "termcheck rows": len(rows),
        "termcheck rows enforced": usable,
        "termcheck spelling rows": len(spelling),
        "resolvecheck section 10 forms": forms,
    }


def compare_script_counts(before, after, report):
    if before is None or after is None:
        return
    for key in before:
        if before[key] != after[key]:
            report.fail(
                "script visibility",
                f"{key}: {before[key]} before, {after[key]} after. "
                "The scripts now see a different number of rows than they "
                "did, which means a row stopped being checked.",
            )
    report.note(
        "Script-visible counts unchanged: "
        + "; ".join(f"{k} {v}" for k, v in after.items())
    )


# ------------------------------------------------------------------ input


def read(path):
    return Path(path).read_text(encoding="utf-8")


def read_git(repo, ref, rel):
    return subprocess.run(
        ["git", "-C", str(repo), "show", f"{ref}:{rel}"],
        capture_output=True, text=True, check=True,
    ).stdout


def snapshot_dir(sandbox):
    return sandbox / "govcheck-baseline"


def take_snapshot(repo, sandbox):
    target = snapshot_dir(sandbox)
    target.mkdir(parents=True, exist_ok=True)
    for rel in (GLOSSARY_REL, OPENTERMS_REL):
        name = Path(rel).name
        (target / name).write_text(read(repo / rel), encoding="utf-8")
    return target


# ------------------------------------------------------------------- main


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=str(DEFAULT_REPO))
    parser.add_argument("--sandbox", default=str(SANDBOX))
    parser.add_argument("--snapshot", action="store_true",
                        help="save the current governing files as the baseline and exit")
    parser.add_argument("--baseline", choices=("snapshot", "git"), default="snapshot")
    parser.add_argument("--ref", default="HEAD",
                        help="git ref to compare against when --baseline git")
    parser.add_argument("--history", nargs="*", default=None,
                        help="history file paths; defaults to the two sandbox files")
    args = parser.parse_args()

    repo = Path(args.repo)
    sandbox = Path(args.sandbox)

    if args.snapshot:
        target = take_snapshot(repo, sandbox)
        print(f"Baseline saved to {target}")
        print("Edit the governing files, then run this script with no "
              "arguments to check what changed.")
        return 0

    if args.baseline == "git":
        before_glossary = read_git(repo, args.ref, GLOSSARY_REL)
        before_openterms = read_git(repo, args.ref, OPENTERMS_REL)
        baseline_label = f"git {args.ref}"
        baseline_glossary_path = None
    else:
        target = snapshot_dir(sandbox)
        if not target.exists():
            print(f"No baseline at {target}. Run with --snapshot first.",
                  file=sys.stderr)
            return 2
        before_glossary = read(target / "GC-glossary.txt")
        before_openterms = read(target / "GC-open-terms.md")
        baseline_label = str(target)
        baseline_glossary_path = target / "GC-glossary.txt"

    after_glossary = read(repo / GLOSSARY_REL)
    after_openterms = read(repo / OPENTERMS_REL)

    history_paths = ([Path(p) for p in args.history]
                     if args.history is not None else DEFAULT_HISTORY)
    history_text = "\n".join(
        read(p) for p in history_paths if Path(p).exists()
    )
    missing_history = [str(p) for p in history_paths if not Path(p).exists()]

    report = Report()

    compare_glossary(before_glossary, after_glossary, report)
    compare_open_terms(before_openterms, after_openterms, report)

    compare_refs_whole_file(before_glossary, after_glossary, history_text,
                            "GC-glossary.txt", report)
    compare_lao_content(before_glossary, after_glossary, history_text,
                        "GC-glossary.txt", report)
    compare_english_content(before_glossary, after_glossary, history_text,
                            "GC-glossary.txt", report)

    compare_refs_whole_file(before_openterms, after_openterms, history_text,
                            "GC-open-terms.md", report)
    compare_lao_content(before_openterms, after_openterms, history_text,
                        "GC-open-terms.md", report)
    compare_english_content(before_openterms, after_openterms, history_text,
                            "GC-open-terms.md", report)

    check_characters(after_glossary, "GC-glossary.txt", report)
    check_characters(after_openterms, "GC-open-terms.md", report)
    check_characters(history_text, "history files", report)

    after_counts = script_counts(repo, repo / GLOSSARY_REL, report, "working tree")
    if baseline_glossary_path is not None:
        before_counts = script_counts(repo, baseline_glossary_path, report, "baseline")
    else:
        # A git baseline has no file on disk for the scripts to read, so
        # write it to the sandbox first rather than skipping the check.
        tmp = sandbox / "govcheck-git-baseline-GC-glossary.txt"
        tmp.write_text(before_glossary, encoding="utf-8")
        before_counts = script_counts(repo, tmp, report, "baseline")
    compare_script_counts(before_counts, after_counts, report)

    print(f"Baseline: {baseline_label}")
    print(f"Working tree: {repo}")
    if missing_history:
        print("History files not found (nothing has been moved out yet): "
              + ", ".join(missing_history))
    print()

    for message in report.notes:
        print(f"  NOTE  {message}")
    print()

    if report.ok:
        removed = (len(REF.sub("", before_glossary).split())
                   + len(REF.sub("", before_openterms).split())
                   - len(REF.sub("", after_glossary).split())
                   - len(REF.sub("", after_openterms).split()))
        print(f"PASS — every invariant holds. {removed} words removed from "
              "what agents load.")
        return 0

    print(f"FAIL — {len(report.violations)} violation(s).")
    print()
    for check, message in report.violations:
        print(f"  {check}: {message}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
