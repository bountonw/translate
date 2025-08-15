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

@dataclass
class FootnoteReport:
    resolved: int = 0
    unresolved: int = 0
    duplicate_ref_ids: Dict[str, int] = None  # id -> count (>1 means duplicate)
    duplicate_def_ids: Dict[str, int] = None  # id -> count of defs (>1 means duplicate definition)
    orphan_def_ids: List[str] = None          # defs never referenced
    markers_inside_macros: List[Tuple[str, str]] = None  # (macro name, snippet)

    # Sanitizer counters (footnote-only)
    sanitize_leading_trim: int = 0
    sanitize_combo_fixes: int = 0
    sanitize_trailing_trim: int = 0

    # Blank-line normalization
    blanklines_collapsed: int = 0

    def __post_init__(self):
        if self.duplicate_ref_ids is None:
            self.duplicate_ref_ids = {}
        if self.duplicate_def_ids is None:
            self.duplicate_def_ids = {}
        if self.orphan_def_ids is None:
            self.orphan_def_ids = []
        if self.markers_inside_macros is None:
            self.markers_inside_macros = []


def sanitize_footnote_text(text: str, report: FootnoteReport) -> str:
    """
    Footnote-only cleanup that assumes braceful spacing macros:
      - Drop leading \\space{} / \\nbsp{} (any count); preserve leading \\nobreak if present.
      - Normalize small combos anywhere in the footnote:
          \\space{}\\nbsp{}  -> \\nbsp{}
          \\nbsp{}\\space{}  -> \\nbsp{}
          \\space{}\\nobreak -> \\nobreak
      - Trim trailing \\space{} / \\nbsp{} at the very end.
    Do NOT remove braces from spacing macros; we keep braceful forms (\space{}, \nbsp{}).
    """
    changed = False

    # 1) Leading trims: repeatedly remove \space{} / \nbsp{} at the start (keep \nobreak)
    leading_pattern = re.compile(r'^(?:\s|\\space\{\}|\\nbsp\{\})+')
    m = leading_pattern.match(text)
    if m:
        new_text = text[m.end():]
        if new_text != text:
            report.sanitize_leading_trim += 1
            text = new_text
            changed = True

    # 2) Combo fixes anywhere
    combo_patterns = [
        (re.compile(r'\\space\{\}\\nbsp\{\}'), r'\\nbsp{}'),
        (re.compile(r'\\nbsp\{\}\\space\{\}'), r'\\nbsp{}'),
        (re.compile(r'\\space\{\}\\nobreak'), r'\\nobreak'),
    ]
    for pat, repl in combo_patterns:
        text, n = pat.subn(repl, text)
        if n:
            report.sanitize_combo_fixes += n
            changed = True

    # 3) Trailing trims: remove trailing \space{} / \nbsp{} (and whitespace) at the very end
    trailing_pattern = re.compile(r'(?:\s|\\space\{\}|\\nbsp\{\})+\Z')
    text2, n2 = trailing_pattern.subn('', text)
    if n2:
        report.sanitize_trailing_trim += 1
        text = text2
        changed = True

    return text


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
# Footnote collection + replacement
# ============================================================

_DEF_LINE_RE = re.compile(r'^[ \t]*\[\^([^\]]+)\]:[ \t]*(.*)$', re.MULTILINE)
_MARKER_RE   = re.compile(r'\[\^([^\]]+)\]')

def collect_footnote_definitions(working: str) -> Tuple[Dict[str, str], Dict[str, int], Dict[str, List[Tuple[int,int]]]]:
    """
    Scan the *working* text (with placeholders) for single-line definitions.
    Returns:
      defs:  id -> text (if multiple defs for same id, last one wins)
      def_counts: id -> number of definitions found
      def_spans: id -> list of (start, end) spans in working for each def line
    """
    defs: Dict[str, str] = {}
    def_counts: Dict[str, int] = {}
    def_spans: Dict[str, List[Tuple[int,int]]] = {}
    for m in _DEF_LINE_RE.finditer(working):
        fid = m.group(1)
        ftext = m.group(2)
        defs[fid] = ftext  # last one wins (but we also count)
        def_counts[fid] = def_counts.get(fid, 0) + 1
        def_spans.setdefault(fid, []).append((m.start(), m.end()))
    return defs, def_counts, def_spans


def find_markers_in_text(working: str) -> Dict[str, int]:
    """
    Return counts of [^id] markers in the *working* body.
    """
    counts: Dict[str, int] = {}
    for m in _MARKER_RE.finditer(working):
        # skip definitions (those are line-anchored and have ':') — our pattern doesn't match ':' anyway here
        fid = m.group(1)
        counts[fid] = counts.get(fid, 0) + 1
    return counts


