"""
md_spacing_punctuation_to_tex.py
---------------------------------

Purpose:
    Centralized spacing and punctuation conversion logic for Markdown to LaTeX.
    Handles all space-related and punctuation-related transformations to ensure
    consistent processing across the pipeline.

Commands Processed by This Helper:
    SPACING COMMANDS:
    • \space{} - Original spaces between words
    • \nbsp{} - Non-breaking spaces (e.g., "1 ຊາມູເອນ" → "1\nbsp{}ຊາມູເອນ")
    • \scrspace{} - Scripture spacing between book names and references
    • \fs{} - Flex space (converted from \s)
    • \rs{} - Rigid space (converted from \S)
    • \cs{} - Compound space (converted from ~S~ in dictionary)
    
    PUNCTUATION COMMANDS:
    • \nobreak{} - Prevent line breaks before/after punctuation
    • \ellipsis{} - Standard ellipsis (…)
    • \ellbefore{} - Ellipsis before punctuation
    • \ellafter{} - Ellipsis after punctuation
    • \laorepeat{} - Lao repetition mark (ໆ)
    • \laorepeatbefore{} - Lao repetition before punctuation
    
    SCRIPTURE/REFERENCE COMMANDS:
    • \scrref{} - Scripture reference wrapper
    • \egw{} - Ellen G. White reference wrapper with \nbsp{}

TO DELETE FROM MODULE 1:
    1. load_numbered_bible_books()
    2. protect_numbered_bible_books()
    3. load_all_bible_books()
    4. protect_scripture_spacing()
    5. split_reference_components()
    6. format_reference_components()
    7. protect_scripture_references()
    8. normalize_nonbreaking_commands()
    9. EGW reference conversion logic in clean_markdown_body()

TO DELETE FROM MODULE 2:
    1. is_punctuation()
    2. is_opening_punctuation()
    3. is_closing_punctuation()
    4. needs_nobreak_protection()
    5. apply_punctuation_protection()
    6. handle_ellipsis_context()
    7. handle_lao_repetition_context()
    8. Space-to-\space{} conversion in process_text_groups()
    9. \s → \fs{} and \S → \rs{} conversion in restore_protected_commands()

"""

import re
import json
from pathlib import Path
from typing import List, Tuple, Dict, Optional, Set


# ============================================================================
# BIBLE DATA LOADING
# ============================================================================

def load_bible_data() -> Tuple[List[str], List[str], Dict[str, str], re.Pattern]:
    """
    Load Bible book data from JSON file for scripture processing.

    Source: Module 1 - Replaces load_all_bible_books()

    Purpose:
        Provides the data needed for identifying and protecting Bible book names
        and scripture references in Lao text.

    Issue Solved:
        Bible book names with numbers need special spacing protection, and
        scripture references need proper formatting for LaTeX typesetting.

    Returns:
        Tuple of (all_books, numbered_books, numbered_mapping, reference_pattern)

    TODO:
        1. Move bible_books.json inside the package and load via 
           importlib.resources.files(...) (keep current Path traversal until 
           that refactor is done).
        2. Convert RuntimeError to a small domain exception (e.g., BibleDataLoadError) 
           and add logging once the logging policy for helpers is finalized.
    """
    try:
        script_dir = Path(__file__).parent
        json_path = (
            script_dir
            / ".."
            / ".."
            / ".."
            / ".."
            / "assets"
            / "data"
            / "bible"
            / "bible_books.json"
        )

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        all_books = [book["lao_name"] for book in data["books"]]
        numbered_books = [
            book["lao_name"] for book in data["books"] if book.get("numbered", False)
        ]

        numbered_mapping: Dict[str, str] = {}
        for book in data["books"]:
            if book.get("numbered", False):
                # Protect the first space (between numeral and name)
                nbsp_form = book["lao_name"].replace(" ", "\\nbsp{}", 1)
                numbered_mapping[book["lao_name"]] = nbsp_form

        reference_pattern = re.compile(
            r"\d+:\d+(?:[,-\u2013-]\d+)*(?:\s*[,;\u2013-]\s*\d+(?::\d+)?)*"
        )

        return all_books, numbered_books, numbered_mapping, reference_pattern

    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        # Fail fast: callers shouldn't proceed without this core data.
        raise RuntimeError(f"Could not load Bible books JSON: {e}") from e


