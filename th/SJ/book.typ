// =============================================================================
// Main book entry point
// Always renders book mode (A5, book margins) — never proofs.
// Compiles the complete book by including all chapters in order.
// =============================================================================

#import "04_assets/template/lib.typ": *

// Force book layout for the whole document, including every included chapter.
// Chapter files carry `proofing: true` for standalone drafting; this flag (read
// by apply-styles) overrides that so the full build always renders as a book.
#book-mode.update(true)

#show: apply-styles

// -----------------------------------------------------------------------------
// Front matter
// -----------------------------------------------------------------------------
#include "04_assets/template/covers.typ"

// -----------------------------------------------------------------------------
// Chapters
// -----------------------------------------------------------------------------
#include "03_public/SJ01_th.typ"
#include "03_public/SJ02_th.typ"
#include "03_public/SJ03_th.typ"
#include "03_public/SJ04_th.typ"
#include "03_public/SJ05_th.typ"
#include "03_public/SJ06_th.typ"
#include "03_public/SJ07_th.typ"
#include "03_public/SJ08_th.typ"
#include "03_public/SJ09_th.typ"
#include "03_public/SJ10_th.typ"
#include "03_public/SJ11_th.typ"
#include "03_public/SJ12_th.typ"
#include "03_public/SJ13_th.typ"
#include "03_public/SJ14_th.typ"
#include "03_public/SJ15_th.typ"

// -----------------------------------------------------------------------------
// Back matter
// -----------------------------------------------------------------------------
// #include "04_assets/template/glossary.typ"
// #include "04_assets/template/index.typ"
