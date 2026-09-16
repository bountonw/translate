#!/usr/bin/env python3
"""Word budgets of the instruction files. Reads only; exits 1 when a file is over.

    python3 th/SC/04_assets/scripts/instruction_budget.py

Run by the "check" step of the SC procedure and by a session after every edit
to a file in the table. Never run by git. A line added over budget means a
line cut.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BUDGET = {
    "CLAUDE.md": 1250,
    "th/SC/CLAUDE.md": 1350,
    ".claude/commands/th-sc.md": 120,
    ".claude/agents/sc-batch-auditor.md": 1750,
    ".claude/agents/sc-resolve-check.md": 900,
    ".claude/agents/th-glossary-miner.md": 450,
    "th/assets/translation_profile/thai-profile.txt": 900,
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