# ============================================================================
# BIBLE REFERENCE PROCESSING
# ============================================================================


def protect_scripture_references(text: str) -> str:
    """
    Apply all scripture reference transformations in a single pass.
    - Numbered book protection (1 Samuel → 1\\nbsp{}Samuel)
    - Scripture spacing (John 3:16 → John\\scrspace{}3:16)
    - Reference wrapping (3:16,18 → \\scrref{3:16},\\scrspace{}\\scrref{18})
    
    Args:
        text: Input text containing Bible references
        
    Returns:
        Text with all scripture transformations applied
        
    Example:
        Input:  "1 Samuel 3:16, 18-20; 4:1"
        Output: "1\\nbsp{}Samuel\\scrspace{}\\scrref{3:16},\\scrspace{}\\scrref{18-20};\\scrspace{}\\scrref{4:1}"
    """

    all_books, numbered_books, _, reference_pattern = load_bible_data()
    if not all_books or not reference_pattern:
        return text
    
    # Build pattern matching any book (in original form)
    book_patterns = []
    numbered_set = set(numbered_books)
    
    for book in all_books:
        # Keep original form for pattern matching
        escaped = re.escape(book)
        book_patterns.append(escaped)
    
    # Create single regex matching any book followed by reference
    books_pattern = '|'.join(book_patterns)
    full_pattern = rf'({books_pattern})\s+({reference_pattern.pattern})'
    
    def format_match(match):
        """Process a matched Bible reference."""
        book_part = match.group(1)
        ref_part = match.group(2)
        
        # Apply \nbsp{} to numbered books AFTER matching
        if book_part in numbered_set and ' ' in book_part:
            book_part = book_part.replace(' ', '\\nbsp{}', 1)
        
        # Split reference on commas and semicolons
        parts = re.split(r'([,;])', ref_part)
        formatted = []
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            elif part in ',;':
                formatted.append(f'{part}\\scrspace{{}}')
            else:
                formatted.append(f'\\scrref{{{part}}}')
        
        # Properly escape braces in f-string
        formatted_str = "".join(formatted)
        return f'{book_part}\\scrspace{{}}{formatted_str}'
    
    # Single pass through entire text
    return re.sub(full_pattern, format_match, text)


# ============================================================================
# EGW REFERENCE PROCESSING
# ============================================================================

def convert_egw_references(text: str) -> str:
    """
    Convert Ellen G. White references to LaTeX format.
    
    Source: Module 1 - Replaces EGW conversion logic in clean_markdown_body()
    
    Purpose:
        Converts markdown-style EGW references to proper LaTeX commands.
    
    Issue Solved:
        Ensures consistent formatting of EGW references with non-breaking
        space between book code and page number.
    
    Args:
        text: Input text with {GC x.y} style references
        
    Returns:
        Text with converted references
        
    Example:
        "{GC 3.14}" → "\\egw{GC\\nbsp{}3.14}"
    """
    egw_pattern = r'\{(GC) (\d+\.\d+)\}'
    return re.sub(egw_pattern, r'\\egw{\1\\nbsp{}{\\refdigits \2}}', text)

def convert_text_references(text: str) -> str:
    arr = ["TKJV", "TH1940", "TNCV", "NTV", "THSV", "THA-ER", "LCV", "KJV", "TH1971", "LO1972", "version", "Adventist"]
    for x in arr:
        paraX = "(" + x + ")"
        if (paraX in text):
            text = text.replace(paraX, "{\\smallerscale " + paraX + "}")
        else:
            text = text.replace(x, "{\\smallerscale " + x + "}")
    return text

# ============================================================================
# PUNCTUATION DETECTION (constants and helpers for Module 1)
# ============================================================================

# Explicit character sets (no extra dependencies; focused on Lao interaction)
_OPENERS: Set[str] = {
    "(", "[", "{", "<", "«", "‹", "“", "‘", "‚", "„"
}

_CLOSERS: Set[str] = {
    ")", "]", "}", ">", "»", "›", "”", "’"
}

# Phrase/segment enders that trail Lao text and must not be separated
_ENDERS: Set[str] = {",", ".", ":", ";", "?", "!"}

