# Side quests — the queue

Work that is agreed but not scheduled, in the order it will be done. When Brian asks how many are queued and in what order, this file is the answer and no agent answers from memory.

It lives under `04_assets/planning/` for two reasons. Every numbered-stage assets directory is excluded from the textlint and remark checks, and a queue has no paragraph anchors to satisfy the reference-code rule with. And the root of `04_assets` is swept periodically, so a document meant to last needs a named subdirectory of its own. Most entries are GC work; where one reaches another project, its own text says so.

Rules for keeping it. An issue he defers rather than decides is added here in the same reply that defers it, never left in a chat. An entry is deleted when the work is finished, not marked done, because a finished quest is in the git history. Each entry says what the job is, where its detail lives, and roughly how big it is, and nothing else — the reasoning belongs in the detail file.

## 26. Generate the website HTML for the shipped book

The print file went to the press on 2 September 2026 and the website should now serve the same text. Run the converter at `lo/websites/mdconverter/` (a dotnet program; `Program.cs`) over the 42 chapters and the introduction in `lo/GC/03_public/`, against the website folder with its `chapter_header.html`, `chapter_footer.html` and `metadata/chapter-key.txt`. The converter already strips every TeX carry-over the manuscripts contain — `\lw`, `\p`, `\GCcode`, `\newpage` — and the chapter-end page fixes of 2 September live in module 2's TeX path only, so the manuscripts are clean for the web without further work. Verify all 43 files convert, the prev/next links resolve against the chapter key, and the served text matches the press text.

Detail: none written; this entry is the whole brief. Small — a build, a run, and a check pass.

## 27. Build a landing page for the website

The front page of the website is basically blank. Build a landing page: the book title ປາຍທາງແຫ່ງຄວາມຫວັງ and author, a short description of what the book is, the way into the text (the introduction and chapter 1, or a table of contents), a note that the first printing is September 2026, and the contact address the introduction gives (laoegw@proton.me, with the online home www.laoegw.com/GC). Design choices are the translator's; the quest starts with a mock to react to, not a finished page.

Detail: none written; this entry is the whole brief. Small to medium.

## 28. Cleanup from the 2 September pre-press session

Four pieces, none urgent, all known.

First, signature padding in the build. The shipped file's two trailing blank pages were made by hand in typst. A self-adjusting pad — module 3 appends a TeX loop to the full book only, filling with truly blank pages to the next multiple of 8 — was designed and verified the same day: 520 pages on the real book, final blanks empty at text and pixel level, chapter proofs untouched. It was not applied to the repository because the file had already gone. Apply it (the verified copy sits in `~/claude-sandbox/gc-audit/book-build/lo/GC/04_assets/scripts/module3_preprocess.py`) or decide against it and write the typst step down instead, so the next printing's build makes a press-shaped file by itself.

Second, the second-printing wrap program. The line-break audit of the shipped book read all 13,353 spaceless line breaks and classified 550 flags into four tiers; the file is `wrap-audit-20260902.tsv` beside this queue. Tier A is eleven verified mis-segmentations where the dictionary knows the compound and the segmenter split it anyway; tier B is sixty reviewed splits of genuine single words the lexicon holds as two (ນ້ຳມັນ, ຫົວໃຈ, ເຄື່ອງມື, ວັນອາທິດ and the rest); roughly seventy compound rows follow from A and B, and about sixteen sites compose actively wrong readings. Adding the rows re-wraps the whole book, which is why the work waits for the second printing. The loose line at {GC 456.2} (foot of printed page 340) rechecks itself then. This folds naturally into entry 17's glossary rework or runs beside it.

Third, dictionary row tidy. `GC21_lo.txt` and `GC_lo.txt` both carry the same ຟັອດເວນ row (harmless duplicate; the book-level one suffices). In `patch.txt`, the ນາຍຊ່າງ row duplicates `main.txt` byte for byte, and the bare ນາມນີ້ row no longer fires anywhere now that ມີນາມນີ້ covers the only site. Review and drop the dead rows.

Fourth, record the binding segmentation gate. The pre-press dictcheck answers whether a token can be covered by dictionary words; the pipeline's segmenter chooses greedily and can still strand letters that print in red. The gate that actually binds is: run modules 1 and 2 for every chapter and require `grep -c nodict temp/*_stage2.tex` to be zero everywhere. Write that into the pre-press procedure so the next book's final check tests the real thing.

