// =============================================================================
// Styles
// Show/set rules for headings, paragraphs, lists, and other elements.
// =============================================================================

#import "dictionary.typ": protect-words, apply-soft-hyphens
#import "config.typ": text-lang, make-base, chapter-header, chapter-footer, proof-header, proof-footer

// -----------------------------------------------------------------------------
// Font families
// List multiple fonts for fallback - Typst uses the first available.
// -----------------------------------------------------------------------------
#let font-body = ("Sarabun", "Noto Sans Thai")
#let font-heading = ("Sarabun", "Noto Sans Thai")

// -----------------------------------------------------------------------------
// Text sizing
// -----------------------------------------------------------------------------
#let size-body = 12pt
#let size-small = 9pt
#let size-large = 14pt

// -----------------------------------------------------------------------------
// Heading styles
// -----------------------------------------------------------------------------
#let heading-styles(body) = {
  show heading.where(level: 1): it => {
    set text(size: 1.4em, weight: "light", font: font-heading)
    v(0.3em)
    it
    v(0.3em)
  }

  show heading.where(level: 2): it => {
    set text(size: 1.2em, weight: "bold", font: font-heading)
    v(0.3em)
    it
    v(0.2em)
  }

  show heading.where(level: 3): it => {
    set text(size: 1em, weight: "bold", font: font-heading)
    v(0.3em)
    it
    v(0.2em)
  }

  body
}

// -----------------------------------------------------------------------------
// Paragraph styles
// `leading` is parameterized so apply-styles can widen it for proof mode
// (room to write between lines on a printout).
// -----------------------------------------------------------------------------
#let paragraph-styles(leading: 1.2em, body) = {
  set par(
    justify: true,
    linebreaks: "optimized",
    leading: leading,
    first-line-indent: (amount: 1.5em,),
    justification-limits: (
      spacing: (min: 100%, max: 120%),
      tracking: (min: -0.01em, max: 0.025em, emergency: 0.05em),
      glyph-scale: (min: 98%, max: 104%),
    ),
  )
  body
}

// -----------------------------------------------------------------------------
// Footnote styles
// -----------------------------------------------------------------------------
#let footnote-styles(body) = {
  set footnote.entry(
    separator: line(length: 30%, stroke: 0.5pt),
    //indent: 1em,
  )
  show footnote.entry: set text(size: size-small)
  body
}

// Leading values per mode. Bump proof-leading higher for more annotation room.
#let book-leading = 1.2em
#let proof-leading = 1.7em

// -----------------------------------------------------------------------------
// apply-styles — single document-level setup.
// Sets paper, base margin, default footer, text settings, and all show rules.
// proofing: false → A5 book layout. proofing: true → A4 with equal margins.
// Use as: #show: apply-styles                       (book mode, in book.typ)
//         #show: apply-styles.with(proofing: true)  (proof mode, in chapter files)
// -----------------------------------------------------------------------------
#let apply-styles(proofing: false, body) = {
  set text(font: font-body, size: size-body, ..text-lang)
  set page(
    ..make-base(proofing: proofing),
    header: if proofing { proof-header } else { chapter-header },
    footer: if proofing { proof-footer } else { chapter-footer },
  )
  show: heading-styles
  show: paragraph-styles.with(leading: if proofing { proof-leading } else { book-leading })
  show: footnote-styles
  show: protect-words
  show: apply-soft-hyphens
  body
}
