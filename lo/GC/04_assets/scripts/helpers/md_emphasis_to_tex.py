r"""
md_emphasis_to_tex.py
---------------------

Purpose:
    Convert Markdown emphasis (bold, italic, underline, 
    strikethrough) to LaTeX commands.
    
Responsibilities:
    • Convert **text** and __text__ to \textbf{text}
    • Convert *text* and _text_ to \emph{text}
    • Convert ***text*** to \textbf{\emph{text}}
    • Convert ~~text~~ to \sout{text} (requires ulem)
    • Convert ++text++ to \uline{text} (requires ulem)
    • Handle nested emphasis correctly
    • Preserve escaped asterisks and underscores
    • Warn about unmatched markers

Pattern Priority:
    Process from longest to shortest to avoid mis-parsing:
    1. Bold+italic (*** or ___) 
    2. Strikethrough (~~)
    3. Underline (++)
    4. Bold (** or __)
    5. Italic (* or _)
"""

import re
import logging
from typing import Tuple, Dict, List

logger = logging.getLogger(__name__)


def protect_escaped_chars(text: str) -> Tuple[str, Dict[str, str]]:
    """
    Replace escaped special characters with placeholders.
    
    Args:
        text: Text with escaped characters like \* \_ \~ \+
        
    Returns:
        Tuple of:
        - Text with placeholders
        - Dictionary mapping placeholders to original escaped chars
    """
    protected = {}
    counter = 0
    
    # Pattern for escaped emphasis characters
    escaped_pattern = r'\\([*_~+])'
    
    def make_placeholder(match):
        nonlocal counter
        escaped_char = match.group(0)  # e.g., '\*'
        placeholder = f"〈ESCAPED_{counter}〉"
        protected[placeholder] = escaped_char
        counter += 1
        return placeholder
    
    text = re.sub(escaped_pattern, make_placeholder, text)
    
    return text, protected


def restore_escaped_chars(text: str, 
                         protected: Dict[str, str]) -> str:
    """
    Restore escaped characters from placeholders.
    
    Args:
        text: Text with placeholders
        protected: Dictionary mapping placeholders to escaped chars
        
    Returns:
        Text with escaped characters restored
    """
    for placeholder, original in protected.items():
        text = text.replace(placeholder, original)
    return text


def check_unmatched_markers(text: str) -> List[str]:
    """
    Check for unmatched emphasis markers.
    
    Args:
        text: Text to check (after escapes are protected)
        
    Returns:
        List of warning messages for unmatched markers
    """
    warnings = []
    
    # Check for odd number of markers
    # (Simple check - could be enhanced)
    
    # Triple markers
    triple_stars = len(re.findall(r'\*\*\*', text))
    if triple_stars % 2 != 0:
        warnings.append(
            f"Unmatched *** markers (found {triple_stars})"
        )
    
    # After removing triples, check doubles
    text_no_triple = re.sub(r'\*\*\*', '', text)
    double_stars = len(re.findall(r'\*\*', text_no_triple))
    if double_stars % 2 != 0:
        warnings.append(
            f"Unmatched ** markers (found {double_stars})"
        )
    
    # After removing doubles, check singles
    text_no_double = re.sub(r'\*\*', '', text_no_triple)
    single_stars = len(re.findall(r'\*', text_no_double))
    if single_stars % 2 != 0:
        warnings.append(
            f"Unmatched * markers (found {single_stars})"
        )
    
    # Check tildes
    tildes = len(re.findall(r'~~', text))
    if tildes % 2 != 0:
        warnings.append(
            f"Unmatched ~~ markers (found {tildes})"
        )
    
    # Check plus signs
    plusses = len(re.findall(r'\+\+', text))
    if plusses % 2 != 0:
        warnings.append(
            f"Unmatched ++ markers (found {plusses})"
        )
    
    return warnings


