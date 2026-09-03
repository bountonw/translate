# SC pre-publication rounds — conductor

This file governs work on the Thai translation of *Steps to Christ* in th/SC. It is not loaded automatically; read it in full before running any part of this procedure. The repository root CLAUDE.md governs reporting, register, Thai text handling and concurrency, and is not restated here.

## 1. Trigger

1.A. "pre SCNN" — run the pre-processing round of section 3 on a raw chapter.
1.B. "QA1 SCNN" and "QA2 SCNN" — the whole-book rounds, run with the section 3 procedure and the round name in every dispatch. QA1 audits the facts and accuracy of every assertion against the English; QA2 runs after QA1's resolutions have landed and the glossary exists, and edits for readability, flow, understanding and the reader experience. Ruled by the translator on 16 August.
1.C. "check SCNN" — the translator has finished resolving markers; run the post-resolution sweep of section 4.
1.D. "terms SCNN [SCNN ...]" — dispatch th-glossary-miner over the named chapters' English sources to find the terms they need and every existing rendering in th/PP and finished SC, then relay the results to the translator in adjudication chunks of 15 heads; adjudicated rows go into the section 2.C governing files.
1.E. A term or corpus question — answer it yourself with grep over th/PP and th/SC, copying every Thai form out of a file and never retyping one. There is no Thai formfind script yet, so group raw matches by their surrounding words before quoting a count, because a short form matches across word boundaries.
1.F. Anything else — ask rather than guess.

## 2. Paths

2.A. Chapter under work: chapters live in th/SC/01_raw, th/SC/02_edit or th/SC/03_public depending on maturity, so confirm the stage with ls rather than assuming. SC12 and SC13 are in 01_raw.
2.B. English source: th/SC/00_source/SCNN_en.md, anchored with "## {SC ###.#}" headings.
2.C. Governing files, shared by every Thai project: th/assets/translation_profile/thai-glossary.txt and thai-profile.txt. Both are being built — a row enters only after the translator adjudicates it from a mining chunk — so while they are thin, term-consistency evidence still comes from grepping the finished Thai translations: th/PP (03_public plus PP31–43 in 02_edit), th/MB (published), th/SJ (03_public, no English source), and the finished SC chapters. Part 1 of lo/assets/translation_profile/profile.txt is the language-agnostic translation philosophy and binds this project; every later part of that file is Lao-only.
2.D. Session outputs: ~/claude-sandbox/sc-audit/
2.E. Scripts: th/SC/04_assets/scripts/, invoked by that exact relative path from the repository root so permission allow-rules match. Nothing there yet belongs to these rounds.

## 3. Pre round procedure

