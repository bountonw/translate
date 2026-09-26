#!/usr/bin/env python3
"""Data packet for the phrase round on one Fundamental Belief. Reads only; judges nothing.

    python3 lo/FB/04_assets/scripts/fb_packet.py --belief 07 [--out ~/claude-sandbox/fb-audit]

Writes fbNN-packet.md with: the English statement; every verse of its reference list in KJV, LCV
and LO2012 (a range of up to 8 verses is quoted, a whole chapter or a longer range is listed);
the verse each embedded quotation most resembles, searched over the quoted verses and the KJV text of every listed chapter; the GC glossary rows whose English head occurs
in the statement, with the count of each Lao form in lo/GC/03_public and lo/AA; the translator's
conventions (sections 5 and 6 of the web instructions); and every Lao belief file already in
lo/FB. Verses come from ~/programming/LMV/scripts/brief.py; zero-width spaces and pilcrows are
stripped from every quoted line.
"""
import argparse
import difflib
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BRIEF = Path.home() / "programming/LMV/scripts/brief.py"
GLOSSARY = ROOT / "lo/GC/04_assets/translation_profile/GC-glossary.txt"
CONVENTIONS = [ROOT / "lo/FB/04_assets/planning/web-instructions.txt", ROOT / "lo/FB/statements.txt"]
CORPUS = [ROOT / "lo/GC/03_public", ROOT / "lo/AA"]
MAX_QUOTED_RANGE = 8
KJV_DIR = Path.home() / "programming/bible/en/KJVS"

BOOKS = {
    "Gen": "GEN", "Exod": "EXO", "Lev": "LEV", "Num": "NUM", "Deut": "DEU", "Josh": "JOS", "Judg": "JDG",
    "Ruth": "RUT", "1 Sam": "1SA", "2 Sam": "2SA", "1 Kings": "1KI", "2 Kings": "2KI", "1 Chron": "1CH",
    "2 Chron": "2CH", "Ezra": "EZR", "Neh": "NEH", "Esther": "EST", "Job": "JOB", "Ps": "PSA", "Prov": "PRO",
    "Eccl": "ECC", "Song": "SNG", "Isa": "ISA", "Jer": "JER", "Lam": "LAM", "Ezek": "EZK", "Dan": "DAN",
    "Hosea": "HOS", "Joel": "JOL", "Amos": "AMO", "Obad": "OBA", "Jonah": "JON", "Mic": "MIC", "Nah": "NAM",
    "Hab": "HAB", "Zeph": "ZEP", "Haggai": "HAG", "Zech": "ZEC", "Mal": "MAL", "Matt": "MAT", "Mark": "MRK",
    "Luke": "LUK", "John": "JHN", "Acts": "ACT", "Rom": "ROM", "1 Cor": "1CO", "2 Cor": "2CO", "Gal": "GAL",
    "Eph": "EPH", "Phil": "PHP", "Col": "COL", "1 Thess": "1TH", "2 Thess": "2TH", "1 Tim": "1TI",
    "2 Tim": "2TI", "Titus": "TIT", "Philemon": "PHM", "Heb": "HEB", "James": "JAS", "1 Peter": "1PE",
    "2 Peter": "2PE", "1 John": "1JN", "2 John": "2JN", "3 John": "3JN", "Jude": "JUD", "Rev": "REV",
}
ONE_CHAPTER = {"OBA", "PHM", "2JN", "3JN", "JUD"}
BOOK_RE = re.compile(r"^((?:[1-3] )?[A-Z][a-z]+)\.?\s+(.*)$")


def read_statement(n):
    p = ROOT / f"lo/FB/00_source/FB{n:02d}_en.md"
    text = p.read_text(encoding="utf-8")
    title = re.search(r"^\s+en: (.+)$", text.split("---")[1], re.M).group(1).strip()
    body = text.split("---", 2)[2]
    para = next(l for l in body.splitlines() if l.strip() and not l.startswith("## "))
    para = re.sub(r"\s*\{FB [0-9.]+\}\s*$", "", para).strip()
    m = re.search(r"\(([^()]*)\.\)\s*$", para)
    refs = m.group(1) if m else ""
    prose = para[: m.start()].strip() if m else para
    return title, prose, refs, para


