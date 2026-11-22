# Working with the translator in this repository

This repository holds translation projects in Thai and Lao. These rules bind every project and every agent that writes to the translator's screen. Each project keeps its procedure file at <language>/<BOOK>/CLAUDE.md, loaded by the command /<language>-<book>, i.e. /th-sc loads th/SC/CLAUDE.md. Read the procedure file in full before running any part of it.

## 1. Replies to the translator

A reply is the message a chat sends to the translator. An item is one numbered part of a reply. The aim of every item is a quick and sound decision.

1.A. Shape

1.A.1. A reply opens with its answers. Each question the translator asked gets its own ANSWER item, in the order asked, and the item quotes the question in the translator's words. A yes-or-no question gets "Yes." or "No." first, then the reason. Nothing stands outside an item.
1.A.2. Every item opens with a bold heading on its own line, a blank line above it: number, kind, subject in plain words, as **4. DECIDE — where the second copy of the rule files is kept**.
1.A.3. The kinds are ANSWER, DECIDE, FIX, STEP, NOTE and RESOLVED. DECIDE asks for a choice. FIX proposes a change to a text or file. STEP is one command the translator runs. NOTE and RESOLVED ask nothing.
1.A.4. Each decision has its own number. Two questions that can be answered differently are two items. Where the points of one item each take their own answer, as the rows of one term family do, each point carries its letter and its own options.
1.A.5. Under the heading, each part opens with a plain label and a colon, as Context:, Question:, FIX1:, You:, with a blank line between parts.
1.A.6. Points that stand side by side go in bullets, one fact to a bullet. Every bullet carries a label, the item's number and a letter, as 12.A, so that the translator can name it. A label goes no deeper than one letter.
1.A.7. Bold is for item headings and for the words at issue inside quoted text. Commands, paths, file names, program names, flags and anything the translator types stand in code formatting. Nothing else is marked. A path is given in full.
1.A.8. A marker's item carries the marker's number. Any other item takes the next number above every marker and item number used in the chat; after 99 the count returns to 1. A reply on two or more chapters numbers its items in one sequence, and each heading names the chapter and the marker. Items stand in number order.

1.B. Context

1.B.1. Write each item for a reader who comes back after a day of other work and remembers nothing of the chat.
1.B.2. Every DECIDE and STEP, and every FIX outside chapter text, opens with a Context: line of up to 3 short sentences: which book or program the item belongs to, what that program or file does for the translator, and what happened that raised the item.
1.B.3. A Question: line quotes the translator's question in the translator's words, or states the item's question in plain words.
1.B.4. A number, date or label never stands for content: no item number, rule number, queue number or "your answer of 19 November". Write the content again.
1.B.5. Never write "above", "below", "earlier", "previous", "as before", "as ruled", "the former", "the latter", "the other option". Name the thing again, by the name the project gave it.
1.B.6. A Now: line holds only what the chat checked in this turn. A Planned: line holds what is not yet built or installed. A Not checked: line holds the rest. A plan is never written in the present tense.
1.B.7. Say what changes for the translator: what the translator will see, type or stop doing. How a program works inside is given only when a decision turns on it or the translator asks.
1.B.8. Every DECIDE, FIX and STEP ends with a You: line that says exactly what the translator types or does.

1.C. Decisions

1.C.1. A DECIDE holds, in order: Context, Question, Now, the options, You. The options are FIX1, FIX2 and on, as many as really differ, with no upper limit. FIX1 is the recommendation.
1.C.2. Each option opens with the choice itself as an action in a few words, as "FIX1: Turn the sound off and keep the `!`." Under it stand bullets, only those that apply, each with its label and its kind: Gain, Loss, You do, Reason.
1.C.3. The translator answers in short forms. `32` alone, or `32.` with nothing after it, takes FIX1 of item 32. `32.1` takes FIX1 and `32.3` takes FIX3. `32a.1` takes FIX1 of the lettered point 32.A. "32. fix3" means the same as `32.3`. `ok` takes FIX1 of every item in the reply. An answer never names anything deeper, as 32b1a would.
1.C.4. Before raising a DECIDE, search the rulings files and the drips. Act on an earlier ruling only when its line can be quoted and the line is about this same book or program and this same question. The RESOLVED item then quotes the line and names its file, so that the translator can stop a wrong use.
1.C.5. Where a ruling is near but about another book, program or question, or where only an agent's note says a ruling exists, ask: the DECIDE quotes the near ruling on a Found: line, and "apply it here too" is one of its options. Never act on a ruling that cannot be quoted.

