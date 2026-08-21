# Side quests — the queue

Work that is agreed but not scheduled, in the order it will be done. When Brian asks how many are queued and in what order, this file is the answer and no agent answers from memory.

It lives under `04_assets/planning/` for two reasons. Every numbered-stage assets directory is excluded from the textlint and remark checks, and a queue has no paragraph anchors to satisfy the reference-code rule with. And the root of `04_assets` is swept periodically, so a document meant to last needs a named subdirectory of its own. Most entries are GC work; where one reaches another project, its own text says so.

Rules for keeping it. An issue he defers rather than decides is added here in the same reply that defers it, never left in a chat. An entry is deleted when the work is finished, not marked done, because a finished quest is in the git history. Each entry says what the job is, where its detail lives, and roughly how big it is, and nothing else — the reasoning belongs in the detail file.

## 1. Rehash the pope as Vicar of Christ and as God's representative

Revisit how the Lao GC renders the pope's claimed title, and be ready to reverse the ruling of 19 August rather than defend it. The Thai GC uses ตัวแทน, the cognate of Lao ຕົວແທນ, which is the word that ruling moved the title away from; if the Thai is right the Lao should follow it and the day's changes are undone.

In scope: the six sites moved from ຕົວແທນ to ຜູ້ແທນ that day, {GC 51.3}, {GC 53.2}, {GC 55.1} and {GC 59.1} in GC03 and {GC 101.1} and {GC 102.1} in GC06; the two emissary sites at {GC 62.4} in GC04, which moved the other way; the Vicar of Christ, Legate and Deputy rows of `lo/GC/04_assets/translation_profile/GC-glossary.txt`; and the sites deliberately left on ຕົວແທນ, which are {GC 50.2} and the first instance at {GC 53.2}, {GC 92.2}, {GC 567.3} and {GC 591.1}.

One obstacle comes first: the Thai GC text is not in this repository, since `th/GC` holds no files, so the Thai evidence has to be supplied or pointed to before any comparison can be made.

Detail: the 19 August litigation and its evidence sit in `lo/GC/04_assets/history/GC-glossary-history.md` under the Vicar of Christ and Legate heads. Medium; Fable for the language judgment.

## 2. Encode the 14 August rulings from the GC 421.3 litigation

Four rulings need writing into the instruction files where agents will see them; Opus or Sonnet work, small. (a) Glossary and corpus attestation support a rendering but never decide it — sentence meaning and paragraph flow rule. (b) In sentence-litigation mode the draft goes above the old paragraph in the manuscript and the old text stays for comparison until Brian finalizes. (c) A translator-added naming gloss stays where the quoted Bible versions use different terms for the same referent. (d) A Fable session works translation issues only; updates like these go to the top of this queue for a smaller model.

Detail: none written; this entry is the whole brief.

## 3. Anonymise the instruction files

Remove the name Brian in every form from the instruction files and replace it with "the user" or another generic term. The name appears 78 times across the eight core instruction files — root `CLAUDE.md`, `lo/GC/CLAUDE.md`, the five `gc-*` agent definitions and `.claude/commands/gc.md` — and about 25 more times in the audit scripts, the governing files, this queue and `04_assets/history/`. The glossary part is already done: all 32 occurrences were removed from `lo/GC/04_assets/translation_profile/GC-glossary.txt` on 21 August, leaving the rest of each sentence intact.

The count understates the work. Those files also carry roughly 54 third-person pronouns — he, his, him, himself — that refer to the same person and read wrongly the moment the noun becomes generic, so a find-and-replace on the name alone leaves the prose broken.

The replacement term was decided on 16 August: "the translator". The new th/SC instruction files already use it and avoid third-person pronouns entirely, which is the pattern for the sweep. The sweep itself stays queued and does not run until scheduled.

Two boundaries to settle as part of the quest. The translator credit in `th/LBF/assets/LBF00_copyright.md` is a real byline and not an instruction, so it is presumably out of scope. The saved memories under `~/.claude/projects/` use the name throughout and are not repository files, so whether they are in scope is a separate decision.

Detail: none written yet.

## 4. Wire the forbidden-terms list into the audit pre-pass

