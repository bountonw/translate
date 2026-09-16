#!/usr/bin/env python3
"""Shared helpers for the SC Thai round scripts.

The chapter files are Typst. Each paragraph carries a "// {SC ###.#}" comment
above it and an "#EGW[\\{SC ###.#\\}]" tag at its end; the English source
anchors the same paragraphs with "## {SC ###.#}" headings. Everything here is
read-only; the scripts that import it write only under ~/claude-sandbox/.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
PROJECT = ROOT / "th" / "SC"
STAGES = ("03_public", "02_edit", "01_raw")
SOURCE_DIRS = (PROJECT / "00_source", ROOT / "source" / "SC")
SANDBOX = Path(os.path.expanduser("~/claude-sandbox/sc-audit"))
# The offline Bible corpus: one directory per version, one file per book. Set
# BIBLE_CORPUS in the environment to point elsewhere.
BIBLE = Path(os.path.expanduser(os.environ.get("BIBLE_CORPUS", "~/programming/bible")))

COMMENT_ANCHOR = re.compile(r"^\s*//\s*\{SC\s+(\d+\.\d+)\}\s*$")
TAG_ANCHOR = re.compile(r"#EGW\[\\\{SC\s+(\d+\.\d+)\\\}\]")
EN_ANCHOR = re.compile(r"^##\s*\{SC\s+(\d+\.\d+)\}\s*$")

CLASSES = ("CHOICE OMISSION ADDITION FACT REF NOTE ALIGN SPELL TERM GRAM CLARITY "
           "READ EDIT FIX REVERT REWORD").split()
MARKER = re.compile(
    r"\[\[(?P<cls>" + "|".join(CLASSES) + r")(?: (?P<sev>HIGH|MED|LOW))? #(?P<num>\d+[a-z]?)"
    r"\|(?P<old>[^|]*?) -> (?P<new>[^|]*?)\|(?P<note>.*?)\]\]", re.S)
OPEN_MARKER = re.compile(r"\[\[")


def chapter_path(nn):
    """The chapter file for NN, searched most finished stage first."""
    name = f"SC{int(nn):02d}_th.typ"
    for stage in STAGES:
        p = PROJECT / stage / name
        if p.exists():
            return p
    sys.exit(f"no chapter file {name} under th/SC/01_raw, 02_edit or 03_public")


def source_path(nn):
    """The English source for NN: th/SC/00_source first, then source/SC."""
    name = f"SC{int(nn):02d}_en.md"
    for d in SOURCE_DIRS:
        p = d / name
        if p.exists():
            return p
    sys.exit(f"no English source {name} under th/SC/00_source or source/SC")


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


def parse_thai(text):
    """Split a Typst chapter into paragraphs by their anchor comments.

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


EN_TAIL = re.compile(r"\{SC\s+(\d+\.\d+)\}\s*$")


def parse_english(text):
    """Map anchor -> English paragraph text.

    A paragraph is anchored by the "## {SC ###.#}" heading above it, or, where
    a source file lacks the heading (SC04_en.md carries one heading for eleven
    paragraphs), by the "{SC ###.#}" tag that closes the paragraph itself.
    """
    paras, heading, buf = {}, None, []

    def flush():
        block = "\n".join(buf).strip()
        if not block:
            return
        m = EN_TAIL.search(block)
        key = m.group(1) if m else heading
        if key:
            paras[key] = (paras[key] + "\n\n" + block) if key in paras else block

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
        buf.append(line)
    flush()
    return paras


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
