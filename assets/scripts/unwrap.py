#!/usr/bin/env python3
"""Join hard-wrapped outline text back into single logical lines.

A logical line starts at column 0 (a marker, a bullet, or a
plain paragraph's first line). A following line indented by one
to three spaces or a tab is a hard-wrap continuation and is folded
back in. A line indented by four or more spaces is an example block
and stays as it is (root CLAUDE.md 7.A). Headings and fenced code
blocks are left untouched.

    python3 assets/scripts/unwrap.py FILE [FILE ...]
"""
import sys


def unwrap(lines):
    out = []
    buf = None
    in_fence = False
    for raw in lines:
        line = raw.rstrip("\n")
        stripped = line.strip()
        if stripped.startswith("```"):
            if buf is not None:
                out.append(buf)
                buf = None
            out.append(line)
            in_fence = not in_fence
            continue
        if in_fence:
            out.append(line)
            continue
        if stripped == "":
            if buf is not None:
                out.append(buf)
                buf = None
            out.append("")
            continue
        if stripped.startswith("#"):
            if buf is not None:
                out.append(buf)
                buf = None
            out.append(stripped)
            continue
        if line.startswith("    "):
            if buf is not None:
                out.append(buf)
                buf = None
            out.append(line)
            continue
        if line[0] in (" ", "\t") and buf is not None:
            buf = buf + " " + stripped
        else:
            if buf is not None:
                out.append(buf)
            buf = stripped
    if buf is not None:
        out.append(buf)
    return out


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: unwrap.py FILE [FILE ...]")
    for path in sys.argv[1:]:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
        result = unwrap(lines)
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(result) + "\n")


if __name__ == "__main__":
    main()
