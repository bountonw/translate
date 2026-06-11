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
#include "03_public/SJ01_th.typ"
#include "03_public/SJ02_th.typ"
#include "03_public/SJ03_th.typ"
#include "03_public/SJ04_th.typ"
#include "03_public/SJ05_th.typ"
#include "03_public/SJ06_th.typ"

// -----------------------------------------------------------------------------
// Back matter
// -----------------------------------------------------------------------------
// #include "04_assets/template/glossary.typ"
// #include "04_assets/template/index.typ"