Two lists of known-wrong spellings exist and neither knows about the other. `.tooling/forbidden_terms/lao.txt` holds 313 terms in `forbidden # correct` form and drives the textlint CI job; section 10 of `lo/GC/04_assets/translation_profile/GC-glossary.txt` holds 30 forms and drives `gc_termcheck.py` and `gc_resolvecheck.py`. So a batch auditor can pass a chapter that CI then fails, which is how ຍຶດເອົາ reached a commit in GC12 and came back as a lint error.

Make the audit scripts read the linter's list as well as section 10, so a forbidden term is caught at the pre-pass rather than after the push. Decide as part of the quest whether the two lists should merge, and whether section 10 rows that are context-dependent can live in the linter's flat format at all. There is a Thai list beside the Lao one, `.tooling/forbidden_terms/`, so whatever is built should serve both.

Detail: none written yet. `.tooling/textlint/rules/lo.js` line 6 shows how the list is loaded.

## 5. Footnote author-gloss sweep

Every author cited in a footnote carries the English name in parentheses after the Lao form, so a Lao reader can pronounce it and also look it up: `[^19]: ມາຕິນ (Martyn), ເຫຼັ້ມ 5, ໜ້າ 417.`

Brian ranked this above everything else in the queue. 240 of 272 sites remain across 31 chapters; 170 resolve from existing glossary rows and 102 need the English source and probably a new proper-noun row. Done so far: 14 Martyn sites, 15 Bliss sites in GC18, GC21 and GC22, and 3 Wolff journal titles in GC20.

Detail: `~/claude-sandbox/gc-audit/footnote-gloss-sweep-prompt.md`, with the per-chapter worklist beside it in `footnote-gloss-worklist.md`.

## 6. Dictionary sync check when a spelling changes

Confirm that `lo/assets/dictionaries/main.txt` is updated whenever a spelling decision changes a form in the manuscripts, and find out what currently keeps the two in step. The Stephen sweep touched the dictionary by hand, which suggests nothing does it automatically.

Open questions for the quest itself: which decisions are supposed to reach the dictionary, whether the line-break entries are the only affected kind, and whether a script should check the two against each other the way `gc_govcheck.py` checks the governing files.

Detail: none written yet. Small to size, unknown to fix.

## 7. Governing-file size reduction

The three files under `lo/GC/04_assets/translation_profile/` are loaded by every agent on every dispatch. Move the decision history out of them into `lo/GC/04_assets/history/`, keyed by the English head, so the rules stay and the evidence stops being paid for on every dispatch.

Scope after Brian's rulings of 13 August: 17 oversized `GC-open-terms.md` entries and 24 glossary rows. The twelve sense-selection rows in the plan's section 6 are not touched at all, and a deferred entry stays at full size until it is adjudicated. `gc_govcheck.py` and its tests already exist and prove a pass loses nothing.

The largest single case measured so far is the Clergy entry of `GC-open-terms.md`, which stands at 806 words against the 15-word limit set by item 4.H of `lo/GC/CLAUDE.md`, in a file of 5,333 words that every agent loads on every dispatch. The GC38 audit of 21 August measured it and Brian deferred the cut, expecting to adjudicate it around Monday 24 August; the entry records a decision it calls closed at GC 15, so what has to stay is the three-way mapping the row states and what goes to the clergy head of `lo/GC/04_assets/history/GC-glossary-history.md` is the site-by-site reasoning behind it.

Detail: `~/claude-sandbox/gc-audit/glossary-reduction-plan.md`.

## 8. ລົບລ້າງ against ລຶບລ້າງ — normalise, or leave both

Both spellings are accurate and the editors want both, which is the ruling of GC 15 and stands. The open question is whether the book should normalise to one form anyway. Brian never read the argument for normalising when it was first put, so it was held rather than closed.

The evidence is already gathered: corpus counts are ລຶບລ້າງ 78 against ລົບລ້າງ 16, the two are not distinguished by sense, GC 287.1 carries both a sentence apart, and the large count is inflated by the fixed phrase in the Day of Atonement glossary row. Not to be raised in a chapter audit meanwhile.

Detail: the `NOTE-SPELL ລົບລ້າງ and ລຶບລ້າງ` entry in `lo/GC/04_assets/translation_profile/GC-open-terms.md`.

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

