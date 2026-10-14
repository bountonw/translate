# Prior Thai translation of Steps to Christ

This directory holds the Thai translation of *Steps to Christ* that already exists, kept for reference. Nothing here is the project's own output: the project's chapters live in `th/SC/01_raw/`, `02_edit/` and `03_public/`. Nothing here is translated, edited or improved; where the printed book is wrong, the file is wrong in the same way.

The project is a new translation, not a revision of this edition. The files are reference only and never precedent: a rendering here is weighed like any other candidate and taken only where it is the best in its passage, and the project's wording is never changed to match it. th/SC/CLAUDE.md 2.G says how the rounds use it.

    print/   the published edition, "เคล็ดลับแห่งความสุข" (สำนักพิมพ์ข่าวประเสริฐ), as the EGW Writings app carries it: book 14099, code ThSC

## What is in `print/`

One file per chapter, `SC01_print_th.typ` through `SC13_print_th.typ`, plus `SC00_preface_print_th.typ` for the publisher's preface (คำนำ), which is the Thai publisher's own text and not the English preface in `th/SC/00_source/SC00_forword_en.md`. Each file is Typst body text with no preamble, as in `th/DA/04_assets/editions/print/`. Each paragraph is preceded by a `// {SC 57.2}` comment and closes with `#EGW[\{SC 57.2\}]`. The chapter title is a `// TITLE:` comment. A paragraph without a code is kept under `// no tag in the print`; the seven are all in the preface. The thirteen chapters carry 273 coded paragraphs, one for every paragraph of the English chapters.

`EXTRACTION-NOTES.tsv` lists every place the extraction decided something: each page break dropped, with its page number, so a paragraph's print page can be found; each poem joined to its source line; the one paragraph joined to the next; each code supplied, corrected or dropped under `RENUMBERED.tsv`; and each paragraph without a code.

## Where the text comes from

The source is the EGW Writings app's data for the book, the zip `~/programming/bible/egw-download/egw-data/PWBRSPX93T.com.whiteestate.library/Application Support/zips/th/1099/14099.zip`: one JSON file per chapter, each a list of paragraph objects whose content is the paragraph's HTML with the English code `{SC page.n}` at its end. Git ignores zip files, so the zip is not in the repository. `th/SC/04_assets/scripts/sc_print_extract.py` reads it; its opening lines list everything the extraction changes. To rebuild:

    python3 th/SC/04_assets/scripts/sc_print_extract.py th/SC/04_assets/editions/print \
        --renumber th/SC/04_assets/editions/print/RENUMBERED.tsv \
        --report th/SC/04_assets/editions/print/EXTRACTION-NOTES.tsv

## The paragraph numbers

The English codes of the Ellen G. White Estate are taken as correct, and every English paragraph has exactly one Thai paragraph under its code, in the English order: 273 in all. The data sets a code on 258 chapter paragraphs, 253 of them right. `RENUMBERED.tsv` corrects the 5 the data sets one or two paragraphs behind or repeats (chapter 1 at 9.2 and 9.3, chapter 3 at 25.2 and 25.3, chapter 12 at 111.3), supplies the 15 the data leaves without a code (one in chapter 1, two in chapter 3, twelve in chapter 13), joins the two paragraphs the data makes of {SC 45.1}, and drops the code the preface's quotation of {SC 49.2} carries so that a search for the code finds the chapter. No Thai word is changed or moved by this. Each line gives the paragraph, the printed code, the action, the code it became and the English words that open the paragraph; each was checked by reading the Thai against the English paragraph, and the script's last lines compare every file's codes with the English source and print one line per chapter.