Detail: this entry and the wrap-audit file are the brief. First and third are small, fourth is a paragraph in a procedure file, second is large and scheduled with entry 17.

## 29. Separate the FB-lo branch from the GC work it carries

The `FB-lo` branch holds two files that belong to the Lao Fundamental Beliefs project and a long history of GC work that does not. Brian's instruction of 24 August was that only `lo/FB/statements.txt` and `lo/FB/statements_lo.txt`, both added by the tip commit `01f5a85c "Begin translation of Fundamental Beliefs"`, belong on that branch, and that everything else it carries belongs to the GC line of work that sat on `GC-QA2-continued` that day. The work is to be done in a worktree of its own at `/home/ton/programming/translate-lo-FB`, which leaves the main checkout on its own branch.

The first step is creating that worktree, which has not happened. The directory exists and was still empty on 3 September, and the command is `git worktree add /home/ton/programming/translate-lo-FB FB-lo`.

Re-verify the branch before touching it, because these figures are from 24 August and the book has gone to press since. On that day `FB-lo` matched `origin/FB-lo` at `01f5a85c`, stood 122 commits ahead of `main` and 2 behind it, and its diff against the merge base touched 57 files: the two Fundamental Beliefs files, the QA1 and QA2 history of 41 GC chapters, `lo/assets/translation_profile/GC-glossary.txt`, three TeX files under `lo/GC/04_assets/scripts/tex/`, and the Lao dictionaries. Nothing could be re-checked on 3 September, because git commands were blocked in that session. The question that sizes the job is whether those GC commits have since reached `main`: if they have, rebuild `FB-lo` as the two Fundamental Beliefs files on top of current `main`; if they have not, land them on a GC branch before reducing `FB-lo`.

Detail: none written; this entry is the whole brief. Small if the GC commits are already on `main`, medium if they are not.

## 2. Encode the 14 August rulings from the GC 421.3 litigation

Four rulings need writing into the instruction files where agents will see them; Opus or Sonnet work, small. (a) Glossary and corpus attestation support a rendering but never decide it — sentence meaning and paragraph flow rule. (b) In sentence-litigation mode the draft goes above the old paragraph in the manuscript and the old text stays for comparison until Brian finalizes. (c) A translator-added naming gloss stays where the quoted Bible versions use different terms for the same referent. (d) A Fable session works translation issues only; updates like these go to the top of this queue for a smaller model.

Detail: none written; this entry is the whole brief.

## 3. Anonymise the instruction files

Remove the name Brian in every form from the instruction files and replace it with "the user" or another generic term. The name appears 78 times across the eight core instruction files — root `CLAUDE.md`, `lo/GC/CLAUDE.md`, the five `gc-*` agent definitions and `.claude/commands/gc.md` — and about 25 more times in the audit scripts, the governing files, this queue and `04_assets/history/`. The glossary part is already done: all 32 occurrences were removed from `lo/GC/04_assets/translation_profile/GC-glossary.txt` on 21 August, leaving the rest of each sentence intact.

The count understates the work. Those files also carry roughly 54 third-person pronouns — he, his, him, himself — that refer to the same person and read wrongly the moment the noun becomes generic, so a find-and-replace on the name alone leaves the prose broken.

The replacement term was decided on 16 August: "the translator". The new th/SC instruction files already use it and avoid third-person pronouns entirely, which is the pattern for the sweep. The sweep itself stays queued and does not run until scheduled.

Two boundaries to settle as part of the quest. The translator credit in `th/LBF/assets/LBF00_copyright.md` is a real byline and not an instruction, so it is presumably out of scope. The saved memories under `~/.claude/projects/` use the name throughout and are not repository files, so whether they are in scope is a separate decision.

Detail: none written yet.

## 4. Forbidden-terms lists — decide whether the two merge

The wiring is done. On 29 August `gc_termcheck.py` and `gc_resolvecheck.py` were changed to read `.tooling/forbidden_terms/lao.txt` alongside section 10 of `lo/GC/04_assets/translation_profile/GC-glossary.txt`, so a form the textlint job forbids is now caught at the pre-pass instead of after the push. The two lists overlap at three forms; the linter supplies 299 the glossary did not have.

