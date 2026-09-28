#!/usr/bin/env python3
"""Corpus data for one glossary head. Reads only; writes one markdown file.

    python3 th/SC/04_assets/scripts/sc_term_data.py --head "propitiation|atonement" \\
        --thai เครื่องบูชาลบบาป,การไถ่ --verses "ROM 3:25,1JN 2:2" --out ~/claude-sandbox/sc-audit/term-propitiation.md

Sections: 1 sites in th/MB, th/PP and th/SC where the English source matches --head
(anchor, set, the English sentence, the --thai forms found in the Thai paragraph or
"none"); 2 counts of each --thai form, as matched sites per set and as occurrences per
book; 3 Bible: each --thai form counted per version on disk, the --verses in THSV,
TH1971, TNCV and TKJV, and the KJV verses matching --head, from the KJVS whole King James, with every Thai version
on disk beside them. Published means MB and PP 1-20; unpublished means PP 21 on.
The Bible corpus path is BIBLE_CORPUS or ~/programming/bible, with Thai versions under th/ and
the King James under en/KJVS.
"""
import argparse, glob, os, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BIBLE = Path(os.path.expanduser(os.environ.get("BIBLE_CORPUS", "~/programming/bible")))
VERSIONS = ("THSV", "TNCV", "TKJV", "TH1940", "TH1971")


def version_dir(ver):
    """A version's directory: bible/th/<ver>, bible/en/<ver>, or bible/<ver>."""
    for d in (BIBLE / "th" / ver, BIBLE / "en" / ver, BIBLE / ver):
        if d.is_dir():
            return d
    return BIBLE / ver
SENT = re.compile(r"(?<=[.;!?])\s+")


def english_paras(book):
    out = {}
    for f in sorted(glob.glob(str(ROOT / f"th/{book}/00_source/*_en.md"))):
        t = open(f, encoding="utf-8").read()
        for m in re.finditer(r"^## \{(\w+ \d+\.\d+)\}\s*\n(.*?)(?=^## \{|\Z)", t, re.M | re.S):
            out[m.group(1)] = re.sub(r"\{\w+ \d+\.\d+\}\s*$", "", m.group(2).strip())
    return out


def thai_paras(book):
    out, chap = {}, {}
    for f in sorted(glob.glob(str(ROOT / f"th/{book}/0[23]_*/*.md")) + glob.glob(str(ROOT / f"th/{book}/0[23]_*/*.typ"))):
        t = open(f, encoding="utf-8").read()
        n = re.search(r"(\d+)", Path(f).name)
        nn = int(n.group(1)) if n else 0
        if f.endswith(".md"):
            it = re.finditer(r"^## \{(\w+ \d+\.\d+)\}\s*\n(.*?)(?=^## \{|\Z)", t, re.M | re.S)
        else:
            it = re.finditer(r"// \{(\w+ \d+\.\d+)\}\s*\n(.*?)#EGW\[", t, re.S)
        for m in it:
            out[m.group(1)] = m.group(2)
            chap[m.group(1)] = nn
    return out, chap


def setname(book, nn):
    if book == "SC":
        return "SC"
    if book == "MB" or nn <= 20:
        return "published"
    return "unpublished"


def verse(ver, code, ch, v):
    """One verse. Files are "VER|BOOK|ch|v|text" lines; a heading line has H in
    the verse field. The older layout, a chapter header line and verses glued to
    the text, is read as a fallback."""
    fs = glob.glob(str(version_dir(ver) / f"*{code}.txt"))
    if not fs:
        return None
    t = open(fs[0], encoding="utf-8").read()
    if "|" in t[:20]:
        for line in t.splitlines():
            parts = line.split("|", 4)
            if len(parts) == 5 and parts[2] == str(ch) and parts[3] == str(v):
                t = re.sub(r"\{[HG]\d+\}", "", parts[4]).replace("\u200b", "")
                t = re.sub(r"\s*§\d*\s*", " ", t).replace("¶", " ")
                return re.sub(r"\s+", " ", t).strip()
        return None
    parts = re.split(r"^(\S.*? (\d+))\s*$", t, flags=re.M)
    for i in range(1, len(parts) - 2, 3):
        if parts[i + 1] == str(ch):
            body = parts[i + 2]
            m = re.search(r"(?<!\d)" + str(v) + r"(?=\D)(.*?)(?=(?<!\d)" + str(v + 1) + r"(?=\D)|\Z)", body, re.S)
            return m.group(1).strip().replace("\n", " ") if m else None
    return None


