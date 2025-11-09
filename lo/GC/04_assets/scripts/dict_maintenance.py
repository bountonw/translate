# 04_assets/scripts/dict_maintenance.py
from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Tuple, Optional


# -------------------------------
# Core parsing / IO helpers
# -------------------------------
def _parse_dict_line(line: str) -> Optional[Tuple[str, str, str]]:
    """
    Return (clean_term, coded_term, original_line) for valid entries,
    or None for comments/empties/invalids.
    """
    raw = line.rstrip("\n")
    s = raw.strip()
    if not s or s.startswith("%") or "|" not in s:
        return None
    left, right = s.split("|", 1)
    clean = left.strip()
    if not clean:
        return None
    return clean, right.strip(), raw


def _read_dictionary(path: Path) -> Tuple[List[str], List[Tuple[str, str, str]], List[str]]:
    """
    Split file into (header_block, entries, trailing_other).
    - header_block: initial comments/empties before the first entry (preserved as-is)
    - entries: list of (clean_term, coded_term, original_line)
    - trailing_other: anything after entries that isn't a valid entry (preserved as-is)
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    header: List[str] = []
    entries: List[Tuple[str, str, str]] = []
    trailing: List[str] = []
    in_header = True

    for line in lines:
        parsed = _parse_dict_line(line)
        if parsed:
            in_header = False
            entries.append(parsed)
        else:
            (header if in_header else trailing).append(line)
    return header, entries, trailing


def _atomic_write(path: Path, lines: List[str]) -> None:
    """Write lines atomically to `path` (UTF-8)."""
    tmp = path.with_suffix(path.suffix + ".tmp_write")
    with tmp.open("w", encoding="utf-8") as f:
        for line in lines:
            f.write(line.rstrip("\n") + "\n")
    tmp.replace(path)


# -------------------------------
# Public operations
# -------------------------------
def sort_dictionary_file(input_path: Path, *, reverse: bool = False, overwrite: bool = True) -> Path:
    """
    Sort dictionary by first column (clean_term), preserving:
      - header block (comments/empties before first entry),
      - trailing non-entry lines,
      - original formatting of entry lines.
    If overwrite=True, replaces the input file in place (atomic).
    Returns the written path.
    """
    header, entries, trailing = _read_dictionary(input_path)
    entries.sort(key=lambda t: t[0], reverse=reverse)  # t[0] = clean_term

    out_lines: List[str] = []
    out_lines.extend(header)
    out_lines.extend(original for _clean, _coded, original in entries)
    out_lines.extend(trailing)

    if overwrite:
        _atomic_write(input_path, out_lines)
        return input_path
    else:
        out_path = input_path.with_name(f"{input_path.stem}_sorted.txt")
        _atomic_write(out_path, out_lines)
        return out_path


def find_duplicates_in_dictionary(input_path: Path) -> Dict[str, List[Tuple[int, str]]]:
    """
    Return {clean_term: [(line_no, original_line), ...]} for any clean term
    that occurs more than once in the given dictionary file.
    """
    dups: Dict[str, List[Tuple[int, str]]] = {}
    with input_path.open("r", encoding="utf-8") as f:
        for idx, raw in enumerate(f, 1):
            parsed = _parse_dict_line(raw)
            if not parsed:
                continue
            clean, _coded, _orig = parsed
            dups.setdefault(clean, []).append((idx, raw.rstrip("\n")))
    return {k: v for k, v in dups.items() if len(v) > 1}


def _write_duplicate_log_if_needed(
    *, main_path: Path, patch_path: Optional[Path], temp_dir: Path
) -> Optional[Path]:
    """
    If duplicates exist in MAIN and/or PATCH, write a single consolidated log:
      04_assets/temp/dictionary_duplicates.log
    Print a console message when a log is created.
    Returns the log path if written, else None.
    """
    temp_dir.mkdir(parents=True, exist_ok=True)
    main_dups = find_duplicates_in_dictionary(main_path)
    patch_dups: Dict[str, List[Tuple[int, str]]] = {}
    if patch_path and patch_path.exists():
        patch_dups = find_duplicates_in_dictionary(patch_path)

    if not main_dups and not patch_dups:
        print("✅ No dictionary duplicates found; no log written.")
        return None

    log_path = temp_dir / "dictionary_duplicates.log"
    with log_path.open("w", encoding="utf-8") as f:
        f.write("=== DICTIONARY DUPLICATE REPORT ===\n\n")
        f.write(f"Main:  {main_path}\n")
        if patch_path and patch_path.exists():
            f.write(f"Patch: {patch_path}\n")
        f.write("\n")

        if main_dups:
            f.write(f"⚠️  Duplicates in MAIN ({len(main_dups)} terms):\n")
            for term, occ in sorted(main_dups.items()):
                f.write(f"\n{term} ({len(occ)} entries):\n")
                for ln, line in occ:
                    f.write(f"  L{ln:>5}: {line}\n")
            f.write("\n")

        if patch_dups:
            f.write(f"⚠️  Duplicates in PATCH ({len(patch_dups)} terms):\n")
            for term, occ in sorted(patch_dups.items()):
                f.write(f"\n{term} ({len(occ)} entries):\n")
                for ln, line in occ:
                    f.write(f"  L{ln:>5}: {line}\n")
            f.write("\n")

    # Console message(s)
    if main_dups:
        print(f"⚠️  Duplicates found in MAIN. See log: {log_path}")
    if patch_dups:
        print(f"⚠️  Duplicates found in PATCH. See log: {log_path}")
    return log_path


def maintain_dictionaries(*, project_root: Optional[Path] = None, reverse: bool = False) -> Dict[str, Optional[str]]:
    """
    Sort (and overwrite) main.txt and patch.txt if present.
    Only write a duplicate log if duplicates exist; otherwise print a success message.
    Returns dict with written paths and optional log path.
    """
    script_dir = Path(__file__).parent
    dict_dir = script_dir / "../../../../lo/assets/dictionaries"
    root = project_root or script_dir.parent.parent
    temp_dir = root / "04_assets" / "temp"

    main_path = dict_dir / "main.txt"
    patch_path = dict_dir / "patch.txt"

    written_main = sort_dictionary_file(main_path, reverse=reverse, overwrite=True)
    written_patch = patch_path if patch_path.exists() and sort_dictionary_file(
        patch_path, reverse=reverse, overwrite=True
    ) else None

    log_path = _write_duplicate_log_if_needed(main_path=main_path, patch_path=patch_path if patch_path.exists() else None, temp_dir=temp_dir)

    return {
        "main": str(written_main),
        "patch": str(written_patch) if written_patch else None,
        "duplicate_log": str(log_path) if log_path else None,
    }


# -------------------------------
# Optional CLI
# -------------------------------
if __name__ == "__main__":
    # Manual run: sort & overwrite; print duplicate summary; write log only if needed.
    stats = maintain_dictionaries()
    print("\n[dict_maintenance] Done.")
    for k, v in stats.items():
        print(f"  {k}: {v}")