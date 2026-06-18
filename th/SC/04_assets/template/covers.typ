// =============================================================================
// Covers
// Title page, copyright, dedication, and table of contents.
// Mode-agnostic: paper/margin come from apply-styles. Header and footer are
// auto-suppressed on pre-chapter pages by the smart chapter-header/chapter-footer
// functions, so no set page() is needed here.
// =============================================================================

#import "config.typ": book-metadata

// -----------------------------------------------------------------------------
// Title page
// -----------------------------------------------------------------------------
#align(center + horizon)[
  #text(size: 2.5em, weight: "regular")[#book-metadata.title]
  #v(2em)
  #text(size: 1.2em)[#book-metadata.author]
]

#pagebreak()

// -----------------------------------------------------------------------------
// Copyright / colophon
// -----------------------------------------------------------------------------
#align(center + bottom)[
  #text(size: 0.9em)[
    #datetime.today().year()
  ]
]

#pagebreak()


// -----------------------------------------------------------------------------
// Table of contents
// -----------------------------------------------------------------------------
#align(center)[
  #text(size: 1.2em)[
    *สารบัญ*
  ]
]
#outline(
  title: none,
  depth: 2,
)

#pagebreak()

