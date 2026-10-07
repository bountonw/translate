#!/usr/bin/env python3
"""The drafter's packet for one batch of a DA chapter. Reads only; writes one file.

    python3 th/DA/04_assets/scripts/da_packet.py --chapter 4 --range 43.1 46.2
    python3 th/DA/04_assets/scripts/da_packet.py --chapter 0

Writes ~/claude-sandbox/da-audit/daNN-packet-FIRST-LAST.md with seven sections:
1 the chapter title, the based-on line and the English paragraphs of the
range; 2 the glossary rows of sections 1 and 2 whose English head occurs in
the range, and the whole spelling table; 3 the rows of thai-names.tsv whose
English name occurs; 4 the verse picks of pass 1 for the range, from
~/claude-sandbox/da-audit/DANN-verses.tsv, with the picked version's text and
the alternative where the call was close, and whether the citation is hidden
(DA 3.D); 5 thai-profile.txt whole and section 3 of th/DA/CLAUDE.md; 6 the PP
style samples of th/DA/04_assets/pp_samples.txt, English and Thai; 7 the Thai
already in the chapter before the range. The 2023 print never enters the
packet. Chapter 0 is the preface; without --range the whole chapter is the batch.
"""
import argparse
import glob
import re
import sys
from pathlib import Path

from da_common import (ROOT, PROJECT, SANDBOX, PROFILE, NAMES, GLOSSARY, chapter_path, source_path,
                       source_header, parse_thai, parse_english, in_range, anchor_key, based_on,
                       in_based_on, load_verse_picks, parse_ref_code, load_version, book_names,
                       glossary_rows, SUBTITLE_LINE)

SAMPLES = PROJECT / "04_assets" / "pp_samples.txt"
DA_CLAUDE = PROJECT / "CLAUDE.md"


def head_regex(head):
    """"trial (God testing)" -> a regex for the word "trial" and its inflections."""
    base = re.split(r"\(|,", head)[0].strip()
    words = [w for w in re.split(r"\s+", base) if w]
    if not words:
        return None
    return re.compile(r"\b" + r"\s+".join(re.escape(w) + r"\w*" for w in words), re.I)


def section_of(text, number):
    """The text of "## N." up to the next "## " heading."""
    m = re.search(rf"^## {number}\..*?(?=^## |\Z)", text, re.M | re.S)
    return m.group(0).rstrip() if m else f"(no section {number})"


