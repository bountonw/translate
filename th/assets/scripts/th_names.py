#!/usr/bin/env python3
"""Biblical names of every Thai book, spelled as THSV spells them. Reads the
corpus; writes th/assets/translation_profile/thai-names.tsv and prints the
exceptions.

    python3 th/assets/scripts/th_names.py                 # names new to the table
    python3 th/assets/scripts/th_names.py --book DA       # one book's sources
    python3 th/assets/scripts/th_names.py --all           # rebuild every row

The rule is profile 5.A: a name keeps the spelling the series has printed, in
the glossary's section 2 or in the finished books; a name no book has printed
takes THSV's spelling; a people takes ชาว before its root, Israel and its tribes
คน (DA 3.K). Columns: English, who, form (the spelling to use), series (the
printed form and where), THSV, TH1971, TNCV, books, verses, status, note.

A name is a capitalised English word of a book's source (th/PP, th/MB, th/SC,
th/DA, and th/SJ when its English is on disk), not at the start of a sentence
or a line, that the King James (KJVS) also carries capitalised inside a verse
more often than in lower case, outside a stoplist of divine names, titles,
pronouns, interjections and book names. For each name the script takes up to
forty King James verses carrying it, spread over the whole Bible, and finds
the THSV substring present in the most of those verses and in almost none of
the other verses of the same books: a plausible Thai word of three characters
or more, not a word common across the whole version, the longest of those
whose coverage is within a tenth of the best, with a title or common-noun
prefix such as พระ or เมือง stripped. The same alignment runs on TH1971 and
TNCV; and the finished books (th/PP, th/MB, th/SJ, th/SC) are read at the
English sites that carry the name to see whether the THSV form stands there
or another form does. Among equally covered candidates the one whose
consonants best follow the English name's consonants wins, so อาดัม beats a
fragment of it. A name in one or two verses cannot be aligned by coverage:
the Thai word in the THSV verse whose consonants best follow the English
name's is taken where about two in three match, and the note says whether
TH1971 and TNCV write the same; where nothing matches, no form is proposed,
the THSV verse is quoted in the note, and the row is marked weak.

Columns: English, who (blank; the translator fills it where one English name
belongs to several people), THSV, TH1971, TNCV, books, verses, status, note.
Status, in plain words: settled (the THSV form is clear; where TH1971 or TNCV
spell it otherwise the note says so, and profile 5.A rules THSV); "two THSV
forms" (THSV spells the name two ways, each on its own row); "not in KJV"
(the King James has no such word; listed for ruling, not aligned); "a book
differs" (PP, MB, SJ or SC writes another form, anchors given); "weak match"
(under 60 percent of the verses carry the form, or one or two verses on
which the three versions do not agree). Only rows not settled are printed.
Existing rows are kept unless --all is given, so a later book gains only its
new names.
"""
import argparse
import glob
import os
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BIBLE = Path(os.path.expanduser(os.environ.get("BIBLE_CORPUS", "~/programming/bible")))
TABLE = ROOT / "th/assets/translation_profile/thai-names.tsv"
BOOKS = ("PP", "MB", "SC", "DA", "SJ")
VERSIONS = ("THSV", "TH1971", "TNCV")
THAI_RUN = re.compile(r"[฀-๿]+(?:-[฀-๿]+)*")   # THSV hyphenates some names: เท-ราห์, เบ-ลา
CAP = re.compile(r"(?<![\w'’])([A-Z][a-z]+(?:-[A-Za-z][a-z]+)*)(?=[^\w]|$)")
LOWER = re.compile(r"(?<![\w'’])[a-z]+")
STOP = set("""God Lord LORD Jesus Christ Jehovah Saviour Savior Father Son Spirit Holy Ghost Almighty Redeemer
Creator Comforter Messiah King Prince Master Lamb Word Amen Selah Sabbath Scripture Scriptures Bible Gospel
Heaven Hell Paradise Devil Thou Thee Thy Thine Ye You He Him His She Her They Them Their We Us Our My Mine Me I
Behold Verily Alas Lo Oh Ah Woe Hail Yea Nay Alleluia Hallelujah Hosanna Maranatha Rabbi Rabboni Teacher Shepherd
Judge Advocate Mediator Intercessor Deliverer Sovereign Majesty Deity Godhead Providence Infinite Eternal Omnipotent
Testament Law Commandments Decalogue Church Christian Christians Christianity Protestant Protestants Catholic
Reformation Reformers Advent Adventist Sunday Monday Tuesday Wednesday Thursday Friday Saturday January February
March April May June July August September October November December Mr Mrs Dr St Vol No Ch
Genesis Exodus Leviticus Numbers Deuteronomy Kings Chronicles Psalms Psalm Proverbs Ecclesiastes Canticles
Lamentations Acts Romans Corinthians Galatians Ephesians Philippians Colossians Thessalonians Hebrews Revelation
Gentile Gentiles Jew Jews Jewish Greek Greeks Hebrew Latin Legion Levitical Raca Corban Eloi Lama Sabachthani Talitha
Cumi Ephphatha Abba""".split())
MIN_LEN, MAX_LEN = 3, 20
CONSONANT = "ก-ฮ"
LEADING_VOWEL = "เ-ไ"
PLAUSIBLE = re.compile(rf"^[{CONSONANT}{LEADING_VOWEL}].*[^{LEADING_VOWEL}ั]$")
# Common nouns and titles that stand before a name in the Thai versions and are not part of it.
PREFIXES = ("พระ", "หมู่บ้าน", "บ้าน", "เมือง", "กรุง", "นคร", "ชาว", "คน", "พวก", "แคว้น", "กษัตริย์", "จักรพรรดิ",
            "มหา", "ภูเขา", "แม่น้ำ", "ทะเล", "ลำห้วย", "ลำธาร", "หุบเขา", "ถิ่นทุรกันดาร", "แผ่นดิน", "ดินแดน", "ท่าน",
            "ผู้เผยพระวจนะ", "ลูกหลาน", "เผ่า", "ตระกูล", "ที่ราบ", "เนินเขา", "ประตู", "สระ", "ปุโรหิต",
            "ของ", "ใน", "ที่", "และ", "กับ", "จาก", "ถึง", "ไป", "มา", "แก่", "สู่", "ยัง", "ว่า", "คือ", "ชื่อ", "แห่ง",
            "ต่อ", "ตาม", "โดย", "เพื่อ", "เพราะ", "หรือ", "แต่", "ก็", "จึง", "เมื่อ", "ถ้า", "ซึ่ง", "เป็น", "มี", "ให้",
            "บุตร", "ธิดา", "ภรรยา", "สามี", "บิดา", "มารดา", "น้อง", "พี่", "เรียก", "นำ", "พา", "ส่ง", "ไว้",
            "สัญชาติ", "หญิง", "ชาย")