What remains is the question the wiring does not answer: whether the two lists should become one. Section 10 rows carry a Notes cell that says where a correction applies — "Wrong at this head only", "Exception: ລ" — and the linter's flat `wrong # correct` format has nowhere to put that, which is why four of its rules are hand-written lookarounds rather than rows. A Thai list sits beside the Lao one and will want the same answer when a Thai project gets a pre-pass of its own.

Detail: none written. `.tooling/textlint/rules/lo.js` line 6 shows how the linter loads its list.

## 6. Dictionary sync check when a spelling changes

Confirm that `lo/assets/dictionaries/main.txt` is updated whenever a spelling decision changes a form in the manuscripts, and find out what currently keeps the two in step. The Stephen sweep touched the dictionary by hand, which suggests nothing does it automatically.

Open questions for the quest itself: which decisions are supposed to reach the dictionary, whether the line-break entries are the only affected kind, and whether a script should check the two against each other the way `gc_govcheck.py` checks the governing files.

Detail: none written yet. Small to size, unknown to fix.

## 7. Governing-file size reduction

The three files under `lo/GC/04_assets/translation_profile/` are loaded by every agent on every dispatch. Move the decision history out of them into `lo/GC/04_assets/history/`, keyed by the English head, so the rules stay and the evidence stops being paid for on every dispatch.

Scope after Brian's rulings of 13 August: 17 oversized `GC-open-terms.md` entries and 24 glossary rows. The twelve sense-selection rows in the plan's section 6 are not touched at all, and a deferred entry stays at full size until it is adjudicated. `gc_govcheck.py` and its tests already exist and prove a pass loses nothing.

The largest single case measured so far is the Clergy entry of `GC-open-terms.md`, which stands at 806 words against the 15-word limit set by item 4.H of `lo/GC/CLAUDE.md`, in a file of 5,333 words that every agent loads on every dispatch. The GC38 audit of 21 August measured it and Brian deferred the cut, expecting to adjudicate it around Monday 24 August; the entry records a decision it calls closed at GC 15, so what has to stay is the three-way mapping the row states and what goes to the clergy head of `lo/GC/04_assets/history/GC-glossary-history.md` is the site-by-site reasoning behind it.

Detail: `~/claude-sandbox/gc-audit/glossary-reduction-plan.md`.

## 9. Where `unwrap.py` belongs

`~/claude-sandbox/scripts/unwrap.py` is the only tool that does what root `CLAUDE.md` 7.A requires of every instruction file, it operates on repository files, and nothing names it. Under 8.A it belongs in the repository. Decide whether it goes to `lo/GC/04_assets/scripts/` or to a `scripts/` directory at the repository root, which depends on whether it will be used on the Thai and Lao projects too.

Detail: none needed. A move and one line in a procedure file.

## 10. Set up the SC Thai project

Scaffolding was built on 16 August: the procedure file `th/SC/CLAUDE.md`, the `sc-batch-auditor` and `th-glossary-miner` agents, the `/sc` command, and the English sources copied into `th/SC/00_source/`. Nine chapters sit in `02_edit`, two in `03_public`, and SC12 and SC13 in `01_raw` await the pre-processing round.

Remaining: the decisions in the 16 August session report (QA round scope, Thai glossary home, citation style, default Bible version), the glossary mining run over `th/PP`, and the Google Docs pipeline build.

Detail: `th/SC/CLAUDE.md` and `th/SC/04_assets/planning/gdocs-workflow.md`.

## 11. Set up the SJ Thai project

`th/SJ/` is further along than SC in one sense and further behind in another: 32 chapters are already in `03_public`, but the project has no `00_source` and no `02_edit`, so the English it was translated from is not in the repository beside it. It has the same Typst pipeline and the same absence of a procedure file, governing files and agents.

The missing source is the first question of the quest, because a GC-style audit compares the translation against an anchored English source and there is nothing here to compare against yet. Settle where the source comes from and whether it is imported before deciding what else to build.

Detail: none written yet.

## 12. Set up the AA Lao project

