# Side quests — the queue

Work that is agreed but not scheduled, in the order it will be done. When Brian asks how many are queued and in what order, this file is the answer and no agent answers from memory.

It lives under `04_assets/planning/` for two reasons. Every numbered-stage assets directory is excluded from the textlint and remark checks, and a queue has no paragraph anchors to satisfy the reference-code rule with. And the root of `04_assets` is swept periodically, so a document meant to last needs a named subdirectory of its own. Most entries are GC work; where one reaches another project, its own text says so.

Rules for keeping it. An issue he defers rather than decides is added here in the same reply that defers it, never left in a chat. An entry is deleted when the work is finished, not marked done, because a finished quest is in the git history. Each entry says what the job is, where its detail lives, and roughly how big it is, and nothing else — the reasoning belongs in the detail file.

## 1. Wire the forbidden-terms list into the audit pre-pass

Two lists of known-wrong spellings exist and neither knows about the other. `.tooling/forbidden_terms/lao.txt` holds 313 terms in `forbidden # correct` form and drives the textlint CI job; section 10 of `lo/GC/04_assets/translation_profile/GC-glossary.txt` holds 30 forms and drives `gc_termcheck.py` and `gc_resolvecheck.py`. So a batch auditor can pass a chapter that CI then fails, which is how ຍຶດເອົາ reached a commit in GC12 and came back as a lint error.

Make the audit scripts read the linter's list as well as section 10, so a forbidden term is caught at the pre-pass rather than after the push. Decide as part of the quest whether the two lists should merge, and whether section 10 rows that are context-dependent can live in the linter's flat format at all. There is a Thai list beside the Lao one, `.tooling/forbidden_terms/`, so whatever is built should serve both.

Detail: none written yet. `.tooling/textlint/rules/lo.js` line 6 shows how the list is loaded.

## 2. Footnote author-gloss sweep

Every author cited in a footnote carries the English name in parentheses after the Lao form, so a Lao reader can pronounce it and also look it up: `[^19]: ມາຕິນ (Martyn), ເຫຼັ້ມ 5, ໜ້າ 417.`

Brian ranked this above everything else in the queue. 240 of 272 sites remain across 31 chapters; 170 resolve from existing glossary rows and 102 need the English source and probably a new proper-noun row. Done so far: 14 Martyn sites, 15 Bliss sites in GC18, GC21 and GC22, and 3 Wolff journal titles in GC20.

Detail: `~/claude-sandbox/gc-audit/footnote-gloss-sweep-prompt.md`, with the per-chapter worklist beside it in `footnote-gloss-worklist.md`.

## 3. Dictionary sync check when a spelling changes

Confirm that `lo/assets/dictionaries/main.txt` is updated whenever a spelling decision changes a form in the manuscripts, and find out what currently keeps the two in step. The Stephen sweep touched the dictionary by hand, which suggests nothing does it automatically.

Open questions for the quest itself: which decisions are supposed to reach the dictionary, whether the line-break entries are the only affected kind, and whether a script should check the two against each other the way `gc_govcheck.py` checks the governing files.

Detail: none written yet. Small to size, unknown to fix.

## 4. Governing-file size reduction

The three files under `lo/GC/04_assets/translation_profile/` are loaded by every agent on every dispatch. Move the decision history out of them into `lo/GC/04_assets/history/`, keyed by the English head, so the rules stay and the evidence stops being paid for on every dispatch.

Scope after Brian's rulings of 13 August: 17 oversized `GC-open-terms.md` entries and 24 glossary rows. The twelve sense-selection rows in the plan's section 6 are not touched at all, and a deferred entry stays at full size until it is adjudicated. `gc_govcheck.py` and its tests already exist and prove a pass loses nothing.

Detail: `~/claude-sandbox/gc-audit/glossary-reduction-plan.md`.

## 5. ລົບລ້າງ against ລຶບລ້າງ — normalise, or leave both

Both spellings are accurate and the editors want both, which is the ruling of GC 15 and stands. The open question is whether the book should normalise to one form anyway. Brian never read the argument for normalising when it was first put, so it was held rather than closed.

The evidence is already gathered: corpus counts are ລຶບລ້າງ 78 against ລົບລ້າງ 16, the two are not distinguished by sense, GC 287.1 carries both a sentence apart, and the large count is inflated by the fixed phrase in the Day of Atonement glossary row. Not to be raised in a chapter audit meanwhile.

Detail: the `NOTE-SPELL ລົບລ້າງ and ລຶບລ້າງ` entry in `lo/GC/04_assets/translation_profile/GC-open-terms.md`.

## 6. Where `unwrap.py` belongs

`~/claude-sandbox/scripts/unwrap.py` is the only tool that does what root `CLAUDE.md` 7.A requires of every instruction file, it operates on repository files, and nothing names it. Under 8.A it belongs in the repository. Decide whether it goes to `lo/GC/04_assets/scripts/` or to a `scripts/` directory at the repository root, which depends on whether it will be used on the Thai and Lao projects too.

Detail: none needed. A move and one line in a procedure file.