# The titles and common nouns of PREFIXES, as against its function words.
TITLE_WORDS = PREFIXES[:32]
# Function words that follow a name and are never part of it.
SUFFIXES = ("จะ", "ก็", "ที่", "ไป", "แล้ว", "และ", "ว่า", "นั้น", "นี้", "กับ", "ของ", "ใน", "ให้", "ได้", "จึง", "ซึ่ง", "เป็น",
            "เอ๋ย", "ด้วย", "คน", "ชาว", "ผู้", "เถิด", "แห่ง", "มา", "ตอบ", "กล่าว", "ทูล", "พูด")
COMMON_RATIO = 10   # a form in more than ten times as many verses as the name is a common word
# The published Thai Ellen White books, extracted by ~/claude-sandbox/egw/egw_extract.py:
# a light reference that corroborates a form taken from the translator's books.
EGW_TH = Path(os.path.expanduser("~/claude-sandbox/egw/extracted/th"))


def at_boundary(text, start):
    """True when the word at start opens a sentence, a line or a quotation."""
    before = text[:start]
    if re.search(r"(?:^|\n)[ \t]*$", before):
        return True
    before = before.rstrip()
    return not before or before[-1] in ".!?:;“\"—"


def kjv_index():
    """name -> [(code, ch, v)] for capitalised words inside King James verses,
    lowercase counts, and the verse list."""
    names, lower, verses = defaultdict(list), defaultdict(int), {}
    for f in sorted((BIBLE / "en" / "KJVS").glob("*.txt")):
        for raw in f.read_text(encoding="utf-8").splitlines():
            parts = raw.split("|", 4)
            if len(parts) != 5 or not parts[2].isdigit() or not parts[3].isdigit():
                continue
            text = re.sub(r"\{[HG]\d+(?:\s+[HG]\d+)*\}", "", parts[4]).replace("_", "")
            ref = (parts[1], int(parts[2]), int(parts[3]))
            verses[ref] = text
            for m in LOWER.finditer(text):
                lower[m.group(0)] += 1
            for m in CAP.finditer(text):
                if at_boundary(text, m.start()):
                    continue
                w = m.group(1)
                if w not in STOP:
                    names[w].append(ref)
    return names, lower, verses


