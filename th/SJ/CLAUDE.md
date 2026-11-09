# SJ rounds — conductor

This file governs the QA rounds of the Thai *The Story of Jesus* in th/SJ. An SJ session reads this file, th/assets/translation_profile/thai-profile.txt and thai-glossary.txt before working. The root CLAUDE.md governs reports, register, Thai text, agents and git, and binds every file below. Rulings enter this file as one line each. The queue is th/SJ/04_assets/planning/SIDEQUESTS.md.

## 1. Triggers

1.A. "pre SJ01 [SJ02 ...]" or "pre all" — pre-processing, section 11.
1.B. "qa1 SJ01 [SJ02 ...]" — round one, accuracy (3.C), by section 4. Chapters named together run in parallel; batches inside a chapter run in sequence.
1.C. "qa2 SJ01 [SJ02 ...]" — round two, terms (3.D), by section 4, only on a chapter whose QA1 is committed.
1.D. "qa3 SJ01 [SJ02 ...]" — round three, the reader's round (3.E), by section 4, only on a chapter whose QA2 is committed.
1.E. "check SJ01" — the translator has resolved the markers; section 5.
1.F. "editor SJ01" or "editor SJ01 #12 #14" — flatten the remaining markers, or the named ones, into editor parentheses so the chapter can go to Google Docs: python3 th/SJ/04_assets/scripts/sj_editor_markers.py --chapter 01 [--markers 12 14]. A verify: marker is left standing and reported by number.
1.G. "terms SJ01 [SJ02 ...]" — glossary mining, section 7.
1.H. A term or corpus question — answer by grep over th/PP, th/MB, th/SC and th/SJ, copying every Thai form out of a file.
1.I. "7/3/1" and "model: X/Y/Z" — the drill of the root CLAUDE.md, by sj-wording-drill.
1.J. "read SJ01 [SJ02 ...]", a chapter's Finished button, or a reviewers' export — the read-through, section 10.
1.K. Anything else — ask.

## 2. Paths

2.A. Chapters: SJ01 to SJ32 in th/SJ/03_public; SJ00, the front matter, in th/SJ/01_raw. Confirm the stage with ls.
2.B. English source: th/SJ/00_source/SJNN_en.md, anchored "## {SJ ###.#}", written by sj_source_extract.py from the EGW Writings app's book 144 as ~/claude-sandbox/egw/egw_extract.py extracts it; SJ00_en.md is the preface.
2.C. Governing files: th/assets/translation_profile/thai-profile.txt and thai-glossary.txt. A glossary row is silent until its Notes cell carries [CHECK] or [FLAG]. Where both are silent, grep the finished Thai books for evidence; evidence never rules.
2.D. Markers go into the chapter file. Everything else a run produces — the resolution sheet, term candidates, agent reports — goes to ~/claude-sandbox/sj-audit/.
2.E. Scripts in th/SJ/04_assets/scripts/, invoked by that relative path from the repository root: sj_anchors.py, sj_punctcheck.py, sj_refcheck.py, sj_notescheck.py, sj_resolution_sheet.py, sj_editor_markers.py. Each says what it does in its first lines.
2.F. Compile check, from th/SJ: ./typst-custom compile --root . 03_public/SJNN_th.typ $TMPDIR/SJNN.pdf. Never on a chapter holding markers, and book.typ, which includes every chapter, never while any chapter holds one. typst-custom is not tracked; a new worktree takes a copy from the main checkout.
2.G. SJ revises the published Thai translation, เรื่องของพระเยซู, whose OCR is th/SJ/01_raw at commit 2ca0d5a1 and whose PDFs are th/SJ/04_assets/thai_original_pdfs. The print is reference only, never precedent: no candidate is ranked up for matching it or down for departing from it.
2.H. The rounds run on the branch the translator names, first SJ-qa1 in ~/claude-sandbox/wt-SJ-qa1; the start check of root 8.F confirms it.

## 3. The rounds