def parse_refs(refs):
    """Yield (code, chapter, first, last, label). last None = whole chapter; first None = chapter range."""
    book = None
    for tok in [t.strip() for t in refs.split(";") if t.strip()]:
        m = BOOK_RE.match(tok)
        if m and m.group(1) in BOOKS:
            book, rest = BOOKS[m.group(1)], m.group(2).strip()
        else:
            rest = tok
        if book is None:
            continue
        if ":" not in rest:
            if book in ONE_CHAPTER:
                for part in rest.split(","):
                    a, _, b = part.strip().partition("-")
                    yield book, 1, int(a), int(b or a), f"{book} 1:{part.strip()}"
            else:
                yield book, rest, None, None, f"{book} {rest}"
            continue
        chap, _, verses = rest.partition(":")
        chap = int(chap)
        for part in [v.strip() for v in verses.split(",") if v.strip()]:
            if "-" in part:
                a, b = part.split("-", 1)
                if ":" in b:  # cross-chapter range, as 6:14-7:1
                    c2, v2 = b.split(":")
                    yield book, chap, int(a), 999, f"{book} {chap}:{a}-end"
                    yield book, int(c2), 1, int(v2), f"{book} {c2}:1-{v2}"
                else:
                    yield book, chap, int(a), int(b), f"{book} {chap}:{part}"
            else:
                yield book, chap, int(part), int(part), f"{book} {chap}:{part}"


def clean(line):
    return re.sub(r"\s+", " ", line.replace("​", "").replace("¶", " ").replace("_", "")).strip()


def verse(code, chap, v):
    """KJV, LCV, LO2012 for one verse, or None when the verse does not exist."""
    r = subprocess.run([sys.executable, str(BRIEF), code, f"{chap}:{v}", "--no-thai"], capture_output=True, text=True)
    out = {}
    for line in r.stdout.splitlines():
        m = re.match(r"^\s{2}(KJV|LCV|LO2012)\s+(.*)$", line)
        if m:
            out[m.group(1)] = clean(m.group(2))
    return out or None


def gather_verses(refs):
    quoted, listed = [], []
    for code, chap, first, last, label in parse_refs(refs):
        if first is None:
            listed.append(label)
            continue
        if last != 999 and last - first + 1 > MAX_QUOTED_RANGE:
            listed.append(label)
            continue
        v = first
        while v <= last:
            got = verse(code, chap, v)
            if got is None:
                break
            quoted.append((f"{code} {chap}:{v}", got))
            v += 1
    return quoted, listed


def kjv_chapter_verses(code, chapters):
    """(label, KJV text) for every verse of the chapters named, from the KJVS pipe file; Strong's tags stripped."""
    files = list(KJV_DIR.glob(f"*{code}.txt"))
    if not files:
        return []
    out = []
    for line in files[0].read_text(encoding="utf-8", errors="ignore").splitlines():
        parts = line.split("|", 4)
        if len(parts) == 5 and parts[1] == code and int(parts[2]) in chapters:
            out.append((f"{code} {parts[2]}:{parts[3]}", clean(re.sub(r"\{[^}]*\}", "", parts[4]))))
    return out


def listed_chapters(refs):
    """{code: set of chapter numbers} for the whole-chapter references."""
    out = {}
    for code, chap, first, last, label in parse_refs(refs):
        if first is not None:
            continue
        for part in str(chap).split(","):
            a, _, b = part.strip().partition("-")
            if a.isdigit():
                out.setdefault(code, set()).update(range(int(a), int(b or a) + 1))
    return out


def norm_words(s):
    return re.sub(r"[^a-z0-9 ]", " ", s.lower().replace("’", "'")).split()


def match_quotations(prose, quoted, refs):
    pool = [(label, got["KJV"]) for label, got in quoted if "KJV" in got]
    for code, chapters in listed_chapters(refs).items():
        pool += kjv_chapter_verses(code, chapters)
    out = []
    for q in re.findall(r"[“\"]([^”\"]+)[”\"]", prose):
        best = None
        for label, kjv in pool:
            a, b = norm_words(q), norm_words(kjv)
            sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
            hit = sum(bl.size for bl in sm.get_matching_blocks()) / max(1, len(a))
            if best is None or hit > best[0]:
                best = (hit, label)
        out.append((q, best))
    return out