1.D. Findings in a chapter

1.D.1. A finding in chapter text holds, in order: EN, TH or LO, PRINT where the book's procedure asks, ISSUE, the options, You. The heading names the chapter, the anchor and the marker number. Chapter text is located by its anchor, never by a line number.
1.D.2. EN and TH or LO quote the whole sentence, the words at issue in bold. For a Bible quotation they also quote the sentence that leads into it.
1.D.3. A FIX line shows the new words with the words that stand beside them in the text, the changed words in bold, as ให้แก่**มวลมนุษย์**. Its reason follows in a labelled bullet.
1.D.4. ISSUE names the fault in plain words. Several faults are several labelled bullets.
1.D.5. A glossary row or a marker quoted in an item stands alone on its own line.

1.E. Evidence and presentation

1.E.1. Give all the evidence the decision needs. Leave out only the account of how the chat did its work, and anything already said in the same item.
1.E.2. The conclusion stands first and its evidence under it.
1.E.3. Evidence of one kind about several things goes in a table: one row for each thing, the same columns in every row. Every row begins with its label, as 43.A, then the thing's name; no row stands unlabelled.
1.E.4. A sentence states one fact. Three or more facts of one kind go in bullets, never in one sentence joined by "and". No block of running text is longer than 3 sentences.
1.E.5. Give the figure: "3 files", never "several".

1.F. Finished work, waiting items and the size of a reply

1.F.1. All finished work of a reply is one RESOLVED item: a count in the heading, then one labelled line for each thing in the form "now: Y ← was: X", the changed words in bold on both sides. The order is always now first and was second, here and wherever a reply shows a change. Where one side is longer than about 12 words, quote its first words and say what it is.
1.F.2. All clean checks of a reply are one NOTE: a count in the heading and the checks' names. Never how a check was done.
1.F.3. When the chat changed files since its last reply, one NOTE lists them: one labelled bullet for each file, its full path in code formatting, and what changed in a few words.
1.F.4. More detail on finished work or on a check is given when the translator writes "detail" and the number.
1.F.5. An item the translator has not answered is not repeated. The last item of a reply is a NOTE with the count of waiting items and one labelled bullet for each, naming its subject. The translator writes a bullet's label, and that item comes back in full.
1.F.6. A reply holds at most 15 DECIDE and FIX items; ANSWER, NOTE, RESOLVED and STEP items are not counted. The translator may set another mix for a turn, as "15 of subject X plus 3 drips of 2 items each". A heavy design decision counts for more: the chat sends fewer items and says so. Items over the limit join the waiting items.

1.G. Commands

1.G.1. Each command is its own STEP. The heading names the machine and the window. One command stands in one fenced block.
1.G.2. No command line is longer than 70 characters; break a longer one with a backslash at the line's end. Never a here-document (<<). To make a file, give an editor command and show the file's text apart.
1.G.3. Under the block, say what the command does and what the translator should see, and explain each flag not listed in ~/claude-sandbox/memory/translator-already-knows.md.
1.G.4. A step the translator runs is never called done until the translator reports it.

## 2. Register, sending and agents

2.A. Register

2.A.1. Complete short sentences with a concrete subject. No fragment, no figure of speech, no jargon, no sentence that rates another sentence or predicts the translator's experience.
2.A.2. The You: line keeps its label. Elsewhere a sentence may leave the pronoun out, as "Reply `2`." Never "he", "she" or a name for the translator.
2.A.3. No opener and no closer: no "Great question", "I hope this helps", "Let me know", "In summary".

2.B. Before a chat sends a reply

2.B.1. The translator sees only what a chat writes after its last command or file save. So the chat finishes every command and save first and writes the whole reply last.
2.B.2. Before sending, the chat reads its own reply once against this list and corrects whatever fails:
    A. Every question the translator asked has its own ANSWER item.
    B. Every item heading is bold, and every decision has its own number.
    C. No item uses a number, a date or a word of 1.B.5 in place of content.
    D. Every item that needs one has its Context: line and its You: line.
    E. Every Now: line states something the chat checked in this turn.
    F. Every bullet carries its label, and every table row too; every change reads now first, was second.
    G. No block of running text is longer than 3 sentences.
    H. No command line is longer than 70 characters, and none holds "<<".
    I. The reply holds no more DECIDE and FIX items than 1.F.6 allows.
