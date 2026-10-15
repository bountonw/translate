# DA Thai — conductor

This file governs the new Thai translation of *The Desire of Ages* in th/DA. A DA session reads this file, th/assets/translation_profile/thai-profile.txt and thai-glossary.txt before working. The queue is th/DA/04_assets/planning/SIDEQUESTS.md. The commands are listed for the translator in th/DA/04_assets/README.md.

## 1. Triggers

1.A. "names" — the name table, 5.A.
1.B. "register" — the register mining, 5.B.
1.C. "terms DA01 [DA02 ...]" or "terms DA00-DA87" — pass 1, terms and scripture, section 6.
1.D. "draft DA01 [DA02 ...]" — pass 2, the draft, section 7; only on chapters whose pass 1 is ruled.
1.E. "check DA01" — pass 3, section 8.
1.F. "editor DA01" — the file for the editor, 9.A.
1.G. "flags DA01" — the editor's flags into markers, 9.B.
1.H. "7/3/1" and "model: X/Y/Z" — the drill of the root CLAUDE.md, through da-wording-drill.
1.H.1. A page's markers go out in one dispatch, with the model and X/Y/Z the translator writes once for the page or at an item; a bare model name takes 10/10/1; a second model goes out only on request, report only, in one dispatch; a span in ((A/B)) or ((A/??)) with no model word is weighed by the conductor in the chat, who dispatches only where the field is open.
1.I. "status" — each chapter's stage and standing markers, by ls and grep.
1.J. A term or corpus question — grep th/PP, th/MB, th/SJ, th/SC, th/DA and the Thai Bibles.
1.K. "tools" — build or repair the DA agents and scripts, each proposed before it is written.
1.L. Anything else — ask.
1.M. "review DANN page NN" — the translator's round of 4.C on one page: read the page beside the English and any marker standing from an earlier page; every change, editor's choice and comment is an item; a marker is written where a drill is asked and dispatched as 1.H.1; each marker's note and each option list in the report carries the print's reading of the span as a labelled option (3.J).
1.M.1. A marker the review writes for a drill takes the class FLAG.
1.M.2. An editor's choice written in the review is weighed between the translator and the conductor; one standing when the page's review ends is the editor's.

## 2. Paths

2.A. DA root: the repository the session starts in; every path in this file is under it.
2.B. English: th/DA/00_source/DANN_en.md, anchored "## {DA ###.#}"; DA00_preface_en.md is the preface.
2.C. Thai chapters: th/DA/01_raw, 02_edit or 03_public, DANN_th.typ; a "// {DA ###.#}" comment above each paragraph and "#EGW[\{DA ###.#\}]" at its end. Confirm the stage with ls.
2.E. Names: th/assets/translation_profile/thai-names.tsv, shared by every Thai book, built by th/assets/scripts/th_names.py.
2.F. Bibles: the ten Thai versions under ~/programming/bible/th, with the KJV; TFB covers Matthew to 2 Peter only.
2.G. Scripts: th/DA/04_assets/scripts/ for DA, th/assets/scripts/ for every Thai book; each says what it does in its first lines.
2.H. Session outputs: ~/claude-sandbox/da-audit/.
2.I. Compile check, from th/DA: ./typst-custom compile --root . <stage>/DANN_th.typ $TMPDIR/DANN.pdf; never on a chapter holding markers.
2.J. Humble Hero, the simplified DA, outside the repository: ~/programming/bible/egw-download/modern/HH/HH.md and HH-toc.tsv, read by da-subtitles only.

## 3. Book rules

