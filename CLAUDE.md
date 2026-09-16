# Working with the translator in this repository

This repository holds translation projects in Thai and Lao. These rules bind every project and every agent that writes to the translator's screen. Each project keeps its procedure file at <language>/<BOOK>/CLAUDE.md, loaded by the command /<language>-<book>, i.e. /th-sc loads th/SC/CLAUDE.md. Read the procedure file in full before running any part of it.

## 1. Report shape

1.A. A report is the detail section, then the summary list in full at the bottom.
1.B. The summary list is one line per item, grouped FIX, DECIDE, NOTE, RESOLVED. Each line carries the number and label in bold, the reference that locates the item — a paragraph anchor, a marker number, or a path and line for code and governing files — and what changes, in one short sentence. A DECIDE line ends with the recommended option. Anchored prose is located by its anchor, never by a line number.

    **1. FIX** {SC 13.1} — the footnote cites Luke 21:39–45; Luke 21 has 38 verses.
    **2. DECIDE** th/assets/translation_profile/thai-glossary.txt:14 — the trial row keeps การทดสอบ or adds ความยากลำบาก; I recommend adding.

1.C. Name the subject on every line and state the change itself. Never write "it", "several" or a bare label where the subject's name belongs.
1.D. Nothing sits outside a numbered item: a file created, a passing correction, a clean check, an offer, a question — each is an item. An agent's report to the conductor may begin with one headline line, such as "VERDICT: PASS".
1.E. The detail section comes first. Each item has a heading and a labelled block: EN (the source, words at issue in **bold**), TH or LO (the translation as it stands, the same way), ISSUE (one or two sentences), FIX1, FIX2, up to FIX4. Every labelled line opens with a sentence that can be read alone.
1.F. FIX1 is the recommendation; its reason is one sentence. Add a further option only where it is genuinely different.
1.G. Quote enough to identify the issue and no more. Show the text of a false alarm too. Give full paths. Drop a field that does not apply.
1.G.1. One numbering scheme per report. Enumerate inside an item by extending its number: 3.A, then 3.A.1. The options of a DECIDE keep the labels FIX1, FIX2.
1.G.2. An item about a marker carries the marker's own number. An item without one takes the next number above the chapter's highest marker. Grouping never renumbers.
1.G.3. Every item stands on its own with no memory of the exchange: name the text, the file and the change; give the figures rather than "several"; put the recommendation first.
1.H. A dispatched agent does not receive this file. An agent definition that produces a report carries the format itself.
1.I. A dispatched agent writes its report to a file under the sandbox of 8.B and returns the path. The conductor builds the translator's report from that file, in this shape and in plain language, and passes nothing on that it cannot itself explain.

## 2. Register

2.A. Brief, complete sentences. Never fragments.
2.B. No compressed or figurative phrasing. Say the plain fact.
2.C. Brevity comes from cutting evidence not asked for and restatements. Never from dropping verbs.
2.D. Every sentence carries a fact the translator can check. The reason for a rule may be one plain sentence. Cut a sentence that rates another sentence or predicts his experience.
2.E. Short declarative sentences with concrete subjects. State the fact and stop.

## 3. Raising issues

3.A. Deferring is the translator's decision. Raise an issue in the same report with numbered options. Never write "later".
3.B. When he defers one, add it to the project's queue file, named in the project's procedure file, in the same reply; say which position it took; delete the entry when the work is done.
3.C. "model: X/Y/Z" — default "fable: 7/3/1"; a bare "7/3/1" means that — asks for candidate wordings: dispatch the named model at xhigh effort, weigh up to X candidates, show the top Y ranked, write the top Z into the marker. "Up to X" means as many real candidates as exist and never one more; a large X asks for wide thinking, and some sites have one or two candidates. Weigh each candidate in its whole passage; a glossary row guides and never rules.
3.D. In the translator's replies, "N. fixK" applies fix K at marker N and deletes the marker; "N. applied" reports his own work, and the marker is left as he left it.

## 4. Parallel sessions

4.A. The translator runs several sessions at once. Never revert, stage, stash or commit another session's work, and never ask him to commit it.
4.B. Never write over a line another session is editing. Raise it as a DECIDE.

## 5. Thai and Lao text

5.A. Western numerals unless the project's procedure file says otherwise. Never Thai digits (U+0E50–U+0E59) or Lao digits (U+0ED0–U+0ED9).
5.B. Never insert a zero-width space or any invisible character in a chapter file. An export to HTML or EPUB may add its own.
5.C. Never transliterate Thai or Lao. Copy a form out of the file; grep any form you did not copy before it reaches the translator.

## 6. Evidence

6.A. Corpus evidence is evidence, never a verdict. Only the translator adjudicates.
6.B. Never write that the corpus settles a question, and never infer a rule from existing text and apply it. Present the evidence, name what has been ruled, recommend.
6.C. A rule an agent wrote citing a ruling of the translator's is not evidence that he ruled it. Ask him before building on it.
6.D. A ruling is written into its governing file in the same reply that receives it, as one line saying what to do, with no date or story. Every other governing-file edit is proposed first.

## 7. Instruction files

7.A. Each numbered item is one unwrapped line. Indented examples stay as blocks.
7.B. A rule says what to do. A session's mishap never becomes a rule.
7.C. Every instruction file has a word budget in th/SC/04_assets/scripts/instruction_budget.py. Each project's check step runs the script, and so does the reply that edits an instruction file. A line added over budget means a line cut.

## 8. Git and files

8.A. You never stage, commit, push, pull, merge, rebase, stash, tag, rename, delete or install a hook. The translator does all of that. Hand him the command and stop. Read-only git commands are allowed.
8.B. A script or record that operates on this repository lives in the repository. A session's own working files live in the sandbox directory outside the repository, ~/claude-sandbox/.
8.C. A directory named sandbox inside the repository is the translator's. Never write to it.
8.D. Standing memory is one markdown file per lesson under memory/ in the sandbox directory of 8.B; nothing there is loaded automatically. A lesson an agent needs on dispatch is written into that agent's definition.
