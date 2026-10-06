# DA — how to run the project

The new Thai translation of *The Desire of Ages*, ผู้พึงปรารถนาแห่งปวงชน ฉบับแปลใหม่. The procedure is th/DA/CLAUDE.md; this page lists what you type.

Start Claude Code in the checkout that holds the DA branch, then type `/th-DA` followed by one of the commands below. Every report comes back in the usual shape, with numbered items and the summary at the bottom.

The agents and scripts these commands call are not built yet. `/th-DA tools` builds them; it is entry 1 of th/DA/04_assets/planning/SIDEQUESTS.md. Until then, every other command stops and says which agent is missing.

## Once, before the first chapter

| Type | What happens | What you do |
|---|---|---|
| `/th-DA tools` | The agents and scripts are proposed, then written and tested on DA00. | Approve each before it is written. |
| `/th-DA names` | A script takes every biblical name's spelling from THSV and lists only the names that need a ruling. | Rule the exceptions. |
| `/th-DA register` | Sonnet mines PP and MB for how the narrator speaks of Jesus, the disciples and the leaders, and how people address Jesus. | Rule the register. |

## Each chapter

| Type | Pass | What happens | What you do |
|---|---|---|---|
| `/th-DA terms DA01` | 1 | Opus lists the terms, quotations and allusions. Sonnet gathers the data. Fable proposes each glossary row and ranks the top three Bible versions for each quotation. | Rule each row. Close verse calls come later as markers. |
| `/th-DA terms DA00-DA87` | 1 | The same for a run of chapters, so the glossary can be built before translating. | As above. |
| `/th-DA draft DA01` | 2 | Fable drafts and checks itself, Opus checks against the English, Fable fixes or raises an issue. | Commit the agent draft, read the chapter whole, settle every marker and editor's choice. |
| `/th-DA check DA01` | 3 | Scripts and Opus check that your resolutions left no damage. | Commit; the chapter moves to 02_edit. |
| `/th-DA editor DA01` | — | The chapter is made ready to upload to Google Docs. | Upload by hand; the editor reads and flags. |
| `/th-DA flags DA01` | — | Each flag you bring back becomes a marker with proposals. | Settle them, then `check` again; the chapter moves to 03_public. |

## Any time

| Type | What happens |
|---|---|
| `/th-DA 7/3/1` or `/th-DA model: fable 7/3/1` | The wording drill on named markers. |
| `/th-DA status` | Each chapter's stage and its standing markers. |
| `/th-DA` with a question | A term or corpus question, answered from the Thai books and Bibles. |

## Where things are

| What | Where |
|---|---|
| English source | th/DA/00_source/DANN_en.md |
| Your chapters | th/DA/01_raw, 02_edit, 03_public |
| The 2023 print, for reference | th/DA/04_assets/editions/print |
| Names | th/DA/04_assets/names.tsv |
| Scripts | th/DA/04_assets/scripts |
| Session outputs and agent reports | ~/claude-sandbox/da-audit/ |
