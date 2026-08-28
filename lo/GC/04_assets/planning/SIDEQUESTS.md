# Side quests — the queue

Work that is agreed but not scheduled, in the order it will be done. When Brian asks how many are queued and in what order, this file is the answer and no agent answers from memory.

It lives under `04_assets/planning/` for two reasons. Every numbered-stage assets directory is excluded from the textlint and remark checks, and a queue has no paragraph anchors to satisfy the reference-code rule with. And the root of `04_assets` is swept periodically, so a document meant to last needs a named subdirectory of its own. Most entries are GC work; where one reaches another project, its own text says so.

Rules for keeping it. An issue he defers rather than decides is added here in the same reply that defers it, never left in a chat. An entry is deleted when the work is finished, not marked done, because a finished quest is in the git history. Each entry says what the job is, where its detail lives, and roughly how big it is, and nothing else — the reasoning belongs in the detail file.

## 18. Cut the stale justification-by-faith passage from the GC procedure file

Item 6.G of `lo/GC/CLAUDE.md` carries the three justification-by-faith anchors into the QA3 pass as sites a batch must be told about, and says the entry leaves the queue when its sites are resolved. Those sites were resolved in commit 65c51b93, "QA3 Batch 4", so the instruction has already fired and now names three anchors that need no special handling. Restored entry 14 is about a governing file rather than about manuscript sites, so nothing replaces the passage. Cut it and keep the Vicar of Christ sentence that follows, which is a separate ruling and still stands.

Detail: none needed beyond this entry. Opus or Sonnet work, very small; one passage in one file, written as a single unwrapped line per item 7.A of the root instructions.

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

## 14. Justification by faith — correct the open-terms entry that now contradicts the manuscript

The three GC 14 manuscript sites are settled and are not part of this quest any longer. The subheading above {GC 253.2} reads ລອດພົ້ນໂດຍທາງຄວາມເຊື່ອ, {GC 253.2} reads ຄວາມຊອບທຳໂດຍຄວາມເຊື່ອ, and {GC 256.3} reads ຄວາມຊອບທຳໂດຍທາງຄວາມເຊື່ອໃນພຣະໂລຫິດຂອງພຣະຄຣິສ. All three were changed in commit 65c51b93, "QA3 Batch 4", as marker resolutions inside a batch rather than in a session devoted to this term.

What is outstanding is the `DEFER-TERM "justification by faith"` entry in `lo/GC/04_assets/translation_profile/GC-open-terms.md`, which every agent loads on every dispatch and which now states the opposite of what the chapter says. It reads "DECIDED for GC 14 only — Brian ruled on chapter 14: keep the wording as it stands", and it names the three sites as ຄວາມລອດພົ້ນໂດຍທາງຄວາມເຊື່ອ, ຄວາມລອດໂດຍທາງຄວາມເຊື່ອ and ຄວາມລອດດ້ວຍຄວາມເຊື່ອໃນພຣະໂລຫິດ, none of which the manuscript still carries. It then tells any pre-pass that surfaces those three that it "is looking at a decided site and does not flag them as wrong". An agent reading it today is told to protect wording that no longer exists.

Two things have to be settled before the entry is rewritten, and only Brian settles them. First, whether he ever ruled "keep the wording as it stands" for GC 14: the sentences claiming it first enter the repository in commit 66c183e of 11 August, written by an agent after the run, and the GC 14 run's own proposals file of 10 August ends the entry "not adjudicated in batch". Second, whether the QA3 Batch 4 change supersedes that claimed ruling or simply contradicts an invention. The answer decides whether the entry is corrected or struck outright.

The family question is separate and stays open. The English phrase occurs five times: GC 07 {GC 140.3} reads ຄວາມຊອບທຳໂດຍຄວາມເຊື່ອ, GC 09 {GC 178.2} renders it as a verb clause, GC 14 twice, and GC 28 {GC 483.3} is the bare noun ຄວາມຊອບທຳ. Whether a glossary row is added and which form it carries has never been decided.