3.A. Preflight. Confirm 2.A and 2.B exist for the chapter. If the chapter already contains [[ markers, stop and say which numbers remain. Check cleanliness with git status --short -- th/SC, read per root section 4: your chapter's file must be unmodified, another chapter's file is never a reason to stop. Do not read the chapter body into your own context; grep only.
3.B. Size and split exactly as the GC rule: wc -w on the English source, batch count is that word count divided by 2200 rounded up, a chapter under 2700 English words is one batch, cut at anchors so no remainder piles onto the last batch. State the split and proceed without waiting for approval.
3.C. Dispatch sc-batch-auditor per batch, sequentially, never in parallel: marker numbering depends on order. Each dispatch states chapter NN, ref range, starting marker number, round "pre", and whether it is the first batch. The next batch's starting number is the previous batch's reported last number plus one; a batch that wrote nothing leaves the number unchanged.
3.D. After the last batch, check the run yourself — there is no run-check agent yet. Grep the chapter for unbalanced or malformed [[ ]] markers, confirm the numbering is sequential with no gaps or repeats, and confirm with git status that nothing under th/SC changed except the chapter. The chapter's diff legitimately holds three kinds of change — markers, the silent citation conversions of 5.E, and the header repair of 5.F — and anything else is a failure to report, never to repair silently.
3.E. Report per the root CLAUDE.md report shape. The reference mark is the {SC ###.#} anchor plus the marker number. Report the counts by class, every DECIDE, and any item whose effect reaches past its own site; a decision confined to one marker is settled at the cursor and is not repeated in the report.

## 4. Post-resolution sweep ("check SCNN")

4.A. Grep the chapter for [[ first; standing markers end the check, so name their numbers and stop.
4.B. When the chapter is clear of markers, sweep for what resolution leaves behind: choice-parentheses still in the body text, Thai digits (U+0E50–U+0E59), zero-width or other invisible characters, unbalanced quotation marks, and doubled spaces. Report each find with its anchor. A choice-parenthesis the translator has ruled to stand for the editors is reported as a NOTE naming that ruling, never as a defect. A clean sweep means the chapter is ready to upload to Google Docs.

## 5. Rules

5.A. You orchestrate; agents work. Do not audit paragraphs or edit the chapter yourself. A run's only repo edit is markers in the chapter file; every other artifact goes to ~/claude-sandbox/sc-audit/.
5.B. Chapter files are Typst. Each paragraph carries a "// {SC ###.#}" comment above it and an "#EGW[\{SC ###.#\}]" tag at its end; footnotes are inline "#footnote[...]". Reference prose by anchor, never by line number. A chapter holding markers must not be added to book.typ, because markers are not Typst and will not compile.
5.C. Thai text rules. Western digits only, per root 5.A. No invisible characters, per root 5.B — the Thai corpus carries none and Typst does its own Thai line breaking. Never transliterate, per root 5.C. Thai sentences do not close with a period and questions usually carry no question mark; spaces mark phrase and sentence boundaries. Thai does not space around และ the way Lao spaces its conjunctions: และ stays closed on both sides unless the clause it joins is long. Ruled by the translator on 18 August. None of the Lao punctuation rules in lo/GC/CLAUDE.md section 5 carries over, and gc_punctcheck.py must not be run on Thai files.
5.D. Parentheses in a raw or edit-stage chapter are the translator's own unresolved word choices: (A/B) offers alternatives, (word) marks a tentative word or phrase. Resolving every one is pre-round work, never something to leave standing, except where the translator rules that a specific choice goes to the editors — that parenthesis stands for the round and travels to Google Docs. Parentheses holding a scripture citation in the finished chapters are ordinary text, not choices.
5.E. Scripture citations, ruled by the translator on 16 August. The book is migrating citations from footnotes to inline: a citation sits in parentheses wherever it fits the flow of the sentence, sometimes at the paragraph end; where a parenthesis would break the flow it is worked into the prose ("as ยอห์น 3:16 says...") or left as a footnote. The default Bible version is THSV — an unlabelled citation means THSV, so a THSV label is redundant. The mechanical footnote-to-inline conversion is made silently with no marker, because the translator cherry-picks from the diff; only a genuine question of placement or flow gets a marker.
5.F. Header repair. The raw chapters lack the #import and #show: apply-styles lines every edit-stage chapter carries; the first batch of a pre round inserts them silently, matching the 02_edit shape with proofing: true and the run date.
5.G. Line breaking is never fixed in a manuscript. Thai break points live centrally in th/SC/04_assets/template/dictionary.typ — protected words and soft-hyphen hints applied at typeset time — so manuscripts stay free of soft hyphens and a bad break is fixed by a dictionary entry. th/SJ carries the most developed template and dictionary and is the model when SC's typesetting is brought up to date; that work is pending, belongs to typesetting rather than to these rounds, and this line is the standing note of it.
5.H. Both agents carry their model and effort in their own definitions (Opus at xhigh for the auditor, Sonnet at medium for the miner), so name the agent in the dispatch and do not override either.
5.I. Context you load is the dominant cost of a run. Grep rather than read, pass an agent what you already know, and gather corpus evidence as lines, never as whole files.

## 6. Google Docs loop

6.A. The translator's editor and reviewers work in Google Docs while the repository stays authoritative. The agreed design is th/SC/04_assets/planning/gdocs-workflow.md; none of it is built yet, and until it is, the translator uploads a chapter by hand after the section 4 sweep passes.

## 7. Reporting specifics

7.A. The root CLAUDE.md report shape governs; in detail blocks the TH: label replaces LO:.
7.B. Front the decision. A DECIDE detail block opens with the decision to be made and the recommendation in its first sentence — the reader decides at a sprint — and every labelled part (ISSUE, FIX1, FIX2) is separated from the next by a blank line, never run together into one block of text.
7.C. In the summary list, bold each line's number and label — as in **1. DECIDE** — so the eye can jump down the list.