def load_version(label):
    out = {}
    for f in sorted((BIBLE / "th" / label).glob("*.txt")):
        for raw in f.read_text(encoding="utf-8").splitlines():
            parts = raw.split("|", 4)
            if len(parts) == 5 and parts[2].isdigit() and parts[3].isdigit():
                out[(parts[1], int(parts[2]), int(parts[3]))] = parts[4].replace("​", "").replace("¶", " ")
    return out


def candidates(text):
    """Every substring of a Thai run, MIN_LEN to MAX_LEN characters."""
    out = set()
    for run in THAI_RUN.findall(text):
        for i in range(len(run)):
            for j in range(i + MIN_LEN, min(len(run), i + MAX_LEN) + 1):
                out.add(run[i:j])
    return out


def score(cands, texts, pool, denom=None):
    """[(coverage, other_rate, length, form)] for candidates present in a quarter of the texts."""
    denom = denom or len(texts)
    out = []
    for c in cands:
        cov = sum(c in t for t in texts) / denom
        if cov < 0.25:
            continue
        other = sum(c in t for t in pool) / len(pool) if pool else 0.0
        out.append((cov, other, len(c), c))
    return out


THAI_LETTER = re.compile(r"[฀-๿]")
# How an English consonant is usually transliterated into Thai, for comparing a
# candidate's consonant skeleton with the English name's.
EN_MAP = {"b": "บ", "c": "คซกข", "d": "ด", "f": "ฟ", "g": "กจ", "h": "ฮห", "j": "ยจ", "k": "คกข", "l": "ล", "m": "ม",
          "n": "น", "p": "พปฟ", "q": "ค", "r": "ร", "s": "สซศษ", "t": "ทตถ", "v": "ว", "w": "ว", "x": "กซ", "y": "ย", "z": "ซส"}
DIGRAPHS = {"ch": "คชขก", "th": "ธทตถ", "ph": "ฟพ", "sh": "ชซ", "ck": "คก"}
THAI_CONS = set("กขฃคฅฆงจฉชซฌญฎฏฐฑฒณดตถทธนบปผฝพฟภมยรลวศษสหฬอฮ")
DEP_VOWEL = set("ะัาำิีึืุู")
LEAD_VOWEL = set("เแโใไ")


PEOPLE_SUFFIX = re.compile(r"^(.{3,}?)(itish|itans|itan|ites|ite|ians|ian|enes|ene|eans|ean|ines|ine|ish)$")
TRIBES = {"israel", "levi", "judah", "benjamin", "reuben", "simeon", "dan", "naphtali", "gad", "asher", "issachar",
          "zebulun", "joseph", "ephraim", "manasseh"}
# Names the translator has deferred until a chapter meets them; they are left out of the table.
DEFER = {"Belial"}
# King James spellings that the glossary carries under another head.
ALIAS = {"Messias": "Messiah", "Jesus": "Jesus", "Elias": "Elijah", "Eliseus": "Elisha", "Esaias": "Isaiah", "Jeremias": "Jeremiah",
         "Osee": "Hosea", "Noe": "Noah", "Core": "Korah", "Sem": "Shem", "Juda": "Judah", "Judas": "Judas"}


def en_skeleton(name):
    """The consonants of an English name as sets of the Thai letters each may become;
    a people's suffix (Ishmaelites, Moabitish) is dropped, since Thai writes the people
    as คน or ชาว before the place or father's name."""
    s = name.lower().replace("'s", "")
    m = PEOPLE_SUFFIX.match(s)
    if m:
        s = m.group(1)
    out, i = [], 0
    while i < len(s):
        if s[i:i + 2] in DIGRAPHS:
            out.append(set(DIGRAPHS[s[i:i + 2]]))
            i += 2
        elif s[i] in EN_MAP and not (s[i] == "y" and i > 0):
            # A "y" inside a name is a vowel sound (Assyria, Syria) and is written as a Thai vowel.
            out.append(set(EN_MAP[s[i]]))
            i += 1
        else:
            i += 1
    return out


def th_skeleton(form):
    """The consonant letters of a Thai word: a vowel-carrying อ and a leading ห
    before another consonant are left out; a letter under ์ stays, since it
    mirrors a letter of the English name (อาเนอร์, ยอห์น)."""
    out = []
    for i, c in enumerate(form):
        if c not in THAI_CONS:
            continue
        nxt = form[i + 1] if i + 1 < len(form) else ""
        prv = form[i - 1] if i else ""
        if c == "อ" and (i == 0 or nxt in DEP_VOWEL or prv in LEAD_VOWEL or prv == "ื" or (i >= 2 and form[i - 2] in LEAD_VOWEL)):
            continue   # a vowel carrier, or the vowel of เ-อ and -ือ
        if c == "ห" and nxt in THAI_CONS and nxt != "อ":
            continue
        out.append(c)
    return out