Detail: this entry is the whole brief. Small; one governing-file edit once the two questions above are answered.

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

## 17. Rework the glossary system: one glossary per language, with book-specific overlays

Brian's direction of 23 August: what the GC governing files have become is not working, and the replacement has to serve every project in each language, with more projects lining up. One glossary per language holds the terms its books share; each book carries only its own differences on top; a rule is tight where the term is genuinely fixed, such as a proper noun or a closed term family, and loose where literary judgment in the paragraph decides; and the part an agent searches stays light enough to load on every dispatch, while the history and evidence for deep dives live beside it rather than inside it. The Lao version is built first, on GC, and then used as the model for the Thai projects.

Two things fold in. The glossary's sections are numbered from 10 — `## 10. Lao Spelling Glossary`, `## 11. Lao Proper Noun Glossary (GC)`, `## 12. Lao Compound Word-Order Pairs (GC)` in `lo/GC/04_assets/translation_profile/GC-glossary.txt` — a numbering left over from a structure that no longer exists, and the rework renumbers it. And the QA3 record under `lo/GC/04_assets/qa3/`, which gives Fable's in-context verdict on every change QA1 and QA2 made, is the evidence the rework reads before it keeps, loosens or drops any rule the GC runs wrote; every DECIDED, closed or ruled label in the current files is re-examined against that record rather than carried over, because many of those labels were an agent's extrapolation and not a ruling.

Entry 7 (governing-file size reduction) is absorbed by this, and entry 3 (anonymise) runs alongside it; settle the order when the rework is scheduled.

Detail: none written yet; this entry is the whole brief. Large; Fable for the design.

Priority: the papal-emissary/legate/nuncio family and the Vicar of Christ family (entry 1) have never been jointly reviewed with full corpus evidence; the rework should settle both together before either glossary row is marked DECIDED, since both concern how the pope's agents and titles are named and a decision on one constrains the other. Brian's ruling of 26 August.

Ruled, 26 August: the Christendom row (GC-glossary.txt:220) drops its closed list of ten forms. The English word covers three distinct senses depending on what the passage is doing — a historical episode bounded to a place and period (translate the actual geography, which may be Europe alone), a universal doctrinal or prophetic claim (translate the full professing-nations sense), or a general moral statement with no geographic claim (a short paraphrase is fine) — and the row should instruct the reader to establish which of the three a given paragraph is doing before choosing a form, rather than picking from a fixed list. Evidence: {GC 71.2} in GC04 names Europe specifically because the passage is entirely about the medieval Waldensian mission, which never reached beyond Europe; {GC 382.2} and {GC 450.1} make universal doctrinal claims and need the full-scope sense; {GC 162.3} and {GC 525.3} are general statements the corpus already renders as "all Christians" and "churches in general" with no loss of meaning.

QA3 findings for the rework, one line per chapter as they land:

Council row against the French Revolution rows — the Council row at `lo/GC/04_assets/translation_profile/GC-glossary.txt:96` was given a usage note on 28 August saying ປະຊຸມສະພາ and ສະພາ serve a church body or a civil one either way, while the National Convention and National Assembly rows added the same day rule ກອງປະຊຸມແຫ່ງຊາດ for the French bodies and forbid ສະພາ there; the two agree only because a named-body row is more specific than a general one, and the rework should state that precedence in one of the two places rather than leave an agent to infer it.

National Assembly and National Convention rows — both English heads were enforced in the committed glossary and are not enforced in the working tree, because the French Revolution rows written on 28 August carry their rulings in Notes cells with no [CHECK] and no [FLAG], and `gc_termcheck.py` treats an untagged row as silent; the rework should decide whether the two rows are tagged, since the NOT ສະພາ one of them states is a prohibition no script can currently catch.

GC05 {GC 83.2} — the Religious order row at GC-glossary.txt:27 cites GC 83.2 for ຄະນະນັກບວດ, but the QA2 change accepted at that anchor reduced the form there to ຄະນະຂອງຕົນ, so the citation is stale and the rework should repoint or drop it.