2. In `lo/assets/dictionaries/common-spelling.txt` the left column is the correct form and the right lists the wrong variants, notwithstanding the file's own header, which reads `# bad | good` and is stale. Its row `ບົກຜ່ອງ | ບົກຜ່ອງ` carries the same form on both sides and does nothing.

3. Two Lao forbidden-terms lists exist and they disagree. Use `.tooling/forbidden_terms/lao.txt` in this repository, which holds 313 rows in `wrong # correct` form, drives the textlint job, and agrees with the published GC chapters at every row. Never use `markdownlint/forbidden_terms/lao.txt` in the `translate-tooling` repository: it supplies no corrections and four of its entries flag the correct spelling rather than the wrong one, so a round driven by it changes ບົກຜ່ອງ, ປັດຈຸບັນ, ຫຸ້ນສ່ວນ and ຫຼີກລ່ຽງ away from the form GC uses.

4. Lao running text has no word spaces, so a word-boundary regex such as `(?<![\u0e80-\u0eff])` matches almost nothing and a scan built on one reports a clean file when it is not. Match substrings and confirm each hit against a dictionary segmentation.

5. Correct the whole word, never a bare syllable. This is Brian's ruling of 21 August, and it earned itself: ໜຸນ sat in three different words, one of which needed two syllables changed to reach ສະໜັບສະໜູນ, so a syllable swap would have left a form that is still wrong and no longer flagged.

6. A correction whose wrong form is contained in its correct form will fire inside words that are already right. Applying ຟີເລໂມ to ຟີເລໂມນ turned 19 correct instances into ຟີເລໂມນນ. Guard such a pair with a lookaround, and check the count of the correct form before and after.

7. A form that GC contains is not a misspelling. Rejecting any proposal whose wrong side appears in GC is what stopped ວາມ being rewritten to ຄວາມ at 3,843 sites, where ວາມ was only the tail of ຄວາມ left by a failed segmentation.

Detail: none written; this entry is the whole brief.

## 13. Where this queue belongs

This file sits at `lo/GC/04_assets/planning/SIDEQUESTS.md`, and four of its entries — the three project set-ups and the anonymise sweep — are not GC work. Brian deferred the question on 14 August rather than deciding it, so it is recorded here rather than left in a chat.

Deciding it means moving the file to a repository-level planning directory and repointing root `CLAUDE.md` 3.B and this file's own preamble, or leaving it and accepting that a GC path holds the whole repository's queue. Take it together with entry 8, which asks the same question about `unwrap.py`, since both turn on whether a repository-level home is opened at all.

Detail: none needed beyond this entry.

## 14. Run the deferred term "justification by faith" to a finish

The glossary row was decided on 16 August and written into `lo/GC/04_assets/translation_profile/GC-glossary.txt` as `| Justification by faith | ຄວາມຊອບທຳໂດຍຄວາມເຊື່ອ | Decided 16 August |`, with no exception recorded in it for any chapter. The quest is to grep the corpus for the sites that do not conform and bring them to the row, chapter by chapter, with Brian deciding each.

The inventory is already gathered. The English phrase occurs five times in the book. Two sites already carry the row's word and need nothing: GC 07 at {GC 140.3} reads ຄວາມຊອບທຳໂດຍຄວາມເຊື່ອ, which is where the row's form comes from, and GC 09 at {GC 178.2} reads ມະນຸດສາມາດຮັບການອະໄພບາບ ແລະ ເປັນຄົນຊອບທຳໄດ້ໂດຍຜ່ານພຣະໂລຫິດຂອງພຣະຄຣິສ, using the same word as a verb clause because the English there pairs "forgiveness and justification" and the Lao keeps that pair. Brian confirmed both on 16 August. GC 28 at {GC 483.3} renders the bare noun ຄວາມຊອບທຳ and was checked earlier.

