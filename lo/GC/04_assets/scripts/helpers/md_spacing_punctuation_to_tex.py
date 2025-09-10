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

def load_bible_data() -> Tuple[List[str], List[str], Dict[str, str], Optional[re.Pattern]]:
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
        1. Move bible_books.json to within the package and call with 
           "importlib.resources.files(...)"
        2. 
    """
    try:
        script_dir = Path(__file__).parent
        json_path = (
            script_dir
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

        numbered_mapping = {}
        for book in data["books"]:
            if book.get("numbered", False):
                nbsp_form = book["lao_name"].replace(" ", "\\nbsp{}", 1)
                numbered_mapping[book["lao_name"]] = nbsp_form

        reference_pattern = re.compile(
            r"\d+:\d+(?:[,-]\d+)*(?:\s*[,-]\s*\d+(?::\d+)?)*"
        )

        return all_books, numbered_books, numbered_mapping, reference_pattern

    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        print(f"Warning: Could not load Bible books: {e}")
        return [], [], {}, None


# ============================================================================
# BIBLE REFERENCE PROCESSING
# ============================================================================

def protect_numbered_bible_books(text: str) -> str:
    """
    Convert spaces in numbered Bible book names to non-breaking spaces.
    
    Source: Module 1 - Replaces protect_numbered_bible_books()
    
    Purpose:
        Ensures numbered Bible books (like "1 ຊາມູເອນ") stay together on one line.
    
    Issue Solved:
        Prevents awkward line breaks between number and book name in Bible references.
    
    Args:
        text: Input text containing Bible book names
        
    Returns:
        Text with protected Bible book names
        
    Example:
        "1 ຊາມູເອນ 3:16" → "1\\nbsp{}ຊາມູເອນ 3:16"
    """
    _, numbered_books, _, _ = load_bible_data()
    if not numbered_books:
        return text
    
    protected_text = text
    for book in numbered_books:
        protected_book = book.replace(" ", "\\nbsp{}", 1)
        protected_text = protected_text.replace(book, protected_book)
    
    return protected_text


def add_scripture_spacing(text: str) -> str:
    """
    Add scripture spacing between Bible book names and verse references.
    
    Source: Module 1 - Replaces protect_scripture_spacing()
    
    Purpose:
        Provides controlled spacing between Bible book names and chapter:verse references.
    
    Issue Solved:
        Allows proper line breaking between book name and reference while keeping
        the reference components together.
    
    Args:
        text: Input text with Bible references
        
    Returns:
        Text with \\scrspace{} inserted
        
    Example:
        "ໂຢຮັນ 3:16" → "ໂຢຮັນ\\scrspace{}3:16"
    """
    all_books, _, numbered_mapping, reference_pattern = load_bible_data()
    if not all_books or not reference_pattern:
        return text
    
    protected_text = text
    for book in all_books:
        book_forms = [book]
        if book in numbered_mapping:
            book_forms.append(numbered_mapping[book])
        
        for book_form in book_forms:
            pattern = rf'({re.escape(book_form)})\s+({reference_pattern.pattern})'
            protected_text = re.sub(pattern, rf'\1\\scrspace{{}}\2', protected_text)
    
    return protected_text


def split_reference_components(reference_text: str) -> Tuple[List[str], List[str]]:
    """
    Split scripture reference into components and separators.
    
    Source: Module 1 - Replaces split_reference_components()
    
    Purpose:
        Parses complex scripture references for individual processing.
    
    Issue Solved:
        Handles multi-part references like "3:16,18-20" by breaking them
        into manageable components.
    
    Args:
        reference_text: Scripture reference string
        
    Returns:
        Tuple of (components, separators)
    """
    parts = re.split(r'([,;])', reference_text)
    components = []
    separators = []
    
    for part in parts:
        part = part.strip()
        if not part:
            continue
        elif part in [',', ';']:
            separators.append(part)
        else:
            components.append(part)
    
    return components, separators


def format_reference_components(components: List[str], separators: List[str]) -> str:
    """
    Format scripture reference components with proper LaTeX markup.
    
    Source: Module 1 - Replaces format_reference_components()
    
    Purpose:
        Wraps individual scripture references in \\scrref{} commands.
    
    Issue Solved:
        Ensures each reference component can be styled independently in LaTeX.
    
    Args:
        components: List of reference components
        separators: List of separator characters
        
    Returns:
        Formatted reference string
    """
    formatted_parts = []
    
    for i, component in enumerate(components):
        formatted_parts.append(f'\\scrref{{{component}}}')
        
        if i < len(separators):
            separator = separators[i]
            formatted_parts.append(f'{separator}\\scrspace{{}}')
    
    return ''.join(formatted_parts)


def wrap_scripture_references(text: str) -> str:
    """
    Wrap scripture reference components with \\scrref{} commands.
    
    Source: Module 1 - Replaces protect_scripture_references()
    
    Purpose:
        Identifies and wraps scripture references that follow \\scrspace markers.
    
    Issue Solved:
        Provides semantic markup for scripture references to enable proper
        formatting and indexing in LaTeX.
    
    Args:
        text: Input text with \\scrspace markers
        
    Returns:
        Text with wrapped scripture references
        
    Example:
        "\\scrspace{}3:16,18" → "\\scrspace{}\\scrref{3:16},\\scrspace{}\\scrref{18}"
    """
    pattern = r'\\scrspace\s+(\d+:\d+(?:[,–-]\d+)*(?:\s*[,;]\s*\d+(?::\d+)?(?:[,–-]\d+)*)*)(?=\s|[\.;,)\'"'""'‚„‹›«»@#%]|$)'
    
    matches = list(re.finditer(pattern, text))
    
    for match in reversed(matches):
        reference_content = match.group(1).strip()
        components, separators = split_reference_components(reference_content)
        formatted = format_reference_components(components, separators)
        replacement = f'\\scrspace{{{formatted}}}'
        text = text[:match.start()] + replacement + text[match.end():]
    
    return text


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
    return re.sub(egw_pattern, r'\\egw{\1\\nbsp{}\2}', text)


# ============================================================================
# PUNCTUATION DETECTION
# ============================================================================

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
    return char in '.,;:!?()[]{}"\'\'-—–""''‚„‹›«»@#%'


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
    return char in '"\'[{(""'‚„‹«'


def is_closing_punctuation(char: str) -> bool:
    """
    Check if character is closing punctuation.
    
    Source: Module 2 - Replaces is_closing_punctuation()
    
    Purpose:
        Identifies closing punctuation that should not be separated from preceding text.
    
    Issue Solved:
        Closing punctuation/quotes should stay with the text they follow.
    
    Args:
        char: Single character to check
        
    Returns:
        True if character is closing punctuation
    """
    return char in '.,;:!?()[]{}"\'\'-—–"'‚„›»@#%'


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
# SPECIAL CHARACTER HANDLING
# ============================================================================

def handle_ellipsis_with_context(text: str) -> str:
    """
    Convert ellipsis to context-aware LaTeX commands.
    
    Source: Module 2 - Replaces basic ellipsis handling
    
    Purpose:
        Provides proper spacing around ellipsis based on surrounding punctuation.
    
    Issue Solved:
        Prevents awkward spacing when ellipsis appears near other punctuation.
    
    Args:
        text: Input text with ellipsis characters
        
    Returns:
        Text with context-aware ellipsis commands
    """
    # This will be called by Module 2 with more context
    # For Module 1, we do basic conversion
    return text.replace('…', '\\ellipsis{}')


def get_ellipsis_command(prev_is_punct: bool, next_is_punct: bool) -> str:
    """
    Determine appropriate ellipsis command based on context.
    
    Source: Module 2 - Replaces handle_ellipsis_context()
    
    Purpose:
        Selects the correct ellipsis variant based on surrounding punctuation.
    
    Issue Solved:
        Ensures proper spacing when ellipsis appears adjacent to punctuation.
    
    Args:
        prev_is_punct: Whether previous character is punctuation
        next_is_punct: Whether next character is punctuation
        
    Returns:
        Appropriate ellipsis command
    """
    if prev_is_punct:
        return "\\ellafter{}"
    elif next_is_punct:
        return "\\ellbefore{}"
    else:
        return "\\ellipsis{}"


def handle_lao_repetition_with_context(text: str) -> str:
    """
    Convert Lao repetition marks to LaTeX commands.
    
    Source: Module 2 - Replaces basic Lao repetition handling
    
    Purpose:
        Handles the Lao repetition character (ໆ) with proper spacing.
    
    Issue Solved:
        Ensures repetition marks have appropriate spacing based on context.
    
    Args:
        text: Input text with Lao repetition marks
        
    Returns:
        Text with converted repetition marks
    """
    # Basic conversion for Module 1
    return text.replace('ໆ', '\\laorepeat{}')


def get_lao_repetition_command(next_is_punct: bool) -> str:
    """
    Determine appropriate Lao repetition command based on context.
    
    Source: Module 2 - Replaces handle_lao_repetition_context()
    
    Purpose:
        Selects correct repetition command variant based on following character.
    
    Issue Solved:
        Prevents spacing issues when repetition mark appears before punctuation.
    
    Args:
        next_is_punct: Whether next character is punctuation
        
    Returns:
        Appropriate repetition command
    """
    if next_is_punct:
        return "\\laorepeatbefore{}"
    else:
        return "\\laorepeat{}"


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


def convert_compound_spaces(text: str) -> str:
    """
    Convert dictionary compound space markers to LaTeX commands.
    
    Source: Module 2 - Replaces ~S~ conversion in convert_break_points()
    
    Purpose:
        Handles special compound space markers from dictionary processing.
    
    Issue Solved:
        Preserves compound word boundaries that should not be broken.
    
    Args:
        text: Input text with ~S~ markers
        
    Returns:
        Text with converted compound space commands
        
    Example:
        "ການ~S~ສຶກສາ" → "ການ\\cs{}ສຶກສາ"
    """
    return re.sub(r'~S~', r'\\cs{}', text)


def convert_original_spaces_to_latex(text: str) -> str:
    """
    Convert original spaces to \\space{} commands.
    
    Source: Module 2 - Replaces space conversion in process_text_groups()
    
    Purpose:
        Preserves original spacing intent in LaTeX output.
    
    Issue Solved:
        Maintains deliberate spacing from source text that might otherwise
        be normalized by LaTeX.
    
    Args:
        text: Input text with regular spaces
        
    Returns:
        Text with spaces converted to \\space{}
        
    Note:
        This is called selectively by Module 2 for Lao text segments.
    """
    # Simple space replacement for continuous Lao text
    # Module 2 will handle the context-aware application
    return re.sub(r' ', r'\\space{}', text)


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
# PUNCTUATION PROTECTION
# ============================================================================

def apply_punctuation_protection(parts: List[str]) -> List[str]:
    """
    Apply \\nobreak{} protection around punctuation.
    
    Source: Module 2 - Replaces apply_punctuation_protection()
    
    Purpose:
        Prevents line breaks between Lao words and adjacent punctuation.
    
    Issue Solved:
        Stops punctuation from being orphaned on the next line or
        separated from quoted text.
    
    Args:
        parts: List of text parts to process
        
    Returns:
        List with \\nobreak{} commands inserted
        
    Example:
        ["\\lw{word}", "."] → ["\\lw{word}", "\\nobreak{}", "."]
    """
    if len(parts) <= 1:
        return parts
    
    protected_parts = []
    
    for i, part in enumerate(parts):
        protected_parts.append(part)
        
        if i < len(parts) - 1:
            current_part = part
            next_part = parts[i + 1]
            
            # Add \nobreak before closing punctuation
            if (needs_nobreak_protection(current_part) and 
                len(next_part) > 0 and 
                is_closing_punctuation(next_part[0])):
                protected_parts.append('\\nobreak{}')
            
            # Add \nobreak after opening punctuation
            elif (len(current_part) > 0 and 
                  is_opening_punctuation(current_part[-1]) and
                  needs_nobreak_protection(next_part)):
                protected_parts.append('\\nobreak{}')
    
    return protected_parts


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
    text = protect_numbered_bible_books(text)
    text = add_scripture_spacing(text)
    text = wrap_scripture_references(text)
    
    # 2. EGW reference processing
    text = convert_egw_references(text)
    
    # 3. Special character handling
    text = handle_ellipsis_with_context(text)
    text = handle_lao_repetition_with_context(text)
    
    # 4. Space marker conversion
    text = convert_flex_rigid_spaces(text)
    text = convert_compound_spaces(text)
    
    # 5. Final normalization
    text = normalize_spacing_commands(text)
    
    return text


def process_module2_spacing(text_parts: List[Tuple[str, str]], 
                           dictionary_terms: Set[str] = None) -> List[str]:
    """
    Process spacing for Module 2's dictionary-processed text.
    
    Source: NEW - Helper function for Module 2
    
    Purpose:
        Handles context-aware spacing and punctuation for Module 2's
        Lao text processing.
    
    Issue Solved:
        Provides proper spacing for dictionary-segmented Lao text while
        preserving linguistic boundaries.
    
    Args:
        text_parts: List of (type, content) tuples from Module 2
        dictionary_terms: Set of dictionary terms for validation
        
    Returns:
        List of processed text parts with spacing/punctuation applied
    """
    # This function will be called by Module 2 after dictionary processing
    # Implementation will depend on Module 2's specific needs
    processed = []
    
    for i, (part_type, content) in enumerate(text_parts):
        if part_type == 'space':
            processed.append('\\space{}')
        elif part_type == 'ellipsis':
            # Check context
            prev_is_punct = i > 0 and text_parts[i-1][0] == 'punctuation'
            next_is_punct = i < len(text_parts)-1 and text_parts[i+1][0] == 'punctuation'
            processed.append(get_ellipsis_command(prev_is_punct, next_is_punct))
        elif part_type == 'lao_repetition':
            # Check following context
            next_is_punct = i < len(text_parts)-1 and text_parts[i+1][0] == 'punctuation'
            processed.append(get_lao_repetition_command(next_is_punct))
        else:
            processed.append(content)
    
    # Apply punctuation protection
    return apply_punctuation_protection(processed)