GC03 {GC 50.2} — the Bishop of Rome row at GC-glossary.txt:33 does not describe the book's first bishop-of-Rome site: {GC 50.2} reads ຜູ້ປົກຄອງຄຣິສຕະຈັກແຫ່ງນະຄອນໂຣມ, untouched by QA1 and QA2 and clear as it stands, so the rework should widen the row or record this site as a licensed exception.

GC04 {GC 77.1} and {GC 77.2} — "papal bull" reads ຄຳປະກາດ in GC04 (ອອກຄຳປະກາດ at {GC 77.1}, ຄຳປະກາດຂອງສັນຕະປາປາ at {GC 77.2}) while the row at GC-glossary.txt:133 prescribes ໃບປະກາດພິເສດ, which appears in GC06 (1 site), GC07 (3), GC08 (2) and GC12 (1); QA3 judged the GC04 form STANDS inside its own chapter, so the rework decides whether GC04 joins the ໃບປະກາດພິເສດ chapters or the row licenses both.

GC05 {GC 87.2} — the corpus count taken while judging the "gospel doctor" change: ຂ່າວປະເສີດ 227 occurrences against ພຣະກິດຕິຄຸນ 4, the residual four in GC07, GC09, GC15 and GC38; the Gospel row already prescribes ຂ່າວປະເສີດ, so the rework decides whether the four residual sites change.

GC05 {GC 92.2} — the generic-representative row at GC-glossary.txt:35 cites GC 92.2 as its only site; QA3 marker #4 proposes moving that site to ຜູ້ແທນ, so if the translator accepts it the row loses its citation and rows 34–35 can collapse into one, and if he keeps ຕົວແທນ the row is confirmed with its one deliberate site.

GC07 {GC 125.1} and {GC 142.2} — the decretal row at GC-glossary.txt:40 prescribes ຄຳຕັດສິນຂອງສັນຕະປາປາ / ຄຳຕັດສິນ with NOT ຄຳປະກາດ and cites exactly these two sites; QA3 reverted {GC 125.1} to ຄຳປະກາດ because that sentence announces a promised pardon rather than a tribunal verdict, and upheld ຄຳຕັດສິນຂອງສັນຕະປາປາ at {GC 142.2}, where the decretals burn in a list of legal instruments beside the bull ໃບປະກາດພິເສດ and ຄຳປະກາດ would collapse the two list members into each other; the two cited sites legitimately differ, so the rework should replace the row's single prescription and its NOT with passage-led guidance.

GC06 {GC 103.2} — within the countries-professing sense of Christendom the corpus carries two forms of one phrase: the ມີການ form (ທຸກປະເທດທີ່ມີການນັບຖືສາສະໜາຄຣິສ) at 8 sites in GC05, 06, 07, 11, 12 and 25, and the bare form (ທຸກປະເທດທີ່ນັບຖືສາສະໜາຄຣິສ) at 6 sites in GC06, 08, 09, 12, 35 and 39, with {GC 103.2} carrying both in one paragraph; QA3 judged the variation below marker threshold everywhere it met it except {GC 130.2} in GC07, where marker #3 rewords the long form on that paragraph's own argument, so the rework decides whether the form unifies within the sense.

GC06 {GC 108.2} and {GC 116.3} — two below-threshold reservations against ເຈົ້າແຂວງ on the Prince of the empire row at GC-glossary.txt:222: the word carries a modern provincial-governor ring for a mediaeval hereditary prince, though QA3 judged both sites STANDS, and GC08 judged six further sites STANDS on the same row resting on the chapter's {GC 145.1} footnote; evidence for the rework when it weighs the princes family, with no change proposed by QA3 itself.

GC13 {GC 243.2} — the Church Father (early) row at GC-glossary.txt:143 still lists GC 243.2 among five sites pending correction to the long form, but the current text there carries the long form ຄຳສອນຂອງບັນດານັກຂຽນຄຣິສຕຽນຍຸກເລີ່ມຕົ້ນ and grep finds the same long form in GC14, GC18 and GC26, covering three more of the five; the manuscript is right and the row's bookkeeping is behind it, so the rework should refresh or drop the pending list.

