#!/usr/bin/env python3
"""Harvest the CID-to-Unicode table for the Thai printed edition of The Great Controversy.

The print PDF sets its Thai text in subsetted BrowalliaUPC fonts with Identity-H
encoding.  Most of those subsets carry no ToUnicode CMap, so a plain text
extraction returns the CID numbers reinterpreted as Latin codepoints.  A few
subsets in the same file DO carry a correct ToUnicode CMap, and because the
CID ordering is Identity across every subset of the same base font, those maps
are authoritative for the subsets that lack one.

This script unions every trustworthy CMap it can find and writes the result as
a two-column table, reporting any CID that two CMaps disagree about.

Usage:
    python3 th/GC/04_assets/scripts/gc_th_cidmap.py QDF_PDF OUT_TSV
"""

import re
import subprocess
import sys
from collections import defaultdict

# Base fonts whose Identity-H CID numbering this table describes.
FAMILY = re.compile(r"Browallia", re.I)

OBJ_RE = re.compile(r"^(\d+) 0 obj\s*$")


def load_objects(qdf_path):
    """Return {objnum: raw dictionary text} for every non-stream object header."""
    objs = {}
    num = None
    buf = []
    with open(qdf_path, "r", encoding="latin-1") as fh:
        for line in fh:
            m = OBJ_RE.match(line)
            if m:
                num = int(m.group(1))
                buf = []
                continue
            if num is not None:
                if line.startswith("endobj") or line.startswith("stream"):
                    objs[num] = "".join(buf)
                    num = None
                    buf = []
                else:
                    buf.append(line)
    return objs


def stream_text(qdf_path, objnum):
    out = subprocess.run(
        ["qpdf", f"--show-object={objnum}", "--filtered-stream-data", qdf_path],
        capture_output=True,
    )
    return out.stdout.decode("latin-1")


def parse_cmap(text):
    """Parse bfchar and bfrange sections of a ToUnicode CMap into {code: string}."""
    table = {}
    for block in re.findall(r"beginbfchar(.*?)endbfchar", text, re.S):
        for src, dst in re.findall(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", block):
            table[int(src, 16)] = hex_to_str(dst)
    for block in re.findall(r"beginbfrange(.*?)endbfrange", text, re.S):
        # <lo> <hi> <dststart>
        for lo, hi, dst in re.findall(
            r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", block
        ):
            lo_i, hi_i = int(lo, 16), int(hi, 16)
            base = int(dst, 16)
            if hi_i - lo_i > 0xFFFF:
                continue
            for k in range(lo_i, hi_i + 1):
                table[k] = chr(base + (k - lo_i))
        # <lo> <hi> [ <d1> <d2> ... ]
        for lo, hi, arr in re.findall(
            r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*\[(.*?)\]", block, re.S
        ):
            dsts = re.findall(r"<([0-9A-Fa-f]+)>", arr)
            lo_i = int(lo, 16)
            for off, d in enumerate(dsts):
                table[lo_i + off] = hex_to_str(d)
    return table


def hex_to_str(h):
    if len(h) % 4:
        h = h.zfill((len(h) + 3) // 4 * 4)
    return "".join(chr(int(h[i : i + 4], 16)) for i in range(0, len(h), 4))


def main():
    qdf, out_tsv = sys.argv[1], sys.argv[2]
    objs = load_objects(qdf)

    merged = {}
    conflicts = defaultdict(set)
    sources = 0
    for num, body in objs.items():
        if "/Type0" not in body or "/Identity-H" not in body:
            continue
        base = re.search(r"/BaseFont\s*/([^\s/\]>]+)", body)
        tou = re.search(r"/ToUnicode\s+(\d+) 0 R", body)
        if not base or not tou or not FAMILY.search(base.group(1)):
            continue
        sources += 1
        table = parse_cmap(stream_text(qdf, int(tou.group(1))))
        for cid, val in table.items():
            if cid in merged and merged[cid] != val:
                conflicts[cid].add(merged[cid])
                conflicts[cid].add(val)
            merged.setdefault(cid, val)

    with open(out_tsv, "w", encoding="utf-8") as fh:
        fh.write("# cid\tunicode\tcodepoints\n")
        for cid in sorted(merged):
            val = merged[cid]
            pts = " ".join(f"U+{ord(c):04X}" for c in val)
            fh.write(f"{cid}\t{val}\t{pts}\n")

    print(f"source CMaps: {sources}")
    print(f"CIDs mapped: {len(merged)}  range {min(merged)}-{max(merged)}")
    if conflicts:
        print(f"CONFLICTS: {len(conflicts)}")
        for cid, vals in sorted(conflicts.items()):
            print(f"  {cid}: {sorted(vals)}")
    else:
        print("no conflicts")


if __name__ == "__main__":
    main()