# Dashes are treated as "closing" in our sense: no break BEFORE, break AFTER allowed elsewhere
_DASHES: Set[str] = {"-", "\u2010", "\u2011", "\u2012", "\u2013", "\u2014", "\u2015"}  # ‐ - ‒ – — ―

# Ellipsis and Lao repetition
_ELLIPSIS: str = "\u2026"  # …
_LAO_REPEAT: str = "ໆ"     # repetition mark

# Full punctuation universe we care about in Module 1 (for is_punctuation)
_PUNCTUATION_UNIVERSE: Set[str] = (
    _OPENERS
    | _CLOSERS
    | _ENDERS
    | _DASHES
    | {"\"", "'", _ELLIPSIS, _LAO_REPEAT}
)


def is_punctuation(char: str) -> bool:
    """
    Check if a character is punctuation.
    
    Source: Module 2 - Replaces is_punctuation()
    
    Purpose:
        Identifies punctuation characters that may need special spacing treatment.
    
    Issue Solved:
        Punctuation needs different line-breaking behavior than regular text.
    
    Args:
        char: Single character to check
        
    Returns:
        True if character is punctuation
    """
    if not char or len(char) != 1:
        return False
    return char in _PUNCTUATION_UNIVERSE


def is_opening_punctuation(char: str) -> bool:
    """
    Check if character is opening punctuation.
    
    Source: Module 2 - Replaces is_opening_punctuation()
    
    Purpose:
        Identifies opening punctuation that should not be separated from following text.
    
    Issue Solved:
        Opening quotes/brackets should stay with the text they introduce.
    
    Args:
        char: Single character to check
        
    Returns:
        True if character is opening punctuation
    """
    if not char or len(char) != 1:
        return False
    return char in _OPENERS


def is_closing_punctuation(char: str) -> bool:
    """
    Check if character is closing punctuation.
    
    Source: Module 2 - Replaces is_closing_punctuation()
    
    Purpose:
        Identifies closing punctuation that should not be separated from preceding text.
    
    Issue Solved:
        Prevents line breaks between Lao text and trailing punctuation by enabling
        upstream insertion of \\nobreak{} before these marks.
    
    Args:
        char: Single character to check
        
    Returns:
        True if character is closing punctuation
    """
    if not char or len(char) != 1:
        return False

    # Ellipsis is handled by dedicated macros; not treated as closing here
    if char == _ELLIPSIS:
        return False

    # Closing punctuation = paired closers OR phrase enders OR dashes OR Lao repetition mark
    if char in _CLOSERS:
        return True
    if char in _ENDERS:
        return True
    if char in _DASHES:
        return True
    if char == _LAO_REPEAT:
        return True

    return False

# ============================================================================
# Lao repeat character ໆ
# ============================================================================

def handle_lao_repetition_with_context(text: str) -> str:
    """
    Convert Lao repetition marks (ໆ) to LaTeX commands with context.

    Purpose:
        Allow a break after ໆ normally, but never between ໆ and a following
        closing punctuation, dash, ellipsis, or another ໆ (chained repeats).

    Rules:
        - Default: ໆ -> \\laorepeat{}
        - If next char is a closer/ender, a dash, ellipsis (…), or another ໆ:
          ໆ -> \\laorepeatbefore{}  (no break between ໆ and that next mark)

    Notes:
        - Does not modify spaces or other characters.
        - Ellipsis spacing is handled elsewhere; we only prevent a pre-ellipsis
          break here.
    """
    if not text:
        return text

    rep = "ໆ"
    ellipsis = "\u2026"  # …
    enders = {",", ".", ":", ";", "?", "!"}
    closers = {
        ")", "]", "}", ">", "»", "›", "”", "’", "\"", "'",
    }

    dashes = {
        "-", "\u2010", "\u2011", "\u2012", "\u2013", "\u2014", "\u2015",
    }  # ‐ - ‒ – — ―

    out = []
    n = len(text)

    for i, ch in enumerate(text):
        if ch != rep:
            out.append(ch)
            continue

        next_ch = text[i + 1] if i + 1 < n else ""

        if (
            next_ch
            and (
                next_ch in enders
                or next_ch in closers
                or next_ch in dashes
                or next_ch == ellipsis
                or next_ch == rep
            )
        ):
            out.append("\\laorepeatbefore{}")
        else:
            out.append("\\laorepeat{}")

    return "".join(out)

