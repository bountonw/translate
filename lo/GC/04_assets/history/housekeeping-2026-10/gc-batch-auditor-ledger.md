# Trim ledger: .claude/agents/gc-batch-auditor.md


## 1. Numbering

1.A. No item was renumbered, added or deleted. Every number from 1.A to 10.E holds the same rule as before, so the external citations still resolve: lo/GC/CLAUDE.md cites 2.A.1 and 6.C, .claude/agents/gc-resolve-check.md cites 4.D, .claude/agents/gc-glossary-merge.md cites 2.B and 8.C, lo/GC/04_assets/scripts/gc_govcheck.py cites 6.C, and lo/GC/04_assets/history/GC-open-terms-history.md cites 2.B.
1.B. The YAML front matter is unchanged. The description lists the dispatch inputs that 1.A repeats, but it is the routing text the conductor reads, and the SC model keeps the same shape, so it stays.
1.C. The intro paragraph of section 5 was removed; it was unnumbered prose, so no number moved.

## 2. Removed text, by item

2.A. Opening paragraphs.
2.A.1. The author's name and possessive before *The Great Controversy* — the book title identifies the work, and the trim brief says to name no person.
2.A.2. "The Lao represents 2,000+ hours of deliberate editorial work;" — rating.
2.A.3. "No fix is ever auto-applied." — repeat of "You propose; the translator applies."
2.B. 1.A: "(e.g. {GC 237.1}–{GC 240.4})" — example; 10.A shows the range format.
2.C. 1.C.
2.C.1. "and never edited by you" — repeat of 6.E.
2.C.2. "most of it Lao, and that load is the largest single cost in a batch" — justification beyond the size figure.
2.C.3. "which reduced the 94 KB glossary to 3.4 KB of candidates for GC24" — story.
2.C.4. "This is the translator's ruling of 15 August, given after two batches of that chapter spent over 300,000 tokens between them." — date and story.
2.D. 1.D: "so a different spelling of the same path prompts on every batch" — shortened to "so any other spelling prompts"; reason kept in one clause.
2.E. 1.D.1.
2.E.1. "however plainly a corpus-wide count would settle a question" — repeat of "never on your own initiative".
2.E.2. "— that is the translator's ruling of 15 August, given after two batches of GC24 each ran searches nobody had asked for." — date and story.
2.E.3. "you cannot gather" — implied by the rule.
2.E.4. "where the answer changes something" — the conductor's own decision; directs nothing here.
2.E.5. "and a batch that counted ປ່ອຍປະ by hand reported seven sites where three were real, because ປົດປ່ອຍ|ປະເທດ and ປ່ອຍ|ປະຊາຊົນ each look like a hit." — story; the rule and its one-clause reason stay.
2.F. 1.E.
2.F.1. "A chapter in which no batch ever needs an entry therefore ends with no companion file at all," — restates the creation rule.
2.F.2. "which is the translator's ruling of 14 August — the file's existence has to mean it holds something, or he opens it for nothing." — date and justification.
2.F.3. "Never create it empty to reserve the name" — repeat of "created only by the first batch with an entry to write".
2.F.4. "and leave it alone" — repeat of "never create it or append to it".
2.G. 1.F.
2.G.1. "context you load is the dominant cost of a run" — justification; 1.C carries the size fact.
2.G.2. "Corpus-wide evidence is not yours to gather: it goes into a verify: marker under 1.D.1, never into a grep, a script or a read of another chapter." — repeat of 1.D.1; "a read of another chapter" moved into 1.D.1 (see 3.A).
2.H. 2.A: "apply judgment and" — implied by "drop what context licenses".
2.I. 2.A.1.
2.I.1. "so that consecutive batches do not report the same finding twice" — justification.
2.I.2. "Unlike the term pre-pass" — contrast only.
2.I.3. "because every check in it is mechanical: a missing sentence-final period, a quotation mark that never closes, a footnote with no closing punctuation, a Lao or Thai digit, a zero-width character, a straight quotation mark." — justification; the script names each finding's class, and the GRAM/SPELL mapping stays.
2.J. 2.D: "Write markers in text order, numbered sequentially from your starting number." — repeat of 4.B.
2.K. 3.A, TERM row: "(pre-pass survivors and closed decisions)" — repeat of 6.A, now cited as "(6.A)". CLARITY row: "threshold in" shortened to "(3.C)".
2.L. 3.C: "If you cannot name the misreading, no marker." — repeat of the item's first sentence.
2.M. 3.F.
2.M.1. "Where the Lao carries a clause the English does not, or drops one the English has, write the ADDITION or OMISSION marker" — merged into "is always marked as ADDITION or OMISSION".
2.M.2. "— the same shape 2.A.1 requires of a punctuation finding you disagree with." — cross-reference only.
2.M.3. "Judging it licensed and leaving it unmarked puts the decision inside your head, where the translator cannot reach it; marking it puts the decision at his cursor, which is where it belongs, and a marker he dismisses at a glance costs him far less than a difference he never sees." — justification.
2.M.4. "This is the translator's ruling of 14 August, given after a batch found two such differences in one paragraph and marked neither." — date and story.
2.N. 4.A: "they drift" — justification.
2.O. 4.D: "proposal" in "not a deletion proposal", and "to look thorough" — wording and rating.
2.P. 4.E: "Quoting only the English reads as though the note is quoting the very thing it calls missing." — justification.
2.Q. 4.G.
2.Q.1. "The translator resolves at the cursor, so a note that sends him to another file for the English has failed." — restated as the instruction "Never send the translator to another file for the English."
2.Q.2. "A TERM finding quotes the English head too, and always: the head is the entire basis of the finding, so a note that names a Lao form and proposes another without it gives the translator nothing to judge and sends him to the source file to hunt for the sentence." — justification; the TERM instruction stays in the next sentence, and "always" is now carried by "Every marker except SPELL and GRAM".
2.Q.3. "Only SPELL and GRAM findings are genuinely Lao-internal and quote nothing." — merged into the item's first sentence (see 3.C).
2.R. 4.H.
2.R.1. "you hold the manuscript, the source, the glossary and the whole corpus to grep, so drafting a candidate is your job and not his, and he has objected to being asked." — justification and story.
2.R.2. "rather than withholding the first" — implied by "PROPOSED: always holds the Lao you propose".
2.S. Section 5 intro.
2.S.1. "These are editorial decisions, not errors. No marker." — repeat of the section heading "Never report".
2.S.2. "None of them reaches a clause the Lao adds or drops, which item 3.F always marks." — repeat of 3.F ("section 5 never reaches it").
2.T. 5.B.
2.T.1. "so the next chapter finds the answer" — justification.
2.T.2. "Never assume a transposition is a literary variant — a slip and a deliberate choice produce identical evidence." — repeat of "looked up, never judged afresh", with its justification.
2.U. 5.B.1.
2.U.1. "whatever this section otherwise says about punctuation" — repeat of "never style".
2.U.2. "is a defect, and gc_punctcheck.py finds it for you under 2.A.1" — repeat of 2.A.1.
2.U.3. "The translator has caught these himself for nineteen chapters and expects the audit to catch them." — story.
2.U.4. "for the same reason" — referred to the removed story.
2.U.5. "That a marker on an invisible defect is unreadable at the cursor is a reason to write a note explaining what the eye cannot see" — reworded as the instruction "names the codepoints and says in words what the eye cannot see".
2.U.6. "that may never be run" — justification.
2.V. 5.B.2.
2.V.1. "English opens such a quotation afresh at each paragraph and closes it only at the last, so the intermediate paragraphs carry no closing mark; the Lao translation closes every paragraph it opens." — merged into the item's first sentence.
2.V.2. "This is the translator's ruling and not a pattern read off the corpus." — provenance.
2.V.3. "and the English being open is never a reason to dismiss the finding." — repeat of the clause before it.
2.W. 5.D: "Intentional." — rating; the section heading covers it.
2.X. 5.E.1.
2.X.1. "so no Lao chapter carries them; their absence is a settled decision of the translator's and not an omission" — restates "Never mark one".
2.X.2. "and where he judged a point needed explaining he added a footnote instead." — story; 5.D already exempts the translator's added apparatus.
2.Y. 5.G: "Both are established intentional strategies." — rating.
2.Z. 5.H: "Test when unsure whether style or substance" — shortened to "When unsure".
2.AA. 6.C.
2.AA.1. "and not merely the first" — repeat of "every site".
2.AA.2. "in its own words" and "so the disagreement is visible where it happens" — justification.
2.AA.3. "marking every site poses the question, it does not answer it" — justification.
2.AB. 6.D.
2.AB.1. "Every row in it was written for the sentences of some other chapter, in that chapter's context" — condensed to "each row records what was decided for another chapter's sentences".
2.AB.2. "some being hard guides and some soft, but none of them is law" — repeat of "a guide, never law".
2.AB.3. "and let it stand on its own" — repeat of "argue in ordinary language from what the words mean".
2.AC. 6.D.1: "because the history is about those particular men" — justification.
2.AD. 6.E.
2.AD.1. "— not a row, not a character" — emphasis.
2.AD.2. "gc-run-check treats any modification to a governing file as a run failure." — justification; the rule is absolute without it.
2.AE. 6.F: "kept so another project can inherit it" and "it makes no claim about this book" — reason and explanation.
2.AF. 7.A.
2.AF.1. "It is not where English travels: English goes inline under 4.G, for every class without exception." — repeat of 4.G; "for every class without exception" also contradicted 4.G, which exempts SPELL and GRAM.
2.AF.2. "Class never decides it: a FACT marker whose point fits inline stays inline, a TERM or SPELL marker whose point does not fit goes to the companion, and everything else lives entirely at its marker." — condensed to "whatever the class".
2.AF.3. "because every entry is a file the translator has to stop and open" — justification.
2.AF.4. "so a pointer is a dead end" — justification.
2.AF.5. "and an entry only adds depth for a reader who wants it" — restates "every note settles its own point".
2.AG. 7.B: "full finding id, executive summary on its own line in plain English, blank line, English context, blank line, reasoning" — repeat of the example block below it.
2.AH. 7.C: "The translator resolves at the cursor and must never hunt for the English." — repeat of 4.G.
2.AI. 7.D.
2.AI.1. "End the companion with a section headed "## Questions", added by whichever batch creates the file under 1.E." — repeat of 1.E.
2.AI.2. "the translator writes questions there, the conductor writes answers there" — condensed to "the channel between the translator and the conductor".
2.AI.3. "Where no batch had an entry and so no companion exists, that channel has no file for the chapter, and it is the conductor who creates one if the translator asks a question there." — directs the conductor, not this agent.
2.AJ. 8.A: "and section 12 is the one item 5.B already requires you to write" — repeat of 5.B.
2.AK. 8.C: "Size binds every row and entry you propose, because what you write lands in a file every agent loads on every dispatch." — justification.
2.AL. 9.A: "empty new side, note beginning verify:" — repeat of the unresolved-question shape of 4.D, now cited.
2.AM. 9.B.1: "the book has been the wrong side often enough that being in it is not evidence." — justification.
2.AN. 10.A: "for the conductor" and "A batch that wrote nothing uses the same shape:" — wording; both headline examples stay.
2.AO. 10.B: "The shape of the translator's report is the conductor's problem, not yours." — repeat of "The conductor rewrites them for the translator."
2.AP. 10.B.1.
2.AP.1. "so the conductor and the translator name the same object" — justification.
2.AP.2. "Numbering your items 1, 2, 3 alongside markers #8 and #9 gives the run two meanings for the same digit." — justification by example.
2.AQ. 10.C: "is not automatically a DECIDE item here" and "it stays in the file and" — wording; the rule stays.
2.AR. Single intensifiers dropped without change of rule: "ONLY" (1.A), "simply" (4.H), "genuinely" (7.A), "NEVER" (7.A, now "never"), "ALWAYS" (3.F, now "always"), "all" (4.F).

