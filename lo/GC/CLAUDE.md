# GC audit — conductor

This file governs the audit of the Lao translation of *The Great Controversy* in lo/GC. The book is printed; the procedure stands ready for a correction round or a second printing. The LaTeX pipeline in lo/GC/04_assets/scripts/ and the dictionaries in lo/assets/dictionaries/ serve this book only and are kept working for later printings and corrected PDFs; new Lao books typeset with Typst. The root CLAUDE.md governs reports, register and git. Rulings enter this file as one line each. The queue is lo/GC/04_assets/planning/SIDEQUESTS.md.

## 1. Triggers

1.A. "GCNN" or "run GCNN" — the chapter audit, section 3.
1.B. "check GCNN", or the translator says he has finished resolving — section 4.
1.C. "import GCNN" — splice a web-app handoff into the chapter as markers with gc_import_handoff.py, by the procedure at the end of ~/claude-sandbox/gc-audit/web-handoff-prompt.md.
1.D. A term family or corpus question — dispatch gc-term-grep and relay its report verbatim.
1.E. "7/3/1" and "model: X/Y/Z" — the drill of the root CLAUDE.md.
1.F. Anything else — ask.

## 2. Paths

2.A. Chapter: lo/GC/03_public/GCNN_lo.md. English source: lo/GC/00_source/GCNN_en.md, anchored "## {GC ###.#}".
2.B. Governing files: lo/GC/04_assets/translation_profile/GC-glossary.txt, GC-clergy-fixes.md and GC-open-terms.md. Queue entry 17 reworks them into one glossary per language with book overlays.
2.C. Scripts in lo/GC/04_assets/scripts/, invoked by that relative path from the repository root so the allow-rules match; each says what it does in its first lines. The chapter run uses gc_termcheck.py (batch pre-pass), gc_resolution_sheet.py (3.F), gc_resolvecheck.py (post-resolution sweep) and gc_dictcheck.py (4.B). gc_punctcheck.py runs in every batch of gc-batch-auditor and by hand for a sweep. gc_formfind.py runs by hand, or in a batch only where the dispatch names the script and the form. gc_versecheck.py checks unlabelled quotations against LO2012 and LCV. gc_govcheck.py and gc_import_handoff.py are never run by an agent.
2.D. Markers go into the chapter file. Everything else a run produces goes to ~/claude-sandbox/gc-audit/.
2.E. Introduction files (GC00*) are out of scope unless the translator names them.
2.F. Not run input, opened only when the translator asks: lo/GC/04_assets/scripts/build/ (ignored build output: temp files, PDFs and logs); lo/GC/04_assets/history/ (evidence moved out of the governing files, keyed by English head, and the records of finished sweeps); lo/GC/04_assets/qa3/ (the QA3 record per chapter).
2.G. Kept for reference from the finished QA3 round and pre-press sweeps: gc-qa3-reader, gc_qa3_packet.py, gc_namemark.py and gc_versemark.py.

## 3. Chapter procedure

3.A. Preflight: 2.A's files exist; the chapter holds no [[ marker, else name the numbers and stop; git status --short -- lo/GC shows the chapter unmodified, read per 5.D. Grep the chapter; never read it whole.
3.B. Split by English words, never by paragraphs or pages: wc -w on the source; batches = words / 2200 rounded up; under 2700 words is one batch. Walk the anchored paragraphs and close each batch at the anchor nearest its even share, so no remainder piles onto the last batch. State the ranges as full anchors, no anchor in two batches, and proceed.
3.C. Dispatch gc-batch-auditor per batch, in sequence, with chapter, ref range, starting marker number and first-batch flag (the first batch creates the session files). The next start is the last reported number plus one; a batch that wrote nothing reports one below its start, and the next keeps that start. A batch writes gcNN-companion.md and gcNN-glossary-proposals.txt only; never name gcNN-report.md to a batch, because gc-run-check overwrites it. Where a batch opened a lettered family (its 6.C), pass the family, its number and last letter to the next batch; never tell a batch to leave a recurrence unmarked.
3.D. After the last batch, dispatch gc-run-check with the chapter, the expected marker total (the last number reported by the last batch that wrote any, never the sum of counts) and the scoping paragraph of 5.D. No markers: skip it and report the chapter clean.
3.E. If run-check passed and the proposals file has a section that is not "none", dispatch gc-glossary-merge with the chapter and the pass. Never on a failed run and never during one. A failed run skips the merge and says so.
3.F. Run python3 lo/GC/04_assets/scripts/gc_resolution_sheet.py --chapter NN and read its summary line: intact, damaged, unterminated, and markers whose old side is not in the committed chapter. Delete those last markers and establish the findings again. The sheet is not a deliverable; re-run it whenever markers change.
3.G. Report: the counts table from gcNN-report.md, run-check failures, the merge report's applied and escalated counts, and the auditor items whose effect reaches past their own site. A decision confined to one marker stays at the cursor. The translator resolves in Emacs and reviews glossary changes with git diff.

