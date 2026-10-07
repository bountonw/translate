#!/usr/bin/env python3
"""Corpus data for one glossary head, for a DA term study. Reads only; writes one markdown file.

    python3 th/DA/04_assets/scripts/da_term_data.py --head "longing|desire" \\
        --thai ความปรารถนา,ความโหยหา --verses "PSA 42:1,ISA 26:9" --chapter 0 \\
        --out ~/claude-sandbox/da-audit/da00-term-longing.md

Sections: 1 sites in th/MB, th/PP, th/SC and th/DA whose English source matches
--head: anchor, set, the English sentence, the --thai forms found in the Thai
paragraph or "none"; a DA site adds the drafted Thai and the 2023 print's
paragraph in a column labelled print, which is reference only and never a
model. 2 counts of each --thai form: sites per set (reviewed: MB and PP 1–30
and 44–73; unreviewed: PP 31–43; SC; DA) and occurrences per book, SJ by
occurrences only. 3 Bible: each form counted in every Thai version on disk, the
--verses in all of them, and the King James verses matching --head (KJVS,
up to 60) with all the versions beside them. 4 the two Thai GC editions
(th/GC/04_assets/editions/print and alt), counts and up to twelve snippets,
light reference. 5 up to ten Lao GC sites, the English sentence beside the
Lao paragraph from lo/GC, light reference. --chapter limits the print column
to that chapter. The Bible corpus path is BIBLE_CORPUS or ~/programming/bible.
"""
import argparse
import glob
import os
import re
import sys
from pathlib import Path

from da_common import ROOT, SANDBOX, VERSIONS, PRINT_DIR, version_dir, load_version, clean_verse, parse_thai

SENT = re.compile(r"(?<=[.;!?])\s+")
GC_EDITIONS = {"print": ROOT / "th/GC/04_assets/editions/print", "alt": ROOT / "th/GC/04_assets/editions/alt"}


def english_paras(book):
    out = {}
    for f in sorted(glob.glob(str(ROOT / f"th/{book}/00_source/*_en.md"))):
        t = open(f, encoding="utf-8").read()
        for m in re.finditer(r"^## \{(\w+ [\w.]+)\}\s*\n(.*?)(?=^## \{|\Z)", t, re.M | re.S):
            out[m.group(1)] = re.sub(r"\{\w+ [\w.]+\}\s*$", "", m.group(2).strip())
    return out


def thai_paras(book):
    """anchor -> Thai paragraph, anchor -> chapter number, for one book across its stages."""
    out, chap = {}, {}
    files = sorted(glob.glob(str(ROOT / f"th/{book}/0[123]_*/*.md")) + glob.glob(str(ROOT / f"th/{book}/0[123]_*/*.typ")))
    for f in files:
        t = open(f, encoding="utf-8").read()
        n = re.search(r"(\d+)", Path(f).name)
        nn = int(n.group(1)) if n else 0
        if f.endswith(".md"):
            it = re.finditer(r"^## \{(\w+ [\w.]+)\}\s*\n(.*?)(?=^## \{|\Z)", t, re.M | re.S)
        else:
            it = re.finditer(r"// \{(\w+ [\w.]+)\}\s*\n(.*?)#EGW\[", t, re.S)
        for m in it:
            body = m.group(2).strip()
            if body and m.group(1) not in out:
                out[m.group(1)] = body
                chap[m.group(1)] = nn
            elif m.group(1) not in out:
                chap.setdefault(m.group(1), nn)
    return out, chap


def print_paras(chapter=None):
    """anchor -> the 2023 print's paragraph, for one chapter or the whole book."""
    out = {}
    pattern = "*_print_th.typ" if chapter is None else ("DA00_preface_print_th.typ" if chapter == 0 else f"DA{chapter:02d}_print_th.typ")
    for f in sorted(PRINT_DIR.glob(pattern)):
        _, paras = parse_thai(f.read_text(encoding="utf-8"))
        for p in paras:
            out[f"DA {p.anchor}"] = p.prose
    return out


def setname(book, nn):
    if book == "SC":
        return "SC"
    if book == "DA":
        return "DA"
    if book == "MB" or nn <= 30 or 44 <= nn <= 73:
        return "reviewed"
    return "unreviewed"


def kjv_hits(head, limit=60):
    hits = []
    src = version_dir("KJVS") if version_dir("KJVS").is_dir() else version_dir("KJV")
    for f in sorted(glob.glob(str(src / "*.txt"))):
        for line in open(f, encoding="utf-8").read().splitlines():
            parts = line.split("|", 4)
            if len(parts) == 5 and parts[2].isdigit() and parts[3].isdigit():
                text = clean_verse(parts[4])
                if head.search(text):
                    hits.append((parts[1], int(parts[2]), int(parts[3]), text))
                    if len(hits) >= limit:
                        return hits
    return hits


