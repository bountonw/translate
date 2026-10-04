# DA Thai — conductor

This file governs the new Thai translation of *The Desire of Ages* in th/DA. A DA session reads this file, th/assets/translation_profile/thai-profile.txt and thai-glossary.txt before working. The root CLAUDE.md governs reports, register and git. Rulings enter this file as one line each. The queue is th/DA/04_assets/planning/SIDEQUESTS.md. The commands are listed for the translator in th/DA/04_assets/README.md.

## 1. Triggers

1.A. "names" — the name table, 5.A.
1.B. "register" — the register mining, 5.B.
1.C. "terms DA01 [DA02 ...]" or "terms DA00-DA87" — pass 1, terms and scripture, section 6.
1.D. "draft DA01 [DA02 ...]" — pass 2, the draft, section 7; only on chapters whose pass 1 is ruled.
1.E. "check DA01" — pass 3, section 8.
1.F. "editor DA01" — the file for the editor, 9.A.
1.G. "flags DA01" — the editor's flags into markers, 9.B.
1.H. "7/3/1" and "model: X/Y/Z" — the drill of the root CLAUDE.md, through da-wording-drill.
1.I. "status" — each chapter's stage and standing markers, by ls and grep.
1.J. A term or corpus question — grep th/PP, th/MB, th/SJ, th/SC, th/DA and the Thai Bibles, copying every Thai form out of a file.
1.K. "tools" — build or repair the DA agents and scripts, queue entry 1, each proposed before it is written.
1.L. Anything else — ask.

## 2. Paths

2.A. DA root: the repository the session starts in; every path in this file is under it.
2.B. English: th/DA/00_source/DANN_en.md, anchored "## {DA ###.#}"; DA00_preface_en.md is the preface.
2.C. Thai chapters: th/DA/01_raw, 02_edit or 03_public, DANN_th.typ; a "// {DA ###.#}" comment above each paragraph and "#EGW[\{DA ###.#\}]" at its end. Confirm the stage with ls.
2.D. The print: th/DA/04_assets/editions/print, used only as 3.J allows.
2.E. Names: th/DA/04_assets/names.tsv.
2.F. Bibles: the eight Thai versions under ~/programming/bible/th, with the KJV.
2.G. Scripts: th/DA/04_assets/scripts/ for DA, th/assets/scripts/ for every Thai book; each says what it does in its first lines.
2.H. Session outputs: ~/claude-sandbox/da-audit/.
2.I. Compile check, from th/DA: ./typst-custom compile --root . <stage>/DANN_th.typ $TMPDIR/DANN.pdf; never on a chapter holding markers.

## 3. Book rules

3.A. Title: ผู้พึงปรารถนาแห่งปวงชน ฉบับแปลใหม่.
3.B. The default Bible version is THSV; it carries no version label.
3.C. A quotation the English leaves uncited takes a printed citation in parentheses, as in PP and SC; a (ดู …) reference may point the reader to a passage where it helps.
3.D. A quotation in THSV from a verse inside the chapter's based-on reference carries no printed citation, only a hidden comment such as /*ยอห์น 3:16*/; a quotation in any other version is cited and labelled.
3.E. Each quotation takes the version that best carries the meaning of the English and reads best in its passage, THSV where the versions serve equally; a close call, or a point no version carries, takes a marker with the two best choices.
3.F. A based-on line writes บทที่ only when every part is a whole chapter, with a space after the book name; ranges take an unspaced en dash; two chapters take และ; other lists take "; ".
3.G. Question and exclamation marks stand in direct speech and quoted questions only, never in narration.
3.H. New term rows and names that need a ruling enter the shared thai-glossary.txt; names THSV settles stay in th/DA/04_assets/names.tsv.
3.I. The voice is the translator's own in PP; style samples come from th/PP/03_public.
3.J. The 2023 print in th/DA/04_assets/editions/print serves only as a labelled column of term data, as a second reading of the English in the accuracy check, and as a labelled option in a marker; no agent that writes the Thai sees it.

## 4. Order of work

4.A. Chapters go in book order from DA00.
4.B. The register mining of SC queue entry 7 runs from a DA session, with DA's questions added, before DA01 is drafted.
4.C. The agent draft of a chapter is committed before the translator's round.
4.D. The translator reads every chapter whole and settles every marker in his round.
4.E. The editor then reads the chapter in Google Docs, uploaded by hand, and flags what needs another round here.
4.F. Five chapters a week.

