// =============================================================================
// Styles
// Show/set rules for headings, paragraphs, lists, and other elements.
// =============================================================================

#import "dictionary.typ": protect-words, apply-soft-hyphens
// Typography constants (fonts, sizes, leading, spacing) live in config.typ — the
// leaf module — so components can reference them without importing styles.
#import "config.typ": book-mode, text-lang, make-base, chapter-header, chapter-footer, proof-header, proof-footer, font-body, font-heading, size-body, size-small, size-large, book-leading, book-spacing, proof-leading, proof-spacing, ellipsis-gap
// EGW tag, so the ```poetry eval can resolve it in its scope (see poetry-styles).
#import "components.typ": EGW

// -----------------------------------------------------------------------------
// Heading styles
// -----------------------------------------------------------------------------
#let heading-styles(body) = {
  show heading.where(level: 1): it => {
    set par(leading: 1em)
    set text(size: 1.4em, weight: "light", font: font-heading)
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
// `leading` (between lines) and `spacing` (between paragraphs) are both
// parameterized so apply-styles can widen them for proof mode. See the note by
// book-leading/book-spacing in config.typ — for a book, keep the two equal.
// -----------------------------------------------------------------------------
#let paragraph-styles(leading: 1em, spacing: 1em, body) = {
  set par(
    justify: true,
    linebreaks: "optimized",
    leading: leading,
    first-line-indent: (amount: 1.75em,),
    justification-limits: (
      spacing: (min: 100%, max: 120%),
      tracking: (min: -0.01em, max: 0.025em, emergency: 0.05em),
      glyph-scale: (min: 98%, max: 104%),
    ),
    spacing: spacing,
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

// -----------------------------------------------------------------------------
// Poetry / verse styles
// A ```poetry fenced block is re-rendered as indented markup: each source line
// becomes a forced linebreak and leading spaces become horizontal space.
// Must be applied through apply-styles — a bare top-level show rule in an
// imported module never runs.
// -----------------------------------------------------------------------------
#let poetry-styles(body) = {
  show raw.where(lang: "poetry"): it => {
    set par(leading: book-leading)
    set text(font: font-body, size: size-body)
    set raw(theme: none)
    let space-width = 0.5em
    block(
      inset: (x: 1.5em, y: 0.825em),
      eval(
        it.text
          .replace(regex("\\n\\n+"), "#parbreak()")
          .replace(regex("\\n( *)"), (i) => {
            "\ "
            if i.captures.at(0).len() > 0 { "#h(" + repr(i.captures.at(0).len() * space-width) + ")" }
          }),
        mode: "markup",
        scope: (EGW: EGW),
      )
    )
  }
  body
}


// -----------------------------------------------------------------------------
// Ellipsis styles
// Spaced ellipses (3-dot ". . ." and 4-dot ". . . .") render with a thin space
// between dots, boxed so the ellipsis never breaks across a line. The source
// keeps the readable ". . ." form; the dot count is preserved (so the 4-dot
// sentence-period-plus-ellipsis stays four dots).
// -----------------------------------------------------------------------------
#let ellipsis-styles(body) = {
  // Optionally swallow the space before the dots so the ellipsis can be glued to
  // the word before it — a line never starts with dots. Glue: a no-break space
  // when there was a space, else a zero-width word joiner (keeps "Me." attached).
  show regex("( ?)\\.(?: \\.){2,}"): it => {
    let n = it.text.trim().split(" ").len()
    if it.text.starts-with(" ") { "\u{00A0}" } else { "\u{2060}" }
    box(((".",) * n).join(h(ellipsis-gap)))
  }
  body
}