## 3. Rules moved or merged

3.A. 1.F's ban on "a read of another chapter" for corpus evidence moved into 1.D.1, which now reads "Never substitute a corpus grep, a count of your own or a read of another chapter". The word "corpus" was added so the ban does not appear to cover the grep of governing files in 1.C or the grep of copied forms in the opening paragraph.
3.B. 3.F's two sentences on writing the ADDITION or OMISSION marker and giving the reason were merged into one sentence.
3.C. 4.G's list of source-dependent classes and its closing sentence "Only SPELL and GRAM findings ... quote nothing" were merged into "Every marker except SPELL and GRAM quotes in its note the English its finding rests on". NOTE markers were covered only by implication before; they are now covered explicitly.
3.D. 5.B.2's explanation of the English convention was merged into its first sentence.
3.E. 9.A now cites "the unresolved-question shape of 4.D" in place of restating that shape.
3.F. 1.B's sentence that followed the file block now stands on the item line before the block. 1.D's sentence on the exact path and --glossary moved the same way.

## 4. Contradictions found and left as they stand

4.A. 4.D: the TERM example note "closed decision in GC-clergy-fixes.md: monastery" quotes no English, while 4.G requires every TERM note to quote the English head. The OMISSION example note "EN clause absent from the Lao" also does not state both sides, as 4.E requires. Neither example was changed, because changing a rule's example is a governing-file edit to propose, not a trim.
4.B. 10.C: the example numbers its items "1. DECIDE #5" and "2. NOTE", while 10.B.1 (and root CLAUDE.md 1.G.2) says an item about marker #5 carries the number 5 and an item without a marker takes the next number above the highest marker. Not changed, for the reason in 4.A.
4.C. 9.B.1 says to mark every site where the manuscript and a governing file disagree, while 6.D says there is nothing to fix where the Lao already says what the English says, however far it sits from a row, and that accepted term-family variation gets no marker. Both rules were kept as written.
4.D. 4.H says "nothing before the block" in a "verify: DECIDE" note, while 4.G requires the English to be quoted before the explanation. The file does not say where the English goes in a DECIDE note. Both were kept as written.
4.E. Section 10 has the agent return its report in the reply. Root CLAUDE.md 1.I says a dispatched agent writes its report to a file in the sandbox and returns the path, and root 1.E asks for a blank line around each labelled line, which 10.D does not state. Not changed, because the brief was to trim and not to add rules.
4.F. th/SC/04_assets/scripts/instruction_budget.py has no row for .claude/agents/gc-batch-auditor.md. The script passes (exit 0) but does not measure this file. A row near 3,150 would cover the trimmed text.

## 5. Checks run

5.A. Every Lao string in the trimmed file (ອາຮາມນັກບວດ, ສຳນັກນັກບວດ, ຂໍ້ຄວາມທີ່ຂາດ, ຂໍ້ຄວາມເກີນ, ຂໍ້ຄວາມ, ພຄພ, ເຄີຍ) was checked byte for byte against the original and matches. The file has no invisible characters and no Lao or Thai digits.
5.B. The list of item numbers in the trimmed file is identical to the list in the original.

## 6. Word counts

6.A. Before: 4,511 words (whitespace split, the count instruction_budget.py uses; wc -w agrees). The brief gave 4,483, so it was probably counted another way.
6.B. After: 3,125 words, 31% fewer. The text is still over the 2,000 target because each remaining sentence gives an instruction. The rest of the gap from the SC model comes from rules the SC auditor does not have: the companion, the proposals file, the open-terms families, the formfind limits and the verify: DECIDE block.
