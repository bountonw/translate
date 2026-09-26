# FB — conductor

This file governs the Lao translation of the 28 Fundamental Beliefs, and later of the book Seventh-day Adventists Believe, in lo/FB. An FB session reads this file, the governing files of 2.D and the queue lo/FB/04_assets/planning/SIDEQUESTS.md before working. The root CLAUDE.md governs reports, register and git. Rulings enter this file as one line each.

## 1. Triggers

1.A. "FB07", "#7", "belief 7" — the phrase round on belief 7, section 3. The number alone starts it; ask nothing first.
1.B. "sentences FB07" — the sentence round, section 4, on a belief whose phrase choices are all applied.
1.C. "final FB07" — the final read, section 5.
1.D. "check FB07" — the translator has resolved the final markers; section 6.
1.E. "SB07" — a chapter of the book; not built, section 8.
1.F. A term or corpus question — answer by grep over lo/GC/03_public, lo/AA, lo/FB and the Lao Bibles of 2.E, copying every Lao form out of a file.
1.G. "model: X/Y/Z" — overrides the round's drill numbers for the phrases or sentences it names.
1.H. Anything else — ask.

## 2. Paths

2.A. English source: lo/FB/00_source/FBNN_en.md, one belief per file, anchored "## {FB N.1}" with the tag "{FB N.1}" at the paragraph end; FB00_preamble_en.md is the preamble. The official booklet is source/FB/ADV-28Beliefs2020.pdf; lo/FB/04_assets/scripts/fb_source_split.py made the anchored files from its text.
2.B. Lao statements: lo/FB/01_raw, 02_edit or 03_public, FBNN_lo.typ, one belief per file; confirm the stage with ls. A file moves to the next stage when its round is resolved; the translator moves it.
2.C. Lao book chapters: SBNN_lo.typ in the same stage directories, anchored {SB N.P} by chapter and paragraph; a chapter includes its statement file rather than repeating the text. The English source will be lo/FB/00_source/SBNN_en.md.
2.D. Governing files: lo/assets/translation_profile/lao-profile.txt and lao-glossary.txt, shared by every Lao book, a line or row tagged FB binding this project. The GC glossary lo/GC/04_assets/translation_profile/GC-glossary.txt, copied from the GC-instructions branch, is read and never edited. th/assets/translation_profile/thai-glossary.txt and the formal Thai Bible versions are read for wording comparison, because the Lao Bibles are dynamic; the Lao is never translated from the Thai. A row guides and never rules.
2.E. Bibles: LCV and LO2012 under ~/programming/bible, the Thai versions beside them; python3 ~/programming/LMV/scripts/brief.py JHN 3:16 prints every version of a verse; the packet quotes KJV, LCV, LO2012, TH1971, THSV and TKJV. A verse is quoted from its file with its zero-width spaces stripped; a verse not on disk is flagged.
2.F. Session outputs: ~/claude-sandbox/fb-audit/.
2.G. Scripts: lo/FB/04_assets/scripts/, invoked by that relative path from the repository root.

## 3. Phrase round ("FB07")

3.A. Preflight: FB07_en.md exists; no FB07_lo.typ exists in any stage, else name the stage and stop.
3.B. Packet: python3 lo/FB/04_assets/scripts/fb_packet.py --belief 07 writes ~/claude-sandbox/fb-audit/fb07-packet.md: the English; every verse of the reference list and every embedded quotation in the six versions of 2.E; the Lao, GC and Thai glossary rows for the belief's key terms with their counts in lo/GC/03_public and lo/AA; the Lao profile. Data only; no judgment.
3.C. Dispatch fb-phrase-drill (Fable, xhigh) with the belief number and the packet path. It segments the English into phrases smaller than sentences; for each phrase it weighs up to 9 renderings in the whole statement and writes the top 5 to ~/claude-sandbox/fb-audit/fb07-phrases.md, fix1 first with one sentence of reason each, naming any doctrinal weight, loophole or shift of precision the phrase carries. It writes fix1 of every phrase, in order, into lo/FB/01_raw/FB07_lo.typ.
3.D. Report: every phrase as a numbered item, the English in bold, the five fixes, then the summary list. The translator replies "N. fixK" or "N. applied: <wording>" per phrase; the session writes each choice into the draft.

## 4. Sentence round ("sentences FB07")

4.A. Preflight: the draft holds every phrase choice and no [[ marker.
4.B. Dispatch fb-sentence-drill (Fable, xhigh; not built) with the belief number, the packet and the draft. For each sentence it weighs up to 8 renderings that make the chosen phrases work together, reordering or rewording where the fit asks it, and writes a [[SENT #N|old -> new|fix2: ...; fix3: ...; fix4: ...]] marker in the draft with fix1 as new.
4.C. Report: one item per sentence with its four options. The translator resolves in the file or by "N. fixK". Resolved, the file moves to 02_edit.

## 5. Final read ("final FB07")

5.A. Run python3 lo/FB/04_assets/scripts/fb_check.py --belief 07 (not built): the orthography and punctuation of 2.D, digits, invisible characters, quotation marks, the reference line. Each finding takes a [[FIX #N|old -> new|note]] marker.
5.B. Dispatch fb-final-read (Fable, xhigh; not built) with the belief number, the packet and the file. It reads the whole statement against the English from the top: the flow, every theological nuance pointing where the English points, every loophole the Lao leaves that the English closes, no wording more specific or looser than the English. It writes FIX markers only where the statement should not stand, each note quoting the English.
5.C. Report: the markers as items. Resolved, the file moves to 03_public.

## 6. Check ("check FB07")

6.A. Grep the file for [[; a standing marker ends the check. Run fb_check.py again, read the diff of the resolution, and run instruction_budget.py. PASS means clean to commit.

## 7. Rules

7.A. Drill numbers: phrases 9/5/1, sentences 8/4/1. fix1 is the recommendation and the numbers fall from there.
7.B. Bibles, GC, AA and the glossary inform spelling and word choice; each statement stands on its own merits, judged in its whole passage.
7.C. Never more specific or looser than the English. A Lao reading the English excludes is a defect.
7.D. Never transliterate Lao or Thai. Copy every Lao form out of a file; grep any form you did not copy. Never write a zero-width space into a manuscript.
7.E. Western numerals. Literal item numbers, never an auto-numbered list. Text meant to be copied goes in a code box holding only that text.
7.F. Never override an agent's model or effort. Never apply a change across beliefs on your own initiative; give the translator the sites and the change at each.
7.H. Governing files are edited only on the translator's ruling, in the same reply.

## 8. The book

8.A. Seventh-day Adventists Believe has been translated into Lao; the translator adds it later as a resource, queue entry 2. The statements come first.

## 9. Reporting

9.A. The root CLAUDE.md report shape; LO: replaces TH:. A DECIDE opens with the decision and the recommendation.
