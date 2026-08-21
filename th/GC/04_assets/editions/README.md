# Prior Thai translations of The Great Controversy

This directory holds Thai translations of *The Great Controversy* that already exist, kept for reference while a new Thai translation is made from the project's Lao. Nothing here is the project's own output: the new translation will live in `th/GC/03_public/`. Nothing here is translated, edited or improved — where the printed book is wrong, the file is wrong in the same way, deliberately. The paragraph numbers are the single exception, and the section below says which were changed and why.

    print/   the edition in print, "ปลายทางแห่งความหวัง (ฉบับสมบูรณ์)", published by the Thai Adventist Mission
    alt/     the other Thai translation, from GC_alt_th.pdf

## What is in `print/`

One file per chapter, `GC01_print_th.typ` through `GC42_print_th.typ`, plus `GC00_front_print_th.typ` for the cover, imprint, quotations page and table of contents, and `GC00_intro_print_th.typ` for the publisher's foreword and the Introduction. Each file is Typst body text with no preamble, so it carries no `#import` and no `#chapter`; a template and a heading are added later.

Each paragraph is preceded by a `// {GC 17.1}` navigation comment and closes with `#EGW[\{GC 17.1\}]`, following `th/SC/03_public/`. Italic runs are wrapped in `#italic[...]`. The chapter title appears once as a `// TITLE:` comment rather than as a heading, because the Typst template will set it.

`EXTRACTION-NOTES.tsv` records every place the extraction had to decide something: a hyphen dropped at a line break, a word space restored where a line break had swallowed one, and any paragraph that carries no tag. `HYPHEN-CANDIDATES.tsv` holds the 133 soft-hyphen entries the print's own line breaks yield.

Every one of the 647 printed pages was read against a photograph of that page by an agent comparing the two, in 172 batches of four. The reading found one defect the mechanical checks had missed: page 322 prints its tag as `GC 335.2}` without the opening brace.

## What is in `alt/`

One file per chapter, `GC01_alt_th.typ` through `GC42_alt_th.typ`, plus `GC00_intro_alt_th.typ` for the Introduction, holding 1,812 paragraphs in all.

Four English paragraphs are not fully here. `{GC 67.3}` in GC04 and `{GC 410.3}` in GC23 are not in the Thai book at all. `{GC 98.2}` in GC06 renders only the last of its six English sentences. `{GC 356.1}` in GC20 quotes John 17:2 where the English has "the son of perdition". Everything else corresponds one paragraph to one paragraph.

These files hold only text that matches the English original. That edition runs to 804 pages against the English book's 678, because its publisher added a great deal of its own: a 27-page introduction, a 41-page back section, 27 pages of portraits and English quotation graphics with Thai captions, a title and comment page in front of every chapter, pop-out boxes reprinting body sentences in decorated panels, filler padding the last page of a chapter, and headings, dates, reading lists and editorial comment printed between paragraphs. Every chapter was compared paragraph by paragraph against `lo/GC/00_source/` and all of it was deleted. `CLEANED.md` records each deletion by the paragraph it stood in, and `EXTRACTION-NOTES-ALT.tsv` lists by page and kind what the extraction had already set aside before that comparison began.

Explanatory words the translator put inside a sentence were kept, including bracketed glosses and the English term printed beside a Thai one, because those are part of how this translator rendered the sentence. The printed edition's bold and italic markup was removed everywhere, because the English original carries no emphasis of any kind.

`GC00_intro_alt_th.typ` is a special case. This edition prints no paragraph numbers at all in its Introduction, so the `{GC v.1}` through `{GC xii.2}` numbers in that file are ours, taken from the English paragraph each Thai paragraph renders. The file's own header says so.

Its Unicode tables work, so the characters need no decoding table, but the SARA AM vowel is set as a ligature that those tables map to the replacement character, and all 10,071 are composed on the way out. The printed page number sits at the start of the last line of every page and is removed.

## The paragraph numbers

