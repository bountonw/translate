# AA planning

Parked material for the AA project, which does not exist yet. Side quest 12 in `lo/GC/04_assets/planning/SIDEQUESTS.md` is the queue entry that governs it.

`AA06-gemini-partial.typ` is a partially resolved diff, not a manuscript and not a rewrite. Months before August 2025 Gemini was given the AA translation profile and produced its own version of chapter 6 as a separate file. The translator then diffed that file against the chapter as it stands in this repository, and began working through the resulting diff — accepting a hunk, declining it, or rewording it as he went. This file is that diff part-way through, at the point where he stopped.

What that means for anyone picking it up. Prose that reads cleanly has already been resolved and is the translator's decision, whichever side of the diff it came from. The 18 parenthetical groups are the hunks he had not yet settled, holding the competing readings; 11 of them have brackets the diff left unbalanced, in shapes ranging from the clean (ພວມ/ກຳລັງ) to ((ຂ່າວສານແຫ່ງ))) and ( ແລະ ພາ)(ໄປຂັງຄຸກ)). One group carries an English gloss as a fourth option, (ແຂງຂັນ/ດື້ອດ້ານ/ໜັກແໜ້ນ/firmly resisted).

Its limits. It covers paragraphs {AA 57.1} to {AA 62.1} only, and {AA 62.1} carries its anchor with no body. Its paragraph tags are bare {AA 57.1} rather than the manuscript's #EGW[\{AA 57.1\}], and the AM vowel is decomposed throughout, so the spelling round has to run over whatever comes out of it.

Nothing here has been applied. The chapter as committed is the August 2025 line: the translator's earlier Google Docs edits merged in, then the pre-edit spelling round of 88 corrections.

## The pre round, as run on SC12 and SC13 in August 2026

The SC project ran a "pre" round on its raw chapters before QA1, and the mechanics carry over to AA's raw drafts. They were removed from the SC instructions when SC's pre round finished; this is the record.

- The translator's parentheses in a raw draft are his unresolved choices: (A/B) offers alternatives, (word) is tentative. Every one got a CHOICE marker, old = the parenthesis span verbatim, new = the recommended wording, with corpus precedent named in the note; balanced alternatives got new1 / new2. None was resolved by silent editing. A parenthesis he ruled to stand for the editors stood and travelled to Google Docs.
- Stacked parentheses — (phrase))) — were his signal for extra effort: the candidate drill (model: X/Y/Z, default fable 7/3/1) ran on the site.
- His raw notes in the text — an inline [[fable: ...]] tag, a (before: .../after: ...) pair, a bracketed question — were questions to whoever met them: answered, folded into a marker with concrete wording, never counted as defects.
- EDIT markers, soft editorial improvements, were allowed in the pre round only, and only where the gain could be named in one sentence.
- The first batch repaired the raw chapter's header (the #import and #show lines) silently, and footnote citations were converted to inline citations silently, both reviewed in the diff.
- At the end, remaining markers were converted to editor parentheses — (old/new) or (old/new1/new2), current wording first — by th/SC/04_assets/scripts/sc_editor_markers.py, so the chapter could go to Google Docs.
