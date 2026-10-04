# DA side quests — the queue

Work that is agreed but not scheduled, in the order it will be done. When the translator asks how many DA side quests are open and in what order, this file is the answer and no agent answers from memory. An issue he defers rather than decides is added here in the same reply that defers it, and an entry is deleted when its work is finished, not marked done, because a finished quest is in the commit history. Each entry says what the job is, where its detail lives, and roughly how big it is. It sits under a numbered-stage assets directory because the linter excludes those from every check.

## 1. Build the DA tools

The procedure in th/DA/CLAUDE.md is ruled; its agents and scripts are not yet written, so /th-DA stops at its first dispatch. Each agent definition and script is proposed to the translator before it is written, then tested on DA00.

- Scripts copied from th/SC/04_assets/scripts and changed for DA: da_common.py, da_punctcheck.py, da_refcheck.py (the whole Bible), da_resolution_sheet.py, da_editor_markers.py, da_term_data.py. A script that serves every Thai book goes to th/assets/scripts instead.
- New scripts: da_names.py (5.A), da_quotes.py (quotations and allusions by runs of KJV words, with all eight Thai versions), da_packet.py (the drafter's packet).
- New agents in .claude/agents: da-finder (Opus), da-miner (Sonnet), da-verse-study (Fable), da-drafter (Fable), da-check (Opus), da-fixer (Fable), da-resolve-check (Opus, from sc-resolve-check), da-wording-drill (Fable, from sc-wording-drill). th-term-study and th-glossary-miner are reused.
- A row for each new instruction file in th/SC/04_assets/scripts/instruction_budget.py, and DA in the book list of th/assets/scripts/th_charcheck.py.

Detail: th/DA/CLAUDE.md sections 5 to 9. Large.
