// ─── SC Chapter Template ──────────────────────────────────────────────────────
// Reusable template for Steps to Christ (SC) Thai translation.
//
// Exports:
//   sc-template(book-title-th: "...", doc) — apply as a show rule
//   sc-chapter(number: N, title: "...")    — chapter heading + header state
//   EGW(content)                           — inline source-reference marker
//
// Typical usage in a compile wrapper:
//   #import "SC_template.typ": sc-template, sc-chapter as chapter, EGW
//   #show: sc-template.with(book-title-th: "ก้าวสู่พระคริสต์")
//   #include "SCxx_th.typ"

// ─── State for running headers ────────────────────────────────────────────────

#let _ch-title  = state("sc-chapter-title",  "")
#let _ch-number = state("sc-chapter-number", 0)

// ─── EGW inline source-reference marker ──────────────────────────────────────
// Placed at the end of each paragraph to cite the original EGW paragraph number.
// Styled small and muted so it does not compete with the body text.

#let EGW(content) = text(
  size: 0.72em,
  fill: luma(170),
  weight: "regular",
  content
)

// ─── Chapter heading ──────────────────────────────────────────────────────────
// Stores title/number in state (used by the running header) and renders the
// chapter title block.

#let sc-chapter(number: 1, title: "") = {
  _ch-title.update(title)
  _ch-number.update(number)

  v(1.5em)
  align(center,
    text(size: 0.85em, fill: luma(130), tracking: 0.06em)[
      บทที่ #number
    ]
  )
  v(0.5em)
  align(center,
    text(size: 1.4em, weight: "bold")[#title]
  )
  v(2.0em)
}

// ─── Page template ────────────────────────────────────────────────────────────
// Apply with: #show: sc-template.with(book-title-th: "...")

#let sc-template(
  book-title-th: "ก้าวสู่พระคริสต์",
  doc,
) = {

  // ── Page geometry and running header/footer ──────────────────────────────

  set page(
    paper: "a4",
    margin: (top: 2.8cm, bottom: 2.8cm, left: 2.0cm, right: 2.0cm),

    header: context {
      let title = _ch-title.get()
      // Suppress header on the first page (chapter-title page)
      if title != "" and here().page() > 1 [
        #v(-0.3em)
        #grid(
          columns: (1fr, 1fr),
          align(left  + horizon, text(size: 0.78em, fill: luma(135))[#book-title-th]),
          align(right + horizon, text(size: 0.78em, fill: luma(135))[#title]),
        )
        #v(0.2em)
        #line(length: 100%, stroke: 0.4pt + luma(205))
      ]
    },

    footer: context {
      align(center, text(size: 0.8em, fill: luma(155))[#here().page()])
    },
  )

  // ── Typography ────────────────────────────────────────────────────────────

  // LaTeX draft used 17pt; 13pt here gives a generous draft size without being
  // extreme. Increase to 14–15pt if you want more annotation space.
  set text(
    font: ("Thongterm", "Noto Serif Thai", "Libertinus Serif"),
    size: 13pt,
    lang: "th",
  )

  // "optimized" linebreaks (the default when justify:true) has a known Typst bug
  // with Thai: it fails to suppress spaces after line breaks, producing lines
  // that start with a visible gap. "simple" uses greedy left-to-right breaking
  // instead, which sidesteps the bug. The quality tradeoff is negligible for Thai
  // because Typst has no Thai word-segmentation dictionary to optimise against.
  //
  // LaTeX used \doublespacing; 1.4em leading here gives comfortable draft
  // breathing room without going as far as true double-spacing.
  // first-line-indent mirrors LaTeX's \parindent=.5in + indentfirst=true (Thai
  // convention indents every paragraph including the first).
  set par(
    justify: true,
    linebreaks: "simple",
    leading: 1.4em,
    spacing: 1.4em,
    first-line-indent: (amount: 1.5em, all: true),
  )

  // Relax the "runt" penalty so the algorithm accepts a short last line rather
  // than stretching an earlier line to avoid it. (Requires Typst 0.11+.)
  // widow/orphan costs are already non-zero by default in Typst; explicit here
  // to match LaTeX's \widowpenalty=10000.
  set text(costs: (runt: 30%, widow: 200%, orphan: 200%))

  // Soft-hyphen hints: allow line breaks after พระ- in common compounds so the
  // prefix can hang on the previous line.
  let _words = (
    "กาลา-เทีย",
    "ข้า-พระองค์",
    "ข้อ-ความ",
    "ทูต-สวรรค์",
    "ประสบ-การณ์",
    "ปลอด-ภัย",
    "พระ-เจ้า",
    "พระ-คริสต์",
    "พระ-บิดา",
    "พระ-องค์",
    "พลับ-พลา",
    "ศักดิ์-สิทธิ์",
    "สม-ควร",
    "หมาย-ความ",
    "เยี่ยม-เยียน",
    "ฟ้า-สวรรค์"
  )
  show: it => _words.fold(it, (it, word) => {
    show word.replace("-", ""): word.replace("-", sym.hyph.soft)
    it
  })

  // Unbreakable proper nouns: wrap in box() so they are never split across a
  // line break. Add names here as you encounter them in the text.
  let _nobreak = (
    "คาสาอัน",
    "ซาตาน",
    "ปัสกา",
    "ฟาโรห์",
    "มานา",
    "มิเดียน",
    "ยาห์เวห์",
    "ยาโคบ",
    "สะบาโต",
    "อามาเลข",
    "อาโรน",
    "อิสยาห์",
    "อิสอัค",
    "ฮีบรู",
    "เยโธร",
    "เรฟีดิม",
    "เอโดม",
    "เฮอร์",
    "โมอับ",
    "โมเสส",
    "โยเซฟ",
    "โฮเรบ"
  )
  show: it => _nobreak.fold(it, (it, word) => {
    show word: w => box(w)
    it
  })

  // Level-3 headings (=== syntax used in some SC/PP chapters)
  // afterskip mirrors LaTeX's .25\baselineskip after section
  show heading.where(level: 3): it => block({
    v(0.75em)
    text(size: 1.0em, weight: "semibold")[#it.body]
    v(0.25em)
  })

  // LaTeX footnotes: \bfseries\fontsize{10pt}{12pt} — bold, slightly smaller
  show footnote.entry: set text(size: 10pt, weight: "bold")
  set footnote.entry(separator: line(length: 30%, stroke: 0.5pt + luma(160)))

  doc
}
