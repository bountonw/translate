# Side quests — the queue

Work that is agreed but not scheduled, in the order it will be done. When the translator asks how many are queued and in what order, this file is the answer and no agent answers from memory.

It lives under `04_assets/planning/` for two reasons. Every numbered-stage assets directory is excluded from the textlint and remark checks, and a queue has no paragraph anchors to satisfy the reference-code rule with. And the root of `04_assets` is swept periodically, so a document meant to last needs a named subdirectory of its own. Most entries are GC work; where one reaches another project, its own text says so.

Rules for keeping it. An issue he defers rather than decides is added here in the same reply that defers it, never left in a chat. An entry is deleted when the work is finished, not marked done, because a finished quest is in the git history. Each entry says what the job is, where its detail lives, and roughly how big it is, and nothing else — the reasoning belongs in the detail file.

## 26. Generate the website HTML for the shipped book

The print file went to the press on 2 September 2026 and the website should now serve the same text. Run the converter at `lo/websites/mdconverter/` (a dotnet program; `Program.cs`) over the 42 chapters and the introduction in `lo/GC/03_public/`, against the website folder with its `chapter_header.html`, `chapter_footer.html` and `metadata/chapter-key.txt`. The converter already strips every TeX carry-over the manuscripts contain — `\lw`, `\p`, `\GCcode`, `\newpage` — and the chapter-end page fixes of 2 September live in module 2's TeX path only, so the manuscripts are clean for the web without further work. Verify all 43 files convert, the prev/next links resolve against the chapter key, and the served text matches the press text.

Detail: none written; this entry is the whole brief. Small — a build, a run, and a check pass.

## 27. Build a landing page for the website

The front page of the website is basically blank. Build a landing page: the book title ປາຍທາງແຫ່ງຄວາມຫວັງ and author, a short description of what the book is, the way into the text (the introduction and chapter 1, or a table of contents), a note that the first printing is September 2026, and the contact address the introduction gives (laoegw@proton.me, with the online home www.laoegw.com/GC). Design choices are the translator's; the quest starts with a mock to react to, not a finished page.

Detail: none written; this entry is the whole brief. Small to medium.

## 28. Cleanup from the 2 September pre-press session

Three pieces, none urgent, all known.

First, signature padding in the build. The shipped file's two trailing blank pages were made by hand in typst. A self-adjusting pad — module 3 appends a TeX loop to the full book only, filling with truly blank pages to the next multiple of 16, the press's signature size — was designed and verified the same day with a multiple of 8 (520 pages on the real book, final blanks empty at text and pixel level, chapter proofs untouched); at 16 the book is 528 pages. It was not applied to the repository because the file had already gone. Apply it (the verified copy sits in `~/claude-sandbox/gc-audit/book-build/lo/GC/04_assets/scripts/module3_preprocess.py`) or decide against it and write the typst step down instead, so the next printing's build makes a press-shaped file by itself.

Second, the second-printing wrap program. The line-break audit of the shipped book read all 13,353 spaceless line breaks and classified 550 flags into four tiers; the file is `wrap-audit-20260902.tsv` beside this queue. Tier A is eleven verified mis-segmentations where the dictionary knows the compound and the segmenter split it anyway; tier B is sixty reviewed splits of genuine single words the lexicon holds as two (ນ້ຳມັນ, ຫົວໃຈ, ເຄື່ອງມື, ວັນອາທິດ and the rest); roughly seventy compound rows follow from A and B, and about sixteen sites compose actively wrong readings. Adding the rows re-wraps the whole book, which is why the work waits for the second printing. The loose line at {GC 456.2} (foot of printed page 340) rechecks itself then. This folds naturally into entry 17's glossary rework or runs beside it.

Third, dictionary row tidy. `GC21_lo.txt` and `GC_lo.txt` both carry the same ຟັອດເວນ row (harmless duplicate; the book-level one suffices). In `patch.txt`, the ນາຍຊ່າງ row duplicates `main.txt` byte for byte, and the bare ນາມນີ້ row no longer fires anywhere now that ມີນາມນີ້ covers the only site. Review and drop the dead rows.

Detail: this entry and the wrap-audit file are the brief. First and third are small; second is large and scheduled with entry 17.

## 4. Forbidden-terms lists — decide whether the two merge

The wiring is done. On 29 August `gc_termcheck.py` and `gc_resolvecheck.py` were changed to read `.tooling/forbidden_terms/lao.txt` alongside section 10 of `lo/GC/04_assets/translation_profile/GC-glossary.txt`, so a form the textlint job forbids is now caught at the pre-pass instead of after the push. The two lists overlap at three forms; the linter supplies 299 the glossary did not have.

What remains is the question the wiring does not answer: whether the two lists should become one. Section 10 rows carry a Notes cell that says where a correction applies — "Wrong at this head only", "Exception: ລ" — and the linter's flat `wrong # correct` format has nowhere to put that, which is why four of its rules are hand-written lookarounds rather than rows. A Thai list sits beside the Lao one and will want the same answer when a Thai project gets a pre-pass of its own.