def remove_used_definition_lines(working: str, used_ids: set, def_spans: Dict[str, List[Tuple[int,int]]]) -> str:
    """
    Remove only those definition lines whose id is in used_ids; keep orphans.
    IMPORTANT: we also remove ONE trailing newline after each removed def line
    (handles \n, \r\n, or \r) to avoid leaving an extra blank line behind.
    """
    if not used_ids:
        return working

    intervals: List[Tuple[int, int]] = []
    n = len(working)

    for fid in used_ids:
        for (start, end) in def_spans.get(fid, []):
            # extend to include exactly one following linebreak if present
            j = end
            if j < n:
                if working[j:j+2] == '\r\n':
                    end = j + 2
                elif working[j:j+1] in ('\n', '\r'):
                    end = j + 1
            intervals.append((start, end))

    if not intervals:
        return working

    # merge and cut
    intervals.sort()
    out: List[str] = []
    cursor = 0
    for a, b in intervals:
        if cursor < a:
            out.append(working[cursor:a])
        cursor = max(cursor, b)
    out.append(working[cursor:])
    return ''.join(out)

def replace_markers_with_footnotes(working: str, defs: Dict[str, str], report: FootnoteReport) -> str:
    """
    Replace [^id] → \footnote{<defs[id]>}; leave unresolved markers in place and log.
    Also count duplicate refs (same id used >1).

    NOTE: We no longer sanitize here because 'working' still contains placeholders.
    A post-restore pass sanitizes only inside \\footnote{...} bodies on the final text.
    """
    seen_ref: Dict[str, int] = {}

    def repl(m: re.Match) -> str:
        fid = m.group(1)
        seen_ref[fid] = seen_ref.get(fid, 0) + 1
        if fid in defs:
            report.resolved += 1
            if seen_ref[fid] > 1:
                report.duplicate_ref_ids[fid] = seen_ref[fid]
            return r'\footnote{' + defs[fid] + '}'
        else:
            report.unresolved += 1
            return m.group(0)  # leave as-is

    return _MARKER_RE.sub(repl, working)


def collapse_extra_blank_lines(text: str, report: Optional[FootnoteReport] = None) -> str:
    """
    Ensure double-spaced paragraphs: collapse any run of 3+ newlines (with optional
    spaces on blank lines) to exactly 2 newlines. Also normalizes CRLF/CR to LF first.
    """
    # Normalize line endings to LF so collapsing is predictable
    t = text.replace('\r\n', '\n').replace('\r', '\n')

    # Replace 3 or more consecutive "blank line units" with exactly 2 newlines
    # A "blank line unit" here is optional spaces/tabs followed by \n.
    new_text, nsubs = re.subn(r'(?:[ \t]*\n){3,}', '\n\n', t)

    if report is not None and nsubs:
        report.blanklines_collapsed += nsubs

    return new_text


def sanitize_footnotes_in_document(restored_text: str, report: FootnoteReport) -> str:
    """
    After placeholders are restored for the whole document, clean spacing only
    inside \\footnote{...} bodies:
      - Drop leading \\space{} / \\nbsp{} (any count)
      - Normalize combos: \\space{}\\nbsp{} → \\nbsp{}, \\nbsp{}\\space{} → \\nbsp{}, \\space{}\\nobreak → \\nobreak
      - Drop trailing \\space{} / \\nbsp{}
    Other macros (\\lw{...}, \\scrref{...}, \\p{...}, etc.) remain untouched.
    """
    out: List[str] = []
    i = 0
    n = len(restored_text)
    footnote_cmd = re.compile(r'\\footnote\s*\{')

    while i < n:
        m = footnote_cmd.search(restored_text, i)
        if not m:
            out.append(restored_text[i:])
            break

        # Copy text before \footnote{
        out.append(restored_text[i:m.start()])

        # Find balanced body { ... }
        brace_start = m.end() - 1  # at the '{'
        try:
            brace_end = _scan_balanced_braces(restored_text, brace_start)
        except ValueError:
            # Unbalanced; just copy as-is and move on to avoid data loss
            out.append(restored_text[m.start():m.end()])
            i = m.end()
            continue

        body = restored_text[brace_start + 1 : brace_end - 1]
        cleaned = sanitize_footnote_text(body, report)

        out.append(r'\footnote{')
        out.append(cleaned)
        out.append('}')

        i = brace_end

    return ''.join(out)


def detect_markers_inside_macros(original: str, spans: List[Span], report: FootnoteReport) -> None:
    """
    Scan ORIGINAL protected spans; if any contains [^id] marker, log loudly.
    """
    inner_marker_re = re.compile(r'\[\^([^\]]+)\]')
    for s in spans:
        slice_text = original[s.start:s.end]
        if inner_marker_re.search(slice_text):
            snippet = slice_text[:80].replace('\n', ' ') + ('…' if len(slice_text) > 80 else '')
            report.markers_inside_macros.append((s.name, snippet))


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

