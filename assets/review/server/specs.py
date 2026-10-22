"""Chapter and grant specifications shared by the server and review.py.

A chapter list is "01-08", "03" or "1,3,5-7". A grant is "SC" (every
published chapter of SC, now and later), "SC03", or a range "SC01-08".
Chapter ids are the book id followed by a two-digit number: SC03.
"""
import itertools
import re

BOOK_RE = re.compile(r"[A-Z]{1,10}")
CHAPTER_RE = re.compile(r"([A-Z]{1,10})(\d{1,3})")
GRANT_RE = re.compile(r"([A-Z]{1,10})(?:(\d{1,3})(?:-([A-Z]{1,10})?(\d{1,3}))?)?")


class SpecError(ValueError):
    """A chapter list or grant that cannot be read."""


def chapter_id(book, n):
    return f"{book}{n:02d}"


def parse_numbers(spec):
    """'01-08' or '1,3,5-7' to a sorted list of chapter numbers."""
    out = set()
    for part in str(spec).replace(" ", "").split(","):
        m = re.fullmatch(r"(\d{1,3})(?:-(\d{1,3}))?", part)
        if not m:
            raise SpecError(f"cannot read the chapter list {spec!r}; write 01-08 or 03")
        lo = int(m.group(1))
        hi = int(m.group(2) or lo)
        if hi < lo:
            raise SpecError(f"the range {part} runs backwards")
        out.update(range(lo, hi + 1))
    return sorted(out)


def parse_grant(spec):
    """'SC', 'SC03' or 'SC01-08' (comma lists allowed) to a list of (book, chapter or '*')."""
    out = []
    for part in str(spec).replace(" ", "").upper().split(","):
        m = GRANT_RE.fullmatch(part)
        if not m:
            raise SpecError(f"cannot read the grant {spec!r}; write SC, SC03 or SC01-08")
        book, lo, book2, hi = m.groups()
        if book2 not in (None, book):
            raise SpecError(f"the range {part} spans two books")
        if lo is None:
            out.append((book, "*"))
            continue
        lo, hi = int(lo), int(hi or lo)
        if hi < lo:
            raise SpecError(f"the range {part} runs backwards")
        out.extend((book, chapter_id(book, n)) for n in range(lo, hi + 1))
    return list(dict.fromkeys(out))


def grant_label(book, chapter):
    """The spec string for one grant row: 'SC' for all of SC, else the chapter id."""
    return book if chapter == "*" else chapter


def compact(labels):
    """Grant labels for display: ['SC01', 'SC02', 'SC03', 'SC05'] becomes 'SC01-03, SC05'."""
    whole, nums = [], {}
    for label in labels:
        m = CHAPTER_RE.fullmatch(label)
        if m:
            nums.setdefault(m.group(1), set()).add(int(m.group(2)))
        else:
            whole.append(label)
    out = list(whole)
    for book in sorted(nums):
        for _, run in itertools.groupby(enumerate(sorted(nums[book])), key=lambda x: x[1] - x[0]):
            run = [n for _, n in run]
            out.append(chapter_id(book, run[0]) + (f"-{run[-1]:02d}" if len(run) > 1 else ""))
    return ", ".join(out)
