// =============================================================================
// Components
// Custom elements: chapter opener, callouts, illustrations, etc.
// Components are mode-agnostic — paper and base margin come from apply-styles
// in lib.typ. Components only override header/footer (and margin for
// illustrations) via set page rules.
// =============================================================================

#import "config.typ": chapter-num-state, chapter-title-state, chapter-opening-top-space, illustration-margin, font-heading

// -----------------------------------------------------------------------------
// Chapter opener
// First page: header off, footer = page number, extra top space pushed in
// with v(...). Subsequent pages: body header showing the chapter title.
// -----------------------------------------------------------------------------
#let chapter(number: 0, title: "", basedon: "") = {
  counter(footnote).update(0)
  pagebreak(weak: true)
  // Update state instead of calling set page — apply-styles installed the
  // smart header/footer once at document level, and they read this state.
  chapter-num-state.update(number)
  // Running header gets a single-line title: collapse any manual `\n` breaks
  // (used to wrap the centered opener title) back into spaces. eval(.., markup)
  // re-parses the title string as markup so its quotes/apostrophes get smart-
  // quoted (a plain string is inserted as raw text and would stay straight).
  chapter-title-state.update(eval(title.replace("\n", " "), mode: "markup"))

  [#metadata(none)<chapter-opening>]

  v(chapter-opening-top-space)
  align(center, {
    text(size: 1.7em, weight: "light", font: font-heading)[Chapter #number]
    // A `\n` in the title becomes a manual (centered) line break; each line is
    // eval'd as markup so its quotes/apostrophes are smart-quoted.
    heading(level: 1, numbering: none,
      title.split("\n").map(s => eval(s, mode: "markup")).join(linebreak()))
    v(0.5em)
    if basedon != "" {
      text(size: 0.9em, style: "italic")[Based on: #basedon]
      v(1em)
    }
  })
  // Restore the first-line indent on the chapter's opening paragraph.
  // Typst suppresses first-line-indent on the first paragraph after a block,
  // and the opening paragraph lives in the chapter file *after* this call, so a
  // trailing h() here just lands in its own line (the bug we had). Instead emit
  // an invisible, zero-height paragraph to occupy the "first paragraph after a
  // block" slot; the real opening paragraph below then gets the normal indent.
  // (Preferred over first-line-indent's `all: true`, which would also indent
  // footnotes, headings, and the centered title text.)
  {
    set text(size: 0pt)
    set par(leading: 0pt, spacing: 0pt)
    box()
    parbreak()
  }
}

// -----------------------------------------------------------------------------
// Illustration page
// Tighter margins, no header/footer. The next chapter() call will reset
// header/footer; margin persists until the next chapter (acceptable since
// illustrations are typically chapter-bookended).
// -----------------------------------------------------------------------------
#let illustration(path, caption: none, width: 100%) = {
  pagebreak()
  set page(margin: illustration-margin, header: none, footer: none)
  align(center + horizon)[
    #image(path, width: width)
    #if caption != none {
      v(1em)
      text(size: 0.9em, style: "italic")[#caption]
    }
  ]
  pagebreak()
}

// -----------------------------------------------------------------------------
// Callout box
// For notes, warnings, asides.
// -----------------------------------------------------------------------------
#let callout(type: "note", body) = {
  let colors = (
    note: rgb("#e7f3ff"),
    warning: rgb("#fff4e5"),
    quote: rgb("#f5f5f5"),
  )
  let bg = colors.at(type, default: colors.note)

  block(
    fill: bg,
    inset: 1em,
    radius: 4pt,
    width: 100%,
    body,
  )
}

// -----------------------------------------------------------------------------
// Scripture / verse reference
// Inline reference formatting.
// -----------------------------------------------------------------------------
#let scripture(ref) = {
  text(style: "italic")[#ref]
}

// -----------------------------------------------------------------------------
// Italic markdown text
// with no spaces there is an "unclosed delimiter" error
// -----------------------------------------------------------------------------
#let italic(words) = {
  text(style: "italic")[#words]
}

// -----------------------------------------------------------------------------
// Soft line break (HTML-style `<br>`): a forced break within a paragraph, with
// the broken line justified to the measure. Type `#br` in the text; no first-
// line indent or paragraph spacing is added. Searchable/removable via `#br`.
// -----------------------------------------------------------------------------
#let br = linebreak(justify: true)

// ─── EGW inline source-reference marker ──────────────────────────────────────
// Placed at the end of each paragraph to cite the original EGW paragraph number.
// Styled small and muted so it does not compete with the body text.

#let EGW(content) = box(
  text(
    size: 0.75em,
    //fill: luma(170),
    weight: "regular",
    content
  )
)