Both Thai books misprint a few `{GC ###.#}` numbers, almost always by repeating the previous number instead of advancing to the next one. Every such number in both editions was corrected against the English source in `lo/GC/00_source/`, so that a number in these files names the same paragraph it names in English and in Lao. This is the one place where the files do not reproduce the printed page, and it is deliberate: a reference number that points at the wrong paragraph would make the files useless for the comparison they exist for.

The print edition needed five corrections, and `print/RENUMBERED.tsv` names each one, the file it stands in, and what it was changed from. The alt edition needed twelve, and `alt/RENUMBERED-ALT.tsv` does the same.

Two English paragraphs are not in the alt edition at all, `{GC 67.3}` in GC04 and `{GC 410.3}` in GC23, and nothing was invented for either. Every other English paragraph now has exactly one Thai paragraph. Nine numbers the extraction had lost were recovered, and `alt/CLEANED.md` says how each was found.

The English source was checked before it was used to judge the Thai. The paragraphs on the eight English pages concerned were counted by hand in a printed English *Great Controversy*, and every count matched `lo/GC/00_source/` except two headings, `## {GC 74.3}` in `GC04_en.md` and `## {GC 220.4}` in `GC12_en.md`, each of which had stood over two paragraphs and named only the second. Both were corrected.

## Where the text comes from

Not from OCR. `04_assets/thai_original_pdfs/GC_print_th.pdf` carries a complete text layer, but its Thai is set in subsetted BrowalliaUPC fonts with Identity-H encoding and no ToUnicode table, so every general-purpose extractor reads it as Latin gibberish and silently drops every digit and every period. The scripts in `04_assets/scripts/` decode that glyph stream directly through a character table, which makes the characters exact by construction: a glyph either has a table entry or the run stops.

To rebuild the whole thing from the PDF:

    qpdf --qdf --object-streams=disable --stream-data=uncompress \
        th/GC/04_assets/thai_original_pdfs/GC_print_th.pdf /tmp/gc-th.pdf
    python3 th/GC/04_assets/scripts/gc_th_cidmap.py /tmp/gc-th.pdf /tmp/harvest.tsv
    python3 th/GC/04_assets/scripts/gc_th_buildmap.py /tmp/harvest.tsv \
        th/GC/04_assets/scripts/browallia_cid_map.tsv
    python3 th/GC/04_assets/scripts/gc_th_extract.py /tmp/gc-th.pdf \
        th/GC/04_assets/editions/print \
        --report th/GC/04_assets/editions/print/EXTRACTION-NOTES.tsv
    python3 th/GC/04_assets/scripts/gc_th_renumber.py \
        th/GC/04_assets/editions/print print --apply
    python3 th/GC/04_assets/scripts/gc_th_check.py th/GC/04_assets/editions/print

`gc_th_pagedump.py` prints one page in reading order for checking against the printed page, and is what the verification pass compared its images against.

The alt files cannot be rebuilt this way. Running `gc_th_extract_alt.py` reproduces the raw extraction, which still carries all of the publisher's own material, and the deletions recorded in `alt/CLEANED.md` were made by judgment against the English source rather than by rule. `gc_th_flatten_alt.py` removes the bold and italic markup and is the one step of that work a script can repeat.

## What the extraction changes, and what it leaves alone

It composes SARA AM. Every one of the 9,937 instances in the book is stored decomposed, as a nikhahit followed by a SARA AA, which renders correctly and matches no search; the extraction writes U+0E33, and puts a tone mark before it where the typesetting put one between the parts.

It restores word spaces. The typesetter set many of them by inflating the advance of the preceding glyph rather than by setting a space character, so they exist on the page but not in the stream.

It drops a hyphen where a Thai word was broken across a line, joins the lines of a paragraph, reads the two columns in the right order, and leaves out the running head.

It changes nothing else. Spelling, wording and punctuation are the book's own, however wrong they are. The corrected paragraph numbers are the only departure, and the section above lists every one of them.
