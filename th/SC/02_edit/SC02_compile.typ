// ─── SC02 Compile Wrapper ─────────────────────────────────────────────────────
// Compiles "SC02_th.typ" (บทที่ 2 — คนบาปต้องการพระเยซู) to PDF.
//
// ── Prerequisites ─────────────────────────────────────────────────────────────
//
//   1. Typst 0.11 or later
//      Download: https://github.com/typst/typst/releases
//      Or via Homebrew: brew install typst
//
//   2. Noto Serif Thai font
//      Download from Google Fonts:
//        https://fonts.google.com/noto/specimen/Noto+Serif+Thai
//      Install the .ttf files system-wide (double-click → Install on macOS/Windows).
//      If unavailable, Typst will fall back to Noto Serif or FreeSerif for Latin
//      characters but Thai glyphs will not render correctly.
//
// ── Compile ───────────────────────────────────────────────────────────────────
//
//   Single compile (from this directory):
//     typst compile SC02_compile.typ
//   → produces SC02_compile.pdf in the same directory
//
//   Watch mode (live PDF preview while editing):
//     typst watch SC02_compile.typ
//
//   Custom output path:
//     typst compile SC02_compile.typ ../../03_public/SC02_th.pdf
//
// ─────────────────────────────────────────────────────────────────────────────

#import "SC_template.typ": sc-template, sc-chapter as chapter, EGW

#show: sc-template.with(book-title-th: "ก้าวสู่พระคริสต์")

#include "SC02_th.typ"
