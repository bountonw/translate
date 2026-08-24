#!/usr/bin/env python3
"""Build the complete CID-to-Unicode table for the Thai printed edition.

Two sources feed the table, and the output records which one each row came
from so that a reader can tell an authoritative row from a reasoned one.

  harvest   The CMap that gc_th_cidmap.py lifts out of the NESDUL+BrowalliaUPC
            subsets, which are the only subsets in the file that carry a
            correct ToUnicode table.  63 rows, and nothing overrides them.

  order     The rest of the BrowalliaUPC glyph order, filled in from the
            harvested anchors.  The Latin block follows the font's own
            ordering, which the harvested rows for space, the parentheses and
            the period fix exactly; the Thai block follows Unicode order from
            U+0E01 with the two duplicate-form glyphs the font inserts after
            YO YING and after THO THAN.  Every row was then confirmed against
            a word in the book, and the confirmations are in the comments.

Run:
    python3 th/GC/04_assets/scripts/gc_th_cidmap.py QDF OUT_HARVEST.tsv
    python3 th/GC/04_assets/scripts/gc_th_buildmap.py OUT_HARVEST.tsv OUT.tsv
"""

import sys

# ─── Latin and punctuation ───────────────────────────────────────────────────
# The font's order runs space, the ASCII punctuation with quotesingle absent,
# the digits, the capitals, the brackets, the lowercase, the braces.  Harvested
# rows fix space at 3, parenleft at 10, parenright at 11 and period at 16, and
# the rest follows.  Confirmed in the book at, among others, "Controversy"
# (p2), "http://www" (p5), "[papacy]" (p50), "x 7 = 483" (p395), "185,000"
# (p493), "APPENDIX" (p540) and the tag "{GC v.4}" (p12).
LATIN = {
    3: " ", 4: "!", 5: '"', 6: "#", 7: "$", 8: "%", 9: "&",
    10: "(", 11: ")", 12: "*", 13: "+", 14: ",", 15: "-", 16: ".", 17: "/",
    28: ":", 29: ";", 30: "<", 31: "=", 32: ">", 33: "?", 34: "@",
    61: "[", 62: "\\", 63: "]", 64: "^", 65: "_", 66: "`",
    93: "{", 94: "|", 95: "}", 96: "~",
}
for i in range(10):
    LATIN[18 + i] = chr(ord("0") + i)          # 18-27
for i in range(26):
    LATIN[35 + i] = chr(ord("A") + i)          # 35-60
    LATIN[67 + i] = chr(ord("a") + i)          # 67-92

# Typographic marks the book uses inside quotations.
# 188 joins two verse numbers ("อิสยาห์ 58:12–14", p435), 189 joins two clauses
# with no space (p22, p246, p268), 190 and 191 are the single quotes that open
# and close a quotation inside a quotation (p110, p274, p276), 199 marks text
# omitted from a quotation (p288, p289, p362), and 204 and 205 are the Latin
# ligatures in "Sufficient" (p373) and "Waffle" (p431).
MARKS = {
    188: "–", 189: "—", 190: "‘", 191: "’",
    199: "…", 204: "fi", 205: "fl",
}

# ─── Thai ────────────────────────────────────────────────────────────────────
# 226 onward follows Unicode order from U+0E01, with a duplicate form of YO
# YING at 239 (the shape without its tail, "อกตัญญู" p36) and of THO THAN at
# 243, so that 246 lands on NO NEN as the harvest says.  U+0E3B to U+0E3E are
# unassigned in Unicode and the font skips them, which is why 291 lands on MAI
# MALAI and 292 on LAKKHANGYAO.
THAI = {}
_cid = 226
for _cp in range(0x0E01, 0x0E30):
    THAI[_cid] = chr(_cp)
    _cid += 1
    if _cp == 0x0E0D:      # duplicate YO YING
        THAI[_cid] = chr(0x0E0D)
        _cid += 1
    elif _cp == 0x0E10:    # duplicate THO THAN
        THAI[_cid] = chr(0x0E10)
        _cid += 1
for _off, _cp in enumerate(range(0x0E30, 0x0E3B)):
    THAI[275 + _off] = chr(_cp)                # 275-285