`lo/AA/` has the fullest raw material of the three — 58 English source files, 54 raw translations, four chapters in `02_edit` — and nothing in `03_public` but a placeholder. It has no procedure file, no `04_assets/translation_profile/` and no agents; its `04_assets` holds only temporary Typst source files. The chapter files are Typst rather than Markdown, which is the same portability question as SC and SJ.

Done on 21 August, before the project existed. A pre-edit spelling round ran over all 58 chapters on the `AA-fix-spelling` branch, in three commits, correcting roughly 4,900 sites. It fixed only spelling and mechanical character defects, on Brian's instruction of "absolutely zero editing". The three passes were: mechanical normalisation, which composed 4,049 decomposed AM vowels, stripped 327 zero-width spaces, and repaired 50 doubled tone or vowel marks, 5 misordered marks and one Thai fragment left untranslated at AA38 {AA 406.1}; a list-driven pass of about 400 corrections from `common-spelling.txt` and the linter's forbidden-terms list; and a word-form pass in which eight agents triaged 554 forms the dictionaries did not recognise, yielding 202 corrections. AA06 was excluded throughout because Brian is editing it on `AA06-edit`, and is being handled there.

Still to do. The project scaffolding itself, on the GC model: a procedure file, governing files under `04_assets/translation_profile/`, and agent definitions. About twenty single-occurrence forms remain that no authority can settle, including ປົກງັວມ at AA35 {AA 379.3}, ໂອຫັວ at AA41 {AA 434.4}, ດູມໍ in AA21 and ຖະນຸ; each needs the English at its anchor rather than a corpus lookup. AA06 also needs a structural check of the kind that found a missing paragraph in it.

Seven things to know before touching AA text.

1. Never add a word to any file under `lo/assets/dictionaries/`. The dictionaries and the GC corpus are the authority and the manuscript is corrected toward them. An unrecognised form is usually a typo, not a gap: `main.txt` carries ໂກຣິນໂທ and the manuscript's ໂກລິນໂທ was simply wrong. This is Brian's instruction of 21 August.

2. In `lo/assets/dictionaries/common-spelling.txt` the left column is the correct form and the right lists the wrong variants, as its header now says. Its row `ບົກຜ່ອງ | ບົກຜ່ອງ` carries the same form on both sides and does nothing.

3. Two Lao forbidden-terms lists exist and they disagree. Use `.tooling/forbidden_terms/lao.txt` in this repository, which holds 313 rows in `wrong # correct` form, drives the textlint job, and agrees with the published GC chapters at every row. Never use `markdownlint/forbidden_terms/lao.txt` in the `translate-tooling` repository: it supplies no corrections and four of its entries flag the correct spelling rather than the wrong one, so a round driven by it changes ບົກຜ່ອງ, ປັດຈຸບັນ, ຫຸ້ນສ່ວນ and ຫຼີກລ່ຽງ away from the form GC uses.

4. Lao running text has no word spaces, so a word-boundary regex such as `(?<![\u0e80-\u0eff])` matches almost nothing and a scan built on one reports a clean file when it is not. Match substrings and confirm each hit against a dictionary segmentation.

5. Correct the whole word, never a bare syllable. This is Brian's ruling of 21 August, and it earned itself: ໜຸນ sat in three different words, one of which needed two syllables changed to reach ສະໜັບສະໜູນ, so a syllable swap would have left a form that is still wrong and no longer flagged.

6. A correction whose wrong form is contained in its correct form will fire inside words that are already right. Applying ຟີເລໂມ to ຟີເລໂມນ turned 19 correct instances into ຟີເລໂມນນ. Guard such a pair with a lookaround, and check the count of the correct form before and after.

7. A form that GC contains is not a misspelling. Rejecting any proposal whose wrong side appears in GC is what stopped ວາມ being rewritten to ຄວາມ at 3,843 sites, where ວາມ was only the tail of ຄວາມ left by a failed segmentation.

Detail: none written; this entry is the whole brief.

Two Claude web-app projects describe the AA project better than anything in this repository does, and importing them is the first step of the set-up rather than an afterthought. Ask Brian for them before designing a procedure file or governing files, because whatever they settle about scope, glossary or pipeline should shape those files rather than be reconciled with them afterwards.