def needs_nobreak_protection(text: str) -> bool:
    """
    Check if text needs nobreak protection.
    
    Source: Module 2 - Replaces needs_nobreak_protection()
    
    Purpose:
        Identifies LaTeX commands that should not be separated from adjacent punctuation.
    
    Issue Solved:
        Prevents line breaks between Lao words and their punctuation.
    
    Args:
        text: Text to check
        
    Returns:
        True if text ends with a command that needs protection
    """
    return (text.endswith('}') or 
            text in ['\\laorepeat{}', '\\laorepeatbefore{}'])


# ============================================================================
# ELLIPSES
# ============================================================================

def handle_ellipsis_with_context(text: str) -> str:
    """
    Convert U+2026 ellipses to context-aware LaTeX commands.

    Variants (selection policy):
      - prev punct, next not            -> \\ellafter{}
      - next punct, prev not            -> \\ellbefore{}
      - both sides punct                -> \\ellall{}   (tight both sides)
      - no next (paragraph/section end) -> \\ellbefore{}
      - special: \\laorepeatbefore{} … text   -> \\laorepeatbefore{}\\ellipsis{}
      - special: \\laorepeatbefore{} … punct  -> \\laorepeatbefore{}\\ellall{}

    Notes:
      - Runs AFTER handle_lao_repetition_with_context(), so raw ໆ has already
        become \\laorepeat{} / \\laorepeatbefore{}.
      - Uses is_punctuation() from this module to classify neighbors.
      - Skips ASCII spaces when scanning neighbors. Macros (\\something{...})
        are treated as non-punctuation for neighbor tests, except the explicit
        look-back for \\laorepeatbefore{} (special cases above).
      - Macro internals (e.g., any \\nobreak{} policy) live in TeX; we only pick
        the correct macro flavor here.
    """
    if not text:
        return text

    ELL = "\u2026"
    n = len(text)
    i = 0
    out = []

    def _scan_prev(idx: int):
        """
        Find the nearest non-space item to the left.
        Returns: (prev_char, prev_is_punct, prev_is_repeatbefore)
        """
        j = idx - 1
        while j >= 0 and text[j] == " ":
            j -= 1
        if j < 0:
            return ("", False, False)

        # If we landed on the end of a macro, check for \laorepeatbefore{}
        if text[j] == "}":
            k = j - 1
            # hop back to a backslash beginning this (flat) macro
            while k >= 0 and text[k] != "\\":
                k -= 1
            if k >= 0:
                macro = text[k:j + 1]
                if macro == "\\laorepeatbefore{}":
                    return ("", False, True)
                # other macros: treat as non-punctuation context
                return ("", False, False)

        ch = text[j]
        return (ch, is_punctuation(ch), False)

    def _scan_next(idx: int):
        """
        Find the nearest non-space item to the right.
        Returns: (next_char, next_is_punct, has_next)
        """
        j = idx + 1
        while j < n and text[j] == " ":
            j += 1
        if j >= n:
            return ("", False, False)

        # If next token starts a macro, treat as non-punctuation (neighbor exists)
        if text[j] == "\\":
            return ("", False, True)

        ch = text[j]
        return (ch, is_punctuation(ch), True)

    while i < n:
        ch = text[i]
        if ch != ELL:
            out.append(ch)
            i += 1
            continue

        prev_ch, prev_is_punct, prev_is_repeatbefore = _scan_prev(i)
        next_ch, next_is_punct, has_next = _scan_next(i)

        # Special cases with \laorepeatbefore{} immediately to the left
        if prev_is_repeatbefore and next_is_punct:
            cmd = "\\ellall{}"
            out.append(cmd)
            i += 1
            continue
        if prev_is_repeatbefore and has_next and not next_is_punct:
            # keep explicit order: \laorepeatbefore{}\ellipsis{}
            out.append("\\ellipsis{}")
            i += 1
            continue

        # General selection
        if not has_next:
            cmd = "\\ellbefore{}"
        elif prev_is_punct and next_is_punct:
            cmd = "\\ellall{}"
        elif prev_is_punct:
            cmd = "\\ellafter{}"
        elif next_is_punct:
            cmd = "\\ellbefore{}"
        else:
            cmd = "\\ellipsis{}"

        out.append(cmd)
        i += 1

    return "".join(out)