GC09 friar sites — the Friar row at GC-glossary.txt:26 prescribes ພຣະກາໂຕລິກ, but every friar site QA2 changed in GC09 now reads ນັກບວດ ({GC 172.1}, {GC 172.2}, twice at {GC 178.4}), all judged STANDS in their paragraphs, while the Jesuits row still states ພວກພຣະກາໂຕລິກ renders monks and friars as persons at fifteen sites elsewhere; the row and the practice disagree, so the rework decides which word the Friar row carries.

GC11 {GC 200.1} — "the liberties of Christendom" now reads ເສລີພາບໃນດິນແດນທີ່ມີການນັບຖືສາສະໜາຄຣິສ, a ດິນແດນ-headed bounded-lands form the Christendom row at GC-glossary.txt:220 does not list among its ten; QA3 judged it right at this site because Wylie argues about the lands Rome then ruled, where the pre-QA ຄຣິສຕຽນທົ່ວໂລກ claimed every Christian on earth, so the rework can take the form as a further attestation within the bounded-place sense.

GC14 {GC 249.1} — the Church Father row at GC-glossary.txt:143 still lists GC 249.1 among the sites pending correction to the long form, but the chapter carries the long form ບັນດານັກຂຽນຄຣິສຕຽນຍຸກເລີ່ມຕົ້ນ at that anchor and QA3 judged it STANDS in the passage; strike GC 249.1 from the pending list, a second confirmation after the GC13 line above that the list is behind the manuscript.

GC18 {GC 335.3} — the same Church Father row's pending list is stale on this site too: the chapter carries the long form ບັນດານັກຂຽນຄຣິສຕຽນຍຸກເລີ່ມຕົ້ນ at {GC 335.3} and QA3 judged it STANDS from the paragraph with the candidate drill ranked inline in the record, so the pending list is now confirmed behind the manuscript at GC13, GC14 and GC18.

GC15 {GC 277.2} — QA3 marker #1 proposed reverting the glossary-driven ຕົວແທນຂອງສັນຕະປາປາ back to the pre-QA ທູດຂອງສັນຕະປາປາ for "a papal nuncio", judging from the passage that the envoy word names the office and the generic representative word does not; Brian applied the revert on 26 August and {GC 277.2} now reads ທູດຂອງສັນຕະປາປາ, evidence for the joint papal-emissary/legate/nuncio review this entry already lists as its priority.

GC11 {GC 198.2} — deferred by Brian on 26 August to the glossary rework: the quoted taunt "The Turks are better than the Lutherans" reads ຊາວມຸດສະລິມ twice where the speaker said Turks, while ຊາວເທີກ stands at {GC 197.2} one page earlier and in GC18 and GC20, and ຊາວມຸດສະລິມ also stands at GC06 {GC 114.2}; the rework settles the Turk/Muslim family and whether the {GC 198.2} generalization stays.

GC17 {GC 304.2} — the Morocco row's comment at lo/GC/04_assets/translation_profile/GC-glossary.txt:545 reads "[CHECK] GC 304.2, where the Lao supplies ເມືອງຫຼວງຂອງ for Ellen White's city of Morocco" and goes stale however GC17 marker #1 resolves, since Brian reopened the site with a 7/3/1 drill on 26 August and accepted ທີ່ຕັ້ງຢູ່ບໍ່ໄກຈາກເມືອງມາຣາເກັສໃນປະເທດໂມຣັອກໂຄ on 28 August with a new footnote 12 on the historical name Marocco City; the rework rewrites the comment to record that outcome and adds a Marrakesh proper-noun row (ມາຣາເກັສ, gloss Marrakesh, coined 26 August after ຮັສ and ເອີຣັສມາສ).