def glossary_rows(prose):
    if not GLOSSARY.exists():
        return [], "glossary file missing"
    words = set(norm_words(prose))
    rows = []
    for line in GLOSSARY.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| ") or line.startswith("| English") or line.startswith("|---"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        heads = [h.strip() for h in re.split(r"/|,", cells[0])]
        for h in heads:
            hw = norm_words(re.sub(r"\(.*?\)", "", h))
            if hw and all(w in words for w in hw):
                rows.append(cells)
                break
    return rows, ""


def corpus_counts(lao_forms):
    counts = {}
    for form in lao_forms:
        n = 0
        for base in CORPUS:
            if not base.exists():
                continue
            for p in base.rglob("*"):
                if p.suffix in (".md", ".typ", ".txt") and p.is_file():
                    n += p.read_text(encoding="utf-8", errors="ignore").count(form)
        counts[form] = n
    return counts


def conventions():
    for p in CONVENTIONS:
        if p.exists():
            text = p.read_text(encoding="utf-8")
            m = re.search(r"^5\. Binding conventions.*?(?=^7\. Output rules)", text, re.M | re.S)
            return p, (m.group(0) if m else text)
    return None, ""


def lao_files():
    out = []
    for stage in ("01_raw", "02_edit", "03_public"):
        for p in sorted((ROOT / "lo/FB" / stage).glob("FB*_lo.typ")):
            out.append((p, p.read_text(encoding="utf-8")))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--belief", required=True, type=int)
    ap.add_argument("--out", default=str(Path.home() / "claude-sandbox/fb-audit"))
    a = ap.parse_args()
    n = a.belief
    title, prose, refs, para = read_statement(n)
    quoted, listed = gather_verses(refs)
    quotations = match_quotations(prose, quoted, refs)
    rows, gloss_note = glossary_rows(prose)
    forms = sorted({f.strip() for r in rows for f in r[1].split("/") if f.strip()})
    counts = corpus_counts(forms)
    conv_path, conv = conventions()
    drafts = lao_files()

    L = [f"# FB{n:02d} packet — {title}", "", "## 1. English", "", f"Title: {title}", "", para, ""]
    L += ["## 2. Reference list, verse by verse", ""]
    for label, got in quoted:
        L.append(f"### {label}")
        for k in ("KJV", "LCV", "LO2012"):
            if k in got:
                L.append(f"{k}: {got[k]}")
        L.append("")
    if listed:
        L += ["Listed, not quoted (whole chapters or ranges over 8 verses): " + "; ".join(listed), ""]
    L += ["## 3. Embedded quotations", ""]
    if quotations:
        for q, best in quotations:
            if best and best[0] >= 0.5:
                L.append(f"- “{q}” — closest verse {best[1]} (word overlap {best[0]:.0%}); its LCV and LO2012 are in section 2 or fetched by brief.py")
            else:
                L.append(f"- “{q}” — no verse of the reference list matches above 50%")
    else:
        L.append("None in quotation marks.")
    L += ["", "## 4. GC glossary rows whose English head occurs in the statement", ""]
    if gloss_note:
        L.append(gloss_note)
    for r in rows:
        L.append("| " + " | ".join(r) + " |")
    L += ["", "Corpus count of each Lao form in lo/GC/03_public and lo/AA:", ""]
    for f, c in counts.items():
        L.append(f"- {f}: {c}")
    L += ["", f"## 5. Conventions ({conv_path.relative_to(ROOT) if conv_path else 'file missing'})", "", conv.rstrip(), ""]
    L += ["## 6. Lao belief files in lo/FB", ""]
    for p, text in drafts:
        L += [f"### {p.relative_to(ROOT)}", "", text.rstrip(), ""]
    if not drafts:
        L.append("None yet.")
    out = Path(a.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    dest = out / f"fb{n:02d}-packet.md"
    dest.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"{dest}: {len(quoted)} verses quoted, {len(listed)} references listed, {len(quotations)} quotations, "
          f"{len(rows)} glossary rows, {len(drafts)} Lao files, {len(' '.join(L).split())} words")
    return 0


if __name__ == "__main__":
    sys.exit(main())
