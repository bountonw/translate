# SC side quests — the queue

Work that is agreed but not scheduled, in the order it will be done. When the translator asks how many SC side quests are open and in what order, this file is the answer and no agent answers from memory. An issue he defers rather than decides is added here in the same reply that defers it, and an entry is deleted when its work is finished, not marked done, because a finished quest is in the commit history. Each entry says what the job is, where its detail lives, and roughly how big it is. It sits under a numbered-stage assets directory because the linter excludes those from every check.

## 3. Bring SC's typesetting dictionary up to SJ's, and feed in the Thai GC hyphenation candidates

th/SJ/04_assets/template/dictionary.typ carries 457 entries and SC's carries 92. The Thai printed edition of GC supplies 133 more in th/GC/04_assets/editions/print/HYPHEN-CANDIDATES.tsv, one per line as คริสต-จักร with the joined word, its break count, its unbroken count and a confidence note; a row becomes an entry mechanically, as (word: "คริสตจักร", parts: ("คริสต", "จักร")). Two things need judgment: eight of the rows occur once only and want a Thai reader before they go in, and the existing entries break a word at every syllable where the new rows give one morpheme boundary, so the two styles have to be reconciled. The larger question is whether SC and SJ keep separate dictionaries at all, since hyphenation is a fact about Thai words and not about a book.

Detail: this entry. Small if the dictionaries stay separate, medium if they merge.

## 4. Google Docs round trip

The translator's editor and reviewers work in Google Docs while the repository stays authoritative. The agreed design is th/SC/04_assets/planning/gdocs-workflow.md, distilled on 16 August; its minimal alternative, uploading the marker-laden file and letting the Doc's own comparison show the differences, is to be tested before anything larger is built. Until something is built, a chapter that passes check SCNN is uploaded by hand.

Detail: th/SC/04_assets/planning/gdocs-workflow.md. Medium.

## 5. QA3 reader agent and packet script

Written after QA2 has run on a first chapter, per th/SC/CLAUDE.md 3.E: a packet script that collects every paragraph QA1 and QA2 changed, with the English, the pre-QA Thai, the current Thai and the changed runs, and a Fable reader agent that judges each change in its whole paragraph and writes REVERT, REWORD or FIX markers only where a change should not stand.

Detail: th/SC/CLAUDE.md 3.E. Medium.

## 6. Restore the anchor headings in th/SC/00_source/SC04_en.md

SC04_en.md carries one "## {SC 37.1}" heading for eleven paragraphs; every other chapter's source has one heading per paragraph. The scripts anchor an English paragraph by its closing "{SC ###.#}" tag when the heading is missing, so the rounds run on SC04 as it stands. The repair is ten heading lines inserted above their paragraphs, in both copies of the file (th/SC/00_source and source/SC), reviewed in the diff.

Detail: none needed. Trivial; deferred on 11 September because no manuscript or source file is edited that day.

## 7. Mine the published MB and PP chapters 1 to 20 for the register and proper-noun sections of thai-profile.txt

Sections 4.C and 5.A of th/assets/translation_profile/thai-profile.txt are awaiting evidence: the pronouns used for the reader, the author and the people in a narrative; the honorifics for prophets, apostles and historical figures; the measure of royal vocabulary for Deity; and whether a transliterated name carries its English in parentheses at first appearance. The translator named the published MB and PP chapters 1 to 20 as his style on 14 September, so th-glossary-miner runs over those books with its register and proper-noun sections as the deliverable, and the translator rules the observations into the profile in chunks.

Detail: th-glossary-miner sections 2.B and 2.C. Medium; one mining run and one adjudication session.

## 8. SC01 notes for qa2

Sites to weigh in qa2, each in its own sentence and never by the row alone: {SC 9.1} ดาวิด for the psalmist, which the row allows; {SC 9.3} กฎเกณฑ์ของพระเจ้า for God's law beside the row's พระบัญญัติของพระเจ้า; {SC 10.2} คุณความดี without พระ beside the goodness row; {SC 13.2} and {SC 14.1} บาปกรรม, a word with no Bible occurrence, for "our redemption" and "your liabilities"; {SC 15.1} ลูกของพระเจ้า beside บุตรของพระเจ้า elsewhere in the chapter, against the children row's one-form-per-book note; {SC 11.2}, {SC 12.2} and {SC 15.2} "tender" folded into ความเมตตากรุณา. The three editor's choices at {SC 9.3} and {SC 11.2} go to Google Docs as they stand. Other chapters, from the SC01 studies: {SC 30.1} renders "the unfallen universe" as สวรรค์, narrowing every unfallen world to heaven, for SC03; {SC 94.2} "the way to the mercy seat" stands without พระที่นั่งกรุณา, for SC11.

Detail: this entry. Small.

## 9. Glossary rows awaiting adjudication

restitution: ชดใช้ in its repayment sense, kept apart from the propitiation row's verb use. Not in SC01; rule it when a chapter carries it.

Detail: this entry. Small.