def process_emphasis(text: str) -> Tuple[str, Dict[str, int]]:
    """
    Convert Markdown emphasis markers to LaTeX commands.
    
    Args:
        text: Markdown text with emphasis markers
        
    Returns:
        Tuple of:
        - Processed text with LaTeX commands
        - Statistics dict with conversion counts
    """
    stats = {
        'bold_italic': 0,
        'bold': 0,
        'italic': 0,
        'strikethrough': 0,
        'underline': 0,
        'warnings': []
    }
    
    # Step 1: Protect escaped characters
    text, protected = protect_escaped_chars(text)
    
    # Step 2: Check for unmatched markers
    warnings = check_unmatched_markers(text)
    if warnings:
        stats['warnings'] = warnings
        for warning in warnings:
            logger.warning(warning)
            # Add ugly marker to force manual fix
            text = f"⚠️UNMATCHED_EMPHASIS⚠️\n{text}"
    
    # Step 3: Process emphasis (existing conversions)
    text, count = convert_bold_italic(text)
    stats['bold_italic'] = count
    
    text, count = convert_strikethrough(text)
    stats['strikethrough'] = count
    
    text, count = convert_underline(text)
    stats['underline'] = count
    
    text, count = convert_bold(text)
    stats['bold'] = count
    
    text, count = convert_italic(text)
    stats['italic'] = count
    
    # Step 4: Restore escaped characters
    text = restore_escaped_chars(text, protected)
    
    return text, stats


def convert_bold_italic(text: str) -> Tuple[str, int]:
    """
    Convert ***text*** or ___text___ to 
    \\textbf{\\emph{text}}.
    """
    count = 0
    
    # Pattern for ***text*** (non-greedy)
    pattern = r'\*\*\*([^*]+?)\*\*\*'
    
    def replace_bold_italic(match):
        nonlocal count
        count += 1
        content = match.group(1).strip()
        return f'\\textbf{{\\emph{{{content}}}}}'
    
    text = re.sub(pattern, replace_bold_italic, text)
    
    # Pattern for ___text___
    pattern = r'___([^_]+?)___'
    text = re.sub(pattern, replace_bold_italic, text)
    
    return text, count


def convert_bold(text: str) -> Tuple[str, int]:
    """Convert **text** or __text__ to \\textbf{text}."""
    count = 0
    
    # Pattern for **text** (non-greedy)
    pattern = r'\*\*([^*]+?)\*\*'
    
    def replace_bold(match):
        nonlocal count
        count += 1
        content = match.group(1).strip()
        return f'\\textbf{{{content}}}'
    
    text = re.sub(pattern, replace_bold, text)
    
    # Pattern for __text__
    pattern = r'__([^_]+?)__'
    text = re.sub(pattern, replace_bold, text)
    
    return text, count


def convert_italic(text: str) -> Tuple[str, int]:
    """Convert *text* or _text_ to \\emph{text}."""
    count = 0
    
    # Pattern for *text* (non-greedy, avoid */\* patterns)
    # Negative lookbehind/ahead to avoid escaped chars
    pattern = r'(?<![\\*])\*([^*]+?)\*(?![*])'
    
    def replace_italic(match):
        nonlocal count
        count += 1
        return f'\\emph{{{match.group(1)}}}'
    
    text = re.sub(pattern, replace_italic, text)
    
    # Pattern for _text_ (word boundaries help)
    pattern = r'\b_([^_]+?)_\b'
    text = re.sub(pattern, replace_italic, text)
    
    return text, count


def convert_strikethrough(text: str) -> Tuple[str, int]:
    """Convert ~~text~~ to \\sout{text}."""
    count = 0
    
    pattern = r'~~([^~]+?)~~'
    
    def replace_strikethrough(match):
        nonlocal count
        count += 1
        content = match.group(1).strip()
        return f'\\sout{{{content}}}'
    
    text = re.sub(pattern, replace_strikethrough, text)
    
    return text, count


def convert_underline(text: str) -> Tuple[str, int]:
    """Convert ++text++ to \\uline{text}."""
    count = 0
    
    pattern = r'\+\+([^+]+?)\+\+'
    
    def replace_underline(match):
        nonlocal count
        count += 1
        content = match.group(1).strip()
        return f'\\uline{{{content}}}'
    
    text = re.sub(pattern, replace_underline, text)
    
    return text, count