// -----------------------------------------------------------------------------
// Keep the citation tag from ever sitting alone on a paragraph's final line by
// gluing it to the word before it (the space before the tag box becomes
// non-breaking). Done at the paragraph level — `show par` runs after eval but
// before layout, so it sees the whole paragraph structure (text runs, smart-
// quote elements, the trailing tag box) and its edit still steers line-breaking.
// Only paragraphs whose LAST child is a box (the EGW tag) are touched, so titles,
// running headers, the TOC, ellipses, and untagged paragraphs are left alone, and
// smart quotes stay intact (they are sibling elements, never re-typed). The runt
// cost in apply-styles is the soft backstop for an otherwise-short last line.
// NOTE: this does NOT force a 2-word minimum — stock Typst has no soft rule for
// that; a forced 2-word glue loosens the line above. Natural breaking gives 2+
// words in most paragraphs anyway.
// -----------------------------------------------------------------------------
#let keep-tail-together(body) = {
  // Earlier text-regex attempts (kept for reference): a text show-rule can't see
  // into the tag box, so it also fired on titles/ellipses/other quotes, and
  // re-emitting it.text dropped smart-quote conversion.
  //   show regex("(?m)\\S+ \\S+$"): it => it.text.replace(" ", "\u{00A0}")
  //   show regex("(?m)\\S+ \\S+$"): it => text(fill: red)[#it.text.replace(" ", "\u{00A0}")]
  //   show regex("(?m)\\S+ \\S+$"): it => box(text(fill: blue, it))

  show par: it => {
    if "children" not in it.body.fields() { return it }
    let kids = it.body.children
    let n = kids.len()
    if n < 2 or kids.last().func() != box { return it }
    // Glue ONLY the tag to its preceding word: turn the space just before the tag
    // box into a non-breaking one, so the tag can never be orphaned alone on a
    // line. (Gluing a rigid two-word block instead over-constrained the break and
    // loosened the line above, so we don't.)
    kids.enumerate().map(((j, c)) =>
      if j == n - 2 and repr(c.func()) == "space" { "\u{00A0}" } else { c }
    ).sum(default: [])
  }

  // ── Alternative, kept for records: glue the last TWO words together (not just
  // the tag). Guarantees a 2-word minimum on the last line, but force-gluing a
  // rigid block over-constrains the break and leaves the line above loose:
  //   show par: it => {
  //     if "children" not in it.body.fields() { return it }
  //     let kids = it.body.children
  //     let texts = kids.enumerate().filter(((j, c)) => c.func() == text)
  //     if kids.len() == 0 or kids.last().func() != box or texts.len() == 0 { return it }
  //     let ti = texts.last().at(0)                // last text run, before the tag box
  //     let t = kids.at(ti).text
  //     let m = t.match(regex("(\\S+) (\\S+)$"))    // its last two words
  //     if m == none { return it }
  //     let head = t.slice(0, m.start)
  //     let last2 = text(hyphenate: false, m.text.replace(" ", "\u{00A0}"))
  //     let after = kids.slice(ti + 1).map(c => if repr(c.func()) == "space" { "\u{00A0}" } else { c }).sum(default: [])
  //     kids.slice(0, ti).sum(default: []) + head + last2 + after
  //   }

  body
}

// -----------------------------------------------------------------------------
// apply-styles — single document-level setup.
// Sets paper, base margin, default footer, text settings, and all show rules.
// proofing: false → A5 book layout. proofing: true → A4 with equal margins.
// updated → last-updated date string, shown centered in the proof header only.
// Use as: #show: apply-styles                       (book mode, in book.typ)
//         #show: apply-styles.with(proofing: true)  (proof mode, in chapter files)
//         #show: apply-styles.with(proofing: true, updated: "17 มิถุนา 2026")
//
// A full-book build flips book-mode on (see config.typ + book.typ). Because the
// body is wrapped in `context`, the page setup is decided at layout time and can
// read that flag: when set, it overrides any chapter's own `proofing: true` so the
// whole document renders as a book. A standalone chapter compile leaves the flag
// at its default (false) and proofs exactly as before.
// -----------------------------------------------------------------------------
#let apply-styles(proofing: false, updated: none, body) = context {
  // The full-book build overrides each chapter's own proofing flag (see book-mode
  // in config.typ) so the entire document renders as a book.
  let proofing = proofing and not book-mode.get()
  // runt: 400% rescues a last line that would hold ONLY the citation tag (pulls
  // one word down). It can't guarantee 2+ words — Typst has no minimum-words knob,
  // so higher values do nothing more. For a hard 2-word rule, glue with `~`.
  set text(font: font-body, size: size-body, costs: (runt: 400%), ..text-lang)
  set page(
    ..make-base(proofing: proofing),
    header: if proofing { proof-header(updated: updated) } else { chapter-header },
    footer: if proofing { proof-footer } else { chapter-footer },
  )
  show: heading-styles
  show: paragraph-styles.with(
    leading: if proofing { proof-leading } else { book-leading },
    spacing: if proofing { proof-spacing } else { book-spacing },
  )
  show: footnote-styles
  show: poetry-styles
  // Manual `\n` breaks in a chapter title should collapse to a space in TOC.
  show outline.entry: it => { show linebreak: it2 => [ ]; it }
  show: ellipsis-styles
  show: keep-tail-together
  show: protect-words
  show: apply-soft-hyphens
  body
}
