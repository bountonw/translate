# Prior Thai translation of The Desire of Ages

This directory holds the Thai translation of *The Desire of Ages* that already exists, kept for reference. Nothing here is the project's own output: the project's chapters live in `th/DA/01_raw/`, `02_edit/` and `03_public/`. Nothing here is translated, edited or improved; where the printed book is wrong, the file is wrong in the same way. The one exception is a mark the print sets twice on one letter, which overlaps on the page and is kept once; the notes file lists the seven.

    print/   the published edition, "ผู้พึงปรารถนาของปวงชน" (สำนักพิมพ์ข่าวประเสริฐ, 2023)

## What is in `print/`

One file per chapter, `DA01_print_th.typ` through `DA87_print_th.typ`, plus `DA00_preface_print_th.typ` for the publishers' preface (บทนำ). Each file is Typst body text with no preamble, as in `th/GC/04_assets/editions/print/`. Each paragraph is preceded by a `// {DA 19.1}` comment and closes with `#EGW[\{DA 19.1\}]`. The chapter title is a `// TITLE:` comment and the "based on" line a `// BASEDON:` comment. A paragraph the print sets without a tag is kept under `// no tag in the print`.

`EXTRACTION-NOTES.tsv` lists every place the extraction decided something or found the print irregular: each hyphen dropped at a line break, each pull quote and chapter-end filler left out (with its full text), each paragraph without a tag, each doubled mark, each title taken from the contents, and each English tag the print does not carry, carries twice, or carries wrongly.

## Where the text comes from

The source is `AW_ผู้พึงปรารถนาของปวงชน (72 res).pdf`, the whole book in one file of 1,098 pages, inside the zip in `th/DA/04_assets/`. Git ignores zip files, so the PDF is not in the repository. The zip also holds the same book in five volumes.

The PDF's fonts map many marks to the wrong character, but each such glyph carries the right text in an ActualText span, and `th/DA/04_assets/scripts/da_th_extract.py` reads those spans. Its opening lines list everything the extraction changes. To rebuild:

    qpdf --qdf --object-streams=disable --stream-data=uncompress \
        "/path/to/AW_ผู้พึงปรารถนาของปวงชน (72 res).pdf" /tmp/da-th.pdf
    python3 th/DA/04_assets/scripts/da_th_extract.py /tmp/da-th.pdf \
        th/DA/04_assets/editions/print \
        --report th/DA/04_assets/editions/print/EXTRACTION-NOTES.tsv \
        --renumber th/DA/04_assets/editions/print/RENUMBERED.tsv

## The paragraph numbers

The English codes of the Ellen G. White Estate are taken as correct, and every English paragraph has exactly one Thai paragraph under its code, in the English order: 2,614 in all. The print carries 2,594 of them, some misprinted. Where the print gave a Bible verse no code, the verse stood joined to the paragraph before it and every printed code after it ran one behind; such a paragraph is split where the English splits and the codes after it are moved up. No Thai word is changed or moved by this. `print/RENUMBERED.tsv` records every correction: the file, the printed code, the action and the code or codes it became. An English paragraph the Thai does not render would stand as an empty paragraph under its code; there is none.

Each correction was proposed by an agent reading the Thai against the English and checked again by a second; every paragraph of the book was then compared with its English paragraph for where it begins and ends.
