#!/usr/bin/env python3
"""Shared helpers for the DA Thai scripts. Reads only; nothing here writes.

The chapter files are Typst. Each paragraph carries a "// {DA ###.#}" comment
above it and an "#EGW[\\{DA ###.#\\}]" tag at its end; the English source
anchors the same paragraphs with "## {DA ###.#}" headings and closes each with
the "{DA ###.#}" tag. Chapter 0 is the preface, DA00_preface_th.typ and
DA00_preface_en.md. The scripts that import this file write only under
~/claude-sandbox/da-audit/, except da_editor_markers.py, which rewrites the
chapter on the translator's "editor" command.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
PROJECT = ROOT / "th" / "DA"
STAGES = ("03_public", "02_edit", "01_raw")
SOURCE_DIR = PROJECT / "00_source"
PRINT_DIR = PROJECT / "04_assets" / "editions" / "print"
NOTES = PROJECT / "04_assets" / "notes" / "DA_notes.txt"
SANDBOX = Path(os.path.expanduser("~/claude-sandbox/da-audit"))
# The offline Bible corpus: one directory per version under th/ or en/, one
# pipe file per book, "VER|BOOK|chapter|verse|text"; a heading row carries H in
# the verse field. Set BIBLE_CORPUS in the environment to point elsewhere.
BIBLE = Path(os.path.expanduser(os.environ.get("BIBLE_CORPUS", "~/programming/bible")))
# Every DA script carries all ten Thai versions; TFB has Matthew to 2 Peter only.
VERSIONS = ("THSV", "TNCV", "TKJV", "TH1940", "TH1971", "THA-ERV", "TCV", "NTV", "TCL", "TFB")
DEFAULT_VERSION = "THSV"
KNOWN_LABELS = set(VERSIONS) | {"ERV", "KJV", "RV"}
# Book names as the manuscripts write them, shared with SC: CODE | Thai | English names.
TH_BOOKS = ROOT / "th" / "SC" / "04_assets" / "scripts" / "th_books.txt"
GLOSSARY = ROOT / "th" / "assets" / "translation_profile" / "thai-glossary.txt"
PROFILE = ROOT / "th" / "assets" / "translation_profile" / "thai-profile.txt"
NAMES = ROOT / "th" / "assets" / "translation_profile" / "thai-names.tsv"

THAI = "฀-๿"
COMMENT_ANCHOR = re.compile(r"^\s*//\s*\{DA\s+(\d+\.\d+)\}\s*$")
TAG_ANCHOR = re.compile(r"#EGW\[\\\{DA\s+(\d+\.\d+)\\\}\]")
EN_ANCHOR = re.compile(r"^##\s*\{DA\s+(\d+\.\d+)\}\s*$")
EN_TAIL = re.compile(r"\s*\{DA\s+(\d+\.\d+)\}\s*$")
EN_FOOTNOTE_DEF = re.compile(r"^\[\^(\d+)\]:\s*(.*)$")
EN_FOOTNOTE_REF = re.compile(r"\[\^\d+\]")

# Marker vocabulary of the DA rounds. Severity HIGH, MED or LOW stands on FACT,
# OMISSION, ADDITION, TERM and CLARITY; none on the others.
CLASSES = ("VERSE TERM FACT OMISSION ADDITION REF NOTE SPELL GRAM CLARITY "
           "PRINT SUBTITLE FLAG FIX").split()
WITH_SEVERITY = {"FACT", "OMISSION", "ADDITION", "TERM", "CLARITY"}
ROUND_CLASSES = {
    "draft": {"VERSE", "TERM", "FACT", "OMISSION", "ADDITION", "REF", "NOTE", "SPELL", "GRAM", "CLARITY",
              "PRINT", "SUBTITLE"},
    "flags": {"FLAG"},
    "check": {"FIX"},
}
MARKER = re.compile(
    r"\[\[(?P<cls>" + "|".join(CLASSES) + r")(?: (?P<sev>HIGH|MED|LOW))? #(?P<num>\d+[a-z]?)"
    r"\|(?P<old>[^|]*?) -> (?P<new>[^|]*?)\|(?P<note>.*?)\]\]", re.S)
OPEN_MARKER = re.compile(r"\[\[")
# An editor's choice: ((original:A/B)) when the standing wording is one option, ((A/B)) when both are new.
EDITOR_CHOICE = re.compile(r"\(\([^()]*\)\)")
# A citation hidden in a Typst block comment, for a THSV quotation from the based-on passage (DA 3.D).
HIDDEN_CITE = re.compile(
    rf"/\*\s*(?P<cite>(?:[1-3]\s)?[{THAI}]+\s+\d+(?::\d+(?:\s*[-–]\s*\d+)?(?:,\s*\d+(?:\s*[-–]\s*\d+)?)*)?"
    rf"(?:\s+(?P<label>[A-Z][A-Z0-9-]+))?)\s*\*/")


def version_dir(label):
    """A version's directory: bible/th/<label>, bible/en/<label>, or bible/<label>."""
    for d in (BIBLE / "th" / label, BIBLE / "en" / label, BIBLE / label):
        if d.is_dir():
            return d
    return BIBLE / label


