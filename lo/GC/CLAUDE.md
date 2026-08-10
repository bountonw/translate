# GC audit — conductor

## 1. Trigger

1.A. When Brian names a chapter ("GC17", "run GC13"), run
     the full chapter procedure in section 3. When he
     names a term family or corpus question, dispatch
     gc-term-grep instead. Anything else: ask.
1.B. When Brian says "check GCNN" (or says he has
     finished resolving), dispatch gc-resolve-check with
     the chapter number and relay its report verbatim.
     A PASS means the chapter is clean to commit.

## 2. Paths

2.A. Chapter under audit: lo/GC/03_public/GCNN_lo.md
2.B. English source:      lo/GC/00_source/GCNN_en.md
2.C. Governing files:     lo/assets/translation_profile/
     (GC-glossary.txt, GC-clergy-fixes.md,
     GC-open-terms.md)
2.D. Session outputs:     ~/claude-sandbox/gc-audit/
2.E. Introduction files (GC00*) are out of scope unless
     Brian names them explicitly.

## 3. Chapter procedure

3.A. Preflight. Confirm 2.A and 2.B exist. If the chapter
     already contains [[ markers, stop and tell Brian —
     he resolves markers between runs. Do not read the
     chapter body into your own context; grep only.
3.B. List the chapter's {GC ###.#} anchors (grep). Split
     into batches of about 5 pages at paragraph
     boundaries.
3.C. Dispatch gc-batch-auditor per batch, SEQUENTIALLY,
     never in parallel (marker numbering and file appends
     depend on order). Each dispatch states: chapter NN,
     ref range, starting marker number, and whether it is
     the first batch (first batch creates the session
     files). Next batch's starting number = previous
     batch's reported last number + 1.
3.D. After the last batch, dispatch gc-run-check.
3.E. Report to Brian: the counts table from
     gcNN-report.md, any run-check failures, and any
     items the auditors raised for conversation. Nothing
     else. Brian resolves markers in Emacs; your run is
     done.

## 4. Rules

4.A. You orchestrate; agents work. Do not audit
     paragraphs or edit the chapter yourself.
4.B. Your context stays small: summaries from agents,
     grep output, the report. Never load full chapter or
     source texts.
4.C. Repo edits from a run are markers in the chapter
     file, nothing else. All other artifacts go to
     ~/claude-sandbox/gc-audit/.
4.D. Never transliterate Lao or Thai, and never let an
     agent summary that does so pass through to Brian.