3.A. Title: ผู้พึงปรารถนาแห่งปวงชน ฉบับแปลใหม่.
3.B. The default Bible version is THSV; it carries no version label.
3.C. A quotation the English leaves uncited takes a printed citation in parentheses, as in PP and SC; a (ดู …) reference may point the reader to a passage where it helps. A phrase the author repeats as a refrain prints its citation at its first full quotation and carries a hidden comment, as /*มัทธิว 1:23*/, at each repeat.
3.C.1. A quotation repeated in a paragraph from one it cites in print takes a hidden comment carrying that citation's label, as /*ฮีบรู 10:5 TKJV*/, and no printed citation.
3.D. A quotation in THSV from a verse inside the chapter's based-on reference carries no printed citation, only a hidden comment such as /*ยอห์น 3:16*/; a quotation in any other version is cited and labelled.
3.D.1. A hidden comment takes no space before it and a space after it only at a phrase boundary.
3.E. Each quotation takes the version that best carries the meaning of the English and reads best in its passage, THSV where the versions serve equally; a close call, or a point no version carries, takes a marker with the two best choices.
3.F. A based-on line writes บทที่ only when every part is a whole chapter, with a space after the book name; ranges take an unspaced en dash; two chapters take และ; other lists take "; ".
3.G. Question and exclamation marks stand in direct speech and quoted questions. In narration the drafter keeps a mark where the English has one; da_punctcheck.py lists each as a NOTE; the editor decides, and his ruling enters this line.
3.H. Names follow profile 5.A. Ruled names and new term rows enter the shared thai-glossary.txt; the names the series or THSV settles stay in thai-names.tsv, whose form column the drafter follows.
3.I. The voice is the translator's own in PP; style samples come from th/PP/03_public.
3.J. The 2023 print in th/DA/04_assets/editions/print is closed to da-drafter, whose every grep over th/ passes --exclude-dir=editions; the review reports the print's reading of each span to the translator as a labelled option; the check and the rounds after it read it as a labelled column of term data and as a second reading of the English.
3.K. A people as a body takes ชาว before its place or father's name, as PP writes ชาวอียิปต์ and ชาวฟีลิสเตีย; one person named by his people may take คน, as PP 628.2 writes โฮบับ…เป็นคนเคไนต์; a quotation keeps its version's word; Israel and its tribes are คน, as THSV and PP write คนอิสราเอล and คนเลวี.
3.L. A name the author spells against THSV is raised with the King James, TKJV and Byzantine readings beside THSV's; the ruling names the spelling the text keeps and the footnote at its first site, worded by an 8/5/1 drill at drafting.
3.M. Subtitles: two to four in a chapter of about seven pages, as a guideline; the content decides: up to five pages may run without one, and two may stand on consecutive paragraphs where the matter turns twice.

## 4. Order of work

4.A. Chapters go in book order from DA01; the preface, DA00, waits until the chapters have passed their final check.
4.B. The agent draft of a chapter is committed before the translator's round.
4.C. The translator reads every chapter whole and settles every marker in his round.
4.D. The editor then reads the chapter in Google Docs, uploaded by hand, and flags what needs another round here.
4.E. Five chapters a week.

## 5. Book preparation

5.A. Names: th_names.py gives each biblical name its form by profile 5.A, a glossary row first, with TH1971 and TNCV beside it; a people takes ชาว by 3.K. The report lists only the exceptions: a name no book printed that THSV spells two ways, a name the KJV lacks, two printed forms, a weak match. A ruled exception becomes a glossary row; a name outside the Bible takes the study of profile 5.A.1, and every ruled name gets its break split in th/assets/typeset/thai-breaks.txt.
5.B. Profile refresh, queue entry 1: th-glossary-miner (Sonnet) runs over PP in runs of about eight chapters and over MB, each run writing its observations on pronouns, honorifics, royal vocabulary, dialogue, description and poetry, sentence shape, subtitle placement and wording, and DA's questions: the narrator's pronouns for Jesus, the disciples and the leaders, how people address Jesus, and royal vocabulary for Christ's acts. One Fable agent reads the observation files, never the chapters, and proposes profile lines with counts; a ruling enters the profile or section 3.

## 6. Pass 1: terms and scripture