def get_ellipsis_command(prev_is_punct: bool, next_is_punct: bool, has_next: bool = True) -> str:
    """
    Selector for ellipsis variant when neighbors are already classified.

    Args:
        prev_is_punct: True if previous neighbor is punctuation
        next_is_punct: True if next neighbor is punctuation
        has_next:      False at paragraph/section end (default True)

    Returns:
        One of: \\ellipsis{}, \\ellafter{}, \\ellbefore{}, \\ellall{}
    """
    if not has_next:
        return "\\ellbefore{}"
    if prev_is_punct and next_is_punct:
        return "\\ellall{}"
    if prev_is_punct:
        return "\\ellafter{}"
    if next_is_punct:
        return "\\ellbefore{}"
    return "\\ellipsis{}"

# ============================================================================
# SPACE CONVERSION
# ============================================================================

def convert_flex_rigid_spaces(text: str) -> str:
    """
    Convert flex/rigid space markers to LaTeX commands.
    
    Source: Module 2 - Replaces \s and \S conversion in restore_protected_commands()
    
    Purpose:
        Transforms simple space markers into semantic LaTeX space commands.
    
    Issue Solved:
        Provides fine-grained control over spacing behavior in typeset output.
    
    Args:
        text: Input text with \\s and \\S markers
        
    Returns:
        Text with converted space commands
        
    Example:
        "word\\s word" → "word\\fs{} word"
        "word\\S word" → "word\\rs{} word"
    """
    text = re.sub(r'\\s(?![A-Za-z])', r'\\fs{}', text)
    text = re.sub(r'\\S(?![A-Za-z])', r'\\rs{}', text)
    return text

def load_compound_phrases_list() -> List[str]:
    """
    Load multi-word phrases for Module 1 to join with \\cs{}.

    Source file (UTF-8, optional):
        assets/dictionaries/compound_phrases.txt

    Each non-empty line may be:
        <left phrase> | <ignored right/template> [ % comment]
      or
        <left phrase>                         [ % comment]

    We only use the LEFT side to identify phrases in raw text. Internal
    whitespace is normalized to single spaces for matching.

    Returns:
        List of phrases (with spaces) sorted longest-first (by token count).
    """
    phrases: List[str] = []
    try:
        script_dir = Path(__file__).parent
        fp = (script_dir / ".." / ".." / ".." / ".."
              / "assets" / "dictionaries" / "compound_phrases.txt")

        if not fp.exists():
            return phrases

        with open(fp, "r", encoding="utf-8") as fh:
            for line_num, raw in enumerate(fh, 1):
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                
                # Debug: Check what we're reading for lines with our target text
                if "ເອຊະຣາ" in line and "ຮານລ໌" in line:
                    print(f"DEBUG: Line {line_num} raw: {repr(raw.strip())}")
                    print(f"DEBUG: Looking for pipe: {'|' in line}")
                
                # Strip trailing comment first
                if "%" in line:
                    line = line.split("%", 1)[0].rstrip()
                
                # Split on pipe character - try different variants
                left = None
                if "|" in line:
                    left = line.split("|", 1)[0].strip()
                elif "｜" in line:  # Full-width pipe (U+FF5C)
                    left = line.split("｜", 1)[0].strip()
                elif "│" in line:  # Box drawing character (U+2502)
                    left = line.split("│", 1)[0].strip()
                else:
                    # No pipe found - check if the line has the pattern we expect
                    # If it contains both regular spaces and ~S~, it's likely missing the pipe
                    if " " in line and "~S~" in line:
                        # Try to extract just the Lao part (before the ~S~ pattern)
                        parts = line.split()
                        lao_parts = []
                        for part in parts:
                            if "~S~" in part:
                                break
                            lao_parts.append(part)
                        if lao_parts:
                            left = " ".join(lao_parts)
                    else:
                        # No pipe and no pattern, use the whole line
                        left = line.strip()
                
                # Normalize internal whitespace
                if left:
                    left = re.sub(r"\s+", " ", left)
                    
                    # Debug for our target phrase
                    if "ເອຊະຣາ" in left and "ຮານລ໌" in left:
                        print(f"DEBUG: Extracted left side: '{left}'")
                    
                    # Only add if it has multiple words
                    if " " in left:
                        phrases.append(left)

        # Deduplicate and prefer longer phrases first (more tokens -> earlier)
        phrases = sorted(set(phrases), key=lambda s: (-len(s.split()), s))
        
        # Final debug: check if our target is in the final list
        target = "ເອຊະຣາ ຮານລ໌ ຈີເລັດ"
        if target in phrases:
            print(f"DEBUG: SUCCESS - Target phrase '{target}' is in final phrases list")
        
        return phrases
    except Exception as e:
        # Fail-soft: if anything goes wrong, return empty list (no joins applied)
        print(f"WARNING: Failed to load compound phrases: {e}")
        return []

