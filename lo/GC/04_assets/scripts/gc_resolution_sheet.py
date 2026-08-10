#!/usr/bin/env python3
"""Build a resolution sheet for a GC chapter under audit.

For every [[...]] marker left in the Lao manuscript, emit a block giving the
marker's number, class, severity, its {GC ###.#} anchor, the proposed change,
the auditor's note, and the FULL English paragraph for that anchor -- so the
marker can be judged without leaving the sheet to hunt for the source.

Markers whose header has been damaged during resolution (class and severity
stripped, an unterminated bracket, an unparseable body) are reported too,
under a RESIDUE heading, because a damaged marker is exactly what is easiest
to miss by eye.

Brian's inline questions are collected as well, each with its anchor and its
English paragraph, so they can be answered in one pass. He writes them either
as {{Q#4|...}} / {{Q|...}} anywhere in the manuscript, or by appending
"|his question" to the note field of the marker he is asking about. See
~/claude-sandbox/gc-audit/communication.md.

    python3 gc_resolution_sheet.py --chapter 13
    python3 gc_resolution_sheet.py --lo path/to/GC13_lo.md --en path/to/GC13_en.md

Read-only with respect to the repository: the only file written is the sheet.
"""

import argparse
import os
import re
import sys

ANCHOR_RE = re.compile(r"^##\s*\{GC\s*(\d+\.\d+)\}\s*$")
MARKER_RE = re.compile(r"\[\[(.*?)\]\]", re.DOTALL)
QUESTION_RE = re.compile(r"\{\{Q(?P<num>#\d+)?\s*\|?(?P<q>.*?)\}\}", re.DOTALL)
# Brian's voice inside a note: a direct question, or first person, or an
# instruction aimed at the conductor rather than a description of a finding.
ASKED_RE = re.compile(r"\?|\bI \b|\bI'|\bexplain\b|\bexpand in chat\b|\bwe are talking\b"
                      r"|^\s*Note:|\bcan't\b|\bdoesn't\b",
                      re.IGNORECASE)
HEADER_RE = re.compile(r"^(?P<cls>[A-Z]+)\s+(?P<sev>[A-Z]+)\s+#(?P<num>\d+)\|(?P<rest>.*)$", re.DOTALL)
NUMONLY_RE = re.compile(r"^#?(?P<num>\d+)\|(?P<rest>.*)$", re.DOTALL)

DEFAULT_REPO = os.path.expanduser("~/programming/translate")
DEFAULT_OUT_DIR = os.path.expanduser("~/claude-sandbox/gc-audit")


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def parse_english(text):
    """Map {GC ###.#} -> the paragraph body under that heading."""
    paras, ref, buf = {}, None, []
    for line in text.splitlines():
        m = ANCHOR_RE.match(line)
        if m:
            if ref is not None:
                paras[ref] = "\n".join(buf).strip()
            ref, buf = m.group(1), []
        elif ref is not None:
            buf.append(line)
    if ref is not None:
        paras[ref] = "\n".join(buf).strip()
    return paras


def split_change(rest):
    """'old -> new|note' -> (old, new, note). The first pipe ends the change."""
    change, _, note = rest.partition("|")
    old, sep, new = change.partition("->")
    if not sep:
        return change.strip(), None, note.strip()
    return old.strip(), new.strip(), note.strip()


def parse_markers(text):
    """Walk the Lao manuscript, returning markers in text order."""
    lines = text.splitlines()
    offsets, pos = [], 0
    for line in lines:
        offsets.append(pos)
        pos += len(line) + 1

    anchors = []  # (char offset, ref)
    for idx, line in enumerate(lines):
        m = ANCHOR_RE.match(line)
        if m:
            anchors.append((offsets[idx], m.group(1)))

    def anchor_for(offset):
        found = None
        for start, ref in anchors:
            if start <= offset:
                found = ref
            else:
                break
        return found

    markers = []
    for m in MARKER_RE.finditer(text):
        body, ref = m.group(1), anchor_for(m.start())
        hm = HEADER_RE.match(body)
        if hm:
            old, new, note = split_change(hm.group("rest"))
            markers.append(dict(kind="ok", num=int(hm.group("num")), cls=hm.group("cls"),
                                sev=hm.group("sev"), ref=ref, old=old, new=new, note=note))
            continue
        nm = NUMONLY_RE.match(body)
        if nm:
            old, new, note = split_change(nm.group("rest"))
            markers.append(dict(kind="residue", num=int(nm.group("num")), cls=None,
                                sev=None, ref=ref, old=old, new=new, note=note,
                                raw=nm.group("rest").strip(),
                                why="class and severity are missing from the header"))
            continue
        markers.append(dict(kind="residue", num=None, cls=None, sev=None, ref=ref,
                            old=None, new=None, note=None,
                            why="the body does not parse as a marker",
                            raw=body.strip()))

    questions = []
    # Brian also asks by appending "|his question" to a marker's note, which is
    # quicker than typing a construct when the cursor is already inside the
    # marker. Treat the tail after a second pipe as a question on that marker.
    for mk in markers:
        # A damaged marker often lost its note pipe along with its header, so
        # fall back to the whole surviving body when looking for his voice.
        note = mk.get("note") or mk.get("raw") or ""
        if not note:
            continue
        if "|" in note:
            body, _, asked = note.partition("|")
            mk["note"] = body.strip()
            questions.append(dict(num=str(mk["num"]) if mk["num"] else None,
                                  ref=mk["ref"], text=asked.strip(), sure=True))
        elif ASKED_RE.search(note):
            # He more often types straight into the note with no delimiter, so
            # flag anything that reads as his voice rather than the auditor's.
            questions.append(dict(num=str(mk["num"]) if mk["num"] else None,
                                  ref=mk["ref"], text=note.strip(), sure=False))
    for q in QUESTION_RE.finditer(text):
        num = q.group("num")
        questions.append(dict(num=num[1:] if num else None,
                              ref=anchor_for(q.start()),
                              text=q.group("q").strip()))

    # An opening bracket with no closing one never reaches the regex at all.
    unclosed = text.count("[[") - len(markers)
    return markers, unclosed, questions


