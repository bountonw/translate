# What was deleted from the Thai alt edition

Every chapter of this edition was compared paragraph by paragraph against the English original in `lo/GC/00_source/`, and everything the Thai publisher added was deleted, so that these files hold only text corresponding to the English chapters. This file records each deletion by the paragraph it stood in. Thirty of the 42 chapters needed no deletion at all.

The publisher's additions fall into four kinds. Some are pop-out boxes, where sentences from the body were reprinted in a decorated panel, which the extraction had read as a second paragraph carrying the same number. Some are end-of-chapter filler padding the last page, usually by repeating body text. Some are headings, notes, dates, reading lists and editorial comment printed between two paragraphs, which the extraction swallowed into the paragraph that followed. The rest are debris from the printing, such as a paragraph number that came out malformed.

Explanatory words the translator put inside a sentence were kept throughout, including bracketed glosses and the English term printed beside a Thai one, because those are part of how this translator rendered the sentence rather than publisher's furniture.

This file names the kind of material removed at each paragraph rather than reproducing it. What the printed book says at any of these points has to be read in the book itself, `GC_alt_th.pdf`, which is not in this repository. Given that file, `gc_th_extract_alt.py` regenerates the whole uncleaned extraction.

The printed edition's bold and italic markup was removed everywhere, because the English original carries no emphasis of any kind.

## Deletions by chapter

    GC01  {GC 27.3}   an editorial sentence claiming Jesus prophesied Jerusalem's fall in AD 31 and that it happened in AD 70, with its citation
    GC03  {GC 59.3}   the decorated pop-out copy standing at the top of the file; the plain body copy was kept
    GC03  {GC 49.1}   the chapter heading "บทที่ 3" glued to the front of the paragraph
    GC03  {GC 53.2}   a 2,782-character insertion listing the Ten Commandments in both Protestant and Roman Catholic numbering with an editorial comparison
    GC07  {GC 140.4}  the decorated pop-out copy standing at the top of the file; the plain body copy was kept
    GC07  {GC 120.1}  a John Huss paragraph and the chapter heading "บทที่ 7Martin Luther" glued to the front
    GC07  {GC 120.3}  a Reformation Day footnote about 31 October 1517 and the Ninety-five Theses
    GC07  {GC 125.2}  the note "(ริเริ่มโดยลูเธอร์ ค.ศ. 1517 Protestant Reformation)"
    GC07  {GC 129.2}  the date "( 31-10-1517)" and a note that Protestants now celebrate it
    GC07  {GC 132.2}  the citation "(ยอห์น 6: 45)", which the English paragraph does not give
    GC11  {GC 203.4}  the citation "(กิจการ 5: 29 KJV)" glued between two sentences
    GC12  {GC 234.2}  "(ค.ศ. 1540 สันตะปาปาเห็นด้วยกับการก่อตั้ง)", a founding date for the Jesuit order
    GC12  {GC 235.2}  the publisher's own account of the Inquisition, carrying a casualty figure
    GC12  {GC 235.2}  a reading list of websites, books and a video search appended to the paragraph
    GC21  {GC 390.2}  a 2,099-character essay on the church, science and modern politics, with web and video citations
    GC23  {GC 415.3}  the malformed tag "{GC 41532}", debris from the printing
    GC25  {GC 439.1}  the decorated duplicate at the end of the file, carrying an English polemical passage, two web addresses and two video references
    GC32  {GC 522.4}  a stray ". " opening the paragraph
    GC32  {GC 528.3}  a stray ". " opening the paragraph
    GC35  {GC 563.1}  an Isaiah 28:17,18 epigraph, the chapter number, the chapter title and an editorial heading glued to the chapter's opening paragraph
    GC35  {GC 563.2}  a trailing "See – See You tube:" note
    GC35  {GC 564.1}  a book and documentary recommendation and an editorial heading
    GC35  {GC 564.3}  the heading "Religious liberty in America is threatened"
    GC35  {GC 565.3}  a rhetorical-question heading in front of the paragraph
    GC35  {GC 565.3}  an end-of-chapter filler block mixing several unrelated topics
    GC35  {GC 565.4}  end-of-chapter filler repeating the paragraph's opening sentence
    GC35  {GC 566.1}  a front-of-chapter copy that quoted the English untranslated inside a warning box
    GC35  {GC 568.3}  a summary heading in front of the paragraph
    GC35  {GC 569.2}  a decorated pop-out copy at the head of the file
    GC35  {GC 569.2}  a casualty claim in front of the paragraph and half a web address after it
    GC35  {GC 569.3}  the other half of that web address
    GC35  {GC 570.2}  filler quoting fragments of {GC 565.3} and {GC 570.1} rather than this paragraph's own text
    GC35  {GC 571.1}  a note questioning the authenticity of the Luke 9:54-56 quotation
    GC35  {GC 571.1}  a second, redundant heading
    GC35  {GC 571.2}  end-of-chapter filler repeating the paragraph's closing sentence
    GC35  {GC 571.4}  a reading recommendation beginning at the end of the paragraph
    GC35  {GC 572.1}  the rest of that recommendation, two more book recommendations and a heading
    GC35  {GC 573.1}  the heading "Protestants are going astray, will enact a Sunday law"
    GC35  {GC 574.2}  a decorative pull-quote repeating {GC 566.1}, and a heading
    GC35  {GC 576.1}  a heading foreshadowing later content
    GC35  {GC 578.3}  a heading, a KJV and Revelation parenthetical, and a "See Appendix" note
    GC35  {GC 579.1}  a heading about Sabbath-keepers being falsely blamed
    GC35  {GC 580.1}  a heading redundant with the sentence it precedes
    GC35  {GC 581.1}  a heading redundant with the sentence it precedes
    GC37  {GC 596.2}  the editorial note "(หมายเหตุ: อธิบายให้เข้าใจได้ดีขึ้นได้ไหม)"
    GC37  {GC 594.1}  the italicised pop-out copy at the end of the file, repeating the body copy's closing sentences
    GC38  {GC 610.1}  the malformed tag "{GC 609.1", debris from the printing
    GC42  {GC 665.1}  the editorial note "(อยู่-เลื่อนไปอยู่ก่อนจุดนี้)" in the middle of a sentence

