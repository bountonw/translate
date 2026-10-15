# Trim ledger: .claude/agents/gc-resolve-check.md

File: .claude/agents/gc-resolve-check.md

Words are counted by whitespace split, the method of th/SC/04_assets/scripts/instruction_budget.py. The starting text is the working copy, which already carried the uncommitted name-to-"the translator" edits.

## 1. Numbering

1.A. No item was renumbered. Every item from 1.A to 7.E, including 7.B.1 to 7.B.3, keeps its number.
1.B. 5.E keeps its number and its content, because lo/GC/CLAUDE.md 4.C, as it stands in the working tree after another session's edit, cites "its 5.E".
1.C. The headings of sections 2 to 5 keep "Pass 1" to "Pass 4", because the docstring of lo/GC/04_assets/scripts/gc_resolvecheck.py cites "passes 1, 2 and 3" and "pass 4".
1.D. Blank lines between items were removed, to match sc-resolve-check. The three indented example blocks stay as blocks.

## 2. Removed, with reasons

### Front matter

2.1. "in the manuscript" (after "resolved the audit markers"): restates the body.
2.2. "into the manuscript for each defect it finds" became "per defect": restates section 7.

### Opening paragraphs

2.3. "He has accepted, dismissed, or modified the inline markers in his editor": context that directs nothing; the dismissal sentence and 5.D carry the rules.
2.4. "your job is to confirm the chapter is clean to commit" was folded into the first sentence: merge, nothing lost.
2.5. "rather than retyping it" (after "Copy a Lao form out of the file"): restates "copy".
2.6. "One rule above all:": rating.
2.7. "that is a decision, not a defect" became "is a dismissal, not a defect": rewording.
2.8. "Treat a stray Lao or Thai digit in the resolved prose as a defect to be marked" was kept as the clause "a stray one in the resolved prose is a defect to mark". The digit ranges are now written U+0ED0–U+0ED9 and U+0E50–U+0E59, as in the root CLAUDE.md.

### Section 1

2.9. 1.A "so section 7 can continue the sequence": repeats 7.C.
2.10. 1.B "The measurement window is git." and "Read-only git commands only." were merged into "The window is git, read-only".
2.11. 1.B "clean" (in "the clean pre-run chapter"): rating.
2.12. 1.B "Scope both commands to the chapter": repeats the commands, which name the chapter.
2.13. 1.B "compares the working tree against the index and": mechanism beyond the one reason kept ("returns nothing once the resolutions are staged").
2.14. 1.B "(one line is one paragraph)" became "one line per paragraph", and "within them" was dropped: rewording.
2.15. 1.C "— the translator may already have committed, and he will tell you what to diff against": story and reason; the rule "never guess at a commit" stays.
2.16. 1.E "relative" and "allow-" (in "exact relative path ... permission allow-rule"): wording only; the exact path and the permission reason stay.
2.17. 1.E "a pass it prints as OK is settled and contributes one word to your report": repeat of 6.E.
2.18. 1.E "rather than a defect" became "not a defect", and "context-dependent, and you judge those in context" became "depend on context; judge each in context": rewording.
2.19. 1.E "the judgment read," (after "section 5"): repeats the section 5 heading.
2.20. 1.E "fall back to sections 2 through 4 by hand" became "do sections 2 to 4 by hand": rewording.

### Section 2

2.21. 2.A "the whole chapter": repeats the heading "chapter-wide".
2.22. 2.A "either an unresolved marker or a half-deleted one": explanation that directs nothing.
2.23. 2.B "only" and "These are splice leftovers." became ": splice leftovers": rewording.
2.24. 2.C "the whole chapter": repeats the heading.
2.25. 2.C "and they are transient scaffolding that must never reach a commit" became "which never reach a commit": figurative phrasing cut.
2.26. 2.C "answers live in the companion document, not the manuscript": reason beyond "never answer one".

### Section 3

