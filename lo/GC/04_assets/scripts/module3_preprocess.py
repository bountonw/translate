#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
Module 3 — Markdown→LaTeX inline + footnotes (Step 1: scaffold)
----------------------------------------------------------------
This step implements ONLY:
- CLI & file discovery (parity with Module 1/2: positional files/ranges)
- Protect–then–restore (slice-only) engine
- Identity round-trip (no transforms), writing .tex output
- Optional debug/verbose summary

Next steps (not in this commit):
- Footnote collect/resolve  [^n] + matching [^n]: ...
- Markdown *** / ** / * transforms to \textbf{\emph{…}} etc.
- TeX special escaping in plain text (% $ & # _ ^)
- Clean-LaTeX checks & warnings

Notes:
- We NEVER alter internals of protected macros like \lw{…}, \nodict{…}, \scrref{…}, etc.
- We protect any \letters{…} command with balanced braces, plus select bare commands.
"""

from __future__ import annotations

import argparse
import sys
import re
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple, Iterable, Optional, Dict


# ============================================================
# Reuse-compatible helpers (parity with Module 1 & 2)
# ============================================================

def get_project_root() -> Path:
    """
    Get the project root directory based on script location.
    Script is in 04_assets/scripts/, so project root is two levels up.
    """
    script_dir = Path(__file__).parent
    return script_dir.parent.parent


def expand_chapter_ranges(file_specs: List[str]) -> List[str]:
    """
    Expand chapter range specifications like GC[01..05] into individual chapters.
    """
    expanded: List[str] = []
    for spec in file_specs:
        m = re.match(r'GC\[(\d+)\.\.(\d+)\]', spec)
        if m:
            start_num = int(m.group(1))
            end_num = int(m.group(2))
            for chapter_num in range(start_num, end_num + 1):
                expanded.append(f"GC{chapter_num:02d}")
        else:
            expanded.append(spec)
    return expanded


def resolve_file_specification_module3(file_spec: str, temp_dir: Path) -> Optional[Path]:
    """
    Resolve a Module 3 input spec to an existing .tmp path in temp_dir.

    Rules:
      - If file_spec endswith .tmp, use it verbatim (under temp_dir) if it exists.
      - If file_spec is GC##, auto-append '_lo' → GC## _lo.
      - Prefer '{base}_stage2.tmp', else '{base}.tmp'.
    """
    # Exact .tmp provided
    if file_spec.endswith('.tmp'):
        cand = temp_dir / file_spec
        return cand if cand.exists() else None

    # Auto-complete the base
    base = file_spec
    if re.match(r'^GC\d+$', base):
        base += '_lo'

    candidates = [
        temp_dir / f"{base}_stage2.tmp",  # preferred
        temp_dir / f"{base}.tmp",         # fallback
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def get_input_files_module3(args: argparse.Namespace) -> List[Path]:
    """
    Get list of input files for Module 3 using positional args (like Module 1/2).
    If no files are provided, process all available in temp dir,
    preferring *_stage2.tmp where present.
    """
    project_root = get_project_root()
    temp_dir = project_root / '04_assets' / 'temp'
    if not temp_dir.exists():
        print(f"Error: {temp_dir} directory not found")
        return []

    # Specific files provided → resolve them
    if args.files:
        files: List[Path] = []
        for spec in expand_chapter_ranges(args.files):
            resolved = resolve_file_specification_module3(spec, temp_dir)
            if resolved:
                files.append(resolved)
                if getattr(args, 'verbose', False) or getattr(args, 'debug', False):
                    print(f"Resolved '{spec}' → {resolved.name}")
            else:
                print(f"Warning: Could not find file for specification '{spec}'")
                base = spec + '_lo' if re.match(r'^GC\d+$', spec) else spec
                print(f"  Searched for: {base}_stage2.tmp, {base}.tmp")
        return files

    # No specs → process all available
    stage2 = list(temp_dir.glob('*_stage2.tmp'))
    if stage2:
        if getattr(args, 'verbose', False) or getattr(args, 'debug', False):
            print(f"Processing all *_stage2.tmp files: {len(stage2)} files")
        return stage2

    tmp_files = list(temp_dir.glob('*.tmp'))
    if tmp_files:
        if getattr(args, 'verbose', False) or getattr(args, 'debug', False):
            print(f"No *_stage2.tmp found; using *.tmp: {len(tmp_files)} files")
        return tmp_files

    print(f"No .tmp files found in {temp_dir}")
    return []


def default_output_path(in_path: Path, temp_subdir: str = "tex") -> Path:
    """
    Map temp input → final .tex path under the *temp* tree.

      foo_stage2.tmp → 04_assets/temp/tex/foo.tex
      foo.tmp        → 04_assets/temp/tex/foo.tex

    Notes:
    - Keep .tex artifacts in temp (transitional; not tracked by git).
    - 'temp_subdir' lets us choose 'tex' (default) or '' to drop them directly in temp/.
    """
    # base name without _stage2 suffix
    base = in_path.stem
    if base.endswith('_stage2'):
        base = base[:-len('_stage2')]

    temp_root = get_project_root() / '04_assets' / 'temp'
    out_dir = temp_root / temp_subdir if temp_subdir else temp_root
    out_dir.mkdir(parents=True, exist_ok=True)

    return out_dir / f"{base}.tex"


# ============================================================
# Protected placeholder data model (slice-only, Option B)
# ============================================================

@dataclass(frozen=True)
class Span:
    """Half-open slice [start, end) in ORIGINAL text."""
    start: int
    end: int
    kind: str   # 'cmd_with_arg' | 'bare_cmd'
    name: str   # macro/control word name (letters only), e.g., 'lw', 'nodict', 'space'


@dataclass(frozen=True)
class Placeholder:
    """
    A placeholder inserted into the working text.
    We store only indices (slice-only, no macro copying).
    """
    token: str              # e.g., '⟪M000001⟫'
    start_in_work: int
    end_in_work: int
    span: Span              # indices into ORIGINAL text


# ============================================================
# Scanner for protected TeX macros (slice-only detection)
# ============================================================

# Bare commands to protect (no argument braces)
# Bare commands to protect (no argument braces)
_BARE_PROTECT = {
    # You requested these:
    "space", "nbsp", "ellipsis",
    # Project-known:
    "scrspace", "nobreak", "fs", "rs", "cs",
    # Newly observed bare macros we must preserve:
    "laorepeat", "laorepeatbefore",
}

# Any \letters{...} with balanced braces is protected generically:
# Examples: \lw{…}, \nodict{…}, \egw{…}, \scrref{…}, \p{…}


def _scan_balanced_braces(text: str, i: int) -> int:
    """
    Given text and index i pointing at '{',
    return index of the matching closing '}' + 1 (i.e., end of slice),
    supporting nested braces. Raise ValueError on mismatch.
    """
    if i >= len(text) or text[i] != "{":
        raise ValueError("brace scan called at non-brace position")
    depth = 0
    j = i
    while j < len(text):
        ch = text[j]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return j + 1
        j += 1
    raise ValueError("Unbalanced braces in macro argument")


def _is_letter(c: str) -> bool:
    # TeX control word names here are ASCII letters; Lao text will not match.
    return ("A" <= c <= "Z") or ("a" <= c <= "z")


def find_protected_spans(text: str) -> List[Span]:
    r"""
    Locate protected macros as half-open slices into ORIGINAL text.

    We protect:
      1) Any backslash + letters command immediately followed by a balanced {…} argument.
         (e.g., \lw{…}, \nodict{…}, \scrref{…}, \p{…}, \egw{…})
      2) Specific *bare* commands with no {…}: \space, \nbsp, \ellipsis,
         plus project-listed ones (\scrspace, \nobreak, \fs, \rs, \cs).
    """
    spans: List[Span] = []
    i = 0
    n = len(text)

    while i < n:
        if text[i] == "\\":
            # Parse control word name
            j = i + 1
            while j < n and _is_letter(text[j]):
                j += 1
            name = text[i + 1:j]

            # If no letters after backslash, skip (e.g., escapes like \{ not protected here)
            if not name:
                i += 1
                continue

            # Case 1: bare command (no argument), protect if in allowlist
            if name in _BARE_PROTECT:
                spans.append(Span(start=i, end=j, kind="bare_cmd", name=name))
                i = j
                continue

            # Case 2: command followed by balanced {…}
            k = j
            # Allow optional spaces between command and '{' (rare in your corpus, harmless)
            while k < n and text[k].isspace():
                k += 1
            if k < n and text[k] == "{":
                try:
                    end_arg = _scan_balanced_braces(text, k)
                except ValueError:
                    # Unbalanced; treat as non-protected and move on
                    i += 1
                    continue
                spans.append(Span(start=i, end=end_arg, kind="cmd_with_arg", name=name))
                i = end_arg
                continue

            # Not bare-protected and no '{…}' — leave it (e.g., \LaTeX). Extend later if needed.
            i += 1
            continue

        i += 1

    # Ensure spans are sorted and non-overlapping
    spans.sort(key=lambda s: s.start)
    non_overlapping: List[Span] = []
    last_end = -1
    for s in spans:
        if s.start >= last_end:
            non_overlapping.append(s)
            last_end = s.end
        # else: overlapping macros (unlikely). Keep leftmost and drop inner; could warn in a later step.
    return non_overlapping


# ============================================================
# Placeholder apply/restore (slice-only Option B)
# ============================================================

_TOKEN_FMT = "⟪M{num:06d}⟫"   # very unlikely to collide with Lao text
_TOKEN_RE = re.compile(r"⟪M\d{6}⟫")

def apply_placeholders(text: str, spans: List[Span]) -> Tuple[str, List[Placeholder]]:
    """
    Replace protected spans with unique placeholder tokens in a single pass.
    Returns (working_text, placeholders). No macro text is copied.
    """
    out_chunks: List[str] = []
    placeholders: List[Placeholder] = []

    cursor = 0
    current_len = 0  # running length of out_chunks joined

    for idx, s in enumerate(spans, start=1):
        # Copy text before this span
        if cursor < s.start:
            chunk = text[cursor:s.start]
            out_chunks.append(chunk)
            current_len += len(chunk)

        token = _TOKEN_FMT.format(num=idx)
        out_chunks.append(token)

        start_in_work = current_len
        end_in_work = start_in_work + len(token)
        current_len = end_in_work

        placeholders.append(
            Placeholder(
                token=token,
                start_in_work=start_in_work,
                end_in_work=end_in_work,
                span=s,
            )
        )
        cursor = s.end

    # Tail
    if cursor < len(text):
        tail = text[cursor:]
        out_chunks.append(tail)
        current_len += len(tail)

    working = "".join(out_chunks)
    return working, placeholders


def restore_placeholders(working: str, placeholders: List[Placeholder], original: str) -> str:
    """
    Restore placeholders with their original slices from 'original' text.
    Left-to-right replacement; placeholders do not overlap by design.
    """
    if not placeholders:
        return working

    # Build a map token -> slice text (slice now; we never stored copies)
    repl: Dict[str, str] = {ph.token: original[ph.span.start:ph.span.end] for ph in placeholders}

    parts: List[str] = []
    i = 0
    n = len(working)

    while i < n:
        m = _TOKEN_RE.search(working, i)
        if not m:
            parts.append(working[i:])
            break
        if m.start() > i:
            parts.append(working[i:m.start()])
        token = m.group(0)
        parts.append(repl.get(token, token))  # if ever missing, leave the literal token
        i = m.end()

    return "".join(parts)


# ============================================================
# Debug summary (optional)
# ============================================================

def debug_summary(original: str, spans: List[Span], placeholders: List[Placeholder]) -> str:
    """
    Two-part summary (+ auto inventory):
      A) Outermost protected spans (placeholder anchors)
      B) Raw literal token counts (ignoring nesting), plus delta(raw - outermost)
      C) UNLISTED MACROS — union of:
         - names found in the raw inventory but not in 'tracked_names'
         - names seen in outermost spans but not in 'tracked_names'
    """
    # A) Outermost protected spans
    total_outer = len(spans)
    by_kind: Dict[str, int] = {}
    by_name: Dict[str, int] = {}
    for s in spans:
        by_kind[s.kind] = by_kind.get(s.kind, 0) + 1
        by_name[s.name] = by_name.get(s.name, 0) + 1
    top_names = sorted(by_name.items(), key=lambda kv: kv[1], reverse=True)[:12]

    # B) Raw literal token counts
    raw = compute_raw_token_counts(original)
    g = lambda d, k: d.get(k, 0)  # convenience

    # Tracked set (names we explicitly report above)
    tracked_names = {
        # brace-taking macros
        'lw', 'nodict', 'p', 'scrref', 'egw', 'section', 'laochapter', 'source',
        'laorepeat', 'laorepeatbefore',
        # bare commands
        'space', 'nbsp', 'ellipsis', 'scrspace', 'nobreak', 'fs', 'rs', 'cs',
    }

    # Deltas for brace-takers (raw literal - outermost spans)
    macro_deltas = {
        'lw': g(raw, 'lw_raw') - g(by_name, 'lw'),
        'nodict': g(raw, 'nodict_raw') - g(by_name, 'nodict'),
        'p': g(raw, 'p_raw') - g(by_name, 'p'),
        'scrref': g(raw, 'scrref_raw') - g(by_name, 'scrref'),
        'egw': g(raw, 'egw_raw') - g(by_name, 'egw'),
        'section': g(raw, 'section_raw') - g(by_name, 'section'),
        'laochapter': g(raw, 'laochapter_raw') - g(by_name, 'laochapter'),
        'source': g(raw, 'source_raw') - g(by_name, 'source'),
        'laorepeat': g(raw, 'laorepeat_raw') - g(by_name, 'laorepeat'),
        'laorepeatbefore': g(raw, 'laorepeatbefore_raw') - g(by_name, 'laorepeatbefore'),
    }

    # Deltas for bare commands (raw literal - outermost bare_cmd spans)
    bare_deltas = {
        'space': g(raw, 'space_raw') - g(by_name, 'space'),
        'nbsp': g(raw, 'nbsp_raw') - g(by_name, 'nbsp'),
        'ellipsis': g(raw, 'ellipsis_raw') - g(by_name, 'ellipsis'),
        'scrspace': g(raw, 'scrspace_raw') - g(by_name, 'scrspace'),
        'nobreak': g(raw, 'nobreak_raw') - g(by_name, 'nobreak'),
        'fs': g(raw, 'fs_raw') - g(by_name, 'fs'),
        'rs': g(raw, 'rs_raw') - g(by_name, 'rs'),
        'cs': g(raw, 'cs_raw') - g(by_name, 'cs'),
    }

    # C) UNLISTED MACROS (auto-detected)
    all_macros = raw.get('all_macros', {})
    unlisted_raw = {name: cnt for name, cnt in all_macros.items() if name not in tracked_names}
    unlisted_outer = {name: cnt for name, cnt in by_name.items() if name not in tracked_names}
    union_names = sorted(set(unlisted_raw) | set(unlisted_outer))
    unlisted_rows = [
        (name, unlisted_raw.get(name, 0), unlisted_outer.get(name, 0), unlisted_raw.get(name, 0) - unlisted_outer.get(name, 0))
        for name in union_names
    ]
    unlisted_rows.sort(key=lambda t: t[1], reverse=True)
    TOP_N_UNLISTED = 20
    unlisted_rows = unlisted_rows[:TOP_N_UNLISTED]

    # Build output
    lines: List[str] = []
    lines.append("[module3] protect/restore summary:")
    lines.append(f"  OUTERMOST (placeholder spans): {total_outer}")
    lines.append(f"    kinds: {by_kind}")
    lines.append(f"    top names: {top_names}")
    lines.append(f"    placeholders: {len(placeholders)}")
    lines.append("  RAW LITERAL COUNTS (ignoring nesting):")
    lines.append(f"    backslashes_total: {raw['backslashes_total']}")
    # Brace-takers with deltas
    lines.append(f"    \\lw{{ : {raw['lw_raw']}}}              (outermost: {g(by_name,'lw')}, delta: {macro_deltas['lw']})")
    lines.append(f"    \\nodict{{ : {raw['nodict_raw']}}}       (outermost: {g(by_name,'nodict')}, delta: {macro_deltas['nodict']})")
    lines.append(f"    \\p{{ : {raw['p_raw']}}}                (outermost: {g(by_name,'p')}, delta: {macro_deltas['p']})")
    lines.append(f"    \\scrref{{ : {raw['scrref_raw']}}}       (outermost: {g(by_name,'scrref')}, delta: {macro_deltas['scrref']})")
    lines.append(f"    \\egw{{ : {raw['egw_raw']}}}             (outermost: {g(by_name,'egw')}, delta: {macro_deltas['egw']})")
    lines.append(f"    \\section{{ : {raw['section_raw']}}}      (outermost: {g(by_name,'section')}, delta: {macro_deltas['section']})")
    lines.append(f"    \\laochapter{{ : {raw['laochapter_raw']}}} (outermost: {g(by_name,'laochapter')}, delta: {macro_deltas['laochapter']})")
    lines.append(f"    \\source{{ : {raw['source_raw']}}}        (outermost: {g(by_name,'source')}, delta: {macro_deltas['source']})")
    lines.append(f"    \\laorepeat : {raw['laorepeat_raw']}      (outermost: {g(by_name,'laorepeat')}, delta: {macro_deltas['laorepeat']})")
    lines.append(f"    \\laorepeatbefore : {raw['laorepeatbefore_raw']} (outermost: {g(by_name,'laorepeatbefore')}, delta: {macro_deltas['laorepeatbefore']})")
    # Bare commands with deltas
    lines.append(f"    \\space : {raw['space_raw']} (outermost: {g(by_name,'space')}, delta: {bare_deltas['space']})")
    lines.append(f"    \\nbsp : {raw['nbsp_raw']} (outermost: {g(by_name,'nbsp')}, delta: {bare_deltas['nbsp']})")
    lines.append(f"    \\ellipsis : {raw['ellipsis_raw']} (outermost: {g(by_name,'ellipsis')}, delta: {bare_deltas['ellipsis']})")
    lines.append(f"    \\scrspace : {raw['scrspace_raw']} (outermost: {g(by_name,'scrspace')}, delta: {bare_deltas['scrspace']})")
    lines.append(f"    \\nobreak : {raw['nobreak_raw']} (outermost: {g(by_name,'nobreak')}, delta: {bare_deltas['nobreak']})")
    lines.append(f"    \\fs : {raw['fs_raw']} (outermost: {g(by_name,'fs')}, delta: {bare_deltas['fs']})")
    lines.append(f"    \\rs : {raw['rs_raw']} (outermost: {g(by_name,'rs')}, delta: {bare_deltas['rs']})")
    lines.append(f"    \\cs : {raw['cs_raw']} (outermost: {g(by_name,'cs')}, delta: {bare_deltas['cs']})")

    # Unlisted macros section
    lines.append("  UNLISTED MACROS (auto-detected; top 20):")
    if unlisted_rows:
        for name, raw_count, outer_count, delta in unlisted_rows:
            lines.append(f"    \\{name} : raw {raw_count} (outermost: {outer_count}, delta: {delta})")
    else:
        lines.append("    (none)")

    return "\n".join(lines)

def compute_raw_token_counts(original: str) -> dict:
    """
    Return raw (literal) counts of common tokens in ORIGINAL text, ignoring nesting.
    Also detect and return ALL macro names seen (\\letters...), grouped in 'all_macros'.

    Strategy:
    - For most brace-taking macros (e.g., \lw{), we use fast literal substring counts.
    - For bare commands (e.g., \space) we use regex with (?![A-Za-z]) to avoid \spaceX.
    - For laorepeat/Before, use the macro-name inventory so we count both bare and braced forms.
    """
    import re

    # --------- Catch-all: ALL macro names seen (fast one-pass) ----------
    all_macros: dict[str, int] = {}
    for m in re.finditer(r'\\([A-Za-z]+)', original):
        name = m.group(1)
        all_macros[name] = all_macros.get(name, 0) + 1

    # --------- Tracked raw counts (brace + selected bare) ----------
    counts = {
        'backslashes_total': original.count('\\'),
        # brace-takers (literal open-brace count is fine for these in your corpus)
        'lw_raw': original.count('\\lw{'),
        'nodict_raw': original.count('\\nodict{'),
        'p_raw': original.count('\\p{'),
        'scrref_raw': original.count('\\scrref{'),
        'egw_raw': original.count('\\egw{'),
        'section_raw': original.count('\\section{'),
        'laochapter_raw': original.count('\\laochapter{'),
        'source_raw': original.count('\\source{'),
        # laorepeat* may appear bare OR braced → count by macro-name inventory
        'laorepeat_raw': all_macros.get('laorepeat', 0),
        'laorepeatbefore_raw': all_macros.get('laorepeatbefore', 0),
    }

    # bare commands: whole control words only
    bare_patterns = {
        'space_raw': r'\\space(?![A-Za-z])',
        'nbsp_raw': r'\\nbsp(?![A-Za-z])',
        'ellipsis_raw': r'\\ellipsis(?![A-Za-z])',
        'scrspace_raw': r'\\scrspace(?![A-Za-z])',
        'nobreak_raw': r'\\nobreak(?![A-Za-z])',
        'fs_raw': r'\\fs(?![A-Za-z])',
        'rs_raw': r'\\rs(?![A-Za-z])',
        'cs_raw': r'\\cs(?![A-Za-z])',
    }
    for key, pattern in bare_patterns.items():
        counts[key] = len(re.findall(pattern, original))

    counts['all_macros'] = all_macros
    return counts


# ============================================================
# Main (Step 1 scaffold: identity round-trip)
# ============================================================

def main(argv: Optional[Iterable[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Module 3 — protect/restore identity round-trip (Step 1)"
    )
    # POSitional files, mirroring Module 1/2
    ap.add_argument('files', nargs='*', help="Chapter specs or filenames (e.g., GC01, GC[01..05], GC01_lo.tmp)")
    ap.add_argument('--debug', action='store_true', help='Print debug summary')
    ap.add_argument('--verbose', action='store_true', help='Verbose resolution output')
    args = ap.parse_args(argv)

    input_files = get_input_files_module3(args)
    if not input_files:
        return 1

    any_error = False
    for in_path in input_files:
        try:
            original = in_path.read_text(encoding='utf-8')

            # Protect (slice-only)
            spans = find_protected_spans(original)
            working, placeholders = apply_placeholders(original, spans)

            # (No transforms in Step 1) — identity pass

            # Restore
            restored = restore_placeholders(working, placeholders, original)

            out_path = default_output_path(in_path)
            out_path.write_text(restored, encoding='utf-8')

            if args.debug or args.verbose:
                print(debug_summary(original, spans, placeholders))
                print(f"[module3] wrote: {out_path}")

        except Exception as e:
            any_error = True
            print(f"[module3] ERROR processing {in_path}: {e}")

    return 0 if not any_error else 2


if __name__ == "__main__":
    sys.exit(main())
