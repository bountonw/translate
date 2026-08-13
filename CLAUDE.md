# Working with Brian in this repository

This repository holds translation projects into Lao and Thai. These rules apply to every project in it and to every agent that writes to Brian's screen. Each project keeps its own procedure file; the GC audit's is `lo/GC/CLAUDE.md`, which is not loaded automatically and must be read in full before any part of that audit is run.

## 1. Report shape

1.A. Every report has three sections: the summary list, the detail, then the summary list repeated in full at the bottom. Repeat it so that Brian sees what is his to do without scrolling in either direction.

1.B. The summary list is one line per item, grouped in priority order FIX, DECIDE, NOTE, RESOLVED. Each line carries a number, the label in block capitals, the reference that locates the item — a paragraph anchor, a marker number, or a full path and line — and then a short description in ordinary English. A DECIDE line ends with the option you recommend. Anchored prose is located by its anchor and never by a line number: a manuscript and its English source are anchored paragraph for paragraph but numbered quite differently, so a line number sends Brian to the wrong paragraph the moment he opens the other file, and it goes stale as soon as either file is edited. A line number is right for code, for a script, and for a governing file such as GC-glossary.txt whose rows carry no anchor.

    1. FIX {GC 299.1} — stray consonant in the Job quotation.
    2. DECIDE lo/GC/04_assets/translation_profile/GC-glossary.txt:62 — the Day of Atonement row keeps the word DECIDED or takes a checkmark; I recommend DECIDED.

1.C. Name the subject on every line, and say what actually changes. A pronoun, a quantifier or a bare label points at nothing on his screen, and a description that refers to a change instead of stating it — "replace it with the right wording", "fix the duplication" — fails the same way, because he then has to read the detail section to learn what the line is proposing.

1.D. Nothing in a report sits outside a numbered item: a file you created, a correction you made in passing, a check that found nothing, each is a NOTE and never a loose sentence. An offer, a recommendation and a question are items in their own right, never a clause inside another item's evidence — anything Brian might answer has to be findable in the summary list, because that list is what he reads. An agent reporting to a conductor rather than to Brian may open with one headline line of bookkeeping, and that is the only exception.

1.E. The detail section repeats each summary line as its heading, in the same order, and gives a labelled block beneath it.

    EN:    the source text, quoted verbatim, with enough context to place it and the words at issue in **bold**
    LO:    the translation as it stands, quoted verbatim, with the same context and the words at issue in **bold**
    ISSUE: what is wrong, in one or two plain sentences
    FIX1:  the option you recommend, with the reason for recommending it in a short clause
    FIX2:  the next option, with its consequence in a short clause
    FIX3:  further options, up to FIX4, each with its consequence

1.F. FIX1 is always the option you recommend. The reason on it is one complete sentence, or two where a consequence has to be stated as well; two is a ceiling and not a target, and it is never a fragment. Give a further option only where it is genuinely different: three or four are allowed when the choice really has that many, and padding the list with an option nobody would take wastes his time as surely as omitting a real one.

1.G. Quote enough context to identify the issue and no more, and show the text for a false alarm too, since he cannot dismiss one without seeing what was flagged. Give the full path of every file you cite. Drop any field that does not apply, and give no block at all to an item that needs no evidence.

1.G.1. A report has one numbering scheme, the summary list's. Never start a second one inside a detail block: two lists give Brian two item 3s and no way to say which he means. Where a block has to enumerate, extend the item's own number instead, alternating numbers and letters as far down as the point needs. Item 1 lists 1.A, 1.B, 1.C; 1.A lists 1.A.1, 1.A.2 beneath it; and so on. Every point in the report then has one address he can quote back at you. The options on a DECIDE are the exception and keep the FIX1, FIX2, FIX3 labels of 1.E and 1.F, prefixed by the item number where he needs to name one exactly, as 3.FIX2. Numbering them 3.A, 3.B, 3.C instead makes a decision stop reading as a decision, which is the one thing the labels exist to prevent. The detail section follows the summary list's order exactly, priority grouping included.

1.H. An agent dispatched with the Agent tool does NOT receive this file. That was tested on 12 August with two probes, one generic and one with a custom definition, and both reported it absent from their context. So every agent definition that produces a report carries the format above in its own text, and a pointer to this file in place of it is a dead reference.

## 2. Register

2.A. Write brief, complete English in every section. Never clip a line into fragments to save words: that is the defect Brian calls caveman talk, and he wants none of it anywhere in a report.

2.B. Compressed or figurative phrasing that only makes sense to you is the same failure under another name. Not "both work mechanically" but "the script ignores that word either way".

2.C. Brevity comes from organisation, from cutting evidence he did not ask for, and from cutting restatements of what you have just done. It never comes from dropping the verbs out of a sentence.

## 3. Raising issues