def apply_compound_cs_joins(text: str, phrases: List[str]) -> str:
    """
    Replace the internal spaces of known multi-word phrases with \\cs{}.

    Production intent:
        • Join only the spaces *inside* phrases listed in `phrases`.
        • Do not add penalties here; Module 2 will handle penalties and \\lw{} wrapping.
        • Allow phrases to be adjacent to Lao letters or punctuation (no word-boundary guards).
        • Do not cross line breaks when matching (only spaces/tabs are considered gaps).

    Examples:
        "...ໄປຊັງ ຫຼຸກສ໌..."   →  "...ໄປຊັງ\\cs{}ຫຼຸກສ໌..."
        "...ທີ່ຊັງ ແອນເຈໂລ..." →  "...ທີ່ຊັງ\\cs{}ແອນເຈໂລ..."

    Args:
        text:     Source text potentially containing multi-word phrases.
        phrases:  Phrases with normal spaces (longest-first preferred).

    Returns:
        The input text with matched phrases joined using \\cs{} in place of
        each inter-token space/tab run.
    """
    if not text or not phrases:
        return text

    result_text = text
    # Gaps inside a phrase may be one-or-more spaces or tabs (not newlines).
    gap_pattern = r"[ \t]+"
    
    # Debug: Check if the target phrase is in the phrases list
    target_phrase = "ເອຊະຣາ ຮານລ໌ ຈີເລັດ"
    if target_phrase in phrases:
        print(f"DEBUG: Target phrase '{target_phrase}' found in phrases list")
    else:
        print(f"DEBUG: Target phrase '{target_phrase}' NOT in phrases list")
        # Show what we have that's similar
        for p in phrases:
            if "ເອຊະຣາ" in p or "ຮານລ໌" in p or "ຈີເລັດ" in p:
                print(f"  Found similar: '{p}'")
    
    # Debug: Check if the target phrase exists in the text
    if target_phrase in text:
        print(f"DEBUG: Target phrase found in text at position {text.index(target_phrase)}")
    else:
        print(f"DEBUG: Target phrase NOT found in text (might have different spacing)")

    for phrase in phrases:
        tokens = phrase.split(" ")
        if len(tokens) < 2:
            continue

        # Build a flexible regex for the phrase: token1 <gap> token2 (<gap> tokenN)...
        core_tokens_regex = gap_pattern.join(re.escape(tok) for tok in tokens)
        phrase_regex = re.compile(core_tokens_regex, flags=re.UNICODE)
        
        # Debug: Check for matches
        matches = list(phrase_regex.finditer(result_text))
        if matches and "ເອຊະຣາ" in phrase:
            print(f"DEBUG: Found {len(matches)} matches for phrase '{phrase}'")
            for m in matches:
                print(f"  Match: '{m.group(0)}' at position {m.start()}-{m.end()}")

        def replace_internal_gaps(match: re.Match) -> str:
            matched_text = match.group(0)
            # Debug output for our target phrase
            if "ເອຊະຣາ" in matched_text and "ຮານລ໌" in matched_text:
                print(f"DEBUG: Replacing gaps in '{matched_text}'")
            # Collapse every inter-token gap to a single \cs{}
            result = re.sub(gap_pattern, r"\\cs{}", matched_text)
            if "ເອຊະຣາ" in matched_text and "ຮານລ໌" in matched_text:
                print(f"DEBUG: Result: '{result}'")
            return result

        result_text = phrase_regex.sub(replace_internal_gaps, result_text)

    return result_text