def phon(name, form):
    """How well the Thai form's consonants follow the English name's, 0 to 1. A
    doubled English letter (Habakkuk) may become one Thai letter or two (อันนา)."""
    e, t = en_skeleton(name), th_skeleton(form)
    if not e or not t:
        return 0.0
    collapsed = [s for i, s in enumerate(e) if i == 0 or s != e[i - 1]]
    prev = [0] * (len(t) + 1)
    for es in e:
        cur = [0]
        for j, tc in enumerate(t, 1):
            cur.append(prev[j - 1] + 1 if tc in es else max(prev[j], cur[j - 1]))
        prev = cur
    return min(1.0, prev[-1] / max(len(collapsed), len(t)))


def first_matches(name, form):
    """True when the first consonant of the Thai form may render the first of the English name."""
    e, t = en_skeleton(name), th_skeleton(form)
    return bool(e and t and t[0] in e[0])


def end_rate(form, texts):
    """The share of the form's occurrences that end a word: at the end of a Thai
    run, or right before a known suffix, prefix or common word."""
    ok = n = 0
    words = SUFFIXES + PREFIXES
    for t in texts:
        i = t.find(form)
        while i >= 0:
            n += 1
            after = t[i + len(form):]
            if not after or not THAI_LETTER.match(after[0]) or any(after.startswith(w) for w in words):
                ok += 1
            i = t.find(form, i + 1)
    return ok / n if n else 0.0


DEP_MARKS = set("ะัาำิีึืุู\u0e47\u0e48\u0e49\u0e4a\u0e4b\u0e4c")


def complete(form, texts):
    """Extend a chosen form over what always follows it in the texts: a vowel sign,
    a tone mark or ์, or one final consonant that ends the word, so ฟีลิสเตี becomes
    ฟีลิสเตีย and อันน becomes อันนา. Stops where the following text varies."""
    for _ in range(6):
        nexts = []
        for tx in texts:
            i = tx.find(form)
            while i >= 0:
                j = i + len(form)
                nxt = tx[j] if j < len(tx) else ""
                after = tx[j + 1] if j + 1 < len(tx) else ""
                if nxt in DEP_MARKS:
                    nexts.append(nxt)
                elif nxt in THAI_CONS and (not after or not THAI_LETTER.match(after) or after in LEAD_VOWEL):
                    nexts.append(nxt)
                else:
                    nexts.append("")
                i = tx.find(form, i + 1)
        if not nexts:
            return form
        top = max(set(nexts), key=nexts.count)
        if not top or nexts.count(top) / len(nexts) < 0.8:
            return form
        form += top
    return form


def phonetic_form(name, texts):
    """For a name in one or two verses: the plausible word in the texts whose
    consonants best follow the English name's, where about two in three match;
    a form whose first consonant renders the name's first is preferred, then a
    form that ends and begins where a word does, then the longer form."""
    cands = [c for c in set().union(*(candidates(t) for t in texts)) if PLAUSIBLE.match(c)]
    best = None
    for c in cands:
        p = phon(name, c)
        if p < 0.65:
            continue
        key = (first_matches(name, c), round(p, 2), end_rate(c, texts) >= 0.5, start_rate(c, texts) >= 0.5, len(c))
        if best is None or key > best[0]:
            best = (key, c)
    if not best:
        return None
    full = complete(best[1], texts)
    return None if any(full in p or (len(p) >= 3 and full.endswith(p)) for p in TITLE_WORDS) else full


def start_rate(form, texts):
    """The share of the form's occurrences that begin a word: at the start of a
    Thai run, or right after a known prefix. "งบาบิโลน", cut from "ของบาบิโลน"
    and "เมืองบาบิโลน", begins a word nowhere; "บาบิโลน" does after ของ and เมือง."""
    ok = n = 0
    for t in texts:
        i = t.find(form)
        while i >= 0:
            n += 1
            before = t[:i]
            if not before or not THAI_LETTER.match(before[-1]) or any(before.endswith(p) for p in PREFIXES):
                ok += 1
            i = t.find(form, i + 1)
    return ok / n if n else 0.0


