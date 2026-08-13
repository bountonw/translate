#!/usr/bin/env python3
"""Find every occurrence of a Lao form across the translator's own corpus.

Answers the question "is this word available in this sense, and in what
construction do I already use it" from the only evidence this repository
holds: the Lao already written here.

    python3 lo/GC/04_assets/scripts/gc_formfind.py ຖັດ

Two things decide whether the answer is any good.

The sources are never pooled into a bare number.  Every count is labelled with
the project it came from and the pipeline stage it sits at — public, then
edit, then raw — and the report lists them in that order, most finished first.
That ordering is the only weighting the tool applies.  What a source is worth
beyond it is Brian's to judge, which is why the source of every count is on
the screen: a form carried only by one raw draft, or only by a project that
was converted rather than translated, says so plainly in the table.

Occurrences are grouped by the words on either side, because a form's meaning
shows in its construction: ມື້ຖັດມາ and ຖັດອອກໄປ are different words doing
different work.  Lao writes no space inside a phrase, so those neighbouring
words are found with the project's own line-breaking dictionary rather than
counted off in characters, which would cut a syllable in half.

Corpus evidence is evidence and never a verdict.  What this prints is what
Brian has done before, not what standard Lao permits; only he adjudicates.
"""

import argparse
import glob
import re
import sys
from collections import defaultdict

# Sources are discovered rather than listed, so a project that does not exist
# yet needs no change here: when FB lands, or when AA finally has a 03_public
# layer, both appear in the next report on their own.  A Lao manuscript is any
# file named *_lo.* inside one of the pipeline stages below.
#
# The stages are ordered by how finished they are — public, then edit, then
# raw — and every report lists its sources in that order.  That ordering is a
# structural fact about the pipeline and is the only weighting the tool
# applies; what a given source is worth beyond it is Brian's judgment, and the
# report gives him the source of every count so he can make it.
STAGES = [("03_public", "public"), ("02_edit", "edit"), ("01_raw", "raw")]

ANCHOR = re.compile(r"\{[A-Z]{2,4} [\d.]+\}")
LAO_DIGITS = re.compile(r"[໐-໙]")
THAI_DIGITS = re.compile(r"[๐-๙]")


def load_corpus(only=None):
    """Return ([(source, path, text)], [source, ...]) in pipeline-stage order.

    `only` restricts to one project, matched case-insensitively.
    """
    files, order = [], []
    for stage_dir, stage in STAGES:
        found = defaultdict(list)
        for path in sorted(glob.glob(f"lo/*/{stage_dir}/*_lo.*")):
            project = path.split("/")[1]
            if only and project.lower() != only.lower():
                continue
            found[project].append(path)
        for project in sorted(found):
            source = f"{project}/{stage}"
            order.append(source)
            for path in found[project]:
                try:
                    with open(path, encoding="utf-8") as handle:
                        files.append((source, path, handle.read()))
                except OSError as exc:
                    print(f"warning: could not read {path}: {exc}",
                          file=sys.stderr)
    return files, order


def anchor_at(text, pos):
    """The nearest {GC 317.1}-style anchor at or before pos, or '' if none."""
    last = ""
    for match in ANCHOR.finditer(text, 0, pos + 1):
        last = match.group(0)
    return last


# Lao writes no space inside a phrase, so the neighbouring WORDS have to be
# found rather than counted off in characters.  Unicode is no help: ະ and າ are
# dependent vowels carrying category Lo exactly like a consonant, so any slice
# by character count cuts a syllable in half and prints a form that exists
# nowhere.  The repository already ships the word list the typesetter uses for
# line breaking, so segment with that.
LEXICON_PATH = "lo/assets/dictionaries/main.txt"
BREAKERS = set(".,;:!?\"'“”‘’()[]{}… \t\n")


def load_lexicon(path=LEXICON_PATH):
    """The set of Lao words in the project's line-breaking dictionary."""
    words = set()
    try:
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                head = line.split("|", 1)[0].strip()
                head = re.sub(r"\\[a-zA-Z]+\{[^}]*\}", "", head)
                if head and all("\u0e80" <= c <= "\u0eff" for c in head):
                    words.add(head)
    except OSError:
        pass
    return words, (max((len(w) for w in words), default=1) if words else 1)


def words_after(text, pos, count, lexicon, longest):
    """The next `count` dictionary words from pos, whole and unbroken."""
    index, taken = pos, 0
    while index < len(text) and taken < count:
        if text[index] in BREAKERS:
            break
        for size in range(min(longest, len(text) - index), 0, -1):
            if text[index:index + size] in lexicon:
                index += size
                break
        else:
            index += 1          # a name or a form the list does not carry
        taken += 1
    return text[pos:index]


def words_before(text, pos, count, lexicon, longest):
    """The previous `count` dictionary words ending at pos."""
    index, taken = pos, 0
    while index > 0 and taken < count:
        if text[index - 1] in BREAKERS:
            break
        for size in range(min(longest, index), 0, -1):
            if text[index - size:index] in lexicon:
                index -= size
                break
        else:
            index -= 1
        taken += 1
    return text[index:pos]