One chapter carries a problem that must be settled before AA06 is edited again. Chapter 6 exists in three states. The committed manuscript is the August 2025 line: Brian's Google Docs edits merged in, then the pre-edit spelling round of 88 corrections, all verified. Separately, months earlier, Gemini was given the AA translation profile and produced its own version of the chapter as a standalone file. Brian diffed that file against the chapter in this repository and began working through the resulting diff, accepting a hunk, declining it or rewording it as he went, until he stopped part-way.

That partially resolved diff is parked at `lo/AA/04_assets/planning/AA06-gemini-partial.typ` in the AA repository, with a README beside it. It is neither a manuscript nor a rewrite: prose that reads cleanly in it has already been resolved and is Brian's decision, whichever side of the diff it came from, while the 18 parenthetical groups are the hunks he had not yet reached and hold the competing readings. Eleven of those groups have brackets the diff left unbalanced, from the clean (ພວມ/ກຳລັງ) to ((ຂ່າວສານແຫ່ງ))) and ( ແລະ ພາ)(ໄປຂັງຄຸກ)), and one carries an English gloss as a fourth option. It covers {AA 57.1} to {AA 62.1} only, with {AA 62.1} holding its anchor and no body, its tags are bare {AA 57.1} rather than #EGW[\{AA 57.1\}], and the AM vowel is decomposed throughout.

Finishing it means resuming the diff from where Brian stopped, settling each remaining parenthetical group, deciding what happens to {AA 62.1} through {AA 69.1} which the diff never reached, and re-running the spelling round on the result. His instruction of 21 August was that this must not be attempted piecemeal in a chat and belongs to the project set-up, and that the work must not be lost, which is why the file is under version control rather than in a sandbox.

## 13. Where this queue belongs

This file sits at `lo/GC/04_assets/planning/SIDEQUESTS.md`, and four of its entries — the three project set-ups and the anonymise sweep — are not GC work. Brian deferred the question on 14 August rather than deciding it, so it is recorded here rather than left in a chat.

Deciding it means moving the file to a repository-level planning directory and repointing root `CLAUDE.md` 3.B and this file's own preamble, or leaving it and accepting that a GC path holds the whole repository's queue. Take it together with entry 8, which asks the same question about `unwrap.py`, since both turn on whether a repository-level home is opened at all.

Detail: none needed beyond this entry.

## 15. Feed the Thai GC hyphenation candidates into the SC and SJ typesetting dictionaries

Thai running text has no word spaces, so the Typst pipeline has to be told where a long word may break. Both Thai projects do this with `04_assets/template/dictionary.typ`, and the two files are separate copies of the same mechanism at very different stages: SJ carries 457 entries and SC carries 92.

The Thai printed edition of GC supplies 133 more, taken from the places its own typesetter chose to break a word. They are in `th/GC/04_assets/editions/print/HYPHEN-CANDIDATES.tsv`, one per line, giving the break as `คริสต-จักร`, the joined word, how often the print breaks it, how often the word occurs unbroken elsewhere in the book, the first page it appears on, and a confidence note. Converting a row to an entry is mechanical: `คริสต-จักร` becomes `(word: "คริสตจักร", parts: ("คริสต", "จักร"))`.

Only 17 of the 133 are already in SJ and 5 in SC, so this roughly doubles SC's dictionary.

Two things need judgment. 125 rows are confirmed by the word appearing unbroken elsewhere in the book, but eight occur once only and their boundary was supplied by a reader rather than by evidence: อาชญา-กรรม, นักขัต-ฤกษ์, คริสตธรรม-กิตติคุณ, อสังหา-ริมทรัพย์, วิทเทม-บาก, พระราช-ชนนี, กรีน-แลนด์ and คอนเนต-ทิกัต. Those eight want a Thai reader before they go in. And the existing entries often break a word into every syllable, as `("พระ", "วิญ", "ญาณ", "บริ", "สุทธิ์")`, where these rows give a single morpheme boundary; settle whether the two styles coexist or whether the new rows should be broken further.

The larger question the quest should answer is whether the two projects keep separate dictionaries at all. Hyphenation is a fact about Thai words rather than about a book, so a shared file with each project importing it would stop SC and SJ diverging, and would give SC the benefit of SJ's 457 entries at once.

