# Trim ledger: .claude/agents/gc-glossary-merge.md

File: .claude/agents/gc-glossary-merge.md

## 1. Numbering

1.A. No item was renumbered. Every item from 1.A to 6.D keeps its number. The blank lines between 4.H, 4.I, 4.I.1, 4.J and between 6.B, 6.C were removed so that each item is one line.

## 2. Removed, with reason

### Front matter description

2.1. "Reads the run's proposals file," — restates body 1.B.
2.2. "and folds" (in "dedupes and folds rows") — restates "dedupes".
2.3. "instead of picking a winner" — restates body 4.E.
2.4. "Never runs during a run." — merged into the previous sentence as "never during a run".

### Opening paragraphs

2.5. "in this project" — adds nothing to "no other agent writes a governing file".
2.6. "and you may do so only after the run that produced the proposals has finished and been verified" — repeat of 1.A.
2.7. "in a row, an entry or a report" — the digit rule is now universal ("Western digits only, never Lao digits (U+0ED0–U+0ED9) or Thai digits (U+0E50–U+0E59)"), so the scope list is covered. The code-point ranges are kept.
2.8. "rather than retyping it" — restates "Copy every Lao form out of a file".
2.9. "Your standing bias is" — rewritten as the imperative "Apply less than you could."
2.10. "and it will be found late or not at all" — rating beyond the one reason sentence kept.

### Section 1

2.11. 1.A "you do not run against an unverified chapter" — repeat of "Without PASS, stop and say so."
2.12. 1.C "(the only two repo files you may touch)" — repeat of 5.C.
2.13. 1.D "Its entries are closed decisions and proposals never target it." — reason; 4.G already names the closed decisions.
2.14. 1.D "never applied" — replaced by the pointer "escalated under 4.G".

### Section 2

2.15. 2.A "Read the destination table's header row and several existing rows before adding to it." — kept in substance as "Before adding to a table, read its header row and several existing rows"; the four "the same ..." phrases were compressed into one list.
2.16. 2.B "Determine whether the destination table is sorted, and by which column." — folded into "If the table is sorted, insert each new row in sort position".
2.17. 2.C "The 1.C files usually carry another session's uncommitted rows, so" — reason clause.
2.18. 2.C "Apply your groups normally under section 4 unless a head matches one of those:" — repeat of 3.C, which sends every group through section 4.
2.19. 2.C "that row is a conflict, so" — restates the escalation that follows.

### Section 3

2.20. 3.B "Batches worked different ranges of the same chapter and" — second reason clause; "did not see each other's output" is kept.
2.21. 3.D "rather than attempting a repair" — reworded as "never repair it".
2.22. 3.F "you are the last gate before these files" — rating.
2.23. 3.F "rather than a preference" — restates "the limit is hard".
2.24. 3.F "— the same limit the batch auditors work under in their 8.C —" — cross-reference that directs nothing.
2.25. 3.F "A proposal over the limit is not escalated for that reason alone:" — reworded as "Cut an over-long proposal down rather than escalating it".
2.26. 3.F "so the translator can see what was dropped and put it elsewhere if he wants it" — reason.
2.27. 3.F "which no agent loads" — reason.
2.28. 3.F "gc-batch-auditor 2.B requires reading it for every ref in a batch's range, so moving bulk into it relocates the cost instead of removing it" — reason beyond one sentence; the short reason "which every batch auditor reads for every ref in its range" is kept.
2.29. 3.F "GC-open-terms.md is not an overflow home:" — merged into the previous sentence as "never in a row and never in GC-open-terms.md".

### Section 4

2.30. 4.A "English" before "head" — the head is always English.
2.31. 4.B "Collapse to one and" — repeat of "Add it once."
2.32. 4.C "The head already has a row," — implied by "The row's Lao cell already carries".
2.33. 4.C "what is there" (in "never reorder what is there") — restatement.
2.34. 4.D "Leave the row exactly as it is." — repeat of 3.C ("leave the ESCALATE groups untouched").
2.35. 4.E "and the difference is not a matter of adding an option: they are" — condensed to "competing translations of the same sense, not an added option".
2.36. 4.E "Do not pick," — repeat of "Apply neither" and of 5.D.
2.37. 4.E "if the batches were arguing, that is a claim you are not entitled to make on the translator's behalf" — condensed to "and that ruling is the translator's".
2.38. 4.H "is a corpus-wide decision and" — reason.
2.39. 4.I "an exhaustive whitelist leaves the family open, because the next chapter audited meets a further form built the same way and it is flagged again" — condensed to "a closed set flags the next form built the same way".
2.40. 4.I "— that contradiction, not the translation, is what makes a pre-pass report an established rendering as a missing mapping" — reason beyond one sentence.
2.41. 4.I.1 "A row records what was decided for the sentences of the chapters it came from, and" — second reason; "a later chapter may mean something different by the same English word" is kept.
2.42. 4.I.1 "Phrasing that reads as an absolute command is what makes a later agent apply a row mechanically against a passage it does not fit, which is the failure the translator names when he says the glossary is a guide and not a constitution." — story and justification.
2.43. 4.J "making no claim about this book" — repeat of "not attested in this corpus".
2.44. 4.J "so that construction stays distinguishable from evidence" — reason.
2.45. 4.J "both are the translator's alone" — reworded as "both are the translator's decision".

### Section 5

2.46. 5.B "You add; you do not edit what was already decided." — reworded as "you only add".
2.47. 5.C "— not the chapter, not the English source, not the companion or report files in the repo" — examples restating the rule.
2.48. 5.D "Section 4.E exists because that judgment is the translator's, and a wrong one propagates silently into every chapter after this one." — reason, repeat of 4.E and of the opening paragraph; replaced by "escalate it".

### Section 6

2.49. 6.B "of the translator's report" — restatement.
2.50. 6.B "That line will read "N. DECIDE <path:line> — <the question>, and I recommend X", so give the conductor every part of it except the recommendation, which is his to make." — the sample restates the list just given; the rule is kept as "Leave the recommendation to the conductor."

## 3. Moved or merged

3.1. The verification condition of the opening paragraph now lives only in 1.A.
3.2. The "not an overflow home" rule for GC-open-terms.md is merged into the last sentence of 3.F.
3.3. The clergy-fixes escalation of 1.D now points to 4.G instead of stating it a second time.

## 4. Observations for the conductor (nothing changed)

4.1. 4.I.1 says the Notes give what an auditor should do "and why", while 3.F says reasoning goes in the merge report and never in a row. The original carried both sentences; both are kept as written.
4.2. 2.C and 3.D run a bare git diff. gc-run-check 2.E says a bare git diff returns nothing once rows are staged and uses git diff HEAD. Kept as written.
4.3. 6.A returns the full report content to the conductor, while root CLAUDE.md 1.I says a dispatched agent returns the path. Kept as written.
4.4. gc-glossary-merge.md has no row in th/SC/04_assets/scripts/instruction_budget.py. No row was added, because the brief said to edit nothing else.
4.5. The result is above the 900-word target. What remains is directives, their single reason sentences, and the 72-word report block of 6.A.

## 5. Word counts

5.1. Before: 1,806 words. After: 1,265 words. Both counted by whitespace split, the method of instruction_budget.py (wc -w gives the same figures).
