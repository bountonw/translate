#!/usr/bin/env python3
"""Import a web-app handoff document into a GC chapter.

Parses Part A of ~/claude-sandbox/gc-audit/gcNN-handoff.{md,txt}, verifies every
block against lo/GC/03_public/GCNN_lo.md, and (with --apply) splices the manifest
in as [[CLASS SEV #N|old -> new|note]] markers. Verification is all-or-nothing:
if any block fails, nothing is written.

Run from the repository root, by that exact relative path so the permission
allow-rules match (lo/GC/CLAUDE.md 2.D):

  python3 lo/GC/04_assets/scripts/gc_import_handoff.py --chapter 12
  python3 lo/GC/04_assets/scripts/gc_import_handoff.py --chapter 12 --apply
"""

import argparse
import os
import re
import sys
from pathlib import Path

# The repository root, found the way the other scripts here find it, so this
# works from a checkout at any path.
REPO = str(Path(__file__).resolve().parents[4])

# The handoff document is a session input rather than repository content, so
# it stays in the sandbox: lo/GC/CLAUDE.md 4.B keeps a run's artifacts there.
SANDBOX = os.path.expanduser("~/claude-sandbox/gc-audit")

HEADER_RE = re.compile(r"^#(\d+[a-z]?)\s+\{GC\s+([0-9]+\.[0-9]+)\}\s+([A-Z]+)(?:\s+(HIGH|MED|LOW))?\s*$")
ANCHOR_RE = re.compile(r"^## \{GC ([0-9]+\.[0-9]+)\}\s*$")
CLASSES = {"OMISSION", "ADDITION", "FACT", "REF", "NOTE", "ALIGN", "SPELL", "TERM", "GRAM", "CLARITY"}


def split_parts(text):
    """Return {'A': str, 'B': str, 'C': str, 'count': str} from the handoff."""
    parts, cur, buf = {}, None, []
    for line in text.splitlines():
        m = re.match(r"^##\s+Part\s+([ABC])\b", line)
        if m:
            if cur:
                parts[cur] = "\n".join(buf)
            cur, buf = m.group(1), []
            continue
        if re.match(r"^##\s+Closing count", line):
            if cur:
                parts[cur] = "\n".join(buf)
            cur, buf = "count", []
            continue
        buf.append(line)
    if cur:
        parts[cur] = "\n".join(buf)
    return parts


def parse_manifest(part_a):
    """Parse Part A into blocks. Returns (blocks, parse_errors)."""
    blocks, errors = [], []
    cur, key = None, None
    for lineno, line in enumerate(part_a.splitlines(), 1):
        m = HEADER_RE.match(line.strip())
        if m:
            if cur:
                blocks.append(cur)
            cur = {
                "num": m.group(1), "anchor": m.group(2), "cls": m.group(3),
                "sev": m.group(4), "old": None, "new": None, "note": None,
                "line": lineno,
            }
            key = None
            continue
        if re.match(r"^#\d", line.strip()):
            # An unparsable header still closes the block before it, or its keys
            # would silently overwrite the previous block's old/new/note.
            errors.append(f"line {lineno}: block header does not parse: {line.strip()[:80]}")
            if cur:
                blocks.append(cur)
            cur, key = None, None
            continue
        if cur is None:
            continue
        km = re.match(r"^(old|new|note):\s?(.*)$", line)
        if km:
            key = km.group(1)
            cur[key] = km.group(2)
            continue
        if line.strip() == "":
            key = None
            continue
        if key:                                  # continuation of the previous key
            cur[key] = (cur[key] + "\n" + line).rstrip()
        else:
            errors.append(f"line {lineno}: stray text outside any key: {line.strip()[:80]}")
    if cur:
        blocks.append(cur)
    return blocks, errors


def load_paragraphs(path):
    """Return {anchor: (start_idx, end_idx)} over the chapter's line list, plus the lines."""
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().splitlines(keepends=True)
    spans, order = {}, []
    for i, line in enumerate(lines):
        m = ANCHOR_RE.match(line.rstrip("\n"))
        if m:
            order.append((m.group(1), i))
    for j, (anchor, start) in enumerate(order):
        end = order[j + 1][1] if j + 1 < len(order) else len(lines)
        if anchor in spans:
            spans[anchor] = ("DUPLICATE", None)
        else:
            spans[anchor] = (start, end)
    return lines, spans


def verify(blocks, lines, spans):
    """Return a list of failure strings."""
    fails = []
    nums = [b["num"] for b in blocks]
    plain = [int(n) for n in nums if n.isdigit()]
    expected = list(range(1, len(plain) + 1))
    if plain != expected:
        missing = sorted(set(expected) - set(plain))
        extra = [n for n in plain if plain.count(n) > 1]
        fails.append(f"NUMBERING: runs {plain[:3]}..{plain[-3:] if plain else []}, "
                     f"expected 1..{len(plain)}; missing {missing}; duplicated {sorted(set(extra))}")
    if len(set(nums)) != len(nums):
        dups = sorted({n for n in nums if nums.count(n) > 1})
        fails.append(f"NUMBERING: duplicate ids {dups}")

    for b in blocks:
        tag = f"#{b['num']} {{GC {b['anchor']}}}"
        if b["cls"] not in CLASSES:
            fails.append(f"{tag}: unknown class {b['cls']}")
        if b["sev"] is None:
            fails.append(f"{tag}: missing severity ({b['cls']})")
        if b["note"] is None or b["note"].strip() == "":
            fails.append(f"{tag}: empty note")
        old, new = b["old"], b["new"]
        if old is None or new is None:
            fails.append(f"{tag}: missing old: or new: line")
            continue
        if old.strip() == "" and new.strip() == "":
            fails.append(f"{tag}: both old and new are empty")
            continue
        if b["anchor"] not in spans:
            fails.append(f"{tag}: anchor not found in chapter")
            continue
        start, end = spans[b["anchor"]]
        if start == "DUPLICATE":
            fails.append(f"{tag}: anchor appears more than once in chapter")
            continue
        para = "".join(lines[start:end])
        if old.strip() == "":
            continue                              # insertion; position handled at splice time
        n = para.count(old)
        if n == 0:
            fails.append(f"{tag}: old span not found in its paragraph")
        elif n > 1:
            fails.append(f"{tag}: old span occurs {n} times in its paragraph (not unique)")
    return fails


