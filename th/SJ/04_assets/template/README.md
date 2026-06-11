# Thai Book Project

Typst book template with two output modes (final book / proof) and a Thai
word-protection layer that prevents ICU4X line-segmentation from breaking
words mid-syllable.

## Structure

Paths below are relative to the **book root** (`th/SJ/`), which is also the
Typst project root — every path inside the book resolves from here.

```text
SJ/                             # book root = Typst project root
├── book.typ                    # Main entry — compiles the full book
├── typst-custom                # Custom Typst binary (git-ignored; build/obtain separately)
├── 01_raw/                     # Draft-stage chapters (earlier in the pipeline)
├── 02_edit/                    # Editing-stage chapters
├── 03_public/                  # Finalized chapters — what book.typ includes (SJ01_th.typ …)
└── 04_assets/
    ├── template/
    │   ├── lib.typ             # Facade — the ONLY file chapters import
    │   ├── config.typ          # Metadata, page sizing, header/footer logic
    │   ├── styles.typ          # Fonts, sizing, headings, paragraphs, apply-styles
    │   ├── components.typ      # chapter(), illustration(), callout(), EGW(), italic(), …
    │   ├── covers.typ          # Title page, copyright, TOC
    │   └── dictionary.typ      # Protected words + soft-hyphen hints
    ├── images/                 # Illustration images (reference as /04_assets/images/…)
    └── thai_original_pdfs/     # Source PDFs of the Thai original
```

The custom `typst-custom` binary is intentionally not tracked in git — it is
shared across other workflows, so build or obtain it separately and place it at
the book root.

## Compiling

Run from the book root (`th/SJ/`):

```bash
# Full book (always book mode — iso-b5). No --root needed: book.typ sits at
# the project root, so its includes (03_public/…, 04_assets/…) resolve directly.
./typst-custom compile book.typ book.pdf

# Single chapter for drafting. A chapter imports the template with a path that
# climbs out of 03_public/, so the project root must be set to the book root:
./typst-custom compile --root . 03_public/SJ01_th.typ SJ01.pdf
```

## Writing a chapter

Every chapter starts with the same boilerplate. Note the import path reaches
the template in `04_assets/` from `03_public/`:

```typst
#import "../04_assets/template/lib.typ": *
#show: apply-styles.with(proofing: false)

#chapter(
  number: 1,
  title: "การประสูติของพระเยซู",
  basedon: "ลูกา 2",   // optional — omit if not used
)

// chapter body below
```

Chapters import only `lib.typ`. If something is missing, add it to the facade.
Because Typst's `#include` does not pass `book.typ`'s imports into the included
file, **every chapter must carry this boilerplate itself.**

## Output modes

`apply-styles` takes a `proofing:` flag that swaps page geometry, leading,
and the running header/footer.

| | Book (`proofing: false`) | Proof (`proofing: true`) |
|---|---|---|
| Paper | iso-b5 | A4 |
| Margins (mm) | top 25 / bottom 16 / outside 16 / inside 24 (asymmetric, inside binding) | top 36 / bottom 20 / left 24 / right 24 (equal sides) |
| Leading | 1.2em | 1.7em (room to write between lines) |
| Header | verso: `page – Book Title` · recto: `*บทที่ N* Title – page` (right) | same on every body page: `Book Title` (left) · `*บทที่ N* Title` (right) |
| Page number | in header on body pages; footer-center on the opening page | footer-center on every page |

Both modes share the same chapter opener, body styles, fonts, and
word-protection rules. Switch by changing the `proofing:` argument in the
chapter file (or in `book.typ` for the full build).

## Configuration

Everything user-tunable lives in two files:

### `template/config.typ`

```typst
#let book-metadata = (
  title: "ชื่อหนังสือ",
  author: "ผู้เขียน",
  language: "th",
)
```

`title` shows up in the running header. `author` shows on the title page
and in the © line on the copyright page.

`make-base(proofing: ...)` controls paper + margins per mode.
`chapter-opening-top-space` (default `16mm`) pushes the chapter title down
on the opener.

### `template/styles.typ`

```typst
#let font-body    = ("Sarabun", "Noto Sans Thai")
#let font-heading = ("Sarabun", "Noto Sans Thai")

#let size-body  = 12pt
#let size-small = 9pt
#let size-large = 14pt

#let book-leading  = 1.2em
#let proof-leading = 1.7em
```

No fonts are bundled with the project — the named families (Sarabun, with
Noto Sans Thai as fallback) must be available to Typst when compiling.

Heading sizes/weights and footnote styling live in the same file in the
`heading-styles` and `footnote-styles` show-rule blocks.

## Components

Available from `lib.typ`:

- `chapter(number:, title:, basedon: "")` — chapter opener (centered title,
  optional source line, body header takes over from the next page).
