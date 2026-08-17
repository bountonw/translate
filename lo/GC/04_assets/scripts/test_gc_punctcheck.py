#!/usr/bin/env python3
"""Prove gc_punctcheck.py's single-quote check fires when it should.

The inner quotation check is the one class the script was blind to until
17 August, so it is the one that needs a test: a paragraph could open an
inner quotation and never close it and the script would pass the chapter.
The cases below build a throwaway chapter for each direction and assert
that the check fires exactly where it should and stays silent everywhere
else. Run it before relying on the checker, and again after changing it:

    python3 lo/GC/04_assets/scripts/test_gc_punctcheck.py

Nothing here touches the repository. Everything happens under
~/claude-sandbox/gc-audit/punctcheck-test/.
"""
import shutil
import subprocess
import sys
from pathlib import Path

SANDBOX = Path.home() / "claude-sandbox" / "gc-audit"
BASE = SANDBOX / "punctcheck-test"
REAL = Path(__file__).resolve().parents[4]
CHECKER = REAL / "lo/GC/04_assets/scripts/gc_punctcheck.py"
PUBLIC = "lo/GC/03_public"

HEAD = "---\nbook:\n  title:\n    en: The Great Controversy\n---\n\n"

# Each case is (name, paragraph, whether single-quote-unclosed must fire).
CASES = [
    ("balanced inner quotation",
     "“ພຣະເຈົ້າຢາເວໄດ້ກ່າວວ່າ, ‘ຈົ່ງຢຸດຢູ່ທີ່ທາງສີ່ແຍກ.’” (ເຢເຣມີຢາ 6:16).",
     False),
    ("inner quotation left open",
     "“ພຣະເຈົ້າຢາເວໄດ້ກ່າວວ່າ, ‘ຈົ່ງຢຸດຢູ່ທີ່ທາງສີ່ແຍກ.” (ເຢເຣມີຢາ 6:16).",
     True),
    # The closing mark doubles as the apostrophe, so an excess of closers is
    # ambiguous and must stay silent or it would bury the real findings.
    ("excess closing mark is not reported",
     "ຄຳວ່າ ’ ນີ້ຢືນຢູ່ຜູ້ດຽວ ແລະ ບໍ່ແມ່ນຄວາມຜິດພາດ.",
     False),
]


def build(paragraph):
    if BASE.exists():
        shutil.rmtree(BASE)
    public = BASE / PUBLIC
    public.mkdir(parents=True)
    (public / "GC99_lo.md").write_text(
        HEAD + "## {GC 999.1}\n\n" + paragraph + " {GC 999.1}\n",
        encoding="utf-8")


def run():
    # The checker reads lo/GC/03_public relative to the working directory, so
    # the throwaway chapter is reached by running it from the sandbox root.
    return subprocess.run(
        [sys.executable, str(CHECKER)],
        cwd=str(BASE), capture_output=True, text=True).stdout


def main():
    if not CHECKER.exists():
        sys.exit(f"checker not found at {CHECKER}")
    failures = 0
    for name, paragraph, must_fire in CASES:
        build(paragraph)
        fired = "single-quote-unclosed" in run()
        if fired != must_fire:
            want = "fire" if must_fire else "stay silent"
            print(f"FAIL  {name}: expected the check to {want}")
            failures += 1
        else:
            print(f"ok    {name}")
    if BASE.exists():
        shutil.rmtree(BASE)
    print(f"\n{len(CASES) - failures} of {len(CASES)} cases passed.")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