def quote(text):
    if not text:
        return "_(none)_"
    return "\n".join("> " + line if line.strip() else ">" for line in text.splitlines())


def describe(mk):
    if mk["old"] == "" and mk["new"]:
        return "**Insert:** " + mk["new"]
    if mk["new"] == "" and (mk["note"] or "").startswith("verify:"):
        return "**Open question, nothing to apply yet.** Flagged span: " + (mk["old"] or "")
    if mk["new"] == "":
        return "**Proposed deletion of:** " + (mk["old"] or "")
    return "**Replace:** " + (mk["old"] or "") + "\n\n**With:** " + (mk["new"] or "")


def build(chapter, lo_path, en_path, paras, markers, unclosed, questions):
    out = [f"# GC{chapter} — resolution sheet", ""]
    out.append(f"Lao manuscript: `{lo_path}`")
    out.append(f"English source: `{en_path}`")
    out.append("")

    intact = [m for m in markers if m["kind"] == "ok"]
    residue = [m for m in markers if m["kind"] == "residue"]

    nums = ", ".join(f"#{m['num']}" for m in intact) or "none"
    out.append(f"{len(intact)} intact marker(s) remaining: {nums}.")
    if residue:
        out.append(f"**{len(residue)} damaged marker(s)** — see the residue section at the end.")
    if unclosed > 0:
        out.append(f"**{unclosed} unterminated `[[` with no closing `]]`** — these are invisible to the parser; find them by hand.")
    out.append("")
    if questions:
        out.append(f"**{len(questions)} inline question(s) from Brian** — answered in the companion's "
                   "Questions section, then deleted from the manuscript.")
    out.append("")
    out.append("Each block below carries the full English paragraph for its anchor. "
               "Nothing here needs to be cross-referenced against another file.")
    out.append("")

    if questions:
        out.append("---")
        out.append("")
        out.append("## Questions from Brian")
        out.append("")
        for idx, q in enumerate(questions, 1):
            tie = f" — about marker #{q['num']}" if q["num"] else ""
            out.append(f"### Q{idx} — {{GC {q['ref']}}}{tie}")
            out.append("")
            out.append(q["text"] or "_(empty question)_")
            out.append("")
            body = paras.get(q["ref"])
            if body is not None:
                out.append(f"**English, {{GC {q['ref']}}}:**")
                out.append("")
                out.append(quote(body))
                out.append("")

    for mk in intact:
        out.append("---")
        out.append("")
        out.append(f"## Marker {mk['num']} — {mk['cls']} {mk['sev']} — {{GC {mk['ref']}}}")
        out.append("")
        out.append(f"**Note:** {mk['note'] or '_(no note)_'}")
        out.append("")
        out.append(describe(mk))
        out.append("")
        out.append(f"**English, {{GC {mk['ref']}}}:**")
        out.append("")
        body = paras.get(mk["ref"])
        out.append(quote(body) if body is not None
                   else f"> _No English paragraph found for this anchor. That is itself worth checking._")
        out.append("")

    if residue:
        out.append("---")
        out.append("")
        out.append("## Residue — damaged markers")
        out.append("")
        for mk in residue:
            label = f"Marker {mk['num']}" if mk["num"] else "Unnumbered marker"
            out.append(f"### {label} — {{GC {mk['ref']}}}")
            out.append("")
            out.append(f"Problem: {mk['why']}.")
            out.append("")
            if mk.get("raw"):
                out.append("Raw body:")
                out.append("")
                out.append(quote(mk["raw"]))
            else:
                out.append(f"**Note:** {mk['note'] or '_(no note)_'}")
                out.append("")
                out.append(describe(mk))
            out.append("")
            body = paras.get(mk["ref"])
            if body is not None:
                out.append(f"**English, {{GC {mk['ref']}}}:**")
                out.append("")
                out.append(quote(body))
                out.append("")

    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chapter")
    ap.add_argument("--lo")
    ap.add_argument("--en")
    ap.add_argument("--repo", default=DEFAULT_REPO)
    ap.add_argument("--out")
    args = ap.parse_args()

    if args.lo and args.en:
        lo_path, en_path = args.lo, args.en
        chapter = args.chapter or "??"
    elif args.chapter:
        chapter = args.chapter
        lo_path = os.path.join(args.repo, f"lo/GC/03_public/GC{chapter}_lo.md")
        en_path = os.path.join(args.repo, f"lo/GC/00_source/GC{chapter}_en.md")
    else:
        ap.error("give --chapter, or both --lo and --en")

    for path in (lo_path, en_path):
        if not os.path.exists(path):
            sys.exit(f"missing: {path}")

    paras = parse_english(read(en_path))
    markers, unclosed, questions = parse_markers(read(lo_path))
    sheet = build(chapter, lo_path, en_path, paras, markers, unclosed, questions)

    out = args.out or os.path.join(DEFAULT_OUT_DIR, f"gc{chapter}-resolution-sheet.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(sheet)

    intact = sum(1 for m in markers if m["kind"] == "ok")
    damaged = sum(1 for m in markers if m["kind"] == "residue")
    print(f"wrote {out}")
    print(f"{intact} intact marker(s), {damaged} damaged, {unclosed} unterminated bracket(s), "
          f"{len(questions)} question(s)")


if __name__ == "__main__":
    main()
