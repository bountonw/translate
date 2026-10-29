# Side quests — the queue

Work that is agreed but not scheduled, in the order it will be done. When the translator asks how many are queued and in what order, this file is the answer and no agent answers from memory.

It lives under `04_assets/planning/` for two reasons. Every numbered-stage assets directory is excluded from the textlint and remark checks, and a queue has no paragraph anchors to satisfy the reference-code rule with. And the root of `04_assets` is swept periodically, so a document meant to last needs a named subdirectory of its own. Most entries are GC work; where one reaches another project, its own text says so.

Rules for keeping it. An issue he defers rather than decides is added here in the same reply that defers it, never left in a chat. An entry is deleted when the work is finished, not marked done, because a finished quest is in the git history. Each entry says what the job is, where its detail lives, and roughly how big it is, and nothing else — the reasoning belongs in the detail file.

## 27. Build the home page of the website

The front page of www.laoegw.com is basically blank. Build the home page of the whole site, not the page of one book: the books it holds, starting with ປາຍທາງແຫ່ງຄວາມຫວັງ, each with its title, author, a short description and the way into its text; the first printing of ປາຍທາງແຫ່ງຄວາມຫວັງ, October 2026, as the printed title page has it; and the contact address the introduction gives (laoegw@proton.me). The page is in Lao first; Thai and English follow soon, and the Thai books (MB first, then SC once it goes to press) join the site as they are ready (rulings of 28 October 2026). Design choices are the translator's: a few questions each turn draw out the ideas, then a mock to react to.

Detail: none written; this entry is the whole brief. Small to medium.

## 29. Add the Thai books to the website

The website build, `websites/assets/scripts/build_book.py`, reads Markdown chapters with GC's front matter. Add MB and LBF first, then SC and PP, which are written in Typst and need a Typst reader in the converter; SJ waits for its editing. Rulings of 16 October 2026: the Sarabun font; the page words สารบัญ, บทที่ and ต้นฉบับภาษาอังกฤษ; LBF's paragraph codes hidden on the page, as its metadata asks, with the paragraph link addresses kept, and its `original` source line left off; Thai line breaks left to the browser for now; no cover images until covers exist. Each book needs the Thai layout folder `websites/assets/layout/th/`, a contents page and a line in the GitHub check.

Detail: this entry is the whole brief. Medium for MB and LBF; large for SC and PP.

## 17. Rework the glossary system: one glossary per language, with book-specific overlays

The translator's direction of 23 August: what the GC governing files have become is not working, and the replacement has to serve every project in each language, with more projects lining up. One glossary per language holds the terms its books share; each book carries only its own differences on top; a rule is tight where the term is genuinely fixed, such as a proper noun or a closed term family, and loose where literary judgment in the paragraph decides; and the part an agent searches stays light enough to load on every dispatch, while the history and evidence for deep dives live beside it rather than inside it. The Thai language glossary, `th/assets/translation_profile/thai-glossary.txt`, is the model. The Lao language glossary, `lo/assets/translation_profile/lao-glossary.txt`, was begun with FB, and the rework moves the GC rows into it.

Two things fold in. The glossary's sections are numbered from 10 — `## 10. Lao Spelling Glossary`, `## 11. Lao Proper Noun Glossary (GC)`, `## 12. Lao Compound Word-Order Pairs (GC)` in `lo/GC/04_assets/translation_profile/GC-glossary.txt` — a numbering left over from a structure that no longer exists, and the rework renumbers it. And the QA3 record under `lo/GC/04_assets/qa3/`, which gives Fable's in-context verdict on every change QA1 and QA2 made, is the evidence the rework reads before it keeps, loosens or drops any rule the GC runs wrote; every DECIDED, closed or ruled label in the current files is re-examined against that record rather than carried over, because many of those labels were an agent's extrapolation and not a ruling.

The size of the three files under `lo/GC/04_assets/translation_profile/`, which every agent loads on every dispatch, is part of this work. Move the decision history out of them into `lo/GC/04_assets/history/`, keyed by the English head, so the rules stay and the evidence stops being paid for on every dispatch. Scope after the translator's rulings of 13 August: 17 oversized `GC-open-terms.md` entries and 24 glossary rows; the twelve sense-selection rows in section 6 of the plan are not touched, and a deferred entry stays at full size until it is adjudicated. `gc_govcheck.py` and its tests prove a pass loses nothing. The largest case is the Clergy entry of `GC-open-terms.md`, 807 words against the 15-word limit of item 5.C of `lo/GC/CLAUDE.md`; the three-way mapping its row states stays, and the site-by-site reasoning goes to the clergy head of `lo/GC/04_assets/history/GC-glossary-history.md`. Plan: `~/claude-sandbox/gc-audit/glossary-reduction-plan.md`.

Detail: none written yet; this entry is the whole brief. Large; Fable for the design. It runs on a branch of its own, not on GC-queue.

QA3 findings for the rework, one line per chapter as they land:

GC28 {GC 489.3} — "so many professed Christians" reads ຜູ້ທີ່ອ້າງວ່າເປັນຄຣິສຕຽນ, identical to GC36's rendering of the identical English phrase, and ອ້າງວ່າເປັນ marks a professed or claimed identity at 32 corpus sites; no row governs "professed", and the rework decides whether one is wanted.

GC29 {GC 503.3} — no row exists for "the Lord of hosts": ອົງຊົງຣິດອຳນາດຍິ່ງໃຫຍ່ carries three English heads across 14 sites in 8 chapters — "the Most High", "Power", and, with ພຣະເຈົ້າຢາເວ or ອົງພຣະຜູ້ເປັນເຈົ້າ prefixed, "the LORD of hosts" — and ຈອມໂຍທາ appears nowhere in the book; a row fixing the full form for "Lord of hosts" and leaving the bare form to "the Most High" would have prevented the QA3 marker at this site.

GC30 {GC 505.2} — no row governs the apostasy family: ການປະຖິ້ມຄວາມເຊື່ອ stands at 15 sites across ten chapters, ຜູ້ປະຖິ້ມຄວາມເຊື່ອ at GC36 and QA2's ຜູ້ທີ່ປະຖິ້ມຄວາມເຊື່ອ at GC30; the rework decides whether a row is wanted and which agent-noun form it fixes.

GC32 {GC 529.1} — a second attestation for the "Lord of hosts" head the GC29 line above proposes: the English source uses the title in nine chapters (GC01, 08, 24, 27, 29, 32, 39, 40, 42) while ຈອມໂຍທາ has zero hits in the Lao book, and at {GC 529.1} the narrator's added attribution renders it with the short title ອົງພຣະຜູ້ເປັນເຈົ້າ, judged STANDS in its paragraph; every site shortens the title independently because no row governs it.

GC35 {GC 578.3} — no row governs "the Old World": QA3 marker #4 proposes reverting ທະວີບເກົ່າ, a calque Lao does not have, to ທະວີບເອີຣົບ; {GC 573.1} renders "the Old World" as ເອີຣົບ in pre-QA and current text alike and GC25 {GC 440.1} expands the phrase to named continents, so the body text never uses the calque, and the rework decides whether a row is wanted.