## 4. Post-resolution check ("check GCNN")

4.A. Grep the chapter for [[. Standing markers end the check: name the numbers and stop.
4.B. Run python3 lo/GC/04_assets/scripts/gc_dictcheck.py --chapter NN. It loads the typesetting dictionaries and lists every changed token they cannot segment. Name each in the gc-resolve-check dispatch: a typo takes a FIX marker, a new word a proposed coded row. After the chapter passes, append the confirmed rows to lo/assets/dictionaries/main.txt under a comment naming the chapter, never editing an existing line, and tell the translator to review them with git diff.
4.C. Dispatch gc-resolve-check with the chapter, the last marker number, and every resolved marker's class, anchor, old span and note (its 5.E needs them). Relay its report verbatim. PASS means clean to commit. Apply its FIX markers one at a time against text you have read, never with a script.

## 5. Rules

5.A. You orchestrate; agents work. A run's only repository edit is markers in the chapter.
5.B. Neither you nor a batch writes a governing file; proposals go to the proposals file. Only gc-glossary-merge writes GC-glossary.txt and GC-open-terms.md, after a passing run, uncontested rows only; no agent writes GC-clergy-fixes.md. A repair of a point the translator has already settled needs no agent: delete a row he declared stale, fold an exact duplicate, mend broken pipes. Anything that chooses between readings or adds a row goes to gc-glossary-merge.
5.C. A Notes cell or GC-open-terms.md entry holds at most 15 words, refs excluded, on one line: the approved form, the wrong form, and "mark any other form" where a family is closed. Counts, ref lists and reasoning go to the run's files, or to the matching history file when displaced from a row.
5.D. Cleanliness is scoped to your chapter. Other chapters' manuscripts and governing-file rows are another session's and never stop a run; gc-glossary-merge writes into an uncommitted tree and refuses only a row another session touched, so a merge is never held back for a dirty tree. Before gc-run-check, name in the dispatch the files under lo/GC that belong to other chapters. Run-check fails your run if your chapter's diff holds anything but markers, if anything under lo/GC is untracked, or if a governing-file line cites your chapter's refs. A path listed as a character device owned by nobody (ls -l) is a sandbox mask, never a defect; .claude and .mcp.json under lo/GC are that case.
5.E. Never apply a fix across chapters on your own initiative. Give the translator the sites, the chapters, the change at each, and which files another session has modified.
5.F. A brief that asks an agent to judge wording says that the glossary guides and never rules, and that the argument comes from the passage.
5.G. Grep rather than read; pass an agent what you already know rather than letting it rediscover it.
5.H. Name a forbidden codepoint rather than printing it.
5.I. LaTeX in a manuscript (\s, \S, {\;}, \thai{} and the rest) is typesetting markup, not audit material. A mangled macro, a lost backslash or brace leaving stray letters in the Lao, takes a FIX marker. Thai quoted in a marker note still goes inside \thai{}.
5.J. When a sentence is redrafted, the draft goes above the old paragraph in the manuscript, and the old text stays for comparison until the translator settles it.
5.K. A naming gloss the translator added stays where the quoted Bible versions use different terms for the same referent.

## 6. Punctuation

6.A. Where English leaves a quotation open across the paragraphs of a multi-paragraph quote, the Lao closes every paragraph it opens. A Lao paragraph whose double quotation marks do not balance is a defect even where the English is open there.
6.B. Every sentence closes with a period, question mark or exclamation mark, and every footnote entry with punctuation. A citation ending a paragraph takes the period after its bracket, and a footnote marker follows that period: (ພຣະນິມິດ 7:10, 12). and (ເບິ່ງ ໂຢບ 9:5 TKJV).[^26] A paragraph may end with a colon only where the next is the block quotation it introduces.
6.C. ແລະ takes a space on each side where it joins two parallel items, and closes up against the next word where it opens a clause with its own subject and predicate. A joined ແລະ after a comma, semicolon, full stop or quotation mark is correct and never raised. In a sentence that holds both uses, quote the whole sentence, say which job each instance does, and let the translator settle it.
6.D. gc_punctcheck.py enforces these and sixteen further classes, digits and invisible characters among them. Where a finding looks wrong, raise it with the translator rather than adding a case to the script.

## 7. Reporting

7.A. The root CLAUDE.md report shape. A summary line is located by its {GC ###.#} anchor and the marker number where there is one. A FIX that needs a manuscript change is also written into the chapter as a [[FIX SEV #N|old -> new|note]] marker.
7.B. gc-resolve-check and gc-term-grep return Lao spans and are relayed verbatim. gc-batch-auditor, gc-run-check and gc-glossary-merge write for you; compose the report from their items, copying every Lao form from their files.

## 8. Print build

8.A. Before a print build, run modules 1 and 2 for every chapter; from lo/GC/04_assets, grep -c nodict scripts/build/temp/*_stage2.tex must be zero for every file.
8.B. A file sent to the press is kept in lo/GC/05_print/; everything a build writes stays in lo/GC/04_assets/scripts/build/.
