from functools import lru_cache
from pathlib import Path

def get_patch_dictionary_path() -> Path:
    """Return the path to the high‑priority patch dictionary (patch.txt)."""
    script_dir = Path(__file__).parent
    return script_dir / "../../../../lo/assets/dictionaries/patch.txt"

def load_patch_dict(patch_path: Path) -> dict[str, str]:
    """
    Load a patch dictionary.

    Each line:
        term|term_with_penalties % optional_comment
    Notes:
        - 'term' is an exact Lao string (no regex)
        - 'term_with_penalties' is inserted into \\lw{...}
        - Lines starting with '#' or blank lines are ignored
    """
    patch_map: dict[str, str] = {}
    if not patch_path.exists():
        return patch_map
    with patch_path.open(encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "|" not in line:
                continue
            left, right = line.split("|", 1)
            right = right.split("%", 1)[0].strip()
            term = left.strip()
            penalties = right.strip()
            if term and penalties:
                patch_map[term] = penalties
    return patch_map

@lru_cache(maxsize=1)
def _cached_patch_map() -> dict[str, str]:
    """Read and cache patch.txt once per process."""
    return load_patch_dict(get_patch_dictionary_path())

def apply_patch_overrides(text: str) -> str:
    r"""
    Apply exact-match overrides from patch.txt.
    Each match becomes \lw{term_with_penalties}.
    """
    patch_map = _cached_patch_map()
    if not patch_map:
        return text
    for term, penalties in patch_map.items():
        text = text.replace(term, f"\\lw{{{penalties}}}")
    return text