def chapter_name(nn, suffix="_th.typ"):
    nn = int(nn)
    return f"DA00_preface{suffix}" if nn == 0 else f"DA{nn:02d}{suffix}"


def chapter_path(nn):
    """The chapter file for NN, searched most finished stage first; 0 is the preface."""
    name = chapter_name(nn)
    for stage in STAGES:
        p = PROJECT / stage / name
        if p.exists():
            return p
    sys.exit(f"no chapter file {name} under th/DA/01_raw, 02_edit or 03_public")


def source_path(nn):
    """The English source for NN under th/DA/00_source; 0 is the preface."""
    p = SOURCE_DIR / chapter_name(nn, "_en.md")
    if p.exists():
        return p
    sys.exit(f"no English source {p.name} under th/DA/00_source")


def print_path(nn):
    """The 2023 print's chapter under th/DA/04_assets/editions/print, or None."""
    p = PRINT_DIR / chapter_name(nn, "_print_th.typ")
    return p if p.exists() else None


def anchor_key(a):
    page, para = a.split(".")
    return (int(page), int(para))


def in_range(anchor, first, last):
    k = anchor_key(anchor)
    if first and k < anchor_key(first):
        return False
    if last and k > anchor_key(last):
        return False
    return True


class Para:
    __slots__ = ("anchor", "start", "end", "lines", "tags")

    def __init__(self, anchor, start):
        self.anchor = anchor      # from the comment line
        self.start = start        # 1-based line of the comment
        self.end = start
        self.lines = []           # body lines, comment excluded
        self.tags = []            # anchors found in #EGW tags in the body

    @property
    def text(self):
        return "\n".join(self.lines)

    @property
    def body(self):
        """The paragraph's prose: the text without its #EGW tag, trimmed."""
        return TAG_ANCHOR.sub("", self.text).strip()

    @property
    def subtitle(self):
        """The "=== " subtitle line above the paragraph's prose, or None."""
        m = SUBTITLE_LINE.search(self.text)
        return m.group(1).strip() if m else None

    @property
    def prose(self):
        """The body without any "=== " subtitle line."""
        return SUBTITLE_LINE.sub("", self.body).strip()


# A subtitle, crafted by the translator, sits on its own "=== " line between the
# anchor comment and the paragraph's prose, as in th/PP/03_public.
SUBTITLE_LINE = re.compile(r"^===\s+(.*)$", re.M)


def parse_thai(text):
    """Split a Typst chapter (or a print file) into paragraphs by anchor comments.

    Returns (head_lines, paras): head_lines is everything before the first
    anchor comment (the #chapter header and imports); each Para runs from its
    comment line to the line before the next comment.
    """
    lines = text.split("\n")
    head, paras, cur = [], [], None
    for i, line in enumerate(lines, 1):
        m = COMMENT_ANCHOR.match(line)
        if m:
            cur = Para(m.group(1), i)
            paras.append(cur)
            continue
        if cur is None:
            head.append(line)
            continue
        cur.lines.append(line)
        cur.end = i
        cur.tags.extend(TAG_ANCHOR.findall(line))
    return head, paras


def parse_english(text):
    """Map anchor -> English paragraph text, the closing "{DA ###.#}" tag removed.

    A footnote definition line "[^1]: ..." is appended to its paragraph as a
    "NOTE 1: ..." line; the "[^1]" reference stays in the prose. Indented lines
    (poetry) keep their words and lose the indent.
    """
    paras, heading, buf = {}, None, []

    def flush():
        block = "\n".join(buf).strip()
        if not block or heading is None:
            return
        m = EN_FOOTNOTE_DEF.match(block)
        if m:
            paras[heading] = paras.get(heading, "") + f"\nNOTE {m.group(1)}: {m.group(2)}"
            return
        block = EN_TAIL.sub("", block)
        paras[heading] = (paras[heading] + "\n\n" + block) if heading in paras else block

    for line in text.split("\n"):
        m = EN_ANCHOR.match(line)
        if m:
            flush()
            heading, buf = m.group(1), []
            continue
        if line.strip() == "":
            flush()
            buf = []
            continue
        buf.append(line.strip())
    flush()
    return paras