def kjv_hits(head, limit=60):
    """The whole King James is the KJVS set, "KJVS|GEN|1|1|text{H0430}" lines with
    Strong's numbers in braces, which are stripped. KJV (Genesis to 2 Kings) is the
    fallback in either of its two layouts."""
    hits = []
    src = version_dir("KJVS") if version_dir("KJVS").is_dir() else version_dir("KJV")
    for f in sorted(glob.glob(str(src / "*.txt"))):
        code = re.sub(r"^\d+", "", Path(f).stem)
        t = open(f, encoding="utf-8").read()
        if t.startswith(("KJVS|", "KJV|")):
            for line in t.splitlines():
                parts = line.split("|", 4)
                if len(parts) == 5 and parts[2].isdigit() and parts[3].isdigit():
                    text = re.sub(r"\{[HG]\d+\}", "", parts[4])
                    if head.search(text):
                        hits.append((parts[1], int(parts[2]), int(parts[3]), text.strip()))
                        if len(hits) >= limit:
                            return hits
            continue
        parts = re.split(r"^(\S.*? (\d+))\s*$", t, flags=re.M)
        for i in range(1, len(parts) - 2, 3):
            ch, body = parts[i + 1], parts[i + 2]
            for vm in re.finditer(r"(?<!\d)(\d{1,3})(?=\D)(.*?)(?=(?<!\d)\d{1,3}(?=\D)|\Z)", body, re.S):
                if head.search(vm.group(2)):
                    hits.append((code, int(ch), int(vm.group(1)), vm.group(2).strip().replace("\n", " ")))
                    if len(hits) >= limit:
                        return hits
    return hits


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--head", required=True, help="English regex, case-insensitive")
    ap.add_argument("--thai", default="", help="comma-separated Thai candidate forms")
    ap.add_argument("--verses", default="", help='comma-separated "CODE ch:v", e.g. "ROM 3:25,1JN 2:2"')
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    head = re.compile(a.head, re.I)
    forms = [x.strip() for x in a.thai.split(",") if x.strip()]
    L = [f"# Term data: {a.head}", ""]
    L += ["## 1. Sites", "", "| Anchor | Set | English | Thai forms found |", "|---|---|---|---|"]
    site_counts = {f: {"published": 0, "unpublished": 0, "SC": 0} for f in forms}
    recast = {"published": 0, "unpublished": 0, "SC": 0}
    nsites = {"published": 0, "unpublished": 0, "SC": 0}
    occ = {f: {} for f in forms}
    for book in ("MB", "PP", "SC"):
        en = english_paras(book)
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
            if not found:
                recast[s] += 1
            L.append(f"| {{{anchor}}} | {s} | {' / '.join(x[:160] for x in sents[:2])} | {', '.join(found) if found else ('none' if tp else 'no Thai paragraph')} |")
    L += ["", "## 2. Counts", "", f"Sites with the head: published {nsites['published']}, unpublished {nsites['unpublished']}, SC {nsites['SC']}.", "",
          "| Thai form | Sites published / unpublished / SC | Occurrences MB / PP / SC |", "|---|---|---|"]
    for f in forms:
        c = site_counts[f]
        L.append(f"| {f} | {c['published']} / {c['unpublished']} / {c['SC']} | {occ[f].get('MB',0)} / {occ[f].get('PP',0)} / {occ[f].get('SC',0)} |")
    L.append(f"| none of the forms (recast) | {recast['published']} / {recast['unpublished']} / {recast['SC']} | |")
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
            for ver in VERSIONS:
                t = verse(ver, code, ch, v)
                L.append(f"- {ver}: {t if t else '(not on disk)'}")
            L.append("")
    hits = kjv_hits(head)
    L += ["### KJV verses matching the head, with the Thai versions on disk", ""]
    for code, ch, v, t in hits:
        L.append(f"- {code} {ch}:{v} KJV: {t[:200]}")
        for ver in VERSIONS:
            th_v = verse(ver, code, ch, v)
            if th_v:
                L.append(f"  {ver}: {th_v[:220]}")
    if not hits:
        L.append("none")
    Path(os.path.expanduser(a.out)).write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"wrote {a.out}: sites published {nsites['published']}, unpublished {nsites['unpublished']}, SC {nsites['SC']}; KJV hits {len(hits)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
