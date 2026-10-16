# Google Docs review loop — agreed design, not yet built

Distilled on 16 August 2026 from a claude.ai conversation. Status: design only. Nothing below is implemented, and until it is, chapters are uploaded to Google Docs by hand after the post-resolution sweep in th/SC/CLAUDE.md section 4 passes.

## The constraint the design routes around

The Google Docs API cannot create Suggesting-mode edits — it can only make direct edits or read existing suggestions. So Claude Code can never push tracked changes into a Doc; humans suggest, Claude Code ingests.

## The loop

1. Repo to Doc, after each processing round. The repository is authoritative. Export the chapter to docx with pandoc and upload with rclone, overwriting the same Doc so reviewer sharing links and permissions never break. Keep the exact uploaded docx as a snapshot; it is the anchor every later diff runs against.
2. Reviewers leave in-line suggestions in the Doc. Optionally, before a live session, Claude Code pulls pending suggestions via the Docs API (documents.get with suggestionsViewMode=SUGGESTIONS_INLINE) and produces a numbered agenda: each suggestion, its location, its author, and an accept or reject recommendation argued from the translation profile and glossary.
3. The translator and editor resolve suggestions together in the Doc during a live audio session, walking the numbered agenda.
4. Doc to repo, after the session. Download via rclone, extract text, diff against the snapshot from step 1 — the only changes are accepted suggestions, so the diff is small. Claude Code translates the diff into edits on the canonical Typst file, the translator reviews and commits.

## What makes the round trip survivable for Thai

Segment the exported text one sentence or one paragraph per line so diffs align, and normalize invisible characters identically on export and import so they never appear as phantom changes.

## A minimal alternative, raised 16 August

Upload the marker-laden file itself to Google Docs and let the Doc's own comparison show the differences against the clean revision — no export tooling, no re-import parsing. The translator suggested this as the minimal-work path that avoids the tooling rabbit hole entirely; test it before building anything below.

## Open before building

1. rclone remote and auth are not set up.
2. The Docs API agenda needs OAuth credentials; the loop works without it, but the pre-vetted agenda is what upgrades the live session.
3. Whether the editor drives edits during sessions or only discusses was asked in the conversation and never answered; it decides how much of step 3 needs tooling at all.