3.A. Three light rounds. Each round marks one kind of thing; a finding outside the round's classes is neither marked nor reported.
3.B. Every batch runs sj_punctcheck.py and sj_refcheck.py on its range. Each finding line takes a marker, SPELL or REF; a NOTE line takes none. SJ's default Bible version is THSV, written in the chapters as a hidden /*THSV*/ or as a visible THSV, so the batch auditor deletes every THSV label in its range, of either form, silently and reports the count; the report carries it as one NOTE.
3.C. QA1, accuracy: SPELL, GRAM, REF and NOTE, which carry no severity; FACT, OMISSION, ADDITION and ALIGN, which carry HIGH or MED and never LOW. No TERM, CLARITY or wording marker. The table in sj-batch-auditor defines each class.
3.D. QA2, terms: TERM, HIGH, MED or LOW, where the Thai at a glossary head's site carries a different sense from the one the row rules, or lets the reader land on a wrong one; the note says what the sentence does to the reader and gives the row and what it rules as evidence. A site that uses one of the row's forms takes nothing. Candidates come from sj_termcheck.py over every row of glossary sections 1 and 2; the auditor judges each in its sentence. An accuracy finding QA1 missed is marked in its QA1 class. The translator's own ((A/B)) waits for QA3.
3.D.1. A row anchored in a Bible verse or naming a doctrine, an office or a title is set terminology: a departure takes a marker unless the sentence resists the form, and then the report raises the row. A row for an ordinary word or an image guides only: a departure stands where the sense holds.
3.E. QA3, the reader's round: Fable reads every paragraph of the chapter whole, English beside Thai, as a Thai reader would, and marks CLARITY, a wrong reading the reader lands on, HIGH, MED or LOW; READ, a sentence the reader stumbles on or hears as translated, its gain named; CHOICE, two candidates the translator picks between; the translator's own ((A/B)) or ((word)) stands unless the reader raises a new issue at it. It does not check terms against the glossary. For a paragraph QA1 or QA2 changed it also sees the Thai before those rounds and may propose the earlier wording back. An accuracy finding the earlier rounds missed is marked in its QA1 class. READ and CHOICE together are capped at one per 150 English words; a READ changes at most one sentence and a paragraph carries at most two.
3.F. Every wording a QA2 or QA3 marker proposes is drilled at 8/5/1 in its passage: the best candidate is the new side and the next four stand in the note as new2 to new5, one clause each; the numbers come down if the cost demands.
3.G. A round writes at most 20 markers in a chapter, shared across its batches by English words; the auditor spends them on the largest gains and lists the sites it left out.
3.H. A site where a [CHECK] row's forms are absent and the Thai carries the English sense takes no marker; the report raises whether the row should list the form, and a wording kept on purpose goes to SJ_notes.txt under 6.I. When in doubt, the site takes a marker.

## 4. Chapter procedure, every round

