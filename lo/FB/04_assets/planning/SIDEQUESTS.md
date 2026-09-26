# FB side quests — the queue

Work that is agreed but not scheduled, in the order it will be done. When the translator asks how many FB side quests are open and in what order, this file is the answer and no agent answers from memory. An issue he defers rather than decides is added here in the same reply that defers it, and an entry is deleted when its work is finished, not marked done, because a finished quest is in the commit history. Each entry says what the job is, where its detail lives, and roughly how big it is.

## 1. Delete the FB-lo branch

Ruled 26 September: once FB-creation is pushed, the translator deletes FB-lo locally and on origin (`git branch -D FB-lo` and `git push origin --delete FB-lo`); FB-creation carries its two files and main carries its GC work. Every report reminds him until it is done, per lo/FB/CLAUDE.md 7.G. Then the entry "Separate the FB-lo branch from the GC work it carries" in lo/GC/04_assets/planning/SIDEQUESTS.md on the GC-instructions branch is rewritten to say so.

Detail: this entry. Trivial.

## 2. The book Seventh-day Adventists Believe

The book has been translated into Lao. The translator adds it later as a resource for the statement rounds; when it arrives, settle where it lives under lo/FB and how the packet script quotes it. It is not a product of this project for now (ruled 26 September).

Detail: lo/FB/CLAUDE.md 2.C and 8. Small.

## 6. fb-sentence-drill

The Fable xhigh agent of lo/FB/CLAUDE.md 4.B: 8/4/1 per sentence, SENT markers in the draft, on the model of .claude/agents/fb-phrase-drill.md.

Detail: lo/FB/CLAUDE.md 4.B. Small.

## 7. fb_check.py and fb-final-read

The check script of 5.A, built from the conventions of the web instructions section 5 and the corpus checks of lo/GC/04_assets/scripts/gc_punctcheck.py, and the Fable xhigh final reader of 5.B.

Detail: lo/FB/CLAUDE.md 5. Medium.

## 8. FB-profile.txt and FB-glossary.txt

Move sections 5 and 6 of lo/FB/04_assets/planning/web-instructions.txt into lo/FB/04_assets/translation_profile/ as governing files in the shape of th/assets/translation_profile/thai-profile.txt and thai-glossary.txt, and give both a row in instruction_budget.py.

Detail: this entry. Small.

## 9. Typst template for FB

A heading, statement and reference-line layout for a belief in lo/FB/04_assets/template/, on the SC model.

Detail: th/SC/04_assets/template/. Small.