2.27. 3.B "embedded": wording only.
2.28. 3.B "are an established convention and": justification.
2.29. 3.B "(its flex and rigid space markers)" became "(flex and rigid space)": wording only.
2.30. 3.B "A mangled macro is the one exception:" and "is an introduced typo and" were cut: restatement; the rule "a mangled macro ... is a defect" stays.
2.31. 3.B "This is the translator's ruling of 26 August.": date and story.

### Section 4

2.32. 4.B and 4.C were reworded only ("No duplicate footnote numbers" became "No footnote number is duplicated"; "must still follow" became "still follows"). Nothing was removed. The Lao form in 4.C was copied from the file.

### Section 5

2.33. 5.A "in full" became "whole", and "Confirm the sentence still parses across every splice" became "Every splice parses": rewording.
2.34. 5.B "after the edit": implied by "still resolve".
2.35. 5.D "instead of accepting the proposed fix": implied by "his own wording".
2.36. 5.D "do not say his wording differs from it": repeat of "never compare it with the proposed fix".
2.37. 5.D "and do not prefer it because an agent wrote it": repeat of "never ... argue for the proposal".
2.38. 5.E "and never to be confused with it": repeat of "Separately from 5.D".
2.39. 5.E "check that each resolution actually settles the finding that was raised" was merged into the question "whether the text now standing answers its note's point": repeat.
2.40. 5.E "so you can ask one question per site": restates the question.
2.41. 5.E "and is yours": restatement.
2.42. 5.F "get one extra check": framing that directs nothing.
2.43. 5.F "and their wording therefore cannot be verified by anyone but the translator": a second reason; one reason sentence ("the repository holds no Lao Bible") stays.
2.44. 5.F "the quotation must cover the span the English quotes and no more, its verbs must do what the English's verbs do, and its citation must name the right book, chapter and verse" was merged with "A paste that runs past the English's span, stops short of it, or answers a different verse is a defect and is reported": the same rule stated twice. All five tests (past the span, short of it, a different verse, the verbs, the citation) stand in one sentence.
2.45. 5.F "plainly" and "so nobody reads your PASS as covering it": justification. The rule to say the wording was not checked, and why, stays.

### Section 6