Order matters here. SC goes to print first and has a worktree already started, so SC is where the work lands and is proved. SJ has the larger dictionary and is the better source to merge from.

Detail: none written; this entry is the whole brief. `gc_th_hyphens.py` in `th/GC/04_assets/scripts/` is what produced the file and shows how each boundary was decided. Small if the two dictionaries stay separate, medium if they are merged.

## 17. Rework the glossary system: one glossary per language, with book-specific overlays

Brian's direction of 23 August: what the GC governing files have become is not working, and the replacement has to serve every project in each language, with more projects lining up. One glossary per language holds the terms its books share; each book carries only its own differences on top; a rule is tight where the term is genuinely fixed, such as a proper noun or a closed term family, and loose where literary judgment in the paragraph decides; and the part an agent searches stays light enough to load on every dispatch, while the history and evidence for deep dives live beside it rather than inside it. The Lao version is built first, on GC, and then used as the model for the Thai projects.

Two things fold in. The glossary's sections are numbered from 10 — `## 10. Lao Spelling Glossary`, `## 11. Lao Proper Noun Glossary (GC)`, `## 12. Lao Compound Word-Order Pairs (GC)` in `lo/GC/04_assets/translation_profile/GC-glossary.txt` — a numbering left over from a structure that no longer exists, and the rework renumbers it. And the QA3 record under `lo/GC/04_assets/qa3/`, which gives Fable's in-context verdict on every change QA1 and QA2 made, is the evidence the rework reads before it keeps, loosens or drops any rule the GC runs wrote; every DECIDED, closed or ruled label in the current files is re-examined against that record rather than carried over, because many of those labels were an agent's extrapolation and not a ruling.

Entry 7 (governing-file size reduction) is absorbed by this, and entry 3 (anonymise) runs alongside it; settle the order when the rework is scheduled.

Detail: none written yet; this entry is the whole brief. Large; Fable for the design.

QA3 findings for the rework, one line per chapter as they land:

GC28 {GC 489.3} — "so many professed Christians" reads ຜູ້ທີ່ອ້າງວ່າເປັນຄຣິສຕຽນ, identical to GC36's rendering of the identical English phrase, and ອ້າງວ່າເປັນ marks a professed or claimed identity at 32 corpus sites; no row governs "professed", and the rework decides whether one is wanted.

GC29 {GC 503.3} — no row exists for "the Lord of hosts": ອົງຊົງຣິດອຳນາດຍິ່ງໃຫຍ່ carries three English heads across 14 sites in 8 chapters — "the Most High", "Power", and, with ພຣະເຈົ້າຢາເວ or ອົງພຣະຜູ້ເປັນເຈົ້າ prefixed, "the LORD of hosts" — and ຈອມໂຍທາ appears nowhere in the book; a row fixing the full form for "Lord of hosts" and leaving the bare form to "the Most High" would have prevented the QA3 marker at this site.

GC30 {GC 505.2} — no row governs the apostasy family: ການປະຖິ້ມຄວາມເຊື່ອ stands at 15 sites across ten chapters, ຜູ້ປະຖິ້ມຄວາມເຊື່ອ at GC36 and QA2's ຜູ້ທີ່ປະຖິ້ມຄວາມເຊື່ອ at GC30; the rework decides whether a row is wanted and which agent-noun form it fixes.

GC32 {GC 529.1} — a second attestation for the "Lord of hosts" head the GC29 line above proposes: the English source uses the title in nine chapters (GC01, 08, 24, 27, 29, 32, 39, 40, 42) while ຈອມໂຍທາ has zero hits in the Lao book, and at {GC 529.1} the narrator's added attribution renders it with the short title ອົງພຣະຜູ້ເປັນເຈົ້າ, judged STANDS in its paragraph; every site shortens the title independently because no row governs it.

GC35 {GC 578.3} — no row governs "the Old World": QA3 marker #4 proposes reverting ທະວີບເກົ່າ, a calque Lao does not have, to ທະວີບເອີຣົບ; {GC 573.1} renders "the Old World" as ເອີຣົບ in pre-QA and current text alike and GC25 {GC 440.1} expands the phrase to named continents, so the body text never uses the calque, and the rework decides whether a row is wanted.

