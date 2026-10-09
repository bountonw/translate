#!/usr/bin/env python3
"""Prove gc_govcheck.py fails when it should, on a throwaway copy.

Each case mutates a copy of the real governing files, runs the checker
against a snapshot of the unmutated copy, and asserts that the expected
check fires. A checker that passes everything is worth nothing, so this
is the part that makes it trustworthy. Run it before relying on the
checker, and again after changing it:

    python3 lo/GC/04_assets/scripts/test_gc_govcheck.py

Nothing here touches the repository. Everything happens under
~/claude-sandbox/gc-audit/govcheck-test/.
"""
import shutil
import subprocess
import sys
from pathlib import Path

SANDBOX = Path.home() / "claude-sandbox" / "gc-audit"
BASE = SANDBOX / "govcheck-test"
REAL = Path(__file__).resolve().parents[4]
CHECKER = REAL / "lo/GC/04_assets/scripts/gc_govcheck.py"
PROFILE = "lo/GC/04_assets/translation_profile"
SCRIPTS = "lo/GC/04_assets/scripts"


def build():
    if BASE.exists():
        shutil.rmtree(BASE)
    (BASE / "repo" / PROFILE).mkdir(parents=True)
    (BASE / "repo" / SCRIPTS).mkdir(parents=True)
    (BASE / "sandbox").mkdir(parents=True)
    for name in ("GC-glossary.txt", "GC-open-terms.md"):
        shutil.copy(REAL / PROFILE / name, BASE / "repo" / PROFILE / name)
    for name in ("gc_termcheck.py", "gc_resolvecheck.py"):
        shutil.copy(REAL / SCRIPTS / name, BASE / "repo" / SCRIPTS / name)
    shutil.copytree(BASE / "repo", BASE / "pristine")
    run("--snapshot")


def run(*extra):
    return subprocess.run(
        [sys.executable, str(CHECKER),
         "--repo", str(BASE / "repo"),
         "--sandbox", str(BASE / "sandbox"),
         "--history", str(BASE / "history.md"),
         *extra],
        capture_output=True, text=True,
    )


def restore():
    for name in ("GC-glossary.txt", "GC-open-terms.md"):
        shutil.copy(BASE / "pristine" / PROFILE / name,
                    BASE / "repo" / PROFILE / name)
    history = BASE / "history.md"
    if history.exists():
        history.unlink()


def glossary():
    return BASE / "repo" / PROFILE / "GC-glossary.txt"


def openterms():
    return BASE / "repo" / PROFILE / "GC-open-terms.md"


def edit(path, fn):
    path.write_text(fn(path.read_text(encoding="utf-8")), encoding="utf-8")


# ------------------------------------------------------------------ cases

def case_untouched():
    pass


def case_drop_check_tag():
    """The GC16 Bancroft mistake: the row still reads correctly to a human
    but the tooling has quietly stopped enforcing it."""
    edit(glossary(), lambda t: t.replace("| [CHECK] ", "| ", 1))


def case_change_lao_cell():
    def fn(t):
        for line in t.splitlines():
            cells = line.strip().strip("|").split("|")
            if len(cells) == 3 and cells[1].strip() and "[CHECK]" in line:
                return t.replace(line, line.replace(
                    cells[1], cells[1].rstrip() + "x", 1), 1)
        raise AssertionError("no row found to mutate")
    edit(glossary(), fn)


def case_delete_row():
    def fn(t):
        for line in t.splitlines(keepends=True):
            if line.startswith("| Jesuits"):
                return t.replace(line, "", 1)
        raise AssertionError("Jesuits row not found")
    edit(glossary(), fn)