def english_words(text):
    """The words of an English paragraph with footnote references and NOTE lines removed."""
    text = "\n".join(l for l in text.split("\n") if not l.startswith("NOTE "))
    return EN_FOOTNOTE_REF.sub("", text)


def source_header(nn):
    """The English source's header fields: number, title, url, basedon."""
    out = {"number": "", "title": "", "url": "", "basedon": ""}
    text = source_path(nn).read_text(encoding="utf-8")
    head = text.split("\n---\n", 1)[0] if text.startswith("---") else ""
    for key in out:
        m = re.search(rf"^\s*{key}:\s*(.*)$", head, re.M)
        if m:
            out[key] = m.group(1).strip()
    m = re.search(r"^\s*en:\s*(.*)$", head.split("title:", 2)[-1], re.M) if "chapter:" in head else None
    if m:
        out["title"] = m.group(1).strip()
    return out


def load_books():
    """(thai name -> code, english name -> code) from th_books.txt."""
    th, en = {}, {}
    for line in TH_BOOKS.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        code, thai, english = [c.strip() for c in line.split("|")]
        if thai:
            th[thai] = code
        for name in english.split(";"):
            if name.strip():
                en[name.strip()] = code
    return th, en


def book_names():
    """code -> Thai name as the manuscripts write it (the first row of each code)."""
    out = {}
    for line in TH_BOOKS.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        code, thai, _ = [c.strip() for c in line.split("|")]
        out.setdefault(code, thai)
    return out


EN_REF = re.compile(
    r"(?P<book>(?:[1-3]\s)?[A-Z][a-z]+(?:\s(?:of\s)?[A-Z][a-z]+)?)\s+(?P<ch>\d+)"
    r"(?::(?P<vv>\d+(?:\s*[-–]\s*\d+)?(?:,\s*\d+(?:\s*[-–]\s*\d+)?)*))?")
CONT_REF = re.compile(r";\s*(?P<ch>\d+)(?::(?P<vv>\d+(?:\s*[-–]\s*\d+)?(?:,\s*\d+(?:\s*[-–]\s*\d+)?)*))?")


def expand_verses(vv):
    out = set()
    for part in re.split(r",\s*", vv):
        if re.search(r"[-–]", part):
            lo, hi = re.split(r"\s*[-–]\s*", part)
            out.update(range(int(lo), int(hi) + 1))
        else:
            out.add(int(part))
    return out


def parse_refs(text, en_books=None):
    """English references in text as [(code, chapter, verses or None)]; a
    chapter after a semicolon takes the book before it, as in "Matthew 3; Mark
    1:1-11; Luke 3:1-18" and "Luke 1:5-23, 57-80; 2:1-7"."""
    en_books = en_books or load_books()[1]
    out, last_code, pos = [], None, 0
    for m in EN_REF.finditer(text):
        for c in CONT_REF.finditer(text, pos, m.start()):
            if last_code:
                out.append((last_code, int(c.group("ch")), expand_verses(c.group("vv")) if c.group("vv") else None))
        name = re.sub(r"\s+", " ", m.group("book")).strip()
        code = en_books.get(name)
        if code is None:
            words = name.split()
            code = en_books.get(words[-1]) if len(words) > 1 else None
        if code is None:
            pos = m.end()
            continue
        out.append((code, int(m.group("ch")), expand_verses(m.group("vv")) if m.group("vv") else None))
        last_code, pos = code, m.end()
    for c in CONT_REF.finditer(text, pos):
        if last_code:
            out.append((last_code, int(c.group("ch")), expand_verses(c.group("vv")) if c.group("vv") else None))
    return out


def based_on(nn):
    """The chapter's based-on passage as [(code, chapter, verses or None)]; [] when none."""
    line = source_header(nn)["basedon"]
    return parse_refs(line) if line else []


def in_based_on(refs, code, ch, v=None):
    for c, chn, vv in refs:
        if c == code and chn == ch and (vv is None or v is None or v in vv):
            return True
    return False


_versions = {}


