#!/usr/bin/env python3
"""Word budgets of the instruction files kept in this repository. Reads only; exits 1 when a file is over.

    python3 assets/scripts/instruction_budget.py

Run by each project's check step and after every change to a file in the
table. The budget is a guide: a file over budget loses a restatement or gains
a larger row, never a rule.

The rules for every chat, the agents and the commands are kept outside this
repository; their words are counted where they are kept.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUDGET = {
    "assets/read-through.md": 600,
    "th/assets/translation_profile/thai-profile.txt": 1220,
    "th/DA/04_assets/book-rules.md": 580,
    "lo/assets/translation_profile/lao-profile.txt": 900,
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
