# SC side quests — the queue

Work that is agreed but not scheduled, in the order it will be done. When Brian asks how many SC side quests are open and in what order, this file is the answer and no agent answers from memory. An issue he defers rather than decides is added here in the same reply that defers it, and an entry is deleted when its work is finished, not marked done, because a finished quest is in the commit history. Each entry says what the job is, where its detail lives, and roughly how big it is. It sits under a numbered-stage assets directory because the linter excludes those from every check.

## 3. Bring SC's typesetting dictionary up to SJ's, and feed in the Thai GC hyphenation candidates

th/SJ/04_assets/template/dictionary.typ carries 457 entries and SC's carries 92; the Thai printed GC supplies 133 candidates in th/GC/04_assets/editions/print/HYPHEN-CANDIDATES.tsv. The question is whether the two projects share one dictionary. Entry 15 of lo/GC/04_assets/planning/SIDEQUESTS.md is the full brief.

Detail: that GC entry. Small if the dictionaries stay separate, medium if they merge.

## 4. Google Docs round trip

The translator's editor and reviewers work in Google Docs while the repository stays authoritative. The agreed design is th/SC/04_assets/planning/gdocs-workflow.md, distilled on 16 August; its minimal alternative, uploading the marker-laden file and letting the Doc's own comparison show the differences, is to be tested before anything larger is built. Until something is built, a chapter that passes check SCNN is uploaded by hand.

Detail: th/SC/04_assets/planning/gdocs-workflow.md. Medium.

## 5. QA3 reader agent and packet script

Written after QA2 has run on a first chapter, per th/SC/CLAUDE.md 3.E. The models are gc-qa3-reader and lo/GC/04_assets/scripts/gc_qa3_packet.py on the GC-instructions branch; the packet script has to be re-written for Typst anchors.

Detail: th/SC/CLAUDE.md 3.E. Medium.

## 6. Restore the anchor headings in th/SC/00_source/SC04_en.md

SC04_en.md carries one "## {SC 37.1}" heading for eleven paragraphs; every other chapter's source has one heading per paragraph. The scripts anchor an English paragraph by its closing "{SC ###.#}" tag when the heading is missing, so the rounds run on SC04 as it stands. The repair is ten heading lines inserted above their paragraphs, in both copies of the file (th/SC/00_source and source/SC), reviewed in the diff.

Detail: none needed. Trivial; deferred on 11 September because no manuscript or source file is edited that day.