def gc_paras(edition_dir):
    """anchor -> paragraph for a Thai GC edition (Typst files with // {GC ...} comments)."""
    out = {}
    for f in sorted(edition_dir.glob("*.typ")):
        t = f.read_text(encoding="utf-8")
        for m in re.finditer(r"^// \{(GC [^}]+)\}\s*\n(.*?)(?=^// |\Z)", t, re.M | re.S):
            body = re.sub(r"#EGW\[[^\]]*\]", "", m.group(2)).strip()
            if body:
                out[m.group(1)] = body
    return out


def lao_gc():
    """(anchor -> English paragraph, anchor -> Lao paragraph) for lo/GC."""
    en, lo = {}, {}
    for f in sorted(glob.glob(str(ROOT / "lo/GC/00_source/*_en.md"))):
        t = open(f, encoding="utf-8").read()
        for m in re.finditer(r"^## \{(GC [^}]+)\}\s*\n(.*?)(?=^## \{|\Z)", t, re.M | re.S):
            en[m.group(1)] = re.sub(r"\{GC [^}]+\}\s*$", "", m.group(2).strip())
    for f in sorted(glob.glob(str(ROOT / "lo/GC/03_public/*_lo.md")) + glob.glob(str(ROOT / "lo/GC/02_edit/*_lo.md"))):
        t = open(f, encoding="utf-8").read()
        for m in re.finditer(r"^## \{(GC [^}]+)\}\s*\n(.*?)(?=^## \{|\Z)", t, re.M | re.S):
            body = re.sub(r"^###.*$", "", m.group(2), flags=re.M).strip()
            if body:
                lo.setdefault(m.group(1), body)
    return en, lo


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--head", required=True, help="English regex, case-insensitive")
    ap.add_argument("--thai", default="", help="comma-separated Thai candidate forms")
    ap.add_argument("--verses", default="", help='comma-separated "CODE ch:v", e.g. "ROM 3:25,1JN 2:2"')
    ap.add_argument("--chapter", type=int, help="the DA chapter in hand; limits the print column to it")
    ap.add_argument("--out", help="output file; default ~/claude-sandbox/da-audit/daNN-term-HEAD.md")
    a = ap.parse_args()
    head = re.compile(a.head, re.I)
    forms = [x.strip() for x in a.thai.split(",") if x.strip()]
    slug = re.sub(r"[^a-z0-9]+", "-", a.head.lower()).strip("-")[:40]
    out = Path(os.path.expanduser(a.out)) if a.out else SANDBOX / f"da{a.chapter if a.chapter is not None else 0:02d}-term-{slug}.md"
    sets = ("reviewed", "unreviewed", "SC", "DA")
    L = [f"# Term data: {a.head}", "", f"Forms: {', '.join(forms) if forms else 'none given; run again with --thai once the forms are copied out of sections 1 and 3'}", ""]
    L += ["## 1. Sites", "", "| Anchor | Set | English | Thai forms found |", "|---|---|---|---|"]
    site_counts = {f: {s: 0 for s in sets} for f in forms}
    recast = {s: 0 for s in sets}
    nsites = {s: 0 for s in sets}
    occ = {f: {} for f in forms}
    da_rows = []
    prints = print_paras(a.chapter)
    # With --chapter, the DA sites are that chapter's; without it, the whole book's.
    da_anchors = set(prints) if a.chapter is not None else None
    for book in ("MB", "PP", "SC", "DA"):
        en = {k: v.replace("’", "'") for k, v in english_paras(book).items()}
        if book == "DA" and da_anchors is not None:
            en = {k: v for k, v in en.items() if k in da_anchors}
        th, chap = thai_paras(book)
        for f in forms:
            occ[f][book] = sum(p.count(f) for p in th.values())
        for anchor, para in en.items():
            if not head.search(para):
                continue
            s = setname(book, chap.get(anchor, 0))
            nsites[s] += 1
            sents = [x.strip() for x in SENT.split(para) if head.search(x)]
            tp = th.get(anchor, "")
            found = [f for f in forms if f in tp]
            for f in found:
                site_counts[f][s] += 1
            if not found and tp:
                recast[s] += 1
            shown = " / ".join(x[:160] for x in sents[:2])
            if book == "DA":
                pr = prints.get(anchor, "")
                pfound = [f for f in forms if f in pr]
                da_rows.append(f"| {{{anchor}}} | {shown} | {', '.join(found) if found else ('none' if tp else 'not drafted')} | "
                               f"{', '.join(pfound) if pfound else 'none'}: {pr[:200] if pr else '(no print paragraph)'} |")
                continue
            L.append(f"| {{{anchor}}} | {s} | {shown} | {', '.join(found) if found else ('none' if tp else 'no Thai paragraph')} |")
    L += ["", "### DA sites, with the print as a labelled column (reference, never a model)", "",
          "| Anchor | English | Draft Thai forms | print |", "|---|---|---|---|"] + (da_rows or ["| none | | | |"])
    sj_occ = {}
    for f in forms:
        sj_occ[f] = sum(open(p, encoding="utf-8").read().count(f) for p in glob.glob(str(ROOT / "th/SJ/0[123]_*/*.typ")))
    L += ["", "## 2. Counts", "",
          f"Sites with the head: reviewed {nsites['reviewed']}, unreviewed {nsites['unreviewed']}, SC {nsites['SC']}, DA {nsites['DA']}.", "",
          "| Thai form | Sites reviewed / unreviewed / SC / DA | Occurrences MB / PP / SC / DA / SJ |", "|---|---|---|"]
    for f in forms:
        c = site_counts[f]
        L.append(f"| {f} | {c['reviewed']} / {c['unreviewed']} / {c['SC']} / {c['DA']} | "
                 f"{occ[f].get('MB', 0)} / {occ[f].get('PP', 0)} / {occ[f].get('SC', 0)} / {occ[f].get('DA', 0)} / {sj_occ[f]} |")
    L.append(f"| none of the forms (recast) | {recast['reviewed']} / {recast['unreviewed']} / {recast['SC']} / {recast['DA']} | |")

    L += ["", "## 3. Bible", "", "| Thai form | " + " | ".join(VERSIONS) + " |", "|---|" + "---|" * len(VERSIONS)]
    texts = {}
    for ver in VERSIONS:
        texts[ver] = "".join(open(f, encoding="utf-8").read() for f in glob.glob(str(version_dir(ver) / "*.txt")))
    for f in forms:
        L.append(f"| {f} | " + " | ".join(str(texts[v].count(f)) for v in VERSIONS) + " |")
    if a.verses:
        L += ["", "### Requested verses", ""]
        for ref in [x.strip() for x in a.verses.split(",") if x.strip()]:
            m = re.match(r"(\S+)\s+(\d+):(\d+)", ref)
            if not m:
                continue
            code, ch, v = m.group(1), int(m.group(2)), int(m.group(3))
            L.append(f"**{ref}**")
            kj = load_version("KJVS", code)
            L.append(f"- KJV: {kj.get((ch, v), '(not on disk)') if kj else '(not on disk)'}")
            for ver in VERSIONS:
                verses = load_version(ver, code)
                t = verses.get((ch, v)) if verses else None
                L.append(f"- {ver}: {t if t else '(not on disk)'}")
            L.append("")
    hits = kjv_hits(head)
    L += ["### King James verses matching the head, with every Thai version", ""]
    for code, ch, v, t in hits:
        L.append(f"- {code} {ch}:{v} KJV: {t[:200]}")
        for ver in VERSIONS:
            verses = load_version(ver, code)
            th_v = verses.get((ch, v)) if verses else None
            if th_v:
                L.append(f"  {ver}: {th_v[:220]}")
    if not hits:
        L.append("none")

    L += ["", "## 4. The two Thai GC editions (light reference)", ""]
    snippets = 0
    for name, d in GC_EDITIONS.items():
        if not d.is_dir():
            L.append(f"{name}: not on disk ({d.relative_to(ROOT)})")
            continue
        paras = gc_paras(d)
        L.append(f"### {name} ({len(paras)} paragraphs)")
        L.append("")
        for f in forms:
            n = sum(p.count(f) for p in paras.values())
            L.append(f"- {f}: {n} occurrence(s)")
            for anchor, p in paras.items():
                if snippets >= 12:
                    break
                i = p.find(f)
                if i >= 0:
                    L.append(f"  - {{{anchor}}}: …{p[max(0, i - 70):i + len(f) + 70]}…")
                    snippets += 1
        L.append("")

    L += ["## 5. The Lao GC (light reference, the translator's own work)", ""]
    en_gc, lo_gc = lao_gc()
    n = 0
    for anchor, para in en_gc.items():
        if n >= 10:
            break
        if not head.search(para) or anchor not in lo_gc:
            continue
        sents = [x.strip() for x in SENT.split(para) if head.search(x)]
        L.append(f"- {{{anchor}}} EN: {' / '.join(x[:200] for x in sents[:1])}")
        L.append(f"  LO: {lo_gc[anchor][:400]}")
        n += 1
    if n == 0:
        L.append("none")

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"wrote {out}: sites reviewed {nsites['reviewed']}, unreviewed {nsites['unreviewed']}, SC {nsites['SC']}, DA {nsites['DA']}; "
          f"KJV hits {len(hits)}; Lao GC sites {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
