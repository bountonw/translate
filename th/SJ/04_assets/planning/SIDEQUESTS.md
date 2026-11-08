# SJ side quests — the queue

Work that is agreed but not scheduled, in the order it will be done. When the translator asks how many SJ side quests are open and in what order, this file is the answer and no agent answers from memory. An issue the translator defers rather than decides is added here in the same reply that defers it, and an entry is deleted when its work is finished, not marked done, because a finished quest is in the commit history. Each entry says what the job is, where its detail lives, and roughly how big it is. It sits under a numbered-stage assets directory because the linter excludes those from every check.

## Open questions found while setting up SJ (8 November 2026)

1. SJ14 joins the English paragraphs {SJ 91.2} and {SJ 91.3} into one Thai paragraph tagged 91.3. DECIDE: keep the join and mark 91.2 as rendered in 91.3, or split the Thai into two paragraphs. sj_anchors.py holds SJ14 until this is ruled.
2. SJ29 has {SJ 170.8} twice, and the tags after it run one number low through 170.12. FIX: correct the tags. sj_anchors.py holds SJ29 until this is done.
3. SJ's default Bible version is not set: the chapters hide /*THSV*/ at 84 citations and show THSV at 5. FIX1: THSV, written as one line in thai-profile.txt 2.A.
4. SJ00, the front matter, carries the placeholder tag {SJ 666.66} on its 18 paragraphs; three of them answer the English preface 12.1 to 12.3. DECIDE which paragraphs answer the English before SJ00 runs any round.
5. 32 commented-out filler lines from the printed book stand in 23 chapters. DECIDE: keep or remove them.
6. SJ06's Source-url points to p144.175, inside chapter 5; chapter 6 opens at p144.179. FIX: correct the link.