Three sites in GC 14 do not conform and are the substance of the quest: the subheading above {GC 253.2} reads ຄວາມລອດໂດຍທາງຄວາມເຊື່ອ, the main text at {GC 253.2} reads ຄວາມລອດພົ້ນໂດຍທາງຄວາມເຊື່ອ, and {GC 256.3} reads ຄວາມລອດດ້ວຍຄວາມເຊື່ອໃນພຣະໂລຫິດຂອງພຣະຄຣິສ. The argument for changing them is that the English sentence at 253.2 uses justification and salvation as two different words and the Lao gives both ຄວາມລອດ, so Luther's doctrine and Rome's goal end up sharing one name. The corpus supports the split: across the public chapters ຄວາມລອດ occurs 107 times against 112 occurrences of "salvation" in the English, and ຄວາມຊອບທຳ occurs 70 times against 84 of "righteousness". The proposal on the table is ຄວາມຊອບທຳໂດຍຄວາມເຊື່ອ at the subheading and at 253.2, and ຄວາມຊອບທຳໂດຍຄວາມເຊື່ອໃນພຣະໂລຫິດຂອງພຣະຄຣິສ at 256.3. Nothing has been marked in GC 14; the decision is Brian's and the quest begins there.

One correction belongs to this quest as well. The `DEFER-TERM "justification by faith"` entry in `lo/GC/04_assets/translation_profile/GC-open-terms.md` claims the GC 14 sites were DECIDED by Brian, and that claim has no support. The GC 14 run's own proposals file of 10 August ends the entry with "not adjudicated in batch", and the "Brian ruled" sentences first enter the repository in commit 66c183e of 11 August, written by an agent after the run. Strike them when the quest runs, and replace the whole entry with a pointer to the glossary row once GC 14 is settled. That file was modified by another session on 16 August, so it was left untouched then.

Detail: this entry is the whole brief. Small once GC 14 is decided; the corpus grep is one pass.

## 15. Feed the Thai GC hyphenation candidates into the SC and SJ typesetting dictionaries

Thai running text has no word spaces, so the Typst pipeline has to be told where a long word may break. Both Thai projects do this with `04_assets/template/dictionary.typ`, and the two files are separate copies of the same mechanism at very different stages: SJ carries 457 entries and SC carries 92.

The Thai printed edition of GC supplies 133 more, taken from the places its own typesetter chose to break a word. They are in `th/GC/04_assets/editions/print/HYPHEN-CANDIDATES.tsv`, one per line, giving the break as `คริสต-จักร`, the joined word, how often the print breaks it, how often the word occurs unbroken elsewhere in the book, the first page it appears on, and a confidence note. Converting a row to an entry is mechanical: `คริสต-จักร` becomes `(word: "คริสตจักร", parts: ("คริสต", "จักร"))`.

Only 17 of the 133 are already in SJ and 5 in SC, so this roughly doubles SC's dictionary.

Two things need judgment. 125 rows are confirmed by the word appearing unbroken elsewhere in the book, but eight occur once only and their boundary was supplied by a reader rather than by evidence: อาชญา-กรรม, นักขัต-ฤกษ์, คริสตธรรม-กิตติคุณ, อสังหา-ริมทรัพย์, วิทเทม-บาก, พระราช-ชนนี, กรีน-แลนด์ and คอนเนต-ทิกัต. Those eight want a Thai reader before they go in. And the existing entries often break a word into every syllable, as `("พระ", "วิญ", "ญาณ", "บริ", "สุทธิ์")`, where these rows give a single morpheme boundary; settle whether the two styles coexist or whether the new rows should be broken further.

The larger question the quest should answer is whether the two projects keep separate dictionaries at all. Hyphenation is a fact about Thai words rather than about a book, so a shared file with each project importing it would stop SC and SJ diverging, and would give SC the benefit of SJ's 457 entries at once.

Order matters here. SC goes to print first and has a worktree already started, so SC is where the work lands and is proved. SJ has the larger dictionary and is the better source to merge from.

Detail: none written; this entry is the whole brief. `gc_th_hyphens.py` in `th/GC/04_assets/scripts/` is what produced the file and shows how each boundary was decided. Small if the two dictionaries stay separate, medium if they are merged.

## 16. Check the default Bible version's published year

Establish which Lao Bible version the book treats as its default and what year that version was published, so the front matter and any version note can state it. The question arose on 21 August from the ruling that a quotation taken from the book's standard version carries no version label in its citation: the label is omitted precisely because the version is the default, so which version that is has to be recorded somewhere a reader can find it. The version abbreviations already in use across the chapters are the starting inventory.

Detail: none written yet. Small; a lookup and one line of front matter.