def case_trim_with_history():
    """The legitimate operation: narrative leaves the row and lands in the
    history file. This one must PASS."""
    moved = []

    def fn(t):
        out = []
        for line in t.splitlines(keepends=True):
            cells = line.rstrip("\n").strip().strip("|").split("|")
            if len(cells) == 3 and "Verified by exact grep" in cells[2]:
                keep, drop = cells[2].split("Verified by exact grep", 1)
                moved.append("Verified by exact grep" + drop)
                out.append(f"|{cells[0]}|{cells[1]}| {keep.strip()} |\n")
            else:
                out.append(line)
        assert moved, "no row carrying the expected narrative"
        return "".join(out)

    edit(glossary(), fn)
    (BASE / "history.md").write_text(
        "# history\n\n## Minister / Ministers / Pastor / Pastors\n\n"
        + "\n".join(moved) + "\n", encoding="utf-8")


def case_trim_without_history():
    """The same trim with the evidence simply deleted. Must fail."""
    def fn(t):
        out = []
        for line in t.splitlines(keepends=True):
            cells = line.rstrip("\n").strip().strip("|").split("|")
            if len(cells) == 3 and "Verified by exact grep" in cells[2]:
                keep = cells[2].split("Verified by exact grep", 1)[0]
                out.append(f"|{cells[0]}|{cells[1]}| {keep.strip()} |\n")
            else:
                out.append(line)
        return "".join(out)
    edit(glossary(), fn)


def case_change_prefix():
    edit(openterms(), lambda t: t.replace("EXCEPT-TERM", "NOTE-TERM", 1))


def case_drop_site_ref():
    """Delete one site from an indented site list — the lines the first
    version of this checker could not see at all."""
    edit(openterms(),
         lambda t: t.replace("  56.1 123.2 124.2", "  56.1 124.2", 1))


def case_delete_prose_line():
    edit(openterms(),
         lambda t: t.replace("Four distinct bodies in this chapter. "
                             "Do not collapse.\n", "", 1))


def case_delete_table_row():
    def fn(t):
        for line in t.splitlines(keepends=True):
            if line.startswith("| Imperial Diet"):
                return t.replace(line, "", 1)
        raise AssertionError("Imperial Diet row not found")
    edit(openterms(), fn)


def case_lao_digit():
    edit(glossary(),
         lambda t: t.replace("| Jesuits", "| Jesuits" + chr(0x0ED0), 1))


def case_zwsp():
    edit(openterms(),
         lambda t: t.replace("EXCEPT-TERM", chr(0x200B) + "EXCEPT-TERM", 1))


CASES = [
    ("untouched tree", case_untouched, None),
    ("dropped [CHECK] tag", case_drop_check_tag, "glossary tag"),
    ("altered Lao cell", case_change_lao_cell, "glossary Lao cell"),
    ("deleted a row", case_delete_row, "glossary row count"),
    ("trim, evidence moved to history", case_trim_with_history, None),
    ("trim, evidence deleted", case_trim_without_history, "Lao content"),
    ("changed entry prefix", case_change_prefix, "open-terms prefix"),
    ("dropped a site from a site list", case_drop_site_ref, "open-terms refs"),
    ("deleted a free prose line", case_delete_prose_line,
     "open-terms prose lines"),
    ("deleted a table row", case_delete_table_row, "open-terms table rows"),
    ("inserted a Lao digit", case_lao_digit, "characters"),
    ("inserted a zero-width space", case_zwsp, "characters"),
]


def main():
    build()
    failures = 0
    for name, mutate, expected in CASES:
        restore()
        mutate()
        result = run()
        passed = result.returncode == 0
        output = result.stdout + result.stderr

        if expected is None:
            ok, want = passed, "PASS"
        else:
            ok = (not passed) and expected in output
            want = f"FAIL on {expected!r}"

        print(f"  {'ok  ' if ok else 'BAD '} {name:38s} want {want}")
        if not ok:
            failures += 1
            print("        ---- checker output ----")
            for line in output.splitlines():
                print("        " + line)
    restore()
    print()
    print("all cases behaved as expected" if not failures
          else f"{failures} case(s) misbehaved")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