def choose(scored, alltext, n, ratio=COMMON_RATIO, texts=(), name=None):
    """The form among scored substrings: plausible as a Thai word, precise (rare
    outside the name's verses), not a word common across the whole text, one that
    begins a word, and among those whose coverage is within a tenth of the best
    the one whose consonants best follow the English name, then the longest, with
    a known prefix or suffix stripped. alltext is the whole version or book; n
    the number of verses that carry the name in all."""
    # A title (จักรพรรดิ), a piece of one, or a fragment ending in one is never the name.
    cands = [s for s in scored if PLAUSIBLE.match(s[3])
             and not any(s[3] in p or (len(p) >= 3 and s[3].endswith(p)) for p in TITLE_WORDS)]
    strict = [s for s in cands if s[1] <= 0.02]
    pool = strict if strict and max(s[0] for s in strict) >= 0.5 else [s for s in cands if s[1] <= max(0.1, 0.3 * s[0])]
    if not pool:
        return None
    # A common word is dropped unless its consonants follow the English name, as
    # อัสซีเรีย does for Assyrian though Assyria makes it frequent in the Bible.
    rare = [s for s in pool if alltext.count(s[3]) <= ratio * max(1.0, s[0] * n) or (name and phon(name, s[3]) >= 0.6)]
    pool = rare or pool
    top = max(s[0] for s in pool)
    near = [s for s in pool if s[0] >= 0.9 * top]
    if texts:
        starts = [s for s in near if start_rate(s[3], texts) >= 0.5]
        near = starts or near
    if name:
        top_phon = max(phon(name, s[3]) for s in near)
        if top_phon > 0:
            near = [s for s in near if phon(name, s[3]) >= 0.5 * top_phon]
    near.sort(key=lambda s: (-s[2], -s[0]))
    best = near[0]
    by_form = {s[3]: s for s in pool}
    changed = True
    while changed:
        changed = False
        for p in TITLE_WORDS:   # a title is stripped; a function word such as มา may be part of the name (มารีย์)
            rest = best[3][len(p):]
            if best[3].startswith(p) and len(rest) >= MIN_LEN and rest in by_form:
                best, changed = by_form[rest], True
                break
        for p in SUFFIXES:
            rest = best[3][:-len(p)]
            if not changed and best[3].endswith(p) and len(rest) >= MIN_LEN and rest in by_form and (not texts or end_rate(rest, texts) >= 0.5):
                best, changed = by_form[rest], True
                break
    if texts:
        full = complete(best[3], texts)
        if full != best[3]:
            best = (best[0], best[1], len(full), full)
    if any(best[3] in p or (len(p) >= 3 and best[3].endswith(p)) for p in TITLE_WORDS):
        return None   # the completed form is a title after all
    return best


def align(refs, version, pool, alltext, total, name):
    """(form, coverage, other_rate, second) for a name in one version, or None;
    second is (form, coverage) for another spelling covering the verses the first
    misses; total is the number of King James verses carrying the name."""
    texts = sorted((version[r] for r in refs if r in version), key=len)
    if not texts:
        return None
    pool_t = [version[r] for r in pool if r in version]
    cands = set().union(*(candidates(t) for t in texts[:3]))
    if len(texts) > 1:
        head = texts[:5]
        cands = {c for c in cands if sum(c in t for t in head) >= min(2, len(head))}
    best = choose(score(cands, texts, pool_t), alltext, total, texts=texts, name=name)
    if not best:
        return None
    cov, other, _, form = best
    second = None
    rest = [t for t in texts if form not in t]
    if len(rest) >= 2 and len(rest) / len(texts) >= 0.15:
        rest.sort(key=len)
        sc2 = [s for s in score(set().union(*(candidates(t) for t in rest[:2])), rest, pool_t, denom=len(texts))
               if s[3] not in form and form not in s[3] and s[1] <= 0.02 and (not name or phon(name, s[3]) >= 0.5)]
        pick = choose(sc2, alltext, total, texts=rest, name=name)
        if pick and pick[0] * len(texts) >= 2:
            second = (pick[3], pick[0])
    return form, cov, other, second


def book_sources():
    out = {}
    for book in BOOKS:
        paras = []
        for f in sorted(glob.glob(str(ROOT / f"th/{book}/00_source/*_en.md"))):
            t = Path(f).read_text(encoding="utf-8")
            for m in re.finditer(r"^## \{(\w+ [\w.]+)\}\s*\n(.*?)(?=^## \{|\Z)", t, re.M | re.S):
                paras.append((m.group(1), re.sub(r"\{\w+ [\w.]+\}\s*$", "", m.group(2).strip())))
        if paras:
            out[book] = paras
    return out