def find(form, files, lexicon, longest, span=2, near=None):
    """Every occurrence of form, as a list of hit dicts."""
    hits = []
    for source, path, text in files:
        for match in re.finditer(re.escape(form), text):
            start, end = match.start(), match.end()
            window = text[max(0, start - 60):end + 60].replace("\n", " ")
            if near and near not in window:
                continue
            hits.append({
                "source": source,
                "path": path,
                "chapter": path.split("/")[-1].split("_")[0],
                "anchor": anchor_at(text, start),
                "follows": form + words_after(text, end, span, lexicon, longest),
                "precedes": words_before(text, start, span, lexicon, longest) + form,
                "text": text,
                "start": start,
                "end": end,
            })
    return hits


def context(hit, width):
    text, start, end = hit["text"], hit["start"], hit["end"]
    before = text[max(0, start - width):start].replace("\n", " ")
    after = text[end:end + width].replace("\n", " ")
    lead = "…" if start - width > 0 else ""
    tail = "…" if end + width < len(text) else ""
    return f"{lead}{before}[{text[start:end]}]{after}{tail}"


def report(form, hits, order, width, per_group, show_all):
    if not hits:
        print(f"{form} — no occurrence in any corpus searched.")
        print("The form is unattested in this corpus. That is not a verdict "
              "on the language, only on what has been written here.")
        return

    counts = defaultdict(int)
    for hit in hits:
        counts[hit["source"]] += 1

    print(f"{form}")
    print()
    print("WHERE IT STANDS")
    width_label = max(len(s) for s in order if counts[s]) if hits else 8
    for source in order:
        if counts[source]:
            print(f"  {source:<{width_label}}  {counts[source]:>5}")
    print(f"  {'':<{width_label}}  {'':>5}")
    print(f"  {'total':<{width_label}}  {len(hits):>5}")

    def grouped(key, subset):
        buckets = defaultdict(list)
        for hit in subset:
            buckets[hit[key]].append(hit)
        return sorted(buckets.items(), key=lambda kv: (-len(kv[1]), kv[0]))

    def tabulate(title, ordered):
        print()
        print(f"{title} — {len(ordered)} distinct")
        for label, members in ordered:
            where = defaultdict(int)
            for hit in members:
                where[hit["source"]] += 1
            spread = " ".join(f"{s}:{where[s]}" for s in order if where[s])
            print(f"  {label}  —  {len(members)}  ({spread})")

    ordered = grouped("follows", hits)
    tabulate("WHAT FOLLOWS IT", ordered)
    tabulate("WHAT PRECEDES IT", grouped("precedes", hits))

    def sites(subset, heading):
        if not subset:
            return
        print()
        print(heading)
        for token, members in grouped("follows", subset):
            print(f"  {token}")
            shown = members if show_all else members[:per_group]
            for hit in shown:
                where = f"{hit['source']} {hit['chapter']} {hit['anchor']}".strip()
                print(f"    {where}")
                print(f"      {context(hit, width)}")
            if not show_all and len(members) > per_group:
                print(f"    … and {len(members) - per_group} more; "
                      "pass --all to see them")
            print()

    sites(hits, "SITES, grouped by what follows the form")


def main():
    parser = argparse.ArgumentParser(
        description="Find a Lao form across the GC, AA and MB corpora and "
                    "group its occurrences by the construction it sits in.")
    parser.add_argument("forms", nargs="+",
                        help="one or more Lao forms to look for")
    parser.add_argument("--project", metavar="NAME",
                        help="restrict the search to one project, e.g. GC")
    parser.add_argument("--near", metavar="FORM",
                        help="keep only occurrences whose surrounding text "
                             "also contains this form")
    parser.add_argument("--context", type=int, default=45, metavar="N",
                        help="characters of context on each side (default 45)")
    parser.add_argument("--span", type=int, default=2, metavar="N",
                        help="words on each side that define a construction "
                             "(default 2)")
    parser.add_argument("--per-group", type=int, default=3, metavar="N",
                        help="sites to show per construction (default 3)")
    parser.add_argument("--all", action="store_true",
                        help="show every site, not just the first few")
    args = parser.parse_args()

    for form in args.forms:
        if LAO_DIGITS.search(form) or THAI_DIGITS.search(form):
            print(f"refusing to search {form!r}: it contains a Lao or Thai "
                  "digit, which is never correct in this corpus.",
                  file=sys.stderr)
            return 2

    files, order = load_corpus(args.project)
    if not files:
        print("no corpus files found — run this from the repository root",
              file=sys.stderr)
        return 2

    lexicon, longest = load_lexicon()
    if not lexicon:
        print(f"warning: {LEXICON_PATH} was unreadable, so constructions are "
              "grouped on raw text and may cut a word in half",
              file=sys.stderr)

    for index, form in enumerate(args.forms):
        if index:
            print("\n" + "─" * 70 + "\n")
        hits = find(form, files, lexicon, longest, args.span, args.near)
        report(form, hits, order, args.context, args.per_group, args.all)
    return 0


if __name__ == "__main__":
    sys.exit(main())