def pp_index():
    """anchor -> (English paragraph, Thai paragraph) for the PP sample anchors."""
    want = {}
    if not SAMPLES.exists():
        return want, []
    lines = [l for l in SAMPLES.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
    picks = [(l.split("|")[0].strip(), l.split("|", 1)[1].strip() if "|" in l else "") for l in lines]
    anchors = {a for a, _ in picks}
    for f in sorted(glob.glob(str(ROOT / "th/PP/00_source/PP*_en.md"))):
        t = Path(f).read_text(encoding="utf-8")
        hit = [a for a in anchors if f"## {{{a}}}" in t]
        if not hit:
            continue
        nn = Path(f).name[2:4]
        th_file = None
        for stage in ("03_public", "02_edit"):
            p = ROOT / "th/PP" / stage / f"PP{nn}_th.typ"
            if p.exists():
                th_file = p.read_text(encoding="utf-8")
                break
        for a in hit:
            m = re.search(r"^## \{" + re.escape(a) + r"\}\s*\n\n(.*?)(?=\n## \{|\Z)", t, re.M | re.S)
            en = re.sub(r"\s*\{PP [\d.]+\}\s*$", "", m.group(1).strip()) if m else "(English paragraph not found)"
            th = "(Thai paragraph not found)"
            if th_file:
                tm = re.search(r"^// \{" + re.escape(a) + r"\}\s*\n(.*?)#EGW\[", th_file, re.M | re.S)
                if tm:
                    th = tm.group(1).strip()
            want[a] = (en, th)
    return want, picks


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--chapter", type=int, required=True, help="chapter number; 0 is the preface")
    ap.add_argument("--range", nargs=2, metavar=("FIRST", "LAST"), help="anchors, e.g. 43.1 46.2")
    ap.add_argument("--out")
    a = ap.parse_args()
    nn = a.chapter
    first, last = a.range if a.range else (None, None)
    header = source_header(nn)
    english = parse_english(source_path(nn).read_text(encoding="utf-8"))
    chapter = chapter_path(nn)
    head_lines, paras = parse_thai(chapter.read_text(encoding="utf-8"))
    anchors = [k for k in english if in_range(k, first, last)]
    if not anchors:
        sys.exit(f"no English paragraph of DA{nn:02d} lies in the range {first} {last}")
    range_text = "\n".join(english[k] for k in anchors)
    names = book_names()
    basedon = based_on(nn)

    L = [f"# DA{nn:02d} drafter packet — {{DA {anchors[0]}}} to {{DA {anchors[-1]}}}", ""]
    L += ["## 1. The English", ""]
    L.append(f"Chapter {header['number'] or '0 (preface)'}: {header['title']}")
    L.append("Based on: " + (header["basedon"] or "none; the chapter has no based-on line"))
    title_set = bool(re.search(r'title:\s*"[^"]+"', "\n".join(head_lines)))
    basedon_set = bool(re.search(r'basedon:\s*"[^"]+"', "\n".join(head_lines)))
    L.append(f"The chapter header in {chapter.relative_to(ROOT)} has {'a' if title_set else 'no'} Thai title"
             + (f" and {'a' if basedon_set else 'no'} Thai basedon string" if header["basedon"] else "")
             + ("; the first batch writes them (DA 3.F for the basedon string)." if not title_set else "."))
    L.append("")
    for k in anchors:
        L += [f"### {{DA {k}}}", "", english[k], ""]

    L += ["## 2. Glossary rows whose head occurs in the range", ""]
    rows = []
    for sec, cells in glossary_rows():
        if sec == 3 or len(cells) < 2:
            continue
        rx = head_regex(cells[0])
        if rx and rx.search(range_text):
            rows.append(f"| {' | '.join(cells)} |  (section {sec})")
    L += (["| English | Thai | Notes |", "|---|---|---|"] + rows) if rows else ["none"]
    L += ["", "### The spelling table (glossary section 3), whole", "", "| Word | Correct | Incorrect | Notes |", "|---|---|---|---|"]
    L += [f"| {' | '.join(cells)} |" for _, cells in glossary_rows(3)]

    L += ["", "## 3. Names whose English occurs in the range", ""]
    if NAMES.exists():
        lines = NAMES.read_text(encoding="utf-8").splitlines()
        hdr = lines[0] if lines else ""
        hits = [l for l in lines[1:] if l.strip() and re.search(r"\b" + re.escape(l.split("\t")[0]) + r"\b", range_text)]
        L += ([hdr.replace("\t", " | ")] + [h.replace("\t", " | ") for h in hits]) if hits else ["none in the table; a name the table lacks is spelled as THSV spells it, copied out of ~/programming/bible/th/THSV"]
    else:
        L.append(f"{NAMES.relative_to(ROOT)} does not exist yet; spell every biblical name as THSV spells it, copied out of ~/programming/bible/th/THSV")

    L += ["", "## 4. Verse picks of pass 1 for the range", ""]
    picks = [r for r in load_verse_picks(nn) if r.get("anchor") and in_range(r["anchor"], first, last)]
    if not picks:
        L.append("none on file" + ("" if load_verse_picks(nn) else f" ({SANDBOX}/DA{nn:02d}-verses.tsv is absent); raise a TERM or VERSE marker where a quotation's version must be chosen"))
    for r in picks:
        parsed = parse_ref_code(r.get("ref", ""))
        L.append(f"### {{DA {r['anchor']}}} {r.get('kind', '')} — {r.get('ref', '')} — pick {r.get('version', '')}" + (" — CLOSE CALL" if r.get("close", "").lower() == "yes" else ""))
        L.append("")
        L.append(f"EN: {r.get('english', '')}")
        if parsed:
            code, ch, vv = parsed
            vv = sorted(vv) if vv else [1]
            inside = basedon and all(in_based_on(basedon, code, ch, v) for v in vv)
            cite = f"{names.get(code, code)} {ch}:{vv[0]}" + (f"–{vv[-1]}" if len(vv) > 1 else "")
            for label in [r.get("version", ""), r.get("alt_version", "")]:
                if not label:
                    continue
                verses = load_version(label, code)
                txt = " ".join(verses.get((ch, v), "(verse not on disk)") for v in vv) if verses else "(version not on disk)"
                L.append(f"{label}: {txt}")
            L.append("Citation: " + (f"hidden as /*{cite}*/ (THSV from the based-on passage, DA 3.D)" if inside and r.get("version") == "THSV"
                                     else f"printed ({cite}{'' if r.get('version') == 'THSV' else ' ' + r.get('version', '')})"))
        L.append(f"Reason: {r.get('reason', '')}")
        L.append("")

    L += ["## 5. The rules", "", "### thai-profile.txt", "", PROFILE.read_text(encoding="utf-8").rstrip(), "",
          "### th/DA/CLAUDE.md section 3", "", section_of(DA_CLAUDE.read_text(encoding="utf-8"), 3), ""]

    L += ["## 6. Style samples from PP", ""]
    index, picks_pp = pp_index()
    if not picks_pp:
        L.append(f"{SAMPLES.relative_to(ROOT)} is absent or empty")
    for anchor, kind in picks_pp:
        en, th = index.get(anchor, ("(not found)", "(not found)"))
        L += [f"### {{{anchor}}} — {kind}", "", f"EN: {en}", "", f"TH: {th}", ""]

    L += ["## 7. The Thai already in the chapter before the range", ""]
    before = [p for p in paras if first and anchor_key(p.anchor) < anchor_key(first)]
    if not before:
        L.append("none; this is the first batch" if not paras else "none before the range")
    for p in before:
        L += [f"// {{DA {p.anchor}}}", "", p.body, ""]

    SANDBOX.mkdir(parents=True, exist_ok=True)
    out = Path(a.out) if a.out else SANDBOX / f"da{nn:02d}-packet-{anchors[0]}-{anchors[-1]}.md"
    text = "\n".join(L) + "\n"
    out.write_text(text, encoding="utf-8")
    print(f"wrote {out}: {len(anchors)} English paragraph(s), {sum(len(english[k].split()) for k in anchors)} words; "
          f"{len(rows)} glossary row(s), {len(picks)} verse pick(s), {len(before)} earlier Thai paragraph(s); {len(text.split())} words in the packet")
    return 0


if __name__ == "__main__":
    sys.exit(main())