def convert_ascii_spaces_to_spacecmd_with_protections(text: str) -> str:
    """
    Convert all remaining ASCII spaces (U+0020) to \\space{} *except* inside
    protected regions.

    Protected regions (left untouched):
      1) Math mode
         • Inline: $...$, \\(...\\)
         • Display: $$...$$, \\[...\\]
         • Math environments (and their contents): math, displaymath,
           equation, align, gather, multline, flalign, eqnarray, split
           (and anything nested within).
      2) Code / literal text
         • Environments: verbatim, Verbatim, lstlisting, minted, alltt
         • Inline: \\verb<delim>...<delim>, \\lstinline (|...| or {...}),
           \\mintinline[...]{lang}{...}
      3) URL-like inline macros
         • \\url{...}, \\path{...} (entire brace content is protected)
         • \\href{url}{text}: protect only the FIRST brace argument
           (the URL), not link text.

    Not protected (converted as normal):
      • Macro arguments for prose: \\section{...}, \\chapter{...},
        \\laochapter{...}, \\source{...}, \\footnote{...}, blockquote
        environments (once in TeX), and ordinary paragraph text.
      • Spaces immediately after control words are converted too; there
        is no “special gap” to keep.
      • \\cs{} (compound joiner) and other spacing commands are preserved
        as-is (they contain no ASCII spaces).

    Notes:
      • This helper runs LAST in Module 1, after punctuation/repeat/
        ellipsis processing and compound joins.
      • Lists are currently out of scope; if list environments are
        introduced later (itemize/enumerate/etc.), revisit whether any
        part of them should be treated as literal.
        TODO: If Module 3 adds list environments, reassess whether their
        contents require protection.

    Args:
        text: TeX-form text where any remaining ASCII spaces should be
          made explicit.

    Returns:
        Text with all non-protected ASCII spaces replaced by \\space{}.
    """
    if not text:
        return text

    n = len(text)
    protected_spans = []  # list[(start, end)] half-open indices

    def add_spans_from_pattern(pattern: str, flags: int = 0) -> None:
        for m in re.finditer(pattern, text, flags):
            protected_spans.append((m.start(), m.end()))

    # --- 1) Math mode protections ---

    # 1a) $$ ... $$  (ignore escaped dollars; no DOTALL to avoid overreach)
    add_spans_from_pattern(
        r"(?<!\\)\$\$(?:\\.|[^$])*?(?<!\\)\$\$"
    )

    # 1b) Inline $ ... $ (single dollars; exclude $$ and escaped \$)
    add_spans_from_pattern(
        r"(?<![\\$])\$(?!\$)(?:[^$\n\\]|\\.)*?(?<![\\$])\$(?!\$)"
    )

    # 1c) \( ... \) and \[ ... \] with escape-aware inner scanning
    add_spans_from_pattern(r"\\\((?:\\.|[^\\])*?\\\)")
    add_spans_from_pattern(r"\\\[(?:\\.|[^\\])*?\\\]")

    # 1d) Common math environments
    math_envs = [
        "math", "displaymath", "equation", "align", "gather",
        "multline", "flalign", "eqnarray", "split",
    ]
    math_union = "|".join(math_envs)
    add_spans_from_pattern(
        rf"\\begin\{{({math_union})\}}(?:.|\n)*?\\end\{{\1\}}",
        flags=re.DOTALL,
    )

    # --- 2) Code / literal protections ---

    # 2a) Verbatim-like environments
    code_envs = ["verbatim", "Verbatim", "lstlisting", "minted", "alltt"]
    code_union = "|".join(code_envs)
    add_spans_from_pattern(
        rf"\\begin\{{({code_union})\}}(?:.|\n)*?\\end\{{\1\}}",
        flags=re.DOTALL,
    )

    # 2b) \verb<d>...<d>  (single line)
    add_spans_from_pattern(r"\\verb\*?(?P<d>.)(?P<c>[^\\\n]*?)(?P=d)")

    # 2c) \lstinline delimiter form, optional [..] options
    add_spans_from_pattern(
        r"\\lstinline(?:\[[^\]]*\])?(?P<d>[^A-Za-z0-9\s])(?P<c>[^\\\n]*?)(?P=d)"
    )

    # 2d) \lstinline brace form
    add_spans_from_pattern(r"\\lstinline(?:\[[^\]]*\])?\{[^}\n]*\}")

    # 2e) \mintinline[opts]{lang}{content}
    add_spans_from_pattern(r"\\mintinline(?:\[[^\]]*\])?\{[^}]*\}\{[^}]*\}")

    # --- 3) URL-like macros ---

    # 3a) \url{...} and \path{...}
    add_spans_from_pattern(r"\\(?:url|path)\{[^}]*\}")

    # 3b) {\refdigits ...} for slightly scaled english numbers
    add_spans_from_pattern(r"\{\\refdigits [0-9.]*\}")
    
    # 3c) {\smallerscale ...} for slightly downscaled english text
    add_spans_from_pattern(r"\{\\smallerscale [0-9A-z]*\}")

    # 3b) \href{url}{text}: protect only the first {url}
    for m in re.finditer(r"\\href\{[^}]*\}\{", text):
        start = text.find("{", m.start())
        if start != -1 and start < m.end():
            end = text.find("}", start + 1)
            if end != -1:
                protected_spans.append((start, end + 1))

    # Merge overlaps
    if not protected_spans:
        return text.replace(" ", "\\textspace{}")

    protected_spans.sort()
    merged = []
    cur_s, cur_e = protected_spans[0]
    for s, e in protected_spans[1:]:
        if s <= cur_e:
            cur_e = max(cur_e, e)
        else:
            merged.append((cur_s, cur_e))
            cur_s, cur_e = s, e
    merged.append((cur_s, cur_e))
    protected_spans = merged

    # Replace outside protected spans
    pieces = []
    i = 0
    for s, e in protected_spans:
        if i < s:
            pieces.append(text[i:s].replace(" ", "\\space{}"))
        pieces.append(text[s:e])  # protected slice
        i = e
    if i < n:
        pieces.append(text[i:].replace(" ", "\\space{}"))

    return "".join(pieces)


