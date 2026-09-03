---
description: SC Thai rounds — pre-process a raw chapter, check a resolved chapter, or ask a Thai corpus question
argument-hint: pre SC12 | check SC12 | <term question>
---

@th/SC/CLAUDE.md

Before anything else, read th/SC/CLAUDE.md in full. It is the conductor procedure for this project, it lives below the working directory, and it is not loaded automatically at session start — so if you have not read it in this session, you do not yet know the procedure and must not improvise one.

Then act on: $ARGUMENTS

- `pre SCNN` — run the pre-processing round in section 3 of that file.
- `check SCNN` — the translator has finished resolving; run the post-resolution sweep in section 4.
- Anything naming a term or asking a Thai corpus question — answer it per 1.C of that file.
- Anything else — ask rather than guess.

Two preflight checks before you dispatch anything:

1. Cleanliness, per root CLAUDE.md section 4, scoped to your chapter and never to the tree: your chapter's file must be unmodified, and another chapter's or another project's modified file is never a reason to stop.
2. The sc-batch-auditor agent must be listed as available. If it is not, it is not registered, and dispatching it silently falls back to a generic agent with none of its instructions — stop and say so instead.