- `illustration(path, caption: none, width: 100%)` — full-page image,
  no header/footer, tight margins. Reference images with a root-absolute path,
  e.g. `illustration("/04_assets/images/birth.png")`.
- `callout(type: "note" | "warning" | "quote", body)` — colored info block.
- `scripture(ref)` — italicized inline reference.
- `italic(words)` — inline italic span; use when the italic text has no
  surrounding spaces (bare `_..._` would raise an "unclosed delimiter" error).
- `EGW(content)` — small grey paragraph-source marker (used at end of EGW
  paragraphs, e.g. `#EGW[\{SJ 17.1\}]`).

## Thai word protection

Thai has no spaces between words. Typst uses ICU4X to guess word boundaries
for line-breaking, but its dictionary doesn't know proper nouns or
religious vocabulary, so it sometimes breaks words like `พระเยซู` in the
middle. The template solves this with two complementary mechanisms in
`template/dictionary.typ`, both auto-applied by `apply-styles`. Source
text stays unmarked — you write `พระเยซู` normally and the template
handles the rest.

### 1. Protected words (no breaks)

Words in the `protected-words` list are wrapped in `box[]`, which forbids
any line break inside.

```typst
#let protected-words = (
  // longest first — see ordering rule below
  (word: "พระวิญญาณบริสุทธิ์", parts: ("พระวิญญาณ", "บริสุทธิ์")),
  (word: "พระเยซูคริสต์",      parts: ("พระเยซู", "คริสต์")),
  (word: "ทูตสวรรค์",          parts: ("ทูต", "สวรรค์")),
  (word: "พระเยซู",            parts: none),
  (word: "พระเจ้า",            parts: none),
  (word: "สวรรค์",             parts: none),
)
```

- `parts: none` — single unbreakable box. The word will never break, full stop.
- `parts: ("a", "b")` — boxes for each part joined by an invisible soft
  hyphen. The only break point allowed inside the word is between `a`
  and `b`, and the soft hyphen renders only when that break is actually
  used.

To add a word: append a new entry. Use `parts:` only when the word is
long enough that forbidding all breaks would damage justification.

### 2. Soft-hyphen hints (preferred break points)

Words in `soft-hyphen-words` are *not* boxed — Thai segmentation can still
break them anywhere — but a soft hyphen is inserted at the marked split
to nudge the line-breaker toward a sensible break.

```typst
#let soft-hyphen-words = (
  "ความชื่นชม-ยินดี",
  "การ-อธิษฐาน",
  "จิต-วิญญาณ",
  "อาณา-จักร",
)
```

Format: write the word with a `-` at the preferred break point. The rule
strips the hyphen for matching and inserts a real soft hyphen at that
position when rendering.

To add a hint: append the word with `-` at the desired break.

### Choosing between the two

| Use protect-words when… | Use soft-hyphen-words when… |
|---|---|
| The word should never break, or only break at one specific spot | The word can break anywhere but you want to nudge it toward a particular spot |
| Proper nouns, sacred names, brand-like terms | Common compounds with one obvious good break point |

If a word appears in both lists, the box wins (protect-words runs first)
and the soft hyphen has no effect.

### CRITICAL: ordering rule

Within each list, **longer terms must come before any shorter term they
contain**. The show rules run in order, so if `พระ` is matched first,
later compounds like `พระเยซู` will already have been split apart and
won't match. List longest-first and you're safe. (For example, `ทูตสวรรค์`
must precede the standalone `สวรรค์`, and `มหาปุโรหิต` must precede `ปุโรหิต`.)

## Per-chapter state

- **Footnote numbering** resets at the start of each chapter
  (`counter(footnote).update(0)` inside `chapter()`).
- **Running headers** read `chapter-num-state` / `chapter-title-state`,
  which `chapter()` updates. `chapter()` updates this state instead of
  calling `set page()`, so no forced page break happens mid-document.
  (`illustration()` is the one deliberate `set page()` exception, for its
  tighter margins and suppressed header/footer.)
- **Chapter numbering** is passed explicitly via `number:`.

## Customizing — quick reference

| Change | File | Where |
|---|---|---|
| Book title / author | `config.typ` | `book-metadata` |
| Page size or margins | `config.typ` | `make-base` |
| Chapter opener top space | `config.typ` | `chapter-opening-top-space` |
| Running header layout | `config.typ` | `chapter-header` / `proof-header` |
| Fonts | `styles.typ` | `font-body`, `font-heading` |
| Body / footnote sizes | `styles.typ` | `size-body`, `size-small` |
| Leading per mode | `styles.typ` | `book-leading`, `proof-leading` |
| Heading appearance | `styles.typ` | `heading-styles` |
| Add a new component | `components.typ` | new `#let` |
| Protect a Thai word | `dictionary.typ` | `protected-words` (longest first) |
| Soft-hyphenate a Thai word | `dictionary.typ` | `soft-hyphen-words` |