def book_thai(book):
    out = {}
    for f in sorted(glob.glob(str(ROOT / f"th/{book}/0[23]_*/*.md")) + glob.glob(str(ROOT / f"th/{book}/0[23]_*/*.typ"))):
        t = Path(f).read_text(encoding="utf-8")
        if f.endswith(".md"):
            it = re.finditer(r"^## \{(\w+ [\w.]+)\}\s*\n(.*?)(?=^## \{|\Z)", t, re.M | re.S)
        else:
            it = re.finditer(r"// \{(\w+ [\w.]+)\}\s*\n(.*?)#EGW\[", t, re.S)
        for m in it:
            if m.group(2).strip():
                out.setdefault(m.group(1), m.group(2).strip())
    return out


def book_form(thsv_form, sites, thai, alltext, name):
    """(present, total, other_form, anchors): how a finished book writes the name at
    the English sites carrying it; other_form is aligned when the THSV form is
    absent from most sites, or when there is no THSV form at all."""
    present, total, texts, anchors = 0, 0, [], []
    for anchor, para in sites:
        tp = thai.get(anchor)
        if not tp:
            continue
        total += 1
        if thsv_form and thsv_form in tp:
            present += 1
        else:
            texts.append(tp)
            anchors.append(anchor)
    other = None
    need = 2 if thsv_form else 1
    if total >= need and present / total < 0.5 and len(texts) >= need:
        pool = [t for a, t in thai.items() if t not in texts][:300]
        texts.sort(key=len)
        pick = choose([s for s in score(set().union(*(candidates(t) for t in texts[:2])), texts, pool) if s[0] >= 0.5],
                      alltext, len(texts), ratio=3, texts=texts, name=name)
        if pick:
            other = pick[3]
    return present, total, other, anchors[:3]


def read_table():
    rows = {}
    if not TABLE.exists():
        return rows
    for line in TABLE.read_text(encoding="utf-8").splitlines()[1:]:
        if line.strip() and not line.startswith("#"):
            cells = line.split("\t")
            rows[(cells[0], cells[1] if len(cells) > 1 else "")] = cells
    return rows


def glossary_names(paths):
    """English head -> first Thai form, from section 2 of each glossary file given."""
    out = {}
    for path in paths:
        path = Path(os.path.expanduser(str(path)))
        if not path.exists():
            continue
        sec = 0
        for line in path.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^##\s+(\d+)\.", line)
            if m:
                sec = int(m.group(1))
                continue
            if sec != 2 or not line.startswith("|"):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 2 or cells[0] in ("English", "") or set(cells[0]) <= {"-"}:
                continue
            thai_forms = [f.strip() for f in cells[1].split("/") if f.strip()]
            if not thai_forms:
                continue
            for part in re.split(r"[;,]", re.sub(r"\(.*?\)", "", cells[0])):
                head = part.strip()
                if head and head[0].isupper() and " " not in head:
                    people = [f for f in thai_forms if f.startswith(("ชาว", "คน"))]
                    out.setdefault(head, people[0] if people and PEOPLE_SUFFIX.match(head.lower()) else thai_forms[0])
    return out


