# SC side quests — the queue

Work that is agreed but not scheduled, in the order it will be done. When the translator asks how many SC side quests are open and in what order, this file is the answer and no agent answers from memory. An issue he defers rather than decides is added here in the same reply that defers it, and an entry is deleted when its work is finished, not marked done, because a finished quest is in the commit history. Each entry says what the job is, where its detail lives, and roughly how big it is. It sits under a numbered-stage assets directory because the linter excludes those from every check.

## 4. Google Docs round trip

The translator's editor and reviewers work in Google Docs while the repository stays authoritative. The agreed design is th/SC/04_assets/planning/gdocs-workflow.md, distilled on 16 August; its minimal alternative, uploading the marker-laden file and letting the Doc's own comparison show the differences, is to be tested before anything larger is built. Until something is built, a chapter that passes check SCNN is uploaded by hand.

Detail: th/SC/04_assets/planning/gdocs-workflow.md. Medium.

## 5. First live run of the reader's round

sc-reader-qa3, sc_termcheck.py and sc_changes.py were written on 6 October 2026 and have not run on a live round. The first "qa3" on a chapter that has finished QA2 is read against th/SC/CLAUDE.md 3.E, and the agent definition and the scripts are adjusted from what that run shows.

Detail: th/SC/CLAUDE.md 3.E and 4.B.2. Small.

## 8. Two sites from the SC01 studies for other chapters

{SC 30.1} renders "the unfallen universe" as สวรรค์, narrowing every unfallen world to heaven, for SC03's qa2; {SC 94.2} "the way to the mercy seat" stands without พระที่นั่งกรุณา, for SC11's qa2.

Detail: this entry. Small.

## 13. Standardize sons of God in SJ

SJ is unedited and its sons of God sites take one form under the row when SJ is edited.

Detail: this entry. Small.

## 14. SC05 and SC08 notes for qa2, from the SC08 and SC09 term close-out

Sites to weigh in qa2, each in its own sentence. {SC 48.1} (SC05) "through constant surrender to God" reads การมอบให้พระเจ้าอย่างต่อเนื่อง, where มอบ has no object; the candidates are การมอบเจตจำนงให้พระเจ้าอย่างต่อเนื่อง, naming the will as {SC 62.3} does, and การมอบชีวิตให้พระเจ้าอย่างต่อเนื่อง, as {SC 47.1} does. {SC 73.1} (SC08) "as the character of the Divine One was manifested to him" reads พระลักษณะของพระผู้ช่วยให้รอด, which names Christ's work rather than His deity; the candidate is พระลักษณะของพระองค์ผู้ทรงเป็นพระเจ้า, on TNCV's ผู้ทรงเป็นพระเจ้า at โรม 9:5; the translator expects to keep the present wording after review, and the glossary row for "the Divine One" waits on that review.

Detail: ~/claude-sandbox/sc-audit/term-close-S5-study.md and term-close-S6-study.md. Small.

## 15. SC12 note for qa2: the authority sentence at {SC 109.3}

{SC 109.3} "reason must acknowledge an authority superior to itself" reads พระคัมภีร์มีอำนาจเหนือความคิดของเรา, the editor's wording, which stands until qa2 weighs the sentence. The editor rejected สิทธิอำนาจ here as personifying the Bible too much and sounding political; the editor check found that อำนาจเหนือความคิดของเรา can read as control over our thoughts. The drill's two candidates, which the editor has not seen: ยังมีอำนาจที่สูงกว่าความคิดของเราเอง, which leaves the authority unnamed as the English does, and พระคัมภีร์อยู่เหนือความคิดของเราเอง, which can also be heard as "beyond our thinking".

Detail: ~/claude-sandbox/sc-audit/sc12-drill-2-editor.md. Small.

## 16. Feed the Thai GC hyphenation candidates into the Thai typesetting break list

Moved from the GC queue on 9 October. SC no longer keeps its own dictionary.typ list: break points now live in th/assets/typeset/thai-breaks.txt, which build_breaks.py turns into each book's dictionary.typ. The joined form of 77 of the 133 candidates already occurs in thai-breaks.txt, so about 56 remain to review, and the figures below for SJ and SC predate that change.

Thai running text has no word spaces, so the Typst pipeline has to be told where a long word may break. Both Thai projects do this with `04_assets/template/dictionary.typ`, and the two files are separate copies of the same mechanism at very different stages: SJ carries 457 entries and SC carries 92.

The Thai printed edition of GC supplies 133 more, taken from the places its own typesetter chose to break a word. They are in `th/GC/04_assets/editions/print/HYPHEN-CANDIDATES.tsv`, one per line, giving the break as `คริสต-จักร`, the joined word, how often the print breaks it, how often the word occurs unbroken elsewhere in the book, the first page it appears on, and a confidence note. Converting a row to an entry is mechanical: `คริสต-จักร` becomes `(word: "คริสตจักร", parts: ("คริสต", "จักร"))`.

Only 17 of the 133 are already in SJ and 5 in SC, so this roughly doubles SC's dictionary.

Two things need judgment. 125 rows are confirmed by the word appearing unbroken elsewhere in the book, but eight occur once only and their boundary was supplied by a reader rather than by evidence: อาชญา-กรรม, นักขัต-ฤกษ์, คริสตธรรม-กิตติคุณ, อสังหา-ริมทรัพย์, วิทเทม-บาก, พระราช-ชนนี, กรีน-แลนด์ and คอนเนต-ทิกัต. Those eight want a Thai reader before they go in. And the existing entries often break a word into every syllable, as `("พระ", "วิญ", "ญาณ", "บริ", "สุทธิ์")`, where these rows give a single morpheme boundary; settle whether the two styles coexist or whether the new rows should be broken further.

The larger question the quest should answer is whether the two projects keep separate dictionaries at all. Hyphenation is a fact about Thai words rather than about a book, so a shared file with each project importing it would stop SC and SJ diverging, and would give SC the benefit of SJ's 457 entries at once.

Order matters here. SC goes to print first and has a worktree already started, so SC is where the work lands and is proved. SJ has the larger dictionary and is the better source to merge from.

Detail: none written; this entry is the whole brief. `gc_th_hyphens.py` in `th/GC/04_assets/scripts/` is what produced the file and shows how each boundary was decided. Small if the two dictionaries stay separate, medium if they are merged.
