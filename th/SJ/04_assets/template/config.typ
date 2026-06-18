// =============================================================================
// Configuration
// Page sizing, metadata, and the shared header/footer pieces components reuse.
// Proofing mode (A4, equal margins) is selected once via apply-styles in lib.typ.
// =============================================================================

// -----------------------------------------------------------------------------
// Book-mode override
// book.typ flips this to true at the very top of the document. apply-styles reads
// it (via context) and, when true, forces book layout even for chapter files that
// carry `proofing: true` for standalone drafting. This is what lets the full-book
// build win over each chapter's own proof setting — the chapters are included
// inside book.typ's flow, so they see the flag. No build flag is needed: a
// standalone chapter compile never flips it, so it still proofs (A4).
// -----------------------------------------------------------------------------
#let book-mode = state("force-book-mode", false)

// -----------------------------------------------------------------------------
// Language
// -----------------------------------------------------------------------------
#let text-lang = (lang: "th", region: "th")

// -----------------------------------------------------------------------------
// Book metadata
// -----------------------------------------------------------------------------
#let book-metadata = (
  title: "เรื่องของพระเยซู",
  author: "เอเลน จี. ไวท์",
  language: "th",
)

// -----------------------------------------------------------------------------
// Font families
// List multiple fonts for fallback - Typst uses the first available.
// -----------------------------------------------------------------------------
#let font-body = ("Sarabun", "Noto Sans Thai")
#let font-heading = ("Sarabun", "Noto Sans Thai")

// -----------------------------------------------------------------------------
// Text sizing
// -----------------------------------------------------------------------------
#let size-body = 11.5pt
#let size-small = 9pt
#let size-large = 14pt

// leading  = gap between lines WITHIN a paragraph
// spacing  = gap between paragraphs
//
// NOTE: both are measured the same way — the space between the BOTTOM of one
// line and the TOP of the next line (not baseline-to-baseline). For a book it is
// therefore recommended to keep leading and spacing EQUAL.
#let book-leading = 1em
#let book-spacing = 1em   // keep equal to book-leading (see note)
#let proof-leading = 1.7em
#let proof-spacing = 1.7em   // keep equal to proof-leading (see note)

// Thin space inserted between the dots of a spaced ellipsis (". . ." / ". . . .").
#let ellipsis-gap = 0.15em

// -----------------------------------------------------------------------------
// Margin spacings
// -----------------------------------------------------------------------------

// Extra top spacing pushed in by chapter() on the opening page (mode-agnostic).
#let chapter-opening-top-space = 10mm

// Margin used by full-page illustrations.
#let illustration-margin = 1cm


// -----------------------------------------------------------------------------
// Page base — paper + outer margin. Proof mode swaps to A4 with equal borders.
// -----------------------------------------------------------------------------
#let make-base(proofing: false) = if proofing {
  (paper: "a4", margin: (top: 36mm, bottom: 20mm, left: 24mm, right: 24mm), header-ascent: 6mm,)
} else {
  (paper: "a5", margin: (top: 20mm, bottom: 14mm, outside: 14mm, inside: 22mm), header-ascent: 4mm,)
}
// For b5 size, replace the previous line with the following one.
// (paper: "iso-b5", margin: (top: 25mm, bottom: 16mm, outside: 16mm, inside: 24mm))

// -----------------------------------------------------------------------------
// Shared header/footer (mode-agnostic — same in book and proof)
//
// Strategy: page settings are applied ONCE in apply-styles. Header and footer
// are stateless functions that decide what to render per-page using:
//   - the most recent <chapter-opening> label (for opening-page detection)
//   - chapter-num-state / chapter-title-state (updated by chapter())
//
// This avoids any set page() calls mid-document, which Typst treats as a page
// break and would push body content off the chapter opening page.
// -----------------------------------------------------------------------------

// State updated by chapter() — read via .at(here()) inside header/footer.
#let chapter-num-state = state("chapter-num", none)
#let chapter-title-state = state("chapter-title", "")

// Locate the chapter-opening page that applies to the current page.
// Returns the page number of the most recent opening at or before here(),
// or none if there isn't one yet (e.g. covers/frontmatter).
#let _current-opening-page() = {
  let openings = query(<chapter-opening>)
  let cp = here().page()
  let preceding = openings.filter(o => o.location().page() <= cp)
  if preceding.len() == 0 { none } else { preceding.last().location().page() }
}

// Header — all components aligned to the outside edge, with a 0.5pt rule
// underneath spanning the text column. Suppressed on opening pages and
// before any chapter has started (covers/frontmatter).
//
//   Recto (odd):                            *บทที่ N*  Title  –  page
//                  ───────────────────────────────────────────────────
//
//   Verso (even):  page  –  Book Title
//                  ───────────────────────────────────────────────────
#let chapter-header = context {
  let opening-page = _current-opening-page()
  let cp = here().page()
  if opening-page == none { return }       // pre-chapter (covers)
  if cp == opening-page { return }         // chapter opening page

  let number = chapter-num-state.at(here())
  let title = chapter-title-state.at(here())
  let dash = sym.dash.en
  let en-space = h(0.5em)

  let label = if calc.odd(cp) {
    align(right)[*บทที่ #number*#en-space#title#h(0.3em)#dash#h(0.3em)#cp]
  } else {
    align(left)[#cp#h(0.3em)#dash#h(0.3em)#book-metadata.title]
  }

  set par(leading: 1em, spacing: 0.85em)
  text(size: 0.85em)[
    #label
    #line(length: 100%, stroke: 0.5pt)
  ]
}

// Footer — page number centered on the chapter-opening page only. Body pages
// carry the page number in the header instead. Pre-chapter pages get nothing.
#let chapter-footer = context {
  let opening-page = _current-opening-page()
  let cp = here().page()
  if opening-page != none and cp == opening-page {
    align(center, text(size: 0.85em)[#cp])
  }
}

// -----------------------------------------------------------------------------
// Proof-mode header/footer
//
//   Header (every body page):  Book Title      updated date      *บทที่ N*  Title
//                              ──────────────────────────────────────────────
//
//   Footer (every chapter page):                  page
//
// `updated` is the chapter's last-updated date, threaded in from apply-styles
// (set per chapter via #show: apply-styles.with(updated: ...)). It sits in the
// center so a proofreader can see which revision they are marking up. When no
// date is supplied it is `none`, leaving the center blank — book title and
// chapter/title then sit at the two edges exactly as before.
// -----------------------------------------------------------------------------
#let proof-header(updated: none) = context {
  let opening-page = _current-opening-page()
  let cp = here().page()
  if opening-page == none { return }       // pre-chapter (covers)
  if cp == opening-page { return }         // chapter opening page

  let number = chapter-num-state.at(here())
  let title = chapter-title-state.at(here())
  let em-space = h(1em)

  text(size: 0.85em)[
    #book-metadata.title #h(1fr) #updated #h(1fr) *บทที่ #number*#em-space#title
    #v(0.2em)
    #line(length: 100%, stroke: 0.5pt)
  ]
}

#let proof-footer = context {
  let opening-page = _current-opening-page()
  if opening-page == none { return }       // pre-chapter (covers)
  align(center, text(size: 0.85em)[#here().page()])
}
