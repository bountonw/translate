---
description: SC Thai rounds — pre-process a raw chapter, run QA1 or QA2 on one or more chapters, check a resolved chapter, or mine terms for the glossary
argument-hint: pre SC13 | qa1 SC01 SC02 | qa2 SC01 | check SC01 | terms SC01 SC02 | <term question>
---

@th/SC/CLAUDE.md

Before anything else, read th/SC/CLAUDE.md in full. It is the conductor procedure for the SC rounds, it lives below the working directory, and it is not loaded automatically at session start — so if you have not read it in this session, you do not yet know the procedure and must not improvise one.

Then act on: $ARGUMENTS

- `pre SCNN` — the pre-processing round on a raw chapter in th/SC/01_raw; section 1.A and section 4 of that file.
- `qa1 SCNN [SCNN ...]` — round one, accuracy only; section 3.C and section 4. Chapters named together run in parallel, batches inside a chapter in sequence.
- `qa2 SCNN [SCNN ...]` — round two, terms and clarity; section 3.D and section 4. It refuses a chapter whose QA1 markers are not yet resolved or whose terms have no adjudicated glossary rows.
- `qa3 SCNN` — not built yet; say so and stop, per 1.D.
- `check SCNN` — the translator has finished resolving; follow section 5 exactly. It begins by grepping the chapter for [[ before anything is dispatched.
- `editor SCNN` or `editor SCNN #12 #14` — turn the remaining markers, or the named ones, into editor parentheses for Google Docs; section 1.H.
- `terms SCNN [SCNN ...]` — glossary mining; section 7.
- Anything naming a term or asking a corpus question — answer it yourself by grep, per 1.G.
- Anything else — ask rather than guess.

Two preflight checks before you dispatch anything, both of which fail runs for reasons unrelated to the audit:

1. Cleanliness, per section 4.A of that file. Run `git status --short -- th/SC` and read it per chapter, never tree-wide: your chapter's file must be unmodified, while another chapter's manuscript is another session's work and never a reason to stop.
2. The agents sc-batch-auditor, sc-run-check, sc-resolve-check and th-glossary-miner must be listed as available. If one is not, it is not registered, and dispatching it silently falls back to a generic agent with none of its instructions — stop and tell the translator instead.
