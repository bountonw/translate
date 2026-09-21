# SC rounds — conductor

This file governs the Thai translation of *Steps to Christ* in th/SC. An SC session reads this file, th/assets/translation_profile/thai-profile.txt and thai-glossary.txt before working. The root CLAUDE.md governs reports, register and git. Rulings enter this file as one line each. The queue is th/SC/04_assets/planning/SIDEQUESTS.md.

## 1. Triggers

1.A. "qa1 SC01 [SC02 ...]" — round one, accuracy (3.C), by section 4. Chapters named together run in parallel; batches inside a chapter run in sequence.
1.B. "qa2 SC01 [SC02 ...]" — round two, terms, clarity and reading (3.D), by section 4, only on a chapter whose QA1 markers are resolved and checked and whose terms have glossary rows.
1.C. "qa3 SC01" — not built; a final read is decided after qa2 has run on one chapter.
1.D. "check SC01" — the translator has resolved the markers; section 5.
1.E. "editor SC01" or "editor SC01 #12 #14" — flatten the remaining markers, or the named ones, into editor parentheses so the chapter can go to Google Docs: python3 th/SC/04_assets/scripts/sc_editor_markers.py --chapter 01 [--markers 12 14]. Each marker becomes ((old/new)) or ((old/new1/new2)), current wording first. A verify: marker is left standing and reported by number.
1.F. "terms SC01 [SC02 ...]" — glossary mining, section 7.
1.G. A term or corpus question — answer by grep over th/PP, th/MB, th/SJ and th/SC, copying every Thai form out of a file.
1.H. "7/3/1" and "model: X/Y/Z" — the drill of the root CLAUDE.md.
1.I. Anything else — ask.

## 2. Paths

2.A. Chapters: th/SC/01_raw, 02_edit or 03_public; confirm the stage with ls.
2.B. English source: th/SC/00_source/SCNN_en.md, anchored "## {SC ###.#}". SC04_en.md lacks most headings; anchor its paragraphs by the "{SC ###.#}" tag that closes each.
2.C. Governing files: th/assets/translation_profile/thai-profile.txt and thai-glossary.txt. A glossary row is silent until its Notes cell carries [CHECK] or [FLAG]. Where both are silent, grep the finished Thai books for evidence; evidence never rules.
2.D. Markers go into the chapter file. Everything else a run produces — the resolution sheet, term candidates, agent reports — goes to ~/claude-sandbox/sc-audit/.
2.E. Scripts in th/SC/04_assets/scripts/, invoked by that relative path from the repository root: sc_punctcheck.py, sc_refcheck.py, sc_resolution_sheet.py, sc_editor_markers.py, instruction_budget.py. Each says what it does in its first lines.
2.F. Compile check, from th/SC: ./typst-custom compile --root . <stage>/SCNN_th.typ $TMPDIR/SCNN.pdf. Never on a chapter holding markers.

## 3. The rounds

3.A. Three light rounds. Each round marks one kind of thing; a finding outside the round's classes is neither marked nor reported.
3.B. Every batch runs sc_punctcheck.py and sc_refcheck.py on its range. Each finding line takes a marker, SPELL or REF; a NOTE line takes none. SC's default Bible version is THSV, so the batch auditor deletes every THSV label in its range silently and reports the count; the report carries it as one NOTE.
3.C. QA1, accuracy: SPELL, GRAM, REF and NOTE, which carry no severity; FACT, OMISSION, ADDITION and ALIGN, which carry HIGH or MED and never LOW. No TERM, CLARITY or wording marker. The table in sc-batch-auditor defines each class.
3.D. QA2, terms, clarity and reading: TERM and CLARITY, HIGH, MED or LOW; READ, a reading improvement whose gain is named in the note, and CHOICE, two candidates the translator picks between, both without severity. The translator's own ((A/B)) or ((word)) gets a CHOICE marker with the agent's proposal and "keep the parenthesis" as the other option. READ and CHOICE together are capped at one per 300 English words of the batch; a READ marker changes at most one sentence and a paragraph carries at most two. An accuracy finding QA1 missed is marked in its QA1 class. The glossary guides; variation within a term family stands unless there is a reason to narrow it.
3.E. QA3 is decided after QA2 has run on one chapter: either no third round, or one short read of the whole chapter by Fable flagging the few stumbles left; entry 5 of the queue.