2.46. 6.A "Open with one verdict line for the conductor" became "First line, nothing above it": rewording.
2.47. 6.B "The format is given here in full.": directs nothing.
2.48. 6.B "so it has to read correctly on his screen exactly as you write it": consequence of "relays your report unchanged".
2.49. 6.B "There is no summary list above the detail, because every labelled line in the detail already opens with its own summary sentence, and a top copy only makes him scroll past what he has already been told." became "and nothing else": the reason was cut; the rule (detail first, summary at the bottom only) stays.
2.50. 6.B "the reference that locates the item — the marker number you wrote per section 7 and the {GC ###.#} anchor —" became "the reference of 6.C": repeat of 6.C. 6.C now names the {GC ###.#} anchor explicitly.
2.51. 6.B "a pronoun, a quantifier or a bare label points at nothing on his screen, and a description that refers to a change instead of stating it fails the same way" was merged into the stand-alone sentence ("name its subject, ... the change itself, never a pronoun, a quantifier or a bare label"): reason cut, rule kept.
2.52. 6.B "Nothing after the verdict line sits outside a numbered item.": repeat of 6.A.
2.53. 6.B "so that a number the translator types names the same object in the manuscript, in the report and in his reply": reason.
2.54. 6.B "Write every item so that it can be understood with no memory of the exchange that produced it: name the text, the file and the change inside the item itself, and give the actual figures rather than a summarising word such as "both" or "several" standing in for them." was shortened to "Every item stands alone with no memory of the exchange: name its subject, the text, the file and the change itself ... and give the figures rather than "both" or "several"": wording only.
2.55. 6.B "comes first" (in "The detail section comes first"): repeat of the order sentence.
2.56. 6.B "Findings here are Lao-internal, so there is no EN field." was kept as "There is no EN field, because the findings are Lao-internal"; "give no block at all" lost "at all"; "Write brief, complete English throughout and never clip a line into fragments" became "in brief, complete English, never fragments": rewording.
2.57. 6.C "The reference mark is" became "The reference is": rewording.
2.58. 6.D "so he knows it was covered without reading about it": reason.
2.59. 6.E "A clean pass produces no prose." and "The same holds for every pass." were merged into "A clean pass adds its one word to the 6.D line and nothing else": repeat.
2.60. 6.E "If the footnote chain is intact it contributes the word "footnotes"" and "of which reference matched which definition": the footnote example was cut; the general rule covers it.
2.61. 6.E "That rule governs clean passes only and reverses when a pass finds something:": restatement.
2.62. 6.E "a broken footnote chain, a spelling collision or a failed splice": examples cut; "A pass that finds something earns a FIX line" stays.

### Section 7

2.63. Heading "Writing your findings back into the manuscript" became "Writing findings into the manuscript".
2.64. 7.A "so the translator can jump to it rather than hunt for it": reason.
2.65. 7.A "This is the only edit you make; you never change the prose itself.": repeat of the opening paragraph.
2.66. 7.B "Syntax is the run's syntax with the class FIX, written in place as" became "Write it in place in the run's syntax with the class FIX:": rewording.
2.67. 7.B "The marker replaces that exact span at the exact position where it stands": repeat of "in place".
2.68. 7.B "rather than merely sit near it" became "not text near it": rewording.
2.69. 7.B "— a marker a few words away from the fault sends the translator hunting for something he can already see is not there": justification.
2.70. 7.B.2 "A marker replaces the span it flags, so a span that was never in the manuscript writes invented text into the book the moment the translator accepts it.": justification.
2.71. 7.B.3 "Otherwise the two sides print as the same string twice and cannot be told apart without counting characters.": justification. The dashes around the list became "such as". The Lao example was copied from the file.
2.72. 7.C "so a later pass keeps counting upward from wherever the previous one stopped": restates "numbers are never reused".
2.73. 7.D "so the next pass can continue from it": reason.
2.74. 7.E "If a pass finds nothing, you write nothing." and "A PASS never touches the file." were merged into "A PASS writes nothing to the file.": repeat.

## 3. Moved or merged

3.1. 5.E "The conductor gives you every resolved marker's class, anchor, old span and note" moved to 1.A, which now lists it among the inputs. 5.E keeps the check itself.
3.2. The opening sentence "You report only damage introduced by the act of resolution." was merged with 5.E into "You report damage from the act of resolution and, under 5.E, a resolution that leaves the marked fault standing." The old sentence said "only" and so contradicted 5.E; the new one states both, as sc-resolve-check does.
3.3. The three opening paragraphs became one paragraph, as in sc-resolve-check.
3.4. The four unnumbered paragraphs of 6.B and the sentence after its example block became one line, 6.B, before the block.
3.5. The description sentence "Dispatched by the conductor before the translator commits." moved to the end, as in sc-resolve-check.

## 4. Not changed, for the conductor to weigh

4.1. 5.F says "the repository holds no Lao Bible". lo/GC/04_assets/scripts/gc_versecheck.py compares unlabelled quotations with the Lao texts LO2012 and LCV under ~/programming/bible/, outside the repository. The sentence is still literally true, so I left it.
4.2. 6.B says the findings have no EN field because they are Lao-internal, but 5.E and 5.F judge against the English. I left the rule as it stands.
4.3. 6.B asks for the label in block capitals; the root CLAUDE.md 1.B asks for the number and label in bold. I left the agent's wording.
4.4. th/SC/04_assets/scripts/instruction_budget.py has no row for this file, though root CLAUDE.md 7.C says every instruction file has one. I did not add a row; a row of 1,650 would fit the trimmed file.
4.5. The trimmed file is about 600 words over the target of about 1,000. Three parts hold it there, and each carries rules in force: the report format of 6.B (about 205 words, kept under rule 3), the script coverage list of 1.E (about 130 words; the script does not check 3.C's "same word spelled two ways" or 4.C's ibid chain, so "sections 2 to 4" would be wrong), and the fallback passes of sections 2 to 4, which sc-resolve-check also keeps.

## 5. Word counts

5.1. Before: 2,288 words. After: 1,596 words.