## Paragraph numbers that were restored

The extraction first produced these files with eleven English paragraph numbers missing. Nine were recovered.

Four were missing because this edition printed its own paragraph mark but the number came out of the printing malformed, so the extraction could not read it and ran two paragraphs into one. Each paragraph was split again at the point the malformed number stood, and the debris deleted. `{GC 18.2}` in GC01 was joined at `{G18.2}`, `{GC 415.2}` in GC23 at `{GC 41532}`, and `{GC 609.1}` in GC38 at `{GC 609.1` with no closing brace. `{GC 562.1}` is the fourth and a stranger case: this edition prints chapter 34's closing Isaiah 28:17,18 quotation on the same page as chapter 35's title, tagged `{GC 562.1` with no closing brace, so it was extracted into GC35, and it has been moved to the end of GC34 where it belongs.

One, `{GC 581.2}` in GC35, had its only Thai translation printed inside the end-of-chapter filler block rather than in the body, and was recovered from there.

Four were places where this edition runs two English paragraphs together with nothing printed between them: `{GC xi.2}` in the Introduction, and `{GC 567.2}`, `{GC 570.2}` and `{GC 575.1}` in GC35. Each was split at the sentence where the first English paragraph ends and the second begins. In all three GC35 cases a corrupted print reference — `(GC 56)`, `\(GC 570.2)` and `{GC 575.1` — sat at exactly that point and confirmed it independently; all three were deleted after the split.

One paragraph was also moved. `{GC 566.1}` in GC35 stood at the head of the file, because this edition printed it in a panel before the chapter began, and it now stands between `{GC 565.4}` and `{GC 566.2}`.

## English paragraphs this edition does not carry

Two English paragraphs are not in this edition at all: `{GC 67.3}` in GC04 and `{GC 410.3}` in GC23. Neither the surrounding paragraphs nor anywhere else in those files carries their content. Nothing was invented for either.
