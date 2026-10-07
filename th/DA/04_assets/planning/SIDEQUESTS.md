# DA side quests — the queue

Work that is agreed but not scheduled, in the order it will be done. When the translator asks how many DA side quests are open and in what order, this file is the answer and no agent answers from memory. An issue he defers rather than decides is added here in the same reply that defers it, and an entry is deleted when its work is finished, not marked done, because a finished quest is in the commit history. Each entry says what the job is, where its detail lives, and roughly how big it is. It sits under a numbered-stage assets directory because the linter excludes those from every check.

## 1. Build the DA tools

The procedure in th/DA/CLAUDE.md is ruled; its agents and scripts are not yet written, so /th-DA stops at its first dispatch. Each agent definition and script is proposed to the translator before it is written, then tested on DA00.

- Scripts copied from th/SC/04_assets/scripts and changed for DA: da_common.py, da_punctcheck.py, da_refcheck.py (the whole Bible), da_resolution_sheet.py, da_editor_markers.py, da_term_data.py, da_notescheck.py with th/DA/04_assets/notes/DA_notes.txt. A script that serves every Thai book goes to th/assets/scripts instead.
- The proposal and the translator's rulings on each item: ~/claude-sandbox/da-audit/da-tools-proposal.md.
- New scripts: th/assets/scripts/th_names.py (5.A, every Thai book, writing th/assets/translation_profile/thai-names.tsv), da_quotes.py (quotations and allusions by runs of KJV words, with all ten Thai versions), da_packet.py (the drafter's packet).
- New agents in .claude/agents: da-finder (Opus), da-miner (Sonnet), da-verse-study (Fable), da-drafter (Fable), da-check (Opus), da-fixer (Fable), da-print-compare (Opus), da-subtitles (Fable, 7.E.2; Humble Hero is looked for in the EGW download folders first), da-resolve-check (Opus, from sc-resolve-check), da-wording-drill (Fable, from sc-wording-drill). th-term-study and th-glossary-miner are reused.
- A row for each new instruction file in th/SC/04_assets/scripts/instruction_budget.py, and DA in the book list of th/assets/scripts/th_charcheck.py.

Detail: th/DA/CLAUDE.md sections 5 to 9. Large.

## 2. Profile refresh

Before DA01 is drafted, th/assets/translation_profile/thai-profile.txt is brought up to date from the translator's finished books: th-glossary-miner (Sonnet) runs over PP in runs of about eight chapters and over MB, each run writing observations on pronouns, honorifics, royal vocabulary, dialogue, description and poetry, sentence shape, and DA's questions about Jesus, the disciples and the leaders; one Fable agent reads the observation files and proposes profile lines with counts and anchors; the translator rules them in chunks. PP 1–30 and 44–73 carry the grammarian's review and weigh most; the Lao GC informs the principles, not the Thai forms. This replaces the register run of SC queue entry 7.

Detail: th/DA/CLAUDE.md 5.B. Medium; about ten mining runs, one synthesis, several adjudication sessions.
