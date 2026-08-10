---
description: GC QA2 audit — run a chapter, check a resolved chapter, or import a web handoff
argument-hint: GC13 | check GC13 | import GC11 | <term question>
---

@lo/GC/CLAUDE.md

Before anything else, read lo/GC/CLAUDE.md in full. It is the conductor procedure for this audit, it lives below the working directory, and it is not loaded automatically at session start — so if you have not read it in this session, you do not yet know the procedure and must not improvise one.

Then act on: $ARGUMENTS

- A bare chapter name (GC13, or 13) — run the full chapter procedure in section 3 of that file.
- `check GCNN` — Brian has resolved the markers; dispatch gc-resolve-check per 1.B and relay its report verbatim.
- `import GCNN` — import a web-app handoff document; the procedure is at the end of ~/claude-sandbox/gc-audit/web-handoff-prompt.md.
- Anything naming a term family or asking a corpus question — dispatch gc-term-grep.
- Anything else — ask rather than guess.

Two preflight checks before you dispatch anything, both of which fail runs for reasons unrelated to the audit:

1. `git status --short -- lo/GC` must be clean except for the chapter itself. gc-run-check verifies this at the end, so a dirty tree turns a good run into a failed one.
2. The five gc-* agents must be listed as available. If they are not, they are not registered, and dispatching them silently falls back to a generic agent with none of its instructions — stop and tell Brian instead.