3.A. Deferring is Brian's decision, never yours. If an issue is worth raising, put it in the same report: state it in one sentence and give it numbered options in the shape set out in 1.E and 1.F. Never write "not urgent" or "worth revisiting later" in place of putting the choice in front of him.

3.B. When he does defer one, add it to `lo/GC/04_assets/planning/SIDEQUESTS.md` in the same reply that defers it, and say in that reply which position it took. That file is the queue and it is the only answer to "how many side quests are open and in what order" — never answer that from memory or from a chat. Delete an entry when its work is finished rather than marking it done, because a finished quest is in the git history. It sits under a numbered-stage assets directory because `.tooling/textlint/index.js` excludes those from every check; a document with no paragraph anchors cannot satisfy the reference-code rule and does not belong anywhere the linter walks.

## 4. Parallel sessions

4.A. Brian works on several chapters or documents at once in separate sessions. Never revert, stage, stash or commit another session's uncommitted work, and never ask him to commit it to unblock you.

4.B. Never write over a line another session is editing. Where two sessions need the same line, stop and raise it as a numbered DECIDE.

## 5. Lao and Thai text

5.A. Numerals are Western unless Brian states otherwise for the file you are working in. Never use Lao digits (U+0ED0–U+0ED9) or Thai digits (U+0E50–U+0E59). The substitution is invisible: the Lao digit zero closely resembles a vowel character, so a correct word silently becomes a variant that no later search will find.

5.B. Never insert a zero-width space (U+200B) or any other invisible character, and strip any you find in a Lao manuscript. The GC typesetting pipeline wraps every Lao word in \lw{} and supplies its own break opportunities, so a zero-width space there is redundant, and being invisible in the editor it silently breaks a later search. Check how a new project's pipeline breaks lines before carrying this rule over to it.

5.C. Never transliterate Lao or Thai. Copy a Lao or Thai form out of the file rather than retyping it, and grep any form you did not copy before it reaches Brian.

## 6. Evidence and judgment

6.A. Corpus evidence is strong evidence and never a verdict. What the manuscript already does, however consistent and however many sites, is a guide to what Brian intended and nothing more: the translation was made over years without a translation memory, so a pattern may be a considered decision, a repeated accident, or simply wrong. Only Brian adjudicates.

6.B. Never write that the corpus settles a question, and never infer a rule from existing text and then apply it as decided. Present the evidence, call it evidence, name what has actually been ruled and by whom, and recommend. Where a recommendation rests only on what the corpus does, say so.

6.C. A rule an agent wrote into an instruction file, citing a ruling of Brian's, is not evidence that he ruled it. An agent that has just made a mistake will sometimes write a rule that recasts the mistake as a different and smaller problem, and the citation of his authority is the first thing in it to doubt. Where a rule's only support is an agent's account of what he said, ask him before building on it, and never carry the claim into a second file as though it were settled — checking that a set of rules agrees with itself proves nothing about where they came from.

## 7. Editing instruction files

7.A. When you edit this file, a project procedure file, an agent definition or a settings file, write each numbered item as a single unwrapped line and let the editor wrap it on screen. Hard-wrapped prose makes a later reflow rewrite lines that did not change, and `git diff` then stops showing what actually moved. Indented examples are the exception and stay as blocks.

7.B. Never write a session's own mishap into a standing rule. A rule says what to do; the story of how one session got it wrong is evidence and belongs in that session's report. Item 1.B of `lo/GC/CLAUDE.md` went from 99 words to 231 in two days because two sessions each appended their own accident to it, and neither addition changed anything the conductor does. Before adding a sentence to a rule, ask what an agent would do differently for having read it, and drop it if the answer is nothing.

## 8. Where a file belongs

8.A. A script or a record that operates on this repository lives in this repository, under version control; `~/claude-sandbox/` is for a session's own working files. It has a git repository of its own, but the audit files under it are untracked, so nothing kept there is reliably kept. Two things belong here rather than there: a tool that reads or writes repository files, and a record meant to be consulted after the work it describes is over. A brief for a job that has not yet run is neither, however long it took to write — it is spent once the job is done, so it stays in the sandbox and only what the job produced is committed. A file that should not be loaded on every dispatch is kept out by naming it in the project's procedure file, never by keeping it outside the repository. That governs automatic loading and is not a ban on reading: a person opens the file whenever it is wanted, and an agent opens it when Brian asks it to. The point is only that it costs nothing when nobody needs it.

8.B. A directory named sandbox anywhere in this repository is Brian's own workspace. Read from it where that answers a question; never write to it, never clean it, and never propose edits to anything in it. Its contents are generated or experimental, git ignores them under the `**/*[Ss]andbox*/` rule, and a defect visible there is fixed in the source the file was generated from and nowhere else. `~/claude-sandbox/` is the opposite — that is where you write your own working files — and the similar name is all the two have in common.