GC21 {GC 382.2} — the Christendom row at lo/GC/04_assets/translation_profile/GC-glossary.txt:220 carries the note "NOT ເອີຣົບ (scope narrowing)"; QA3 marker #1 read the site as bounded history and proposed the pre-QA ກະສັດທັງຫຼາຍຂອງເອີຣົບ, and Brian resolved it on 28 August to ກະສັດທັງຫຼາຍໃນປະເທດທີ່ນັບຖືສາສະໜາຄຣິສ, the countries-professing form, so the site no longer argues for ເອີຣົບ itself; the row's NOT ເອີຣົບ still wants the three-sense qualification, since {GC 71.2} legitimately names Europe under the bounded sense.

GC22 {GC 398.2} — the Midnight Cry row at GC-glossary.txt:124 carries both [CHECK] and "DECIDED at GC 22" without naming who decided; QA3 upheld ສຽງຮ້ອງປະກາດຍາມທ່ຽງຄືນ at all five chapter sites from the passage and from the translator's own unchanged {GC 400.1}, so the rework can close the row on that evidence rather than on the unattributed DECIDED.

GC25 {GC 448.2} — the Church Father (early) row at GC-glossary.txt:143 still lists GC 448.2 as "NOT yet corrected", but QA2 corrected it to ບັນດານັກຂຽນຄຣິສຕຽນໃນສະຕະວັດຕົ້ນໆ and QA3 judged it STANDS; strike the site from the pending list, and note the form differs from the ຍຸກເລີ່ມຕົ້ນ long form the other chapters carry.

GC26 {GC 455.1} — the same Church Father row's pending list is stale here too: the manuscript reads ບັນດານັກຂຽນຄຣິສຕຽນຍຸກເລີ່ມຕົ້ນ, the long form the row prescribes, so GC 455.1 joins GC13, GC14 and GC18 as confirmation the list is behind the manuscript.

GC28 {GC 489.3} — the Day of Atonement row at GC-glossary.txt:68 lists four forms and says mark any other, but ວັນແຫ່ງການລຶບລ້າງຄວາມບາບອັນຍິ່ງໃຫຍ່ for "the great day of atonement" stands there as a plain expansion of the second listed form with the row's own ອັນຍິ່ງໃຫຍ່ for "great"; the row should admit the ແຫ່ງການ shape or say the expansion is out.

GC28 {GC 489.3} — "so many professed Christians" reads ຜູ້ທີ່ອ້າງວ່າເປັນຄຣິສຕຽນ, identical to GC36's rendering of the identical English phrase, and ອ້າງວ່າເປັນ marks a professed or claimed identity at 32 corpus sites; no row governs "professed", and the rework decides whether one is wanted.

GC29 {GC 503.3} — no row exists for "the Lord of hosts": ອົງຊົງຣິດອຳນາດຍິ່ງໃຫຍ່ carries three English heads across 14 sites in 8 chapters — "the Most High", "Power", and, with ພຣະເຈົ້າຢາເວ or ອົງພຣະຜູ້ເປັນເຈົ້າ prefixed, "the LORD of hosts" — and ຈອມໂຍທາ appears nowhere in the book; a row fixing the full form for "Lord of hosts" and leaving the bare form to "the Most High" would have prevented the QA3 marker at this site.

GC30 {GC 508.1} — the Christian world row at GC-glossary.txt:221 approves only ວົງການຄຣິສຕຽນ and ໂລກຄຣິສຕຽນ, but ວົງການຄຣິສຕຽນທົ່ວໂລກ stands at GC25, GC30 and GC33 and ວົງການຄຣິສຕຽນທົ່ວໄປ at GC32 and GC42, and the modifier-carrying forms read better than the bare ones where they stand; widen the row.

GC30 {GC 505.2} — no row governs the apostasy family: ການປະຖິ້ມຄວາມເຊື່ອ stands at 15 sites across ten chapters, ຜູ້ປະຖິ້ມຄວາມເຊື່ອ at GC36 and QA2's ຜູ້ທີ່ປະຖິ້ມຄວາມເຊື່ອ at GC30; the rework decides whether a row is wanted and which agent-noun form it fixes.