def marker(b):
    return f"[[{b['cls']} {b['sev']} #{b['num']}|{b['old']} -> {b['new']}|{' '.join(b['note'].split())}]]"


def splice(blocks, lines, spans, chapter_path):
    """Write markers into the chapter. Assumes verify() returned no failures.

    Markers are numbered in true text order, not manifest order: within a
    paragraph the manifest sometimes lists findings in a different order than
    their spans occur, and a chapter whose numbers zig-zag makes Brian resolve
    #11 before #10. Returns (count, {manifest_num: chapter_num}).
    """
    # Work paragraph by paragraph so replacements stay scoped and uniqueness holds.
    by_anchor = {}
    for b in blocks:
        by_anchor.setdefault(b["anchor"], []).append(b)
    out, applied, remap = [], 0, {}
    anchors = sorted(spans.items(), key=lambda kv: kv[1][0])
    prev_end = 0
    for anchor, (start, end) in anchors:
        out.append("".join(lines[prev_end:start]))
        para = "".join(lines[start:end])
        group = by_anchor.get(anchor, [])
        for b in group:
            if b["old"].strip() == "":
                raise SystemExit(f"#{b['num']}: empty old has no insertion point; resolve before applying")
            if para.count(b["old"]) != 1:
                raise SystemExit(f"#{b['num']}: uniqueness lost during splice; nothing further written")
        for b in sorted(group, key=lambda b: para.find(b["old"])):
            applied += 1
            remap[b["num"]] = str(applied)
            b = dict(b, num=str(applied))
            para = para.replace(b["old"], marker(b), 1)
        out.append(para)
        prev_end = end
    out.append("".join(lines[prev_end:]))
    with open(chapter_path, "w", encoding="utf-8") as fh:
        fh.write("".join(out))
    return applied, remap


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chapter", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dump-parts", action="store_true",
                    help="write Part B to gcNN-companion.md and Part C to gcNN-glossary-proposals.txt")
    args = ap.parse_args()

    nn = args.chapter
    handoff = None
    for cand in (f"gc{nn}-handoff.md", f"gc{nn}-handoff.txt",
                 f"GC{nn}-handoff.md", f"GC{nn}-handoff.txt"):
        p = os.path.join(SANDBOX, cand)
        if os.path.exists(p):
            handoff = p
            break
    if not handoff:
        sys.exit(f"no handoff file for GC{nn} in {SANDBOX}")
    chapter_path = os.path.join(REPO, f"lo/GC/03_public/GC{nn}_lo.md")

    with open(handoff, encoding="utf-8") as fh:
        parts = split_parts(fh.read())
    blocks, perrors = parse_manifest(parts.get("A", ""))
    lines, spans = load_paragraphs(chapter_path)
    fails = perrors + verify(blocks, lines, spans)

    print(f"handoff: {handoff}")
    print(f"blocks parsed: {len(blocks)}")
    ins = [b['num'] for b in blocks if (b['old'] or '').strip() == '' and (b['new'] or '').strip() != '']
    dels = [b['num'] for b in blocks if (b['new'] or '').strip() == '' and (b['old'] or '').strip() != '']
    verif = [b['num'] for b in blocks if (b['note'] or '').strip().startswith('verify:')]
    print(f"insertions (empty old): {ins}")
    print(f"deletions/questions (empty new): {dels}")
    print(f"verify: notes: {verif}")
    if fails:
        print(f"\nFAILURES ({len(fails)}):")
        for f in fails:
            print("  " + f)
    else:
        print("\nverification: PASS")

    remap = {}
    if args.apply:
        if fails:
            sys.exit("\nnot applying: verification failed")
        n, remap = splice(blocks, lines, spans, chapter_path)
        moved = {k: v for k, v in remap.items() if k != v}
        print(f"\napplied {n} markers to {chapter_path}")
        print(f"renumbered into text order: {moved or 'nothing moved'}")

    if args.dump_parts:
        comp = os.path.join(SANDBOX, f"gc{nn}-companion.md")
        prop = os.path.join(SANDBOX, f"gc{nn}-glossary-proposals.txt")
        body = parts.get("B", "").rstrip()
        if remap:                                 # keep companion keys pointing at the markers
            body = re.sub(r"^(\d+)\.(\s+\{GC)", lambda m: remap.get(m.group(1), m.group(1)) + "." + m.group(2),
                          body, flags=re.M)
        with open(comp, "w", encoding="utf-8") as fh:
            fh.write(f"# GC {nn} — companion document\n" + body + "\n")
        with open(prop, "w", encoding="utf-8") as fh:
            fh.write(parts.get("C", "").strip() + "\n")
        print(f"wrote {comp}\nwrote {prop}")


if __name__ == "__main__":
    main()