2.B.3. The phrase checker is the program /etc/claude-code/hooks/plain-language-check.py. It reads each reply before the translator sees it and sends the reply back to the chat when the reply holds a banned phrase. The chat then sends only the corrected item, not the whole reply again.

2.C. Agents

2.C.1. An agent that a chat dispatches does not receive this file; its definition carries the format it needs. It writes its report to a file under ~/claude-sandbox/ and returns the file's path and first line. The first line may be a headline, such as "VERDICT: PASS".
2.C.2. The chat that dispatched the agent builds the reply from that file by these rules and copies every Thai and Lao form from the file.
2.C.3. Explaining what an agent reported is the work of the chat that dispatched the agent, never the translator's. Where the chat cannot explain a statement, the chat reads the source the agent named and then asks the agent.
2.C.4. A statement still unexplained rests under no finding. One NOTE quotes the agent's words and says what the chat checked.

## 3. Raising issues

3.A. Deferring is the translator's decision. Raise an issue in the same report with numbered options. Never write "later".
3.B. When he defers one, add it to the project's queue file, named in the project's procedure file, in the same reply; say which position it took; delete the entry when the work is done.
3.C. "model: X/Y/Z" — default "fable: 7/3/1"; a bare "7/3/1" means that — asks for candidate wordings: dispatch the named model at xhigh effort, weigh up to X candidates, show the top Y ranked in the report, not the chapter, the top Z recommended. "Up to X" means as many real candidates as exist and never one more; a large X asks for wide thinking, and some sites have one or two candidates. Weigh each candidate in its whole passage; a glossary row guides and never rules.
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

7.A. Each numbered item is one unwrapped line. Indented examples stay as blocks. assets/scripts/unwrap.py rejoins a hard-wrapped file.
7.B. A rule says what to do. A session's mishap never becomes a rule.
7.C. Every instruction file has a word budget in assets/scripts/instruction_budget.py. Each project's check step runs the script, and so does the reply that edits an instruction file. The budget is a guide: a file over budget loses a restatement or gains a larger budget row, never a rule still in force.
7.D. Instruction files, agent definitions, commands and scripts name no person; they say "the translator".

## 8. Git and files

8.A. You never stage, commit, push, pull, merge, rebase, stash, tag, rename, move, delete or install a hook, and you never run rm or mv. The translator does all of that. Put the command in a numbered item of the next report and carry on; never stop or wait for it. A commit message handed to the translator has a first line of at most 35 characters, its count stated, with any detail in a paragraph below it. Read-only git commands are allowed.
8.B. A script or record that operates on this repository lives in the repository. A session's own working files live in the sandbox directory outside the repository, ~/claude-sandbox/.
8.C. A directory named sandbox inside the repository is the translator's. Never write to it.
8.D. Standing memory is one markdown file per lesson under memory/ in the sandbox directory of 8.B; nothing there is loaded automatically. A lesson an agent needs on dispatch is written into that agent's definition.
8.E. Run `echo ok` in the shell before any other work. On a bwrap error naming a file under .git, stop and hand the translator the fix in ~/claude-sandbox/memory/sandbox-bwrap-git-lock.md.
8.F. At the start of a chat, confirm that the worktree the work writes into is on the work's branch, or that the branch is checked out nowhere so a worktree can be made for it; the branch of the folder the chat started in does not matter. If neither holds, the first report says so and gives the command, never one that switches the branch of a folder in use, and no project work starts; this start check is an exception to 8.A.
8.G. When auto mode refuses or holds a command, keep working without it and raise a numbered item that carries the command.
8.H. Grep ~/claude-sandbox/FACTS.md before studying a system; add what you studied, never word studies.
8.I. Every new or updated published file of a book (print PDF, EPUB or web pages) gets a GitHub release, its full steps in the report that hands over the commit: the tag is BOOK-lang-vMAJOR.MINOR, one number covers every format of a text, a correction raises MINOR and a new edition MAJOR, and each file is attached with its sha256 file.
