# Trim ledger: .claude/agents/gc-run-check.md

File: .claude/agents/gc-run-check.md

Words are counted by whitespace split, the method of th/SC/04_assets/scripts/instruction_budget.py. The starting text is the working copy, which already carried the uncommitted name-to-"the translator" edits.

## 1. Numbering

1.A. No item was renumbered. Every item from 1.A to 4.D keeps its number.
1.B. Blank lines between the section 4 items were removed, to match sc-resolve-check. The three indented blocks (files, report table, example lines) stay as blocks, unchanged.
1.C. The YAML front matter, including the description, is unchanged.

## 2. Removed, with reasons

### Opening paragraph

2.1. "(U+0ED0 to U+0ED9 for Lao, U+0E50 to U+0E59 for Thai)" became "Lao digits (U+0ED0–U+0ED9) or Thai digits (U+0E50–U+0E59)": rewording, as in the root CLAUDE.md.
2.2. "A Lao or Thai digit appearing in a marker or in an added line is a defect and fails the run.": repeat of 2.G; moved there (see 3.2).
2.3. "rather than retyping it" (after "Copy a Lao form out of the file"): restates "copy".

### Section 2

2.4. 2.B "and none is missing": repeat of "every number from 1 to N appears exactly once".
2.5. 2.B "spread over several sites is written as" became "at several sites is"; the dashes around "#12a, #12b, #12c" became commas: rewording.
2.6. 2.B "which together count as that single number": repeat of "is one number".
2.7. 2.B "must" (in "its letters must begin at a"): rewording.
2.8. 2.B "Do not require the numbers themselves to ascend in text order." became "Numbers need not ascend in text order": rewording.
2.9. 2.B "A lettered family scattered through the chapter puts its own later letters after higher numbers, and a pass that adds a marker after the run seats it at whatever anchor it belongs to rather than at the end; both break text order by construction" became "a lettered family's later letters and a marker added after the run at its own anchor both break that order": the explanation was shortened; both cases and "neither is a defect" stay.
2.10. 2.C "and holds only the findings whose context is too large to sit in the marker note": explanation that directs nothing.
2.11. 2.C "and no class of marker requires one": repeat of "a marker with no companion entry is never a failure".
2.12. 2.C "Check the other direction only: no companion entry lacks a matching marker" became "Check only that every companion entry has a matching marker": rewording.
2.13. 2.D "and the dispatch says so; in that case" became "which the dispatch names, ...:": rewording.
2.14. 2.E "Scope every git command to the manuscript tree:" and "Read-only git commands only." were merged into "with read-only git scoped to lo/GC:".
2.15. 2.E "at the repository root that are not real files and will otherwise" (about the sandbox placeholders): explanation shortened; "Ignore everything outside lo/GC" and its reason stay.
2.16. 2.E "The translator audits several chapters at once in separate sessions, so expect other chapters' manuscripts to be modified while you run:": story; the rule that those files are out of scope stays.
2.17. 2.E "they are out of scope, you neither read nor diff them" became "are out of scope: never read or diff them": rewording.
2.18. 2.E "What must hold is your own chapter, modified by markers and nothing else, and nothing untracked anywhere under lo/GC." became "Fail if your chapter is modified by anything but markers, or if anything under lo/GC is untracked.": rewording.
2.19. 2.E "is likewise not a failure on its own, because another chapter's merge may be sitting in the tree": reason; the rule "fails only if a line added there cites a ref of your chapter" carries it.
2.20. 2.E "which would mean a batch of yours wrote where only gc-glossary-merge may write" became "since only gc-glossary-merge may write there": shortened reason.
2.21. 2.F "Empty-new markers whose note does not begin verify: are deletion proposals; that is legal." became "An empty new side whose note does not begin verify: is a legal deletion proposal.": rewording.
2.22. 2.G "which is the one place Thai is deliberate": explanation.
2.23. 2.G "to" in the code-point ranges became "–": rewording.

### Section 3

2.24. 3.A "(grep, not memory)" became "with grep, never from memory"; "write the report — issue counts, nothing more" became "write gcNN-report.md: issue counts and nothing more"; "Reproduce this shape exactly" became "in exactly this shape": rewording.

### Section 4

2.25. 4.A "Open with one verdict line for the conductor" became "First line, nothing above it", and "This line is the only thing in your report that sits outside a numbered item." became "It is the only line outside a numbered item.": rewording.
2.26. 4.B "Your report goes to the conductor, who rewrites it for the translator, so give him numbered items" became "The conductor rewrites your report for the translator. Give numbered items": rewording.
2.27. 4.B "The shape of the translator's report is the conductor's problem, not yours.": rating; the sentence before it already says the conductor rewrites the report.
2.28. 4.C "The reference mark is" became "The reference is": rewording.
2.29. 4.D "at all" (in "Say nothing at all"): wording only.

## 3. Moved or merged

3.1. 2.E "the dispatch names them" (other chapters' modified manuscripts) moved to 1.A, which now lists "which modified files under lo/GC belong to other chapters" among the inputs. That matches the third input of lo/GC/CLAUDE.md 3.D. 2.E still says "named in the dispatch".
3.2. The opening sentence on a digit in a marker or added line moved to 2.G, which now ends "Any hit, in a marker or in the prose, fails the run."
3.3. The unnumbered line "Only classes with nonzero counts appear." after the report table moved into the 3.A line, before the block.

## 4. Not changed, for the conductor to weigh

4.1. The example line "2. FIX repo — a governing file was modified during the run." in 4.C contradicts 2.E. Under 2.E a modified governing file fails only when an added line cites a ref of the chapter. I left the example block unchanged.
4.2. th/SC/04_assets/scripts/instruction_budget.py has no row for this file, though root CLAUDE.md 7.C says every instruction file has one. I did not add a row; a row of 800 would fit the trimmed file.
4.3. The trimmed file is about 170 words over the target of about 600. 2.E, the cleanliness check scoped against parallel sessions, holds about 115 words of rules in force, and the front matter and three blocks hold about 100.

## 5. Word counts

5.1. Before: 972 words. After: 768 words.