## 4. Chapter procedure, every round

4.A. Preflight: the chapter holds no [[ marker, else name the numbers and stop; git status --short -- th/SC shows the chapter unmodified. Another chapter's modified file is another session's. Grep the chapter; never read it whole.
4.B. Split: wc -w on the English source; batches = words / 2200 rounded up; under 2700 words is one batch; cut at anchors with no remainder on the last batch. State the split and proceed.
4.C. Dispatch sc-batch-auditor (qa1) or sc-batch-auditor-qa2 (qa2) per batch, in sequence, with chapter, stage directory, ref range, starting marker number, round name and first-batch flag. Markers restart at #1 each round; the next start is the last reported number plus one.
4.D. After the last batch, run python3 th/SC/04_assets/scripts/sc_resolution_sheet.py --chapter NN --round qa1 (or qa2) and read its VERDICT line. Delete a marker whose old side is not in the committed chapter and establish the finding again.
4.E. Report: the counts table, the THSV-label count, every DECIDE, and any item whose effect reaches past its own site. A decision confined to one marker stays at the cursor. Give the sheet's path.

## 5. Post-resolution check ("check SC01")

5.A. Grep the chapter for [[. Standing markers end the check: name the numbers and stop.
5.B. Run sc_punctcheck.py, sc_refcheck.py, instruction_budget.py and the compile check. Each chapter finding becomes a [[FIX #N|old -> new|note]] marker numbered on from the round's last number; a file over budget is a FIX in the report.
5.C. Dispatch sc-resolve-check with chapter, stage directory, last marker number, and every resolved marker's class, anchor, old span and note. Relay its report verbatim. PASS means clean to commit and to upload.

## 6. Rules

6.A. You orchestrate; agents work. A run's only repository edit is markers in the chapter.
6.B. Chapters are Typst: a "// {SC ###.#}" comment above each paragraph, an "#EGW[\{SC ###.#\}]" tag at its end, footnotes inline as "#footnote[...]". Reference prose by anchor, never by line. A chapter holding markers is never compiled or added to book.typ.
6.C. Thai text and citations follow thai-profile.txt.
6.D. An editor's choice is a double parenthesis, ((A/B)) or ((word)), the current wording first: in qa2 it gets a CHOICE marker; in qa1 it stands; sc_punctcheck.py lists every one standing, so none reaches print unseen.
6.I. Many readers of this book are not Christians. Where a passage teaches a principle, a wider word for the religious authority the reader knows may stand for the exact Christian term; where the passage tells history, the exact term stands.
6.E. Line breaking is never fixed in a manuscript; break points live in th/SC/04_assets/template/dictionary.typ.
6.F. Agents carry their own model and effort; do not override.
6.G. Grep rather than read.
6.H. Never apply a fix across chapters on your own initiative. Give the translator the sites and the change at each.

## 7. Glossary building ("terms")

7.A. For every head raised, run python3 th/SC/04_assets/scripts/sc_term_data.py per head into ~/claude-sandbox/sc-audit/. Group interrelated heads into a family and dispatch th-term-study per family with the data files and the translator's question; it weighs the versions, MB and PP 1–20 and the lexicon in each sentence and proposes the rows; no agent counts. A head whose Thai agrees everywhere takes its row from the data file. th-glossary-miner runs only for register and proper nouns, queue entry 7.
7.B. Relay the studied rows in one report per run: each ROW line, the ranked candidates with one sentence each, and a verdict per SC site of the chapter in hand; a conflict with the chapter takes a TERM marker in the same reply, in the book's own phrasing. Ruled rows go into the governing files in the same reply, with [CHECK] or [FLAG] where the translator wants them enforced; Notes at most 15 words.

## 8. Google Docs

8.A. The editor and reviewers work in Google Docs; the repository stays authoritative. The design is th/SC/04_assets/planning/gdocs-workflow.md, not built; the translator uploads by hand after check passes, using "editor" first if markers remain.

## 9. Reporting

9.A. The root CLAUDE.md report shape; TH: replaces LO:. A DECIDE opens with the decision and the recommendation.
9.B. sc-resolve-check writes for the translator and is relayed verbatim. sc-batch-auditor and th-glossary-miner write for you; compose the report from their items, copying every Thai form from their files.