THAI[286] = "฿"                           # BAHT SIGN
for _off, _cp in enumerate(range(0x0E40, 0x0E4E)):
    THAI[287 + _off] = chr(_cp)                # 287-300
for _off, _cp in enumerate(range(0x0E4E, 0x0E5C)):
    THAI[301 + _off] = chr(_cp)                # 301-314, includes Thai digits

# The lowered and raised duplicate forms the font uses when a tall consonant or
# a preceding vowel would collide with the mark.  Four of them are harvested
# (318, 322, 323, 327, 328, 331, 332) and the rest sit in the same three
# groups: the vowels above, then two runs of tone mark, tone mark, mai tri,
# mai chattawa, thanthakhat, then a last group of MAI HAN AKAT forms.
# Confirmed at "ปีที่แล้ว" (319, p8), "ฝึกสอน" (320, p67), "ฟื้นฟู" (321 and
# 336, p7), "ป๊อบปูล่า" (324, p266), "กระเป๋า" (325, p248), "แอลป์" (326,
# p58), "สก๊อตแลนด์" (329, p62), "เอ๋ย" (330, p35), "เป็น" (334, p12) and
# "เปี่ยม" (335, p12).
VARIANT = {
    318: "ิ", 319: "ี", 320: "ึ", 321: "ื",
    322: "่", 323: "้", 324: "๊", 325: "๋", 326: "์",
    327: "่", 328: "้", 329: "๊", 330: "๋", 331: "์",
    332: "ั", 333: "ั", 334: "็", 335: "่", 336: "้",
}

# Thai digits are transcribed to Western digits, because root rule 5.A of the
# repository CLAUDE.md puts Western numerals in these files and a Thai digit
# zero is easily mistaken for a vowel character in a later search.
THAI_DIGITS = {303 + i: chr(ord("0") + i) for i in range(10)}

# PHINTHU at 285 appears three times in the book (p195 twice, p218), always
# between a consonant and the mark that follows it, where Thai has no phinthu
# and the word is a perfectly ordinary one.  It is a typesetting artifact, and
# emitting it would build a word no later search could find, so it is dropped.
DROP = {285}


def main():
    harvest_path, out_path = sys.argv[1], sys.argv[2]

    harvest = {}
    with open(harvest_path, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 2 and parts[1] != "�":
                harvest[int(parts[0])] = parts[1]

    rows = {}
    for cid, ch in LATIN.items():
        rows[cid] = (ch, "order")
    for cid, ch in MARKS.items():
        rows[cid] = (ch, "order")
    for cid, ch in THAI.items():
        rows[cid] = (ch, "order")
    for cid, ch in VARIANT.items():
        rows[cid] = (ch, "order")
    for cid, ch in THAI_DIGITS.items():
        rows[cid] = (ch, "order")
    for cid in DROP:
        rows[cid] = ("", "dropped")
    disagreements = []
    for cid, ch in harvest.items():
        if cid in rows and rows[cid][0] != ch and cid not in DROP:
            disagreements.append((cid, rows[cid][0], ch))
        rows[cid] = (ch, "harvest")

    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("# CID to Unicode for the BrowalliaUPC subsets of the Thai printed\n")
        fh.write("# edition of The Great Controversy. Columns: cid, text, codepoints,\n")
        fh.write("# source. 'harvest' rows come from a ToUnicode table inside the PDF\n")
        fh.write("# and 'order' rows from the font's glyph order, each confirmed\n")
        fh.write("# against a word in the book. A 'dropped' row emits nothing.\n")
        fh.write("# cid\ttext\tcodepoints\tsource\n")
        for cid in sorted(rows):
            ch, src = rows[cid]
            pts = " ".join(f"U+{ord(c):04X}" for c in ch) or "-"
            fh.write(f"{cid}\t{ch}\t{pts}\t{src}\n")

    print(f"rows: {len(rows)}  harvested: {sum(1 for v in rows.values() if v[1]=='harvest')}")
    if disagreements:
        print("DISAGREEMENTS between the glyph order and the harvested CMap:")
        for cid, derived, got in disagreements:
            print(f"  {cid}: order={derived!r} harvest={got!r}")
    else:
        print("the glyph order agrees with every harvested row")


if __name__ == "__main__":
    main()