4.A. Preflight: the chapter holds no [[ marker, else name the numbers and stop; its paragraphs sit under their "// {SJ ###.#}" comments, else name "pre" and stop; git status --short -- th/SJ shows the chapter unmodified. Another chapter's modified file is another session's. Grep the chapter; never read it whole.
4.B. Split: wc -w on the English source; batches = words / 2200 rounded up; under 2700 words is one batch, which every SJ chapter is. State the split and proceed.
4.B.1. For qa2, build the candidate file with python3 th/SJ/04_assets/scripts/sj_termcheck.py --chapter NN, which writes ~/claude-sandbox/sj-audit/sjNN-term-candidates-qa2.md. Pass its path and the queue's qa2 sites for the chapter to every batch.
4.B.2. For qa3, build the changes file with python3 th/SJ/04_assets/scripts/sj_changes.py --chapter NN --base COMMIT, where COMMIT is the parent of the chapter's commit "SJNN qa1" (git log --oneline -- the chapter file); it writes ~/claude-sandbox/sj-audit/sjNN-changes.md. Pass its path and the qa2 side list to every batch.
4.C. Dispatch sj-batch-auditor (qa1), sj-batch-auditor-qa2 (qa2) or sj-reader-qa3 (qa3) per batch, in sequence, with chapter, stage directory, ref range, starting marker number, round name, first-batch flag, the report path ~/claude-sandbox/sj-audit/sjNN-ROUND-batchK.md, and the files of 4.B.1 or 4.B.2. Markers restart at #1 each round; the next start is the last reported number plus one.
4.D. After the last batch, run python3 th/SJ/04_assets/scripts/sj_resolution_sheet.py --chapter NN --round qa1 (or qa2, qa3) and read its VERDICT line. Delete a marker whose old side is not in the committed chapter and establish the finding again.
4.D.1. Before the sheet, narrow every marker to the words that change with python3 th/SJ/04_assets/scripts/sj_minspan.py --chapter NN; where its cut splits a word, re-run it with --prefix or --suffix; write each narrowed marker into the chapter.
4.E. Report: every marker as a full item with EN, the whole TH sentence, PRINT (the print's sentence at that anchor, from th/SJ/01_raw at commit 2ca0d5a1), ISSUE, FIX1 and every further candidate printed in full; then the counts table, the THSV-label count and every DECIDE. A decision confined to one marker is not raised as a DECIDE. Give the sheet's path.

## 5. Post-resolution check ("check SJ01")

5.A. Grep the chapter for [[. Standing markers end the check: name the numbers and stop.
5.B. Run sj_punctcheck.py, sj_refcheck.py, sj_notescheck.py, assets/scripts/instruction_budget.py, then build_breaks.py --book SJ and the compile check. Each chapter finding becomes a [[FIX #N|old -> new|note]] marker numbered on from the round's last number; a stale note is a DECIDE, updated or deleted; a file over budget is a FIX in the report.
5.B.1. A finding the round already judged and the translator ruled on, such as a Typst comment ruled to stand, takes no marker at check and is not raised again.
5.C. Dispatch sj-resolve-check with chapter, stage directory, last marker number, the report path, and every resolved marker's class, anchor, old span and note. Build the report from its file. PASS means clean to commit and to upload.
5.D. A PASS ends with the round's commit as a numbered item: the files to stage, by full path, and the message "SJNN qa1" (8 characters), "SJNN qa2", "SJNN qa3" or "SJNN read", with the round's counts in a paragraph below it. One commit per chapter per round keeps every round in the branch history.
5.E. When the branch's rounds are done, the report says that its pull request is merged with a merge commit, never squashed or rebased, so each round's commit reaches main.

## 6. Rules

6.A. You orchestrate; agents work. A run's only repository edit is markers in the chapter; pre-processing adds the anchor comments.
6.B. Chapters are Typst: a "// {SJ ###.#}" comment above each paragraph, an "#EGW[\{SJ ###.#\}]" tag at its end, footnotes inline as "#footnote[...]". A line commented out with // that carries a tag is a filler from the printed book and stands as it is until the translator rules on it. Reference prose by anchor, never by line. A chapter holding markers is never compiled.
6.C. Thai text and citations follow thai-profile.txt.
6.D. An editor's choice is a double parenthesis, ((A/B)) or ((word)), spanning only the words that differ, the original wording tagged original: so the editor sees it: it stands in every round unless the reader raises a new issue at it; sj_punctcheck.py lists every one standing.
6.E. Line breaking is never fixed in a manuscript. Break points live in th/assets/typeset/thai-breaks.txt; th/assets/scripts/build_breaks.py --book SJ writes th/SJ/04_assets/template/dictionary.typ from it, never edited by hand.
6.F. Never override an agent's model or effort.
6.G. Many readers of this book are not Christians. Where a passage teaches a principle, a wider word for the religious authority the reader knows may stand for the exact Christian term; where the passage tells history, the exact term stands.
6.H. Never apply a fix across chapters on your own initiative. Give the translator the sites and the change at each.
6.I. When the translator keeps a wording against a finding, get the translator's reason, asking if none was given, and in the same reply write one line, in anchor order, in th/SJ/04_assets/notes/SJ_notes.txt: {SJ ###.#} | English words | Thai span copied from the chapter | the translator's reason.
6.J. You stage and commit nothing; every commit is the translator's, from the numbered item of 5.D or 11.E.

## 7. Glossary building ("terms")

7.A. For every head raised, run python3 th/SC/04_assets/scripts/sc_term_data.py per head into ~/claude-sandbox/sj-audit/; it reads MB, PP and SC, and the SJ sites come from grep over th/SJ. Group related heads into a family and dispatch th-term-study per family with the data files and the question. A head whose Thai agrees everywhere takes its row from the data. th-glossary-miner runs only for register and proper nouns.
7.A.1. A head that already has a glossary row takes no study; a chapter site that conflicts with the row or reads badly under it is raised as a TERM marker or a DECIDE.
7.B. Relay the studied rows in one report per run: each ROW line, the ranked candidates, and a verdict per SJ site of the chapter; a conflict takes a TERM marker in the same reply, in the book's phrasing. Ruled rows go into the governing files in the same reply, with [CHECK] or [FLAG] where the translator wants them enforced; Notes at most 15 words.
7.C. Doctrinal heads, and heads MB and PP leave inconclusive, add the three GC texts: lo/GC/03_public and th/GC/04_assets/editions.

## 8. Google Docs

8.A. The editor and reviewers work in Google Docs; the repository stays authoritative. Nothing is built; the translator uploads by hand after check passes, using "editor" first if markers remain.

## 9. Reporting

9.A. The root CLAUDE.md report shape; TH: replaces LO:. A DECIDE opens with the decision and the recommendation.
9.B. Every agent writes its report to the file the dispatch names and returns the path; compose the translator's report from those files, copying every Thai form from them.

## 10. Read-through

10.A. The read-through follows assets/read-through.md, read in full before any part of it runs: the chapter is read at whatever stage it stands (2.A), the branch SJ-read in ~/claude-sandbox/wt-SJ-read, the notes file th/SJ/04_assets/notes/SJ_notes.txt, the drill agent sj-wording-drill. SJ has no reading page yet; the translator's notes come from the proofreader site's export.

## 11. Pre-processing ("pre")

11.A. Run python3 th/SJ/04_assets/scripts/sj_anchors.py --chapter NN, or --all, and read every DEFECT, FILLER and HOLD line; then run it again with --write. It writes the "// {SJ ###.#}" comment above each tagged paragraph and leaves a chapter with a DEFECT unchanged.
11.B. Each DEFECT is a DECIDE in the report: the English and Thai of the paragraphs at issue, and the corrected tag or split as FIX1. Apply the translator's ruling to the tags, then run 11.A on the chapter again.
11.C. A HOLD line is a paragraph under the placeholder tag {SJ 666.66}: SJ00 runs no round until the translator rules which of its paragraphs answer the English preface.
11.D. A FILLER line takes no marker; sj_punctcheck.py prints it as a NOTE.
11.E. The report ends with the commit as a numbered item: the chapters by full path and the message "SJ anchor comments" (18 characters), or "SJNN anchors" for one chapter.
