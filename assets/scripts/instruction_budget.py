#!/usr/bin/env python3
"""Word budgets of the instruction files. Reads only; exits 1 when a file is over.

    python3 assets/scripts/instruction_budget.py

Run by each project's check step and by a session after every edit to a file
in the table. Never run by git. The budget is a guide (root CLAUDE.md 7.C): a
file over budget loses a restatement or gains a larger row, never a rule.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUDGET = {
    "CLAUDE.md": 1325,
    "th/SC/CLAUDE.md": 1900,
    "th/DA/CLAUDE.md": 1850,
    ".claude/commands/th-sc.md": 90,
    ".claude/commands/th-DA.md": 120,
    ".claude/agents/da-finder.md": 720,
    ".claude/agents/da-miner.md": 550,
    ".claude/agents/da-verse-study.md": 750,
    ".claude/agents/da-drafter.md": 1200,
    ".claude/agents/da-check.md": 950,
    ".claude/agents/da-fixer.md": 800,
    ".claude/agents/da-print-compare.md": 700,
    ".claude/agents/da-subtitles.md": 720,
    ".claude/agents/da-resolve-check.md": 1050,
    ".claude/agents/da-wording-drill.md": 750,
    ".claude/agents/sc-batch-auditor.md": 2005,
    ".claude/agents/sc-batch-auditor-qa2.md": 800,
    ".claude/agents/sc-reader-qa3.md": 700,
    ".claude/agents/th-term-study.md": 750,
    ".claude/agents/sc-wording-drill.md": 715,
    ".claude/agents/sc-wording-drill-opus-max.md": 715,
    ".claude/agents/sc-resolve-check.md": 885,
    ".claude/agents/th-glossary-miner.md": 520,
    "th/assets/translation_profile/thai-profile.txt": 1150,
    "lo/FB/CLAUDE.md": 1100,
    ".claude/commands/lo-fb.md": 150,
    ".claude/agents/fb-phrase-drill.md": 900,
    ".claude/agents/fb-sentence-drill.md": 900,
    ".claude/agents/fb-final-read.md": 900,
    "lo/assets/translation_profile/lao-profile.txt": 900,
    "lo/GC/CLAUDE.md": 1600,
    ".claude/commands/lo-gc.md": 100,
    ".claude/agents/gc-batch-auditor.md": 3150,
    ".claude/agents/gc-glossary-merge.md": 1300,
    ".claude/agents/gc-term-grep.md": 800,
    ".claude/agents/gc-resolve-check.md": 1650,
    ".claude/agents/gc-run-check.md": 800,
    ".claude/agents/gc-qa3-reader.md": 2700,
}


def main():
    over = 0
    print(f"{'file':50} {'words':>6} {'budget':>6}")
    for rel, budget in BUDGET.items():
        p = ROOT / rel
        if not p.exists():
            print(f"{rel:50} {'-':>6} {budget:>6}  missing")
            continue
        n = len(p.read_text(encoding="utf-8").split())
        flag = "  OVER" if n > budget else ""
        over += n > budget
        print(f"{rel:50} {n:>6} {budget:>6}{flag}")
    return 1 if over else 0


if __name__ == "__main__":
    sys.exit(main())
