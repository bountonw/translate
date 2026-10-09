# DA side quests — the queue

Work that is agreed but not scheduled, in the order it will be done. When the translator asks how many DA side quests are open and in what order, this file is the answer and no agent answers from memory. An issue he defers rather than decides is added here in the same reply that defers it, and an entry is deleted when its work is finished, not marked done, because a finished quest is in the commit history. Each entry says what the job is, where its detail lives, and roughly how big it is. It sits under a numbered-stage assets directory because the linter excludes those from every check.

## 1. Profile refresh

Before DA01 is drafted, th/assets/translation_profile/thai-profile.txt is brought up to date from the translator's finished books: th-glossary-miner (Sonnet) runs over PP in runs of about eight chapters and over MB, each run writing observations on pronouns, honorifics, royal vocabulary, dialogue, description and poetry, sentence shape, and DA's questions about Jesus, the disciples and the leaders; one Fable agent reads the observation files and proposes profile lines with counts and anchors; the translator rules them in chunks. PP 1–30 and 44–73 carry the grammarian's review and weigh most; the Lao GC informs the principles, not the Thai forms. This replaces the register run of SC queue entry 7.

Detail: th/DA/CLAUDE.md 5.B. Medium; about ten mining runs, one synthesis, several adjudication sessions.

## 2. Typst break list for DA

Run python3 th/assets/scripts/build_breaks.py --book DA, which writes th/DA/04_assets/template/dictionary.typ from the shared list th/assets/typeset/thai-breaks.txt and replaces the hand-written file the project started with; then add a split line to the shared list for each ruled DA name it lacks, in the TNCV hyphenation style ruled on 6 October 2026, as the names session's last step. The check step (th/DA/CLAUDE.md 8.B) runs the script on every chapter from then on.

Detail: th/SC/CLAUDE.md 6.E; th/DA/CLAUDE.md 5.A and 8.B. Small.

## 3. Footnote wording standard

The translator's footnotes in DA take one shape, as LMV's textual notes do: the item, a colon, then what THSV or the King James reads, in one sentence. The first sites are {DA 132.1} (Bethabara), {DA 339.2} (Gergesa), and the first quoted อารัม or คูช in a chapter. The standard is settled before the first of them is drafted; each footnote's wording then comes from a fable 8/5/1 drill (DA 3.L).

Detail: th/DA/CLAUDE.md 3.L; th/DA/04_assets/notes/DA_notes.txt. Small.

## 4. Move the instruction budget table

th/SC/04_assets/scripts/instruction_budget.py holds the word budgets of every project and of the files that belong to none, so it moves to a top-level scripts folder: the translator moves it with git to scripts/instruction_budget.py, and the session changes the script's root line (parents[4] to parents[1]) and the path in root CLAUDE.md 7.C, th/SC/CLAUDE.md and lo/FB/CLAUDE.md, then runs the check.

Detail: root CLAUDE.md 7.C. Small.