def write_logs(report: FootnoteReport, in_path: Path, resolved_ids: Dict[str,int],
               def_counts: Dict[str,int], used_ids: set, temp_dir: Path) -> None:
    """
    Write module3_inline_report.log and module3_warnings.log in 04_assets/temp/.
    """
    inline_path = temp_dir / "module3_inline_report.log"
    warn_path = temp_dir / "module3_warnings.log"

    # Inline report: compact summary
    lines = []
    lines.append(
        f"{in_path.name}: resolved={report.resolved} unresolved={report.unresolved} "
        f"unique_ids={len(resolved_ids)} duplicate_refs={len([k for k,v in report.duplicate_ref_ids.items() if v>1])} "
        f"duplicate_defs={len([k for k,v in report.duplicate_def_ids.items() if v>1])} orphans={len(report.orphan_def_ids)} "
        f"| sanitize: leading_trim={report.sanitize_leading_trim} combos_fixed={report.sanitize_combo_fixes} trailing_trim={report.sanitize_trailing_trim}"
        f"| blanklines_collapsed={report.blanklines_collapsed}"
    )
    if report.duplicate_ref_ids:
        lines.append(f"  duplicate_ref_ids: {sorted(report.duplicate_ref_ids.items(), key=lambda kv: kv[0])}")
    dupe_defs = {k:v for k,v in def_counts.items() if v>1}
    if dupe_defs:
        lines.append(f"  duplicate_def_ids: {sorted(dupe_defs.items(), key=lambda kv: kv[0])}")
    if report.orphan_def_ids:
        lines.append(f"  orphan_def_ids: {sorted(report.orphan_def_ids)}")
    if report.markers_inside_macros:
        lines.append(f"  markers_inside_macros: {[(name, snip) for name, snip in report.markers_inside_macros]}")

    with open(inline_path, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    # Warnings log
    warn_lines = []
    if report.unresolved:
        warn_lines.append(f"{in_path.name}: WARNING unresolved_markers={report.unresolved}")
    if report.orphan_def_ids:
        warn_lines.append(f"{in_path.name}: INFO orphan_def_ids={sorted(report.orphan_def_ids)}")
    if dupe_defs:
        warn_lines.append(f"{in_path.name}: INFO duplicate_definitions={sorted(dupe_defs.items())}")
    if report.duplicate_ref_ids:
        warn_lines.append(f"{in_path.name}: INFO duplicate_references={sorted(report.duplicate_ref_ids.items())}")
    if report.markers_inside_macros:
        warn_lines.append(f"{in_path.name}: ERROR footnote_markers_inside_macros={[(name, snip) for name, snip in report.markers_inside_macros]}")

    with open(warn_path, "a", encoding="utf-8") as f:
        f.write("\n".join(warn_lines) + ("\n" if warn_lines else ""))


# ============================================================
# Main
# ============================================================

def main(argv: Optional[Iterable[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Module 3 — footnotes + protect/restore")
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

            # Footnote processing on working text
            report = FootnoteReport()

            # Detect forbidden markers inside macros (from ORIGINAL protected slices)
            detect_markers_inside_macros(original, spans, report)

            # Collect defs and markers
            defs, def_counts, def_spans = collect_footnote_definitions(working)
            marker_counts = find_markers_in_text(working)

            # Record duplicate defs
            for fid, cnt in def_counts.items():
                if cnt > 1:
                    report.duplicate_def_ids[fid] = cnt

            # Determine which ids are used (present as markers)
            used_ids = set(fid for fid in marker_counts.keys() if fid in defs)

            # Remove ONLY used definition lines (plus their following newline)
            working_no_defs = remove_used_definition_lines(working, used_ids, def_spans)
            
            # Standardize paragraph spacing to exactly one blank line (double-spaced)
            working_no_defs = collapse_extra_blank_lines(working_no_defs, report)
            
            # Replace markers with \footnote{…}
            working_replaced = replace_markers_with_footnotes(working_no_defs, defs, report)

            # Orphans = defs that were never used
            report.orphan_def_ids = sorted(set(defs.keys()) - used_ids)

            # Restore placeholders
            restored = restore_placeholders(working_replaced, placeholders, original)

            # Footnote-only spacing cleanup on the final text
            restored = sanitize_footnotes_in_document(restored, report)


            # Write .tex to temp/tex/
            out_path = default_output_path(in_path, temp_subdir="tex")
            out_path.write_text(restored, encoding='utf-8')

            # Logs
            write_logs(report, in_path, marker_counts, def_counts, used_ids, temp_dir)

            if args.debug or args.verbose:
                print(debug_summary(original, spans, placeholders))
                print(f"[module3] footnotes: resolved={report.resolved}, unresolved={report.unresolved}, "
                      f"defs={len(defs)}, used_ids={len(used_ids)}, orphans={len(report.orphan_def_ids)}")
                if report.markers_inside_macros:
                    print("[module3] ERROR: footnote markers were found inside protected macros (see warnings log).")
                print(f"[module3] wrote: {out_path}")

        except Exception as e:
            any_error = True
            print(f"[module3] ERROR processing {in_path}: {e}")

    return 0 if not any_error else 2


if __name__ == "__main__":
    sys.exit(main())
