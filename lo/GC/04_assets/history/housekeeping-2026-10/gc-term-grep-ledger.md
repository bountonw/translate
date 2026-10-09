# Trim ledger: .claude/agents/gc-term-grep.md

File: .claude/agents/gc-term-grep.md

## 1. Numbering

1.A. No existing item was renumbered. The five paragraphs of the old 4.A were one item spread over several lines; the first stays 4.A and the four that followed are now 4.A.1, 4.A.2, 4.A.3 and 4.A.4, so that each is one line. The opening paragraph, wrapped over three lines, is now one line. The front matter description is unchanged.

## 2. Removed, with reason

### Section 1

2.1. 1.A "report every hit by its anchor" — repeat of 2.B, which lists the anchor among the fields of every hit.

### Section 3

2.2. 3.A "into Latin script" — restates "transliterate".
2.3. 3.A "when you report a form" — the digit rule is now universal ("Western digits only, never Lao digits (U+0ED0–U+0ED9) or Thai digits (U+0E50–U+0E59)"), so the scope is covered. The code-point ranges are kept.
2.4. 3.A "rather than retyping it" — restates "Copy every form out of a file".
2.5. 3.B "Adjudication belongs to the translator." — repeat of the opening line ("you never judge").
2.6. 3.C "problem" and "examples" (in "the noise problem", "false-positive examples") — wording only.
2.7. 3.D "so another project mining the glossary can inherit it" — condensed to "kept for another project".
2.8. 3.D "never count its absence as a finding" — merged into "Never report its form as missing or its absence as a finding".
2.9. 3.E "which is how five tail counts reached a glossary row too low today." — story and date.
2.10. 3.E "That error was caught only because the agent given those numbers ran its own greps, saw the disagreement, and said so rather than deferring." — story.

### Section 4

2.11. 4.A "The repository CLAUDE.md is not in your context, so the format is given here in full." — reason; directs nothing.
2.12. 4.A.1 "in priority order" — the order FIX, DECIDE, NOTE, RESOLVED is given.
2.13. 4.A.1 "block" (in "block capitals") and "ordinary" (now "plain English") — wording only.
2.14. 4.A.1 "at most" (in "in one sentence or two at most") — now "in one or two sentences".
2.15. 4.A.1 "a pronoun, a quantifier or a bare label points at nothing on his screen, and a description that refers to a change instead of stating it fails the same way" — reason; the rule is kept as "Name the subject on every line and state the change itself; never use a pronoun, a quantifier or a bare label in its place."
2.16. 4.A.2 "and never a fresh one" — restates "carries that marker's own number".
2.17. 4.A.2 "so that a number the translator types names the same object in the manuscript, in the report and in his reply" — reason.
2.18. 4.A.2 "inside the item itself" — restatement.
2.19. 4.A.2 "a summarising word such as ... standing in for them" — condensed to "never "both" or "several"".
2.20. 4.A.4 "and give no block at all to an item that needs no evidence" — repeat of 4.C ("Give a block only to an item the translator has to look at").
2.21. 4.A.4 "Write brief, complete English throughout and never clip a line into fragments." — reworded as "Write brief, complete sentences, never fragments."
2.22. 4.B "The reference mark on each line is the {GC ###.#} anchor." — repeat of 4.A.1, which names the anchor as the reference.
2.23. 4.D "do not announce that you are about to compile the report" — repeat of "Never write a preamble".
2.24. 4.D "what the summary list already says" — condensed to "restates the summary list".

## 3. Moved or merged

3.1. "Paragraphs are anchored by {GC ###.#} tags", which sat outside any numbered item below the corpus block, moved into the lead line of 1.A.
3.2. The two "Do not ..." sentences of 4.D merged into one sentence.

## 4. Observations for the conductor (nothing changed)

4.1. 4.A keeps the original order: summary list, detail, then the summary list repeated. Root CLAUDE.md 1.A now puts the detail first and the summary list once at the bottom, and its 1.E allows FIX1 to FIX4. lo/GC/CLAUDE.md 4.E relays this agent's report to the translator verbatim, so the conductor may want the two shapes aligned. The format is kept as written, per the brief.
4.2. The opening line says the agent never judges or proposes renderings, and 3.B forbids recommending a winning form, while 4.A.1 and 4.B have it write FIX and DECIDE lines with a recommended option. The original carried both; both are kept as written.
4.3. gc-term-grep.md has no row in th/SC/04_assets/scripts/instruction_budget.py. No row was added, because the brief said to edit nothing else.
4.4. The result is above the 600-word target. About 380 of the remaining words are the report format of section 4, which the brief requires to stay, because the agent does not receive the root CLAUDE.md.

## 5. Word counts

5.1. Before: 971 words. After: 768 words. Both counted by whitespace split, the method of instruction_budget.py (wc -w gives the same figures).
