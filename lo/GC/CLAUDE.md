# GC audit — conductor

## 1. Trigger

1.A. When Brian names a chapter ("GC17", "run GC13"), run the full chapter procedure in section 3. When he names a term family or corpus question, dispatch gc-term-grep instead. Anything else: ask.
1.B. When Brian says "check GCNN" (or says he has finished resolving), dispatch gc-resolve-check with the chapter number and relay its report verbatim. A PASS means the chapter is clean to commit.

## 2. Paths

2.A. Chapter under audit: lo/GC/03_public/GCNN_lo.md
2.B. English source:      lo/GC/00_source/GCNN_en.md
2.C. Governing files:     lo/GC/04_assets/translation_profile/ (GC-glossary.txt, GC-clergy-fixes.md, GC-open-terms.md)
2.D. Term-check script:   lo/GC/04_assets/scripts/gc_termcheck.py
2.E. Session outputs:     ~/claude-sandbox/gc-audit/
2.F. Introduction files (GC00*) are out of scope unless Brian names them explicitly.
2.G. lo/GC/lookahead_decisions.log belongs to the LaTeX typesetting workflow and is not audit input. Never read it, never cite it.

## 3. Chapter procedure

3.A. Preflight. Confirm 2.A and 2.B exist. If the chapter already contains [[ markers, stop and tell Brian — he resolves markers between runs. Do not read the chapter body into your own context; grep only.
3.B. Size the chapter and split it. Batch size is measured in English words, never in paragraphs: across the book a printed page holds 348 to 380 English words, but anywhere from one to eight paragraphs, so paragraph counts are not a size proxy. Get the English word count with wc -w on the source file and the distinct page numbers by grepping the "## {GC ###.#}" headings. Batch count is the English word count divided by 2000, rounded up; a chapter under 2600 English words runs as one batch. Divide the pages as evenly as that batch count allows, give any remainder to the last batch, and split only at page boundaries — never inside a page. Ranges are stated as full anchors, from the first anchor of the batch's first page to the last anchor of its last page. State the split before the first dispatch and proceed; do not wait for approval.
3.C. Dispatch gc-batch-auditor per batch, SEQUENTIALLY, never in parallel (marker numbering and file appends depend on order). Each dispatch states: chapter NN, ref range, starting marker number, and whether it is the first batch (first batch creates the session files). Next batch's starting number = previous batch's reported last number + 1. A batch that wrote no markers reports a last number one below its starting number; the following batch then keeps that same starting number.
3.D. After the last batch, dispatch gc-run-check with two inputs: the chapter number, and the expected total marker count. The expected total is the last marker number reported by the last batch that wrote any marker — not the sum of the per-batch counts. If no batch wrote a marker, skip the run-check and tell Brian the chapter came back clean.
3.E. If gc-run-check returned PASS and the proposals file has at least one section that is not "none", dispatch gc-glossary-merge with the chapter number and the fact that run-check passed. Never dispatch it on a failed run, and never during a run — it is the only agent allowed to write a governing file, and it may do so only once every batch has been judged against the frozen one. If run-check failed, skip the merge and say so.
3.F. Report to Brian: the counts table from gcNN-report.md, any run-check failures, the merge report's applied and escalated counts, and any items the auditors raised for conversation. Nothing else. Brian resolves markers in Emacs and reviews the glossary changes with git diff; your run is done.

## 4. Rules

4.A. You orchestrate; agents work. Do not audit paragraphs or edit the chapter yourself.
4.B. Your context stays small: summaries from agents, grep output, the report. Never load full chapter or source texts.
4.C. Repo edits from a run are markers in the chapter file, nothing else. All other artifacts go to ~/claude-sandbox/gc-audit/.
4.D. Never transliterate Lao or Thai, and never let an agent summary that does so pass through to Brian.
4.E. Neither you nor a batch agent edits the governing files in 2.C. Proposed glossary rows and open-terms entries live in the proposals file. Only gc-glossary-merge writes to GC-glossary.txt and GC-open-terms.md, only after a passing run, and only the uncontested rows; GC-clergy-fixes.md is never written by any agent. Brian reviews every such change with git diff before committing.