## 5. Book preparation

5.A. Names: da_names.py takes each biblical name's THSV form from the verses that carry it (profile 5.A). The report lists only the exceptions: two THSV spellings, a name the KJV lacks, a form that differs from the finished books, a weak match. A ruled exception becomes a glossary row.
5.B. Register: th-glossary-miner (Sonnet) runs SC queue entry 7 with DA's questions: the narrator's pronouns for Jesus, the disciples and the leaders, how people address Jesus, and royal vocabulary for Christ's acts. The report gives the observations; a ruling enters profile 4.C or section 3.

## 6. Pass 1: terms and scripture

6.A. da-finder (Opus), the whole chapter: lists every head that needs a Thai decision (no row, a row tagged [CHECK] or [FLAG], a name not in names.tsv), every quotation, and every allusion, where the English uses scripture's wording without quoting it; da_quotes.py proposes them by runs of KJV words and the finder confirms each.
6.B. da-miner (Sonnet): per term family, a data file of the eight Thai Bibles at the KJV verses using the word, PP, MB, SJ, SC, the GC editions, the print as a labelled column, and Thai sources online where the network allows; per chapter, all eight versions of every quotation and allusion.
6.C. th-term-study (Fable) per family proposes each row with ranked candidates; a head whose Thai agrees everywhere takes its row from the data.
6.D. da-verse-study (Fable), per chapter, split at about 25 passages: the top three versions of each quotation and allusion, ranked for meaning and readability in the passage, and its pick; a close call is marked as 3.E says.
6.E. The report gives each ROW line for ruling and the verse picks, close calls first. Ruled rows enter the glossary in the same reply; the picks go to ~/claude-sandbox/da-audit/DANN-verses.tsv for pass 2.

## 7. Pass 2: the draft

7.A. Preflight: the chapter's pass 1 is ruled and its verses file exists; the chapter in 01_raw holds no text yet.
7.B. Split at anchors into equal parts: about 1,500 English words a drafter batch, about 3,000 a check batch.
7.C. da-drafter (Fable) per batch: the English range, the rows present, the names, the verse picks, the register rules and the PP samples. It writes the Thai under the anchors, rereads each paragraph against the English for omissions, additions, numbers, names, negations and who did what, and fixes before returning. A close-call verse takes a marker with the two best choices.
7.D. da-check (Opus) per check batch, with da_punctcheck.py, da_refcheck.py and th_charcheck.py: sentence by sentence against the English, the print read as 3.J allows; findings quote the English and give no wording.
7.E. da-fixer (Fable), one dispatch with the flagged paragraphs: where it agrees, it fixes the whole sentence and logs it; where it disagrees, a marker gives both readings; where two wordings serve equally, an editor's choice ((A/B)).
7.F. The report: counts, the markers that reach past one site, the heads the drafter raised. The translator commits the draft (4.C), then reads and settles (4.D).

## 8. Pass 3: the check

8.A. Grep the chapter for [[; a standing marker ends the check. An editor's choice may stand for the editor.
8.B. Run the scripts and dispatch da-resolve-check (Opus); each defect becomes a FIX marker. PASS means clean to commit; the chapter moves to 02_edit.

## 9. The editor

9.A. "editor DA01" turns anything left into editor parentheses, the current wording labelled original:, as in SC.
9.B. "flags DA01": each flag the translator brings back, pasted or saved in ~/claude-sandbox/da-audit/DANN-flags.md, becomes a marker whose options da-fixer writes; after check the chapter moves to 03_public and into book.typ.

## 10. Rules

10.A. You orchestrate; agents work. A run edits only the chapter and the glossary rows the translator rules.
10.B. Never override an agent's model or effort; a named model that is unavailable is retried, never replaced.
10.C. Grep rather than read; never apply a fix across chapters on your own initiative.
10.D. Agents receive no instruction files; each brief carries what its definition lacks.

## 11. Reporting

11.A. The root CLAUDE.md report shape, TH: for LO:. A DECIDE opens with the decision and the recommendation. One report after the last agent, composed from the agents' files.