def clean_verse(t):
    """One verse's text with Strong's tags, pilcrows, section marks, the King
    James italics marks and zero-width spaces removed."""
    t = re.sub(r"\{[HG]\d+(?:\s+[HG]\d+)*\}", "", t).replace("​", "")
    t = re.sub(r"\s*§\d*\s*", " ", t).replace("¶", " ")
    t = re.sub(r"_([^_]+)_", r"\1", t)
    return re.sub(r"\s+", " ", t).strip()


def load_version(label, code):
    """(chapter, verse) -> text for one book of one version, or None when not on disk."""
    key = (label, code)
    if key in _versions:
        return _versions[key]
    vd = version_dir(label)
    files = list(vd.glob(f"*{code}.txt")) if vd.is_dir() else []
    if not files:
        _versions[key] = None
        return None
    verses = {}
    for raw in files[0].read_text(encoding="utf-8").splitlines():
        parts = raw.split("|", 4)
        if len(parts) == 5 and parts[2].isdigit() and parts[3].isdigit():
            verses[(int(parts[2]), int(parts[3]))] = clean_verse(parts[4])
    _versions[key] = verses
    return verses


def verse_text(label, code, ch, v):
    verses = load_version(label, code)
    return verses.get((ch, v)) if verses else None


def load_bounds():
    """code -> {chapter: last verse}, from the WEB pipe files; empty when absent."""
    bounds = {}
    d = version_dir("WEB")
    if not d.is_dir():
        return bounds
    for f in d.glob("*.txt"):
        for line in f.read_text(encoding="utf-8").splitlines():
            parts = line.split("|", 4)
            if len(parts) < 5 or not parts[2].isdigit():
                continue
            try:
                chn, vn = int(parts[2]), int(parts[3].split("-")[-1])
            except ValueError:
                continue
            b = bounds.setdefault(parts[1], {})
            b[chn] = max(b.get(chn, 0), vn)
    return bounds


def mask_markers(text):
    """Replace every intact marker by its old side, so the paragraph is checked
    as it stands while the marker's English note is not."""
    return MARKER.sub(lambda m: m.group("old"), text)


def committed_text(path):
    """The chapter as committed at HEAD, or None when git cannot say."""
    rel = path.resolve().relative_to(ROOT)
    try:
        out = subprocess.run(["git", "-C", str(ROOT), "show", f"HEAD:{rel.as_posix()}"],
                             capture_output=True, text=True, check=True)
        return out.stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def verses_path(nn):
    """The chapter's verse picks from pass 1: ~/claude-sandbox/da-audit/DANN-verses.tsv,
    tab-separated with a header line, the columns
    anchor, kind, english, ref, version, alt_version, close, reason;
    kind is quotation or allusion, ref is "LUK 2:14" or "LUK 2:8–14", close is yes or no."""
    return SANDBOX / f"DA{int(nn):02d}-verses.tsv"


REF_CODE = re.compile(r"^(?P<code>[1-3]?[A-Z]{2,3})\s+(?P<ch>\d+)(?::(?P<vv>\d+(?:\s*[-–]\s*\d+)?(?:,\s*\d+(?:\s*[-–]\s*\d+)?)*))?$")


def parse_ref_code(ref):
    """"LUK 2:8–14" -> ("LUK", 2, {8..14}); a bare chapter gives None for the verses."""
    m = REF_CODE.match(ref.strip())
    if not m:
        return None
    return m.group("code"), int(m.group("ch")), expand_verses(m.group("vv")) if m.group("vv") else None


def load_verse_picks(nn):
    """The rows of the chapter's verses file as dicts, [] when the file is absent."""
    p = verses_path(nn)
    if not p.exists():
        return []
    lines = p.read_text(encoding="utf-8").splitlines()
    if not lines:
        return []
    keys = [k.strip() for k in lines[0].split("\t")]
    rows = []
    for line in lines[1:]:
        if not line.strip() or line.startswith("#"):
            continue
        cells = line.split("\t")
        rows.append({k: (cells[i].strip() if i < len(cells) else "") for i, k in enumerate(keys)})
    return rows


def glossary_rows(section=None):
    """Rows of thai-glossary.txt as (section number, cells); section 1 and 2
    rows are English | Thai | Notes, section 3 rows Word | Correct | Incorrect | Notes."""
    rows, sec = [], 0
    for line in GLOSSARY.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^##\s+(\d+)\.", line)
        if m:
            sec = int(m.group(1))
            continue
        if not line.startswith("|") or sec == 0:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not cells or cells[0] in ("English", "Word") or set(cells[0]) <= {"-"}:
            continue
        if section is None or sec == section:
            rows.append((sec, cells))
    return rows