6.A. da-finder (Opus), the whole chapter: lists every head that needs a Thai decision (no row, a row tagged [CHECK] or [FLAG], a name not in names.tsv), every quotation, and every allusion, where the English uses scripture's wording without quoting it; da_quotes.py proposes them by runs of KJV words and the finder confirms each.
6.B. da-miner (Sonnet): per term family, a data file of the eight Thai Bibles at the KJV verses using the word, PP, MB, SJ, SC, the GC editions and the SC print as light reference, the print as a labelled column, and Thai sources online where the network allows; per chapter, all eight versions of every quotation and allusion.
6.C. th-term-study (Opus; Fable where the translator names it), three or four related families a dispatch, proposes each row with ranked candidates; a head whose Thai agrees everywhere takes its row from the data.
6.D. da-verse-study (Opus), per chapter, split at about 25 passages: the top three versions of each quotation and allusion, ranked for meaning and readability in the passage, and its pick; a close call is marked as 3.E says.
6.E. The report gives each ROW line for ruling and the verse picks, close calls first. Ruled rows enter the glossary in the same reply; the picks go to ~/claude-sandbox/da-audit/DANN-verses.tsv for pass 2.

## 7. Pass 2: the draft

7.A. Preflight: the chapter's pass 1 is ruled and its verses file exists; the chapter in 01_raw holds no text yet.
7.B. Split at anchors into equal parts: about 1,500 English words a drafter batch, about 3,000 a check batch.
7.C. da-drafter (Fable) per batch: the English range, the rows present, the names, the verse picks, the kept wordings of DA_notes.txt for the range, the register rules and the PP samples. It writes the Thai under the anchors.
7.D. da-check (Opus) per check batch, with da_punctcheck.py, da_refcheck.py and th_charcheck.py, the print read as 3.J allows.
7.E. da-fixer (Fable), one dispatch with every findings file: a fix, a marker with both readings, or an editor's choice ((A/B)).
7.E.1. da-print-compare (Opus), after da-fixer, the whole chapter: a PRINT marker where the print carries a point the draft lacks; nothing for style.
7.E.2. da-subtitles (Fable), after da-print-compare, the whole chapter: subtitles are crafted, never translated, at the density of 3.M; the agent writes no marker and returns a table of content notes and candidates with Humble Hero's heading; the translator picks in the chat and the conductor writes the "=== " lines.
7.F. The report: counts, the markers that reach past one site, the heads the drafter raised.

## 8. Pass 3: the check

8.A. Grep the chapter for [[; a standing marker ends the check. An editor's choice may stand for the editor.
8.B. Run the scripts, da_notescheck.py and build_breaks.py --book DA among them, and dispatch da-resolve-check (Opus); each defect becomes a FIX marker. PASS means clean to commit; the chapter moves to 02_edit.

## 9. The editor

9.A. "editor DA01" turns anything left into editor parentheses, the current wording labelled original:, as in SC.
9.B. "flags DA01": each flag the translator brings back, pasted or saved in ~/claude-sandbox/da-audit/DANN-flags.md, becomes a marker whose options da-fixer writes; after check the chapter moves to 03_public and into book.typ.

## 10. Rules

10.A. You orchestrate; agents work. A run edits only the chapter and the glossary rows the translator rules.
10.B. Never override an agent's model or effort; a named model that is unavailable is retried, never replaced.
10.C. Grep rather than read; never apply a fix across chapters on your own initiative.
10.D. Agents receive no instruction files; each brief carries what its definition lacks.
10.E. When the translator keeps a wording against a finding, get his reason, asking if he gave none, and in the same reply write one line, in anchor order, in th/DA/04_assets/notes/DA_notes.txt: {DA ###.#} | English words | Thai span copied from the chapter | his reason.
10.F. Agents go out in waves of four, never more than the remaining allowance can finish.

## 11. Reporting

11.A. The root CLAUDE.md report shape; one report after the last agent.
11.B. A Bible verse quoted as evidence carries its KJV wording beside the Thai, from ~/programming/bible/en/KJVS with the Strong's tags stripped; the KJV directory covers Genesis to 2 Kings only.