# ============================================================================
# SPACE NORMALIZATION
# ============================================================================

def normalize_spacing_commands(text: str) -> str:
    """
    Normalize spacing commands to be self-terminating.
    
    Source: Module 1 - Replaces normalize_nonbreaking_commands()
    
    Purpose:
        Ensures all spacing commands use consistent {} termination and
        have no spurious spaces around them.
    
    Issue Solved:
        Prevents LaTeX parsing errors and ensures consistent rendering
        of spacing commands.
    
    Args:
        text: Input text with spacing commands
        
    Returns:
        Text with normalized spacing commands
        
    Example:
        "word \\nbsp word" → "word\\nbsp{}word"
    """
    # Upgrade bare commands to brace form
    text = re.sub(r'\\(nbsp|scrspace)(?!\s*\{)', r'\\\1{}', text)
    
    # Collapse surrounding spaces
    text = re.sub(r'\s*\\(nbsp|scrspace)\{\}\s*', r'\\\1{}', text)
    
    # Prevent duplication
    text = re.sub(r'(\\(?:nbsp|scrspace)\{\})(?:\s*)(\\(?:nbsp|scrspace)\{\})', r'\1', text)
    
    return text


# ============================================================================
# MAIN PROCESSING FUNCTIONS
# ============================================================================

def process_all_spacing_and_punctuation(text: str) -> str:
    """
    Apply all spacing and punctuation conversions for Module 1.
    
    Source: NEW - Main entry point for Module 1
    
    Purpose:
        Main entry point for Module 1 to process all spacing and punctuation
        in the correct order.
    
    Issue Solved:
        Centralizes all spacing/punctuation logic to ensure consistent
        processing across the pipeline.
    
    Args:
        text: Input markdown text
        
    Returns:
        Text with all spacing and punctuation conversions applied
    """
    # 1. Bible reference processing
    text = protect_scripture_references(text) 

    # 2. EGW reference processing
    text = convert_egw_references(text)

    text = convert_text_references(text)
    
    # 3. Special character handling
    text = handle_lao_repetition_with_context(text)
    text = handle_ellipsis_with_context(text)
    
    # 4. Space marker conversion
    text = convert_flex_rigid_spaces(text)

    # 5. Join multi-word compounds with \cs{}
    phrases = load_compound_phrases_list()
    if phrases:
        text = apply_compound_cs_joins(text, phrases)    

    # 6. Convert ASCII spaces to \space{}
    text = convert_ascii_spaces_to_spacecmd_with_protections(text)

    # 6. Final normalization
    text = normalize_spacing_commands(text)
    
    return text
