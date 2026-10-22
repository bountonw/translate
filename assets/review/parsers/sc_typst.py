"""Parser for books kept as Typst chapters with a Markdown English source (book SC).

A Thai chapter is a .typ file in which each paragraph is a line "// {SC 9.1}"
followed by one text line that ends "#EGW[\\{SC 9.1\\}]". Inline markup is
#italic[...] and #footnote[...] (brackets may nest) with backslash escapes.
The English is a Markdown file with YAML front matter (chapter.title.en),
sections "## {SC 9.1}", and verse lines indented four spaces.

Every format module offers the same function:

    load_chapter(book, n, read) -> chapter

book is the book's entry from books.json (with its "id"), n the chapter
number, and read(path) returns a file's text at the chosen git ref, or None.
The chapter is {"id", "n", "title_th", "title_en", "paragraphs", "sources"};
each paragraph is {"a": "SC 9.1", "th": HTML, "fn": [HTML], "en": HTML}, in
the content model of server/content.py. review.py calls it through
parsers.load_chapter, which also runs the annotators and refuses the
characters the language registry bans, so this module only reads the format.
"""
import html
import itertools
import re

from parsers import ParseError


def chapter_paths(book, n, stage=None):
    """The Thai path for one stage (or the first stage) and the English path.

    The templates take {stage}, {book}, {nn} (two digits) and {name}: the file name's stem,
    the book id and two digits unless the entry's "names" map gives another, as
    {"0": "DA00_preface"}.
    """
    nn = f"{n:02d}"
    name = book.get("names", {}).get(str(n), f"{book['id']}{nn}")
    th = book["thai"].format(stage=stage or book["stages"][0], nn=nn, book=book["id"], name=name)
    en = book["english"].format(nn=nn, book=book["id"], name=name)
    return th, en


def match_bracket(s, i):
    """Index of the ] closing the [ at s[i], skipping escaped brackets."""
    depth = 0
    while i < len(s):
        c = s[i]
        if c == "\\":
            i += 2
            continue
        if c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise ParseError("unclosed bracket")


def typst_inline(s, notes):
    """Typst paragraph text to HTML; footnotes go to notes, #EGW is dropped."""
    out, i = [], 0
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s):
            out.append(html.escape(s[i + 1]))
            i += 2
            continue
        m = re.match(r"#(italic|footnote|EGW)\[", s[i:])
        if m:
            start = i + len(m.group(0)) - 1
            end = match_bracket(s, start)
            inner = s[start + 1:end]
            if m.group(1) == "italic":
                out.append("<em>" + typst_inline(inner, notes) + "</em>")
            elif m.group(1) == "footnote":
                notes.append(typst_inline(inner, notes))
                out.append(f'<sup class="fn">{len(notes)}</sup>')
            i = end + 1
            continue
        if s[i] == "#":
            raise ParseError(f"unknown Typst call: {s[i:i + 30]}")
        out.append(html.escape(s[i]))
        i += 1
    return "".join(out).strip()


def thai_chapter(text, cid):
    """Title and paragraphs of a Thai .typ chapter."""
    if "[[" in text or "((" in text:
        raise ParseError(f"{cid}: the chapter holds a marker or an editor's choice; resolve it first")
    head = text.split("#chapter(", 1)
    m = re.search(r'title:\s*"([^"]*)"', head[1] if len(head) == 2 else text)
    if not m:
        raise ParseError(f"{cid}: no chapter title")
    title = m.group(1).strip()
    paras, anchor = [], None
    for line in text.splitlines():
        m = re.match(r"// \{([A-Za-z]+ \d+\.\d+)\}", line)
        if m:
            anchor = m.group(1)
            continue
        if not line.strip() or line.startswith(("//", "#import", "#show", "#chapter", " ", ")")):
            continue
        if anchor is None:
            raise ParseError(f"{cid}: text before the first anchor: {line[:60]}")
        egw = re.search(r"#EGW\[\\\{([^\\]*)\\\}\]\s*$", line)
        if egw and egw.group(1) != anchor:
            raise ParseError(f"{cid}: {{{anchor}}} ends with the mark {{{egw.group(1)}}}")
        notes = []
        paras.append({"a": anchor, "th": typst_inline(line, notes), "fn": notes})
        anchor = None
    seen = set()
    for p in paras:
        if p["a"] in seen:
            raise ParseError(f"{cid}: {{{p['a']}}} appears twice")
        seen.add(p["a"])
    return title, paras


def english_chapter(text, cid):
    """Title and paragraphs (anchor to HTML) of an English Markdown chapter."""
    parts = text.split("---", 2)
    if not text.startswith("---") or len(parts) < 3:
        raise ParseError(f"{cid}: the English has no front matter")
    front, body = parts[1], parts[2]
    m = re.search(r"^chapter:\s*\n(?:\s+.*\n)*?\s+title:\s*\n\s+en:\s*(.+)$", front, re.M)
    if not m:
        raise ParseError(f"{cid}: the English has no chapter.title.en")
    title = m.group(1).strip().strip('"')
    en = {}
    for block in re.split(r"^## ", body, flags=re.M)[1:]:
        head, _, text_ = block.partition("\n")
        hm = re.match(r"\{([A-Za-z]+ \d+\.\d+)\}", head)
        if not hm:
            raise ParseError(f"{cid}: English heading without an anchor: {head[:40]}")
        a = hm.group(1)
        text_ = re.sub(r"\s*\{[A-Za-z]+ \d+\.\d+\}\s*$", "", text_.strip("\n").rstrip())
        out = []
        for chunk in re.split(r"\n\s*\n", text_):
            # Lines indented four spaces are verse and keep their breaks; other lines are prose.
            for verse, run in itertools.groupby(chunk.split("\n"), key=lambda l: l.startswith("    ")):
                run = [html.escape(l.strip()) for l in run if l.strip()]
                if run:
                    out.append('<p class="verse">' + "<br>".join(run) + "</p>" if verse
                               else "<p>" + " ".join(run) + "</p>")
        en[a] = "".join(out)
    return title, en


def load_chapter(book, n, read):
    """Read chapter n of book through read(path) and return it as the server stores it."""
    cid = f"{book['id']}{n:02d}"
    th_text = th_path = None
    for stage in book["stages"]:
        path, en_path = chapter_paths(book, n, stage)
        th_text = read(path)
        if th_text is not None:
            th_path = path
            break
    en_text = read(en_path)
    if th_text is None or en_text is None:
        raise ParseError(f"{cid}: not found ({'Thai' if th_text is None else 'English'} file missing)")
    title_th, paras = thai_chapter(th_text, cid)
    title_en, en = english_chapter(en_text, cid)
    missing = [p["a"] for p in paras if p["a"] not in en]
    if missing:
        raise ParseError(f"{cid}: no English for {', '.join(missing)}")
    for p in paras:
        p["en"] = en[p["a"]]
    return {"id": cid, "n": n, "title_th": title_th, "title_en": title_en,
            "paragraphs": paras, "sources": [th_path, en_path]}