Detail: none written. `.tooling/textlint/rules/lo.js` line 6 shows how the linter loads its list.

## 7. Governing-file size reduction

The three files under `lo/GC/04_assets/translation_profile/` are loaded by every agent on every dispatch. Move the decision history out of them into `lo/GC/04_assets/history/`, keyed by the English head, so the rules stay and the evidence stops being paid for on every dispatch.

Scope after the translator's rulings of 13 August: 17 oversized `GC-open-terms.md` entries and 24 glossary rows. The twelve sense-selection rows in the plan's section 6 are not touched at all, and a deferred entry stays at full size until it is adjudicated. `gc_govcheck.py` and its tests already exist and prove a pass loses nothing.

The largest single case measured so far is the Clergy entry of `GC-open-terms.md`, which stands at 806 words against the 15-word limit set by item 4.H of `lo/GC/CLAUDE.md`, in a file of 5,333 words that every agent loads on every dispatch. The GC38 audit of 21 August measured it and the translator deferred the cut, expecting to adjudicate it around Monday 24 August; the entry records a decision it calls closed at GC 15, so what has to stay is the three-way mapping the row states and what goes to the clergy head of `lo/GC/04_assets/history/GC-glossary-history.md` is the site-by-site reasoning behind it.

Detail: `~/claude-sandbox/gc-audit/glossary-reduction-plan.md`.

## 17. Rework the glossary system: one glossary per language, with book-specific overlays

The translator's direction of 23 August: what the GC governing files have become is not working, and the replacement has to serve every project in each language, with more projects lining up. One glossary per language holds the terms its books share; each book carries only its own differences on top; a rule is tight where the term is genuinely fixed, such as a proper noun or a closed term family, and loose where literary judgment in the paragraph decides; and the part an agent searches stays light enough to load on every dispatch, while the history and evidence for deep dives live beside it rather than inside it. The Lao version is built first, on GC, and then used as the model for the Thai projects.

Two things fold in. The glossary's sections are numbered from 10 — `## 10. Lao Spelling Glossary`, `## 11. Lao Proper Noun Glossary (GC)`, `## 12. Lao Compound Word-Order Pairs (GC)` in `lo/GC/04_assets/translation_profile/GC-glossary.txt` — a numbering left over from a structure that no longer exists, and the rework renumbers it. And the QA3 record under `lo/GC/04_assets/qa3/`, which gives Fable's in-context verdict on every change QA1 and QA2 made, is the evidence the rework reads before it keeps, loosens or drops any rule the GC runs wrote; every DECIDED, closed or ruled label in the current files is re-examined against that record rather than carried over, because many of those labels were an agent's extrapolation and not a ruling.

Entry 7 (governing-file size reduction) is absorbed by this.

Detail: none written yet; this entry is the whole brief. Large; Fable for the design.

QA3 findings for the rework, one line per chapter as they land:

GC28 {GC 489.3} — "so many professed Christians" reads ຜູ້ທີ່ອ້າງວ່າເປັນຄຣິສຕຽນ, identical to GC36's rendering of the identical English phrase, and ອ້າງວ່າເປັນ marks a professed or claimed identity at 32 corpus sites; no row governs "professed", and the rework decides whether one is wanted.

GC29 {GC 503.3} — no row exists for "the Lord of hosts": ອົງຊົງຣິດອຳນາດຍິ່ງໃຫຍ່ carries three English heads across 14 sites in 8 chapters — "the Most High", "Power", and, with ພຣະເຈົ້າຢາເວ or ອົງພຣະຜູ້ເປັນເຈົ້າ prefixed, "the LORD of hosts" — and ຈອມໂຍທາ appears nowhere in the book; a row fixing the full form for "Lord of hosts" and leaving the bare form to "the Most High" would have prevented the QA3 marker at this site.

GC30 {GC 505.2} — no row governs the apostasy family: ການປະຖິ້ມຄວາມເຊື່ອ stands at 15 sites across ten chapters, ຜູ້ປະຖິ້ມຄວາມເຊື່ອ at GC36 and QA2's ຜູ້ທີ່ປະຖິ້ມຄວາມເຊື່ອ at GC30; the rework decides whether a row is wanted and which agent-noun form it fixes.

GC32 {GC 529.1} — a second attestation for the "Lord of hosts" head the GC29 line above proposes: the English source uses the title in nine chapters (GC01, 08, 24, 27, 29, 32, 39, 40, 42) while ຈອມໂຍທາ has zero hits in the Lao book, and at {GC 529.1} the narrator's added attribution renders it with the short title ອົງພຣະຜູ້ເປັນເຈົ້າ, judged STANDS in its paragraph; every site shortens the title independently because no row governs it.

GC35 {GC 578.3} — no row governs "the Old World": QA3 marker #4 proposes reverting ທະວີບເກົ່າ, a calque Lao does not have, to ທະວີບເອີຣົບ; {GC 573.1} renders "the Old World" as ເອີຣົບ in pre-QA and current text alike and GC25 {GC 440.1} expands the phrase to named continents, so the body text never uses the calque, and the rework decides whether a row is wanted.

