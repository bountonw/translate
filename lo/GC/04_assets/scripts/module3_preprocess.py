#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
Module 3 — Markdown→LaTeX inline + footnotes
---------------------------------------------
Current step implements:
- CLI (positional files/ranges; parity with M1/M2)
- Slice-only protect/restore for TeX macros
- Footnote resolver:
  * Collect single-line definitions:    ^\s*\[\^id\]:\s*text
  * Replace body markers  [^id] → \footnote{text}
  * Remove only USED definition lines; keep orphans
  * Log: unresolved markers, orphan defs, duplicate refs, duplicate defs
  * Warn if a footnote marker appears INSIDE any protected macro span (shouldn't happen)
- Debug (--debug):
  * Outermost protected spans by kind + top names
  * RAW literal counters + deltas (raw minus outermost)
  * "UNLISTED MACROS" (auto-inventory of any \letters control word)
- Output: 04_assets/temp/tex/<base>.tex  (created if missing)

Next steps (future commits):
- Markdown *** / ** / * → \textbf{\emph{…}} with spacing trims
- Plain-text TeX special escaping (% $ & # _ ^) outside protected spans
- Clean-LaTeX checks (brace balance, stray markdown markers)
- Process markdown poetry and block quotes
"""

from __future__ import annotations

import argparse
import sys
import re
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple, Iterable, Optional, Dict
from helpers.md_footnotes_to_tex import process_footnotes

# ============================================================
# Reuse-compatible helpers (parity with Module 1 & 2)
# ============================================================

def get_project_root() -> Path:
    script_dir = Path(__file__).parent
    return script_dir.parent.parent


def expand_chapter_ranges(file_specs: List[str]) -> List[str]:
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
      - If file_spec is GC##, auto-append '_lo' → GC##_lo.
      - Prefer '{base}_stage2.tmp', else '{base}.tmp'.
    """
    if file_spec.endswith('.tmp'):
        cand = temp_dir / file_spec
        return cand if cand.exists() else None

    base = file_spec
    if re.match(r'^GC\d+$', base):
        base += '_lo'

    candidates = [
        temp_dir / f"{base}_stage2.tmp",
        temp_dir / f"{base}.tmp",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def get_input_files_module3(args: argparse.Namespace) -> List[Path]:
    project_root = get_project_root()
    temp_dir = project_root / '04_assets' / 'temp'
    if not temp_dir.exists():
        print(f"Error: {temp_dir} directory not found")
        return []

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
    """
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
    name: str   # macro/control word, e.g., 'lw', 'nodict', 'space'


@dataclass(frozen=True)
class Placeholder:
    token: str              # e.g., '⟪M000001⟫'
    start_in_work: int
    end_in_work: int
    span: Span              # indices into ORIGINAL text


# ============================================================
# Scanner for protected TeX macros (slice-only detection)
# ============================================================

# Bare commands to protect (no argument braces)
_BARE_PROTECT = {
    # You requested these:
    "space", "nbsp", "ellipsis",
    # Project-known:
    "scrspace", "nobreak", "fs", "rs", "cs",
    # Newly observed bare macros:
    "laorepeat", "laorepeatbefore",
}

def _scan_balanced_braces(text: str, i: int) -> int:
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
    return ("A" <= c <= "Z") or ("a" <= c <= "z")

def find_protected_spans(text: str) -> List[Span]:
    r"""
    Protect:
      1) \letters{…} with balanced braces (e.g., \lw{…}, \egw{…}, \scrref{…}, \p{…})
      2) Selected bare commands: \space, \nbsp, \ellipsis, \scrspace, \nobreak, \fs, \rs, \cs,
                                 \laorepeat, \laorepeatbefore
    """
    spans: List[Span] = []
    i, n = 0, len(text)

    while i < n:
        if text[i] == "\\":
            j = i + 1
            while j < n and _is_letter(text[j]):
                j += 1
            name = text[i + 1:j]
            if not name:
                i += 1
                continue

            # Bare command (whole control word only)
            if name in _BARE_PROTECT:
                spans.append(Span(start=i, end=j, kind="bare_cmd", name=name))
                i = j
                continue

            # Command + optional space + balanced {…}
            k = j
            while k < n and text[k].isspace():
                k += 1
            if k < n and text[k] == "{":
                try:
                    end_arg = _scan_balanced_braces(text, k)
                except ValueError:
                    i += 1
                    continue
                spans.append(Span(start=i, end=end_arg, kind="cmd_with_arg", name=name))
                i = end_arg
                continue

            i += 1
            continue

        i += 1

    spans.sort(key=lambda s: s.start)
    non_overlapping: List[Span] = []
    last_end = -1
    for s in spans:
        if s.start >= last_end:
            non_overlapping.append(s)
            last_end = s.end
    return non_overlapping


# ============================================================
# Placeholder apply/restore (slice-only Option B)
# ============================================================

_TOKEN_FMT = "⟪M{num:06d}⟫"
_TOKEN_RE = re.compile(r"⟪M\d{6}⟫")


def apply_placeholders(text: str, spans: List[Span]) -> Tuple[str, List[Placeholder]]:
    out_chunks: List[str] = []
    placeholders: List[Placeholder] = []
    cursor = 0
    current_len = 0
    for idx, s in enumerate(spans, start=1):
        if cursor < s.start:
            chunk = text[cursor:s.start]
            out_chunks.append(chunk)
            current_len += len(chunk)
        token = _TOKEN_FMT.format(num=idx)
        out_chunks.append(token)
        start_in_work = current_len
        end_in_work = start_in_work + len(token)
        current_len = end_in_work
        placeholders.append(Placeholder(token=token, start_in_work=start_in_work, end_in_work=end_in_work, span=s))
        cursor = s.end
    if cursor < len(text):
        tail = text[cursor:]
        out_chunks.append(tail)
    working = "".join(out_chunks)
    return working, placeholders


def restore_placeholders(working: str, placeholders: List[Placeholder], original: str) -> str:
    if not placeholders:
        return working
    repl: Dict[str, str] = {ph.token: original[ph.span.start:ph.span.end] for ph in placeholders}
    parts: List[str] = []
    i, n = 0, len(working)
    while i < n:
        m = _TOKEN_RE.search(working, i)
        if not m:
            parts.append(working[i:])
            break
        if m.start() > i:
            parts.append(working[i:m.start()])
        token = m.group(0)
        parts.append(repl.get(token, token))
        i = m.end()
    return "".join(parts)


# ============================================================
# Debug summary (kept from previous step, extended)
# ============================================================

def compute_raw_token_counts(original: str) -> dict:
    """
    Return raw (literal) counts of common tokens in ORIGINAL text, ignoring nesting.
    Also detect and return ALL macro names seen (\\letters...), grouped in 'all_macros'.
    """
    import re

    # Catch-all inventory once
    all_macros: Dict[str, int] = {}
    for m in re.finditer(r'\\([A-Za-z]+)', original):
        name = m.group(1)
        all_macros[name] = all_macros.get(name, 0) + 1

    counts = {
        'backslashes_total': original.count('\\'),
        # literal brace-taking substring counts
        'lw_raw': original.count('\\lw{'),
        'nodict_raw': original.count('\\nodict{'),
        'p_raw': original.count('\\p{'),
        'scrref_raw': original.count('\\scrref{'),
        'egw_raw': original.count('\\egw{'),
        'section_raw': original.count('\\section{'),
        'laochapter_raw': original.count('\\laochapter{'),
        'source_raw': original.count('\\source{'),
        # laorepeat* can be bare OR braced → count by name inventory
        'laorepeat_raw': all_macros.get('laorepeat', 0),
        'laorepeatbefore_raw': all_macros.get('laorepeatbefore', 0),
    }

    # bare commands via regex (avoid counting \spaceX etc.)
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


def debug_summary(original: str, spans: List[Span], placeholders: List[Placeholder]) -> str:
    """
    Outermost spans + RAW literal counters (+ deltas) + UNLISTED inventory.
    """
    total_outer = len(spans)
    by_kind: Dict[str, int] = {}
    by_name: Dict[str, int] = {}
    for s in spans:
        by_kind[s.kind] = by_kind.get(s.kind, 0) + 1
        by_name[s.name] = by_name.get(s.name, 0) + 1
    top_names = sorted(by_name.items(), key=lambda kv: kv[1], reverse=True)[:12]

    raw = compute_raw_token_counts(original)
    g = lambda d, k: d.get(k, 0)

    tracked_names = {
        'lw','nodict','p','scrref','egw','section','laochapter','source',
        'laorepeat','laorepeatbefore',
        'space','nbsp','ellipsis','scrspace','nobreak','fs','rs','cs',
    }

    macro_deltas = {
        'lw': raw['lw_raw'] - g(by_name, 'lw'),
        'nodict': raw['nodict_raw'] - g(by_name, 'nodict'),
        'p': raw['p_raw'] - g(by_name, 'p'),
        'scrref': raw['scrref_raw'] - g(by_name, 'scrref'),
        'egw': raw['egw_raw'] - g(by_name, 'egw'),
        'section': raw['section_raw'] - g(by_name, 'section'),
        'laochapter': raw['laochapter_raw'] - g(by_name, 'laochapter'),
        'source': raw['source_raw'] - g(by_name, 'source'),
        'laorepeat': raw['laorepeat_raw'] - g(by_name, 'laorepeat'),
        'laorepeatbefore': raw['laorepeatbefore_raw'] - g(by_name, 'laorepeatbefore'),
    }
    bare_deltas = {
        'space': raw['space_raw'] - g(by_name, 'space'),
        'nbsp': raw['nbsp_raw'] - g(by_name, 'nbsp'),
        'ellipsis': raw['ellipsis_raw'] - g(by_name, 'ellipsis'),
        'scrspace': raw['scrspace_raw'] - g(by_name, 'scrspace'),
        'nobreak': raw['nobreak_raw'] - g(by_name, 'nobreak'),
        'fs': raw['fs_raw'] - g(by_name, 'fs'),
        'rs': raw['rs_raw'] - g(by_name, 'rs'),
        'cs': raw['cs_raw'] - g(by_name, 'cs'),
    }

    # UNLISTED union (raw inventory ∪ outermost names) \ tracked
    all_macros = raw.get('all_macros', {})
    unlisted_raw = {name: cnt for name, cnt in all_macros.items() if name not in tracked_names}
    unlisted_outer = {name: cnt for name, cnt in by_name.items() if name not in tracked_names}
    union_names = sorted(set(unlisted_raw) | set(unlisted_outer))
    rows = [(nm, unlisted_raw.get(nm, 0), unlisted_outer.get(nm, 0), unlisted_raw.get(nm, 0) - unlisted_outer.get(nm, 0))
            for nm in union_names]
    rows.sort(key=lambda t: t[1], reverse=True)
    rows = rows[:20]

    lines: List[str] = []
    lines.append("[module3] protect/restore summary:")
    lines.append(f"  OUTERMOST (placeholder spans): {total_outer}")
    lines.append(f"    kinds: {by_kind}")
    lines.append(f"    top names: {top_names}")
    lines.append(f"    placeholders: {len(placeholders)}")
    lines.append("  RAW LITERAL COUNTS (ignoring nesting):")
    lines.append(f"    backslashes_total: {raw['backslashes_total']}")
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
    lines.append(f"    \\space : {raw['space_raw']} (outermost: {g(by_name,'space')}, delta: {bare_deltas['space']})")
    lines.append(f"    \\nbsp : {raw['nbsp_raw']} (outermost: {g(by_name,'nbsp')}, delta: {bare_deltas['nbsp']})")
    lines.append(f"    \\ellipsis : {raw['ellipsis_raw']} (outermost: {g(by_name,'ellipsis')}, delta: {bare_deltas['ellipsis']})")
    lines.append(f"    \\scrspace : {raw['scrspace_raw']} (outermost: {g(by_name,'scrspace')}, delta: {bare_deltas['scrspace']})")
    lines.append(f"    \\nobreak : {raw['nobreak_raw']} (outermost: {g(by_name,'nobreak')}, delta: {bare_deltas['nobreak']})")
    lines.append(f"    \\fs : {raw['fs_raw']} (outermost: {g(by_name,'fs')}, delta: {bare_deltas['fs']})")
    lines.append(f"    \\rs : {raw['rs_raw']} (outermost: {g(by_name,'rs')}, delta: {bare_deltas['rs']})")
    lines.append(f"    \\cs : {raw['cs_raw']} (outermost: {g(by_name,'cs')}, delta: {bare_deltas['cs']})")
    lines.append("  UNLISTED MACROS (auto-detected; top 20):")
    if rows:
        for name, rc, oc, dlt in rows:
            lines.append(f"    \\{name} : raw {rc} (outermost: {oc}, delta: {dlt})")
    else:
        lines.append("    (none)")
    return "\n".join(lines)


# ============================================================
# Logging helpers
# ============================================================

def write_logs(report: Dict[str, any], in_path: Path, temp_dir: Path) -> None:
    """
    Write module3_inline_report.log and module3_warnings.log in 04_assets/temp/.
    """
    inline_path = temp_dir / "module3_inline_report.log"
    warn_path = temp_dir / "module3_warnings.log"

    # Inline report: compact summary
    lines = []
    converted = report.get('converted_count', 0)
    total_markers = report.get('marker_count', 0)
    unresolved = len(report.get('orphaned_markers', []))
    orphaned_defs = report.get('orphaned_definitions', [])
    duplicate_refs = report.get('duplicate_references', {})
    
    lines.append(
        f"{in_path.name}: resolved={converted} unresolved={unresolved} "
        f"total_markers={total_markers} orphaned_defs={len(orphaned_defs)} "
        f"duplicate_refs={len([k for k,v in duplicate_refs.items() if v>1])}"
    )
    
    if duplicate_refs:
        lines.append(f"  duplicate_ref_ids: {sorted(duplicate_refs.items(), key=lambda kv: kv[0])}")
    if orphaned_defs:
        lines.append(f"  orphan_def_ids: {sorted(orphaned_defs)}")

    with open(inline_path, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    # Warnings log
    warn_lines = []
    if report.get('orphaned_markers'):
        warn_lines.append(f"{in_path.name}: WARNING unresolved_markers={report['orphaned_markers']}")
    if orphaned_defs:
        warn_lines.append(f"{in_path.name}: INFO orphan_def_ids={sorted(orphaned_defs)}")
    if duplicate_refs:
        warn_lines.append(f"{in_path.name}: INFO duplicate_references={sorted(duplicate_refs.items())}")

    with open(warn_path, "a", encoding="utf-8") as f:
        f.write("\n".join(warn_lines) + ("\n" if warn_lines else ""))
# ============================================================
# Main
# ============================================================

def main(argv: Optional[Iterable[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Module 3 – footnotes + protect/restore")
    ap.add_argument('files', nargs='*', help="Chapter specs or filenames (e.g., GC01, GC[01..05], GC01_lo.tmp)")
    ap.add_argument('--debug', action='store_true', help='Print debug summary')
    ap.add_argument('--verbose', action='store_true', help='Verbose resolution output')
    args = ap.parse_args(argv)

    input_files = get_input_files_module3(args)
    if not input_files:
        return 1

    temp_dir = get_project_root() / '04_assets' / 'temp'
    any_error = False

    for in_path in input_files:
        try:
            original = in_path.read_text(encoding='utf-8')

            # Protect (slice-only)
            spans = find_protected_spans(original)
            working, placeholders = apply_placeholders(original, spans)

            # Process footnotes using helper
            # Create temporary file for footnote processor
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.md', delete=False) as tmp:
                tmp.write(working)
                tmp_path = Path(tmp.name)
            
            try:
                # Process footnotes on protected text
                processed_working, fn_report = process_footnotes(tmp_path)
            finally:
                # Clean up temp file
                tmp_path.unlink(missing_ok=True)

            # Restore placeholders
            restored = restore_placeholders(processed_working, placeholders, original)

            # Write .tex to temp/tex/
            out_path = default_output_path(in_path, temp_subdir="tex")
            out_path.write_text(restored, encoding='utf-8')

            # Logs
            write_logs(fn_report, in_path, temp_dir)

            if args.debug or args.verbose:
                print(debug_summary(original, spans, placeholders))
                print(f"[module3] footnotes: resolved={fn_report.get('converted_count', 0)}, "
                      f"unresolved={len(fn_report.get('orphaned_markers', []))}, "
                      f"defs={fn_report.get('definition_count', 0)}, "
                      f"orphans={len(fn_report.get('orphaned_definitions', []))}")
                if fn_report.get('orphaned_markers'):
                    print("[module3] WARNING: unresolved footnote markers found (see warnings log).")
                print(f"[module3] wrote: {out_path}")

        except Exception as e:
            any_error = True
            print(f"[module3] ERROR processing {in_path}: {e}")

    return 0 if not any_error else 2

if __name__ == "__main__":
    sys.exit(main())