def spread(refs, n=40):
    """Up to n verses spread over the whole list, so one book's usage does not rule."""
    if len(refs) <= n:
        return refs
    step = len(refs) / n
    return [refs[int(i * step)] for i in range(n)]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--book", choices=BOOKS, help="take the names from this book's sources only")
    ap.add_argument("--all", action="store_true", help="rebuild every row, replacing the table")
    ap.add_argument("--limit", type=int, help="stop after this many names (testing)")
    ap.add_argument("--glossary", action="append", default=[],
                    help="a further glossary file whose section 2 rows rule, besides the repository's; may repeat")
    a = ap.parse_args()
    glossary = glossary_names([ROOT / "th/assets/translation_profile/thai-glossary.txt", *a.glossary])
    random.seed(1)
    names_kjv, lower, kjv_verses = kjv_index()
    sources = book_sources()
    wanted = defaultdict(set)
    for book, paras in sources.items():
        if a.book and book != a.book:
            continue
        for anchor, para in paras:
            for m in CAP.finditer(para):
                if at_boundary(para, m.start()):
                    continue
                w = m.group(1)
                if w not in names_kjv and w.endswith("s") and w[:-1] in names_kjv:
                    w = w[:-1]
                if w in STOP or w not in names_kjv:
                    continue
                if lower.get(w.lower(), 0) > len(names_kjv[w]):
                    continue
                wanted[w].add(book)
    existing = {} if a.all else read_table()
    todo = sorted(n for n in wanted if not any(k[0] == n for k in existing))
    if a.limit:
        todo = todo[:a.limit]
    versions = {v: load_version(v) for v in VERSIONS}
    alltext = {v: "\n".join(versions[v].values()) for v in VERSIONS}
    by_book = defaultdict(list)
    for ref in kjv_verses:
        by_book[ref[0]].append(ref)
    thai_books = {b: book_thai(b) for b in sources}
    book_text = {b: "\n".join(thai_books[b].values()) for b in thai_books}
    egw_th = {f.stem: f.read_text(encoding="utf-8", errors="replace") for f in EGW_TH.glob("*.md")} if EGW_TH.is_dir() else {}
    rows = []
    for name in todo:
        if name in DEFER:
            continue
        refs = names_kjv.get(name, [])
        books = ",".join(sorted(wanted[name]))
        if not refs:
            rows.append([name, "", glossary.get(name, ""), "glossary" if name in glossary else "", "", "", "", books, "0",
                         "settled" if name in glossary else "not in KJV",
                         "glossary row" if name in glossary else "the King James has no such word; rule the spelling by hand"])
            continue
        use = spread(refs)
        in_set = set(refs)
        pool = []
        for code in sorted({r[0] for r in use}):
            pool += [r for r in by_book[code] if r not in in_set]
        random.shuffle(pool)
        pool = pool[:200]
        notes, status, second = [], "settled", None
        forms = {v: "" for v in VERSIONS}
        thsv_form = ""
        if len(refs) <= 2:
            # Too few verses to align by coverage: the word whose consonants follow
            # the English name's is taken; where none does, the THSV verse is quoted
            # so the spelling can be copied out of it by hand.
            thsv_texts = [versions["THSV"][r] for r in use if r in versions["THSV"]]
            form = phonetic_form(name, thsv_texts) if thsv_texts else None
            if form:
                thsv_form = form
                forms["THSV"] = form
                for v in ("TH1971", "TNCV"):
                    tx = [versions[v][r] for r in use if r in versions[v]]
                    f2 = phonetic_form(name, tx) if tx else None
                    forms[v] = f2 or ""
                    if f2 and f2 != form:
                        notes.append(f"{v} writes {f2}")
                agree = all(forms[v] == form for v in VERSIONS)
                notes.insert(0, f"{len(refs)} verse(s) in the King James; " + ("the three versions agree on the form" if agree else "the form follows the English name's consonants"))
            else:
                status = "weak match"
                shown = "; ".join(f"THSV {r[0]} {r[1]}:{r[2]}: {versions['THSV'][r][:160]}" for r in use if r in versions["THSV"])
                notes.append(f"only {len(refs)} verse(s) in the King James and no word follows the English name's consonants; copy the spelling out of the verse: {shown or 'THSV has none of the verses'}")
        else:
            res = {v: align(use, versions[v], pool, alltext[v], len(refs), name) for v in VERSIONS}
            thsv = res["THSV"]
            if thsv is None:
                status = "weak match"
                notes.append("no THSV form found at these verses")
            else:
                thsv_form, cov, other, second = thsv
                forms["THSV"] = thsv_form
                if cov < 0.6:
                    status = "weak match"
                    notes.append(f"THSV form in {int(cov * 100)} percent of {len(use)} verses")
                if other > 0.02:
                    notes.append(f"the form also occurs in {int(other * 100)} percent of other verses")
                if second and cov < 0.85:
                    status = "two THSV forms"
                    notes.append(f"second THSV form {second[0]} in {int(second[1] * 100)} percent")
            for v in ("TH1971", "TNCV"):
                r = res[v]
                forms[v] = r[0] if r else ""
                if r and thsv_form and r[0] != thsv_form:
                    # Profile 5.A rules the THSV spelling; another version's form is information.
                    notes.append(f"{v} writes {r[0]}")
        site_notes, book_forms = [], {}
        for book, paras in sources.items():
            if book not in thai_books:
                continue
            sites = [(anc, p) for anc, p in paras if re.search(r"\b" + re.escape(name) + r"(?:'s)?\b", p)]
            if not sites:
                continue
            present, total, other, anchors = book_form(thsv_form, sites, thai_books[book], book_text[book], name)
            if total and other:
                book_forms[book] = other
                if thsv_form:
                    if status == "settled":
                        status = "a book differs"
                    site_notes.append(f"{book} writes {other} at {', '.join(anchors)} ({present} of {total} sites carry the THSV form)")
                else:
                    site_notes.append(f"{book} writes {other} at {', '.join(anchors)} ({total} site(s))")
            elif total and thsv_form and present < total:
                site_notes.append(f"{book}: {present} of {total} sites carry the THSV form")
        # Profile 5.A: the series' printed spelling first, then THSV.
        series = ""
        if name in glossary or ALIAS.get(name) in glossary:
            form, series, status = glossary.get(name) or glossary[ALIAS[name]], "glossary", "settled"
            notes = ["glossary row" + (f"; THSV writes {thsv_form}" if thsv_form and thsv_form != form else "")] + [n for n in notes if " writes " in n]
        elif book_forms:
            distinct = sorted(set(book_forms.values()), key=len)
            counts = {f: sum(txt.count(f) for txt in egw_th.values()) for f in distinct}
            if len(distinct) == 1:
                form, status = distinct[0], "settled"
                series = f"{form} ({', '.join(sorted(book_forms))})"
                notes = [f"the series prints {form}" + (f"; THSV writes {thsv_form}" if thsv_form and thsv_form != form else "; THSV has no form")] + [n for n in notes if " writes " in n]
            else:
                form, status = "", "two printed forms"
                series = " / ".join(f"{f} ({b})" for b, f in sorted(book_forms.items()))
                notes = ["the finished books disagree" + (f"; THSV writes {thsv_form}" if thsv_form else "")] + [n for n in notes if " writes " in n]
            site_notes = [n for n in site_notes if "sites carry" not in n] + ["; ".join(f"{f} in the Thai EGW library {counts[f]} time(s)" for f in distinct)]
        else:
            form = thsv_form
        if status == "two THSV forms" and series:
            status = "settled"
        rows.append([name, "", form, series, forms["THSV"], forms["TH1971"], forms["TNCV"], books, str(len(refs)), status, "; ".join(notes + site_notes)])
        if status == "two THSV forms" and second:
            rows.append([name, "", "", "", second[0], "", "", books, str(len(refs)), "two THSV forms", f"second THSV form, {int(second[1] * 100)} percent of the verses"])
    # DA 3.K: a people takes ชาว before its root; Israel and its tribes keep คน.
    by_name = {r[0].lower(): r for r in rows}
    for r in rows:
        name = r[0]
        m = PEOPLE_SUFFIX.match(name.lower())
        if not m or name in glossary or not r[2] and r[9] != "settled" and r[4] == "":
            continue
        root = m.group(1)
        own = r[2] or r[4]
        k = re.search(r"(คน|ชาว|พวก)", own)
        if k and k.start() > 0:
            # THSV's run มารีย์ชาวมักดาลา, or the tail the alignment cut from it, gives ชาวมักดาลา.
            own = own[k.start():]
            if own in r[4]:
                r[4] = own
        if own.startswith(("คน", "ชาว", "พวก")):
            root_head = root_row = None
            source = own   # THSV's own people form, as มารีย์ชาวมักดาลา gives ชาวมักดาลา
        else:
            root_head = next((h for h in sorted(glossary) if h.lower().startswith(root) and not PEOPLE_SUFFIX.match(h.lower())), None)
            root_row = None if root_head else next((by_name[k] for k in sorted(by_name)
                                                    if k.startswith(root) and k != name.lower() and not PEOPLE_SUFFIX.match(k) and by_name[k][2]), None)
            source = glossary[root_head] if root_head else root_row[2] if root_row else own
        base = re.sub(r"^(คน|ชาว|พวก)", "", source)
        if not base:
            continue
        prefix = "คน" if any(x.startswith(root) or root.startswith(x) for x in TRIBES) else "ชาว"
        r[2], r[3], r[9] = prefix + base, "", "settled"
        r[10] = f"a people, DA 3.K: {prefix} before {base}" + (f" ({root_head or root_row[0]})" if root_head or root_row else "") + "; " + r[10]
    header = ["English", "who", "form", "series", "THSV", "TH1971", "TNCV", "books", "verses", "status", "note"]
    all_rows = ([] if a.all else list(existing.values())) + rows
    all_rows.sort(key=lambda r: (r[0], r[1] if len(r) > 1 else ""))
    TABLE.parent.mkdir(parents=True, exist_ok=True)
    TABLE.write_text("\t".join(header) + "\n" + "".join("\t".join(r) + "\n" for r in all_rows), encoding="utf-8")
    exceptions = [r for r in rows if r[9] != "settled"]
    for r in exceptions:
        print("\t".join(r))
    print(f"# {len(rows)} name(s) processed, {len(exceptions)} exception(s) above; table {TABLE.relative_to(ROOT)} now holds {len(all_rows)} row(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
