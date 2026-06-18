// =============================================================================
// Main book entry point
// Always renders book mode (A5, book margins) — never proofs.
// Compiles the complete book by including all chapters in order.
// =============================================================================

#import "04_assets/template/lib.typ": *

#show: apply-styles

// -----------------------------------------------------------------------------
// Front matter
// -----------------------------------------------------------------------------
#include "04_assets/template/covers.typ"

// -----------------------------------------------------------------------------
// Chapters
// -----------------------------------------------------------------------------
#include "02_edit/SC01_th.typ"
#include "02_edit/SC02_th.typ"
#include "02_edit/SC03_th.typ"
#include "02_edit/SC04_th.typ"
#include "02_edit/SC05_th.typ"
#include "02_edit/SC06_th.typ"
#include "02_edit/SC07_th.typ"
#include "02_edit/SC08_th.typ"
#include "02_edit/SC09_th.typ"

// -----------------------------------------------------------------------------
// Back matter
// -----------------------------------------------------------------------------
// #include "04_assets/template/glossary.typ"
// #include "04_assets/template/index.typ"